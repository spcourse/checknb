"""Execute a student notebook and write the executed copy to disk.

This is the only part that runs student code. It shells out to `jupyter
nbconvert`, which is the same engine nbgrader uses, and enforces two
independent timeouts:

  cell_timeout   per cell, handled by nbconvert: the kernel is interrupted and
                 execution continues with a KeyboardInterrupt in that cell's
                 output. This is the one that catches infinite loops.
  total_timeout  wall clock for the whole run, handled here. A backstop for a
                 kernel that wedges so badly it stops honouring interrupts.
                 When it fires, nothing is written -- so keep it generous.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

DEFAULT_OUTPUT = "./.tmp.ipynb"


class ExecutionError(RuntimeError):
    """The notebook could not be executed at all (as opposed to failing tests)."""


def execute_notebook(
    notebook: str | Path,
    out_path: str | Path,
    cell_timeout: int = 30,
    total_timeout: int = 600,
) -> Path:
    """Run `notebook`, write the executed copy to `out_path`, return that path.

    Cell errors are *not* failures here -- they are the data we grade on, so
    `--allow-errors` keeps execution going and records them as cell outputs.
    """
    notebook = Path(notebook).resolve()
    out_path = Path(out_path).resolve()
    if not notebook.is_file():
        raise ExecutionError(f"no such notebook: {notebook}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # `sys.executable -m nbconvert`, never a bare "jupyter" off PATH. The kernel
    # nbconvert starts comes from the environment nbconvert itself runs in, so
    # PATH resolution decides which Python grades the notebook.
    #
    # `uvx` prepends its environment's bin to PATH and a bare "jupyter" happens to
    # work; `uv tool install` exposes only the `checknb` entry point, so the same
    # bare "jupyter" silently finds some *other* jupyter -- a conda base env, say --
    # and the notebook is graded against that interpreter's packages instead of the
    # ones installed alongside checknb. Going through sys.executable removes PATH
    # from the question entirely.
    cmd = [
        sys.executable,
        "-m",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        "--allow-errors",
        f"--ExecutePreprocessor.timeout={cell_timeout}",
        "--ExecutePreprocessor.interrupt_on_timeout=True",
        "--output",
        str(out_path),
        notebook.name,
    ]

    env = {
        **os.environ,
        "MPLBACKEND": "Agg",  # plt.show() must not block
        "PYDEVD_DISABLE_FILE_VALIDATION": "1",  # silence the debugger warning
        # The ipykernel wheel ships a kernelspec whose argv[0] is the bare string
        # "python", resolved through PATH when the kernel starts -- so PATH, not
        # sys.executable, decides which interpreter actually runs the notebook.
        # Putting our own bin directory first makes that "python" us.
        #
        # Without this the kernel is whatever `python` the shell finds (a conda
        # base env, typically). The notebook is then graded against that
        # interpreter's packages, so anything installed alongside checknb -- the
        # whole point of the `dp` extra -- is simply absent, and every test
        # reports "name 'test_N' is not defined".
        "PATH": os.pathsep.join(
            [str(Path(sys.executable).parent), os.environ.get("PATH", "")]
        ),
    }

    # cwd = the notebook's own directory, so relative paths like
    # pd.read_csv("products.csv") and `from tests import *` resolve.
    #
    # start_new_session puts nbconvert in its own process group. nbconvert
    # spawns the kernel as a child; killing only nbconvert would leave that
    # kernel running your student's infinite loop forever.
    proc = subprocess.Popen(
        cmd,
        cwd=notebook.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    try:
        output = proc.communicate(timeout=total_timeout)[0]
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        proc.communicate()
        raise ExecutionError(
            f"wall-clock timeout after {total_timeout}s -- no output written"
        ) from None

    if proc.returncode != 0:
        raise ExecutionError(f"nbconvert exited {proc.returncode}:\n{output}")
    if not out_path.is_file():
        raise ExecutionError(f"nbconvert exited 0 but wrote nothing to {out_path}")

    return out_path


def _kill_group(proc: subprocess.Popen) -> None:
    """SIGKILL the whole process group: nbconvert and the kernel it spawned."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()
