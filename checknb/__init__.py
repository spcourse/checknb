"""Run an nbgrader notebook and score its autograded test cells.

Three steps, one per module, usable separately:

    execute.execute_notebook   run the student's notebook via `jupyter nbconvert`
    score.score_notebook       read the executed copy, turn test cells into points
    report.pprint/render_json  present the results for a human or a program

The command-line front end lives in `cli` and is installed as `checknb`.
"""

from .execute import DEFAULT_OUTPUT, ExecutionError, execute_notebook
from .report import build_report, pprint, render_json, render_lines
from .score import (
    cell_duration,
    cell_error,
    cell_stdout,
    describe,
    find_timeouts,
    is_autograded_test,
    score_notebook,
)

__version__ = "0.1.2"

__all__ = [
    "DEFAULT_OUTPUT",
    "ExecutionError",
    "build_report",
    "cell_duration",
    "cell_error",
    "cell_stdout",
    "describe",
    "execute_notebook",
    "find_timeouts",
    "is_autograded_test",
    "pprint",
    "render_json",
    "render_lines",
    "score_notebook",
]
