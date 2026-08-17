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

    cmd = [
        "jupyter",
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
