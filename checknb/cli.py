"""Run an nbgrader notebook and report what its autograded test cells scored."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .execute import DEFAULT_OUTPUT, ExecutionError, execute_notebook
from .report import pprint, render_json
from .score import find_timeouts, score_notebook


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("notebook")
    p.add_argument(
        "-o",
        "--output",
        help="where to keep the executed notebook; without it a scratch copy "
        "is written and deleted again",
    )
    p.add_argument("--cell-timeout", type=int, default=3)
    p.add_argument("--total-timeout", type=int, default=600)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    # No -o means the executed notebook is ours, not the user's, so we clean it
    # up. With -o they asked for it by name and presumably want to read it.
    scratch = args.output is None
    output = DEFAULT_OUTPUT if scratch else args.output

    # The report is named after the submission, not after the executed copy --
    # that one is a temp file and every student's would be called ".tmp".
    name = Path(args.notebook).stem

    ## run notebook
    try:
        out = execute_notebook(
            args.notebook, output, args.cell_timeout, args.total_timeout
        )
    except ExecutionError as e:
        # stderr, so --json keeps stdout parseable even when the run fails
        print(f"error: {e}", file=sys.stderr)
        return 1

    # extract results
    try:
        results = score_notebook(out)
        timeouts = find_timeouts(out)
    finally:
        # finally, so a malformed notebook doesn't leave the scratch file behind
        if scratch:
            out.unlink(missing_ok=True)

    if args.json:
        print(render_json(results, name, timeouts))
    else:
        pprint(results, name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
