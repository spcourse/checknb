"""Turn an executed notebook into points.

Reads the notebook written by `execute_notebook` and scores the autograded test
cells -- the ones nbgrader marks `grade: true, solution: false`. Those are the
locked cells containing asserts; a cell that raised is wrong, a cell that did
not is right. All or nothing, exactly as nbgrader does it.

Manually graded cells (`grade: true, solution: true`) are deliberately ignored
here: no amount of running them tells you what they are worth.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def is_autograded_test(cell: dict) -> bool:
    """A locked test cell whose pass/fail we can decide by running it."""
    ng = cell.get("metadata", {}).get("nbgrader")
    if not ng:
        return False
    return bool(ng.get("grade")) and not ng.get("solution") and not ng.get("task")


def cell_error(cell: dict) -> dict | None:
    """The cell's error output, if it raised."""
    return next(
        (o for o in cell.get("outputs", []) if o.get("output_type") == "error"), None
    )


def cell_stdout(cell: dict, limit: int = 1000) -> str:
    """Everything the cell printed, stdout and stderr, truncated like checkpy."""
    # In the raw .ipynb JSON a multi-line "text" is a list of lines, not a
    # string. nbformat normalises that away; we read the file directly, so we
    # have to cope with both forms.
    chunks = []
    for out in cell.get("outputs", []):
        if out.get("output_type") != "stream":
            continue
        text = out.get("text", "")
        chunks.append(text if isinstance(text, str) else "".join(text))
    text = "".join(chunks)
    if limit and len(text) > limit:
        text = text[:limit] + "..."
    return text


def cell_duration(cell: dict) -> float | None:
    """How many seconds the cell took, or None if it was never timed.

    nbclient records four ISO-8601 timestamps per executed code cell under
    metadata.execution. The span from the kernel echoing the input to it
    sending the reply is the cell's wall time -- including time spent hanging
    before an interrupt, which is what makes a timeout measurable.
    """
    execution = cell.get("metadata", {}).get("execution", {})
    start = execution.get("iopub.execute_input")
    end = execution.get("shell.execute_reply")
    if not start or not end:
        return None
    span = datetime.fromisoformat(end.replace("Z", "+00:00")) - datetime.fromisoformat(
        start.replace("Z", "+00:00")
    )
    return round(span.total_seconds(), 3)


def find_timeouts(executed: str | Path) -> list[dict]:
    """Every cell the per-cell timeout interrupted, in document order.

    A timeout surfaces as a KeyboardInterrupt output, because nbconvert
    interrupts the kernel and carries on. This deliberately scans *all* cells
    rather than just the test cells: the cell that hangs is nearly always the
    student's answer cell, and the test below it then fails with a confusing
    "still None" assertion instead.
    """
    nb = json.loads(Path(executed).read_text())

    timeouts = []
    for index, cell in enumerate(nb["cells"]):
        error = cell_error(cell)
        if not error or error["ename"] != "KeyboardInterrupt":
            continue
        grade_id = cell.get("metadata", {}).get("nbgrader", {}).get("grade_id")
        timeouts.append(
            {
                "cell": index,
                "id": grade_id,
                "description": describe(grade_id) if grade_id else None,
                "duration": cell_duration(cell),
            }
        )
    return timeouts


def describe(grade_id: str) -> str:
    """Turn 'ex03_test' into 'Exercise 3', 'ex05_report' into 'Exercise 5 (report)'.

    nbgrader has no human-readable title for a cell, only the id, so this is a hack
    to get test names.
    """

    match = re.match(r"ex(\d+)_?(.*)", grade_id)
    if not match:
        return grade_id
    number, suffix = match.groups()
    label = f"Test {int(number)}"
    return label if suffix in ("", "test") else f"{label} ({suffix})"


def score_notebook(executed: str | Path, output_limit: int = 1000) -> list[dict]:
    """Score the autograded test cells, one result dict per cell, in document order.

    Each result carries checkpy's keys plus the ones checkpy has no concept of:

        id          the nbgrader grade_id
        passed      True / False (never None here -- manual cells aren't included)
        status      "pass" | "fail" | "timeout"
        description human label derived from the id
        points      0.0 or maxPoints; no partial credit, an assert either
                    raises or it does not
        maxPoints   the `points` value from the cell's own metadata
        message     the assertion text the student should read
        exception   the exception class name, or None
        output      whatever the cell printed before it failed
    """
    nb = json.loads(Path(executed).read_text())

    results: list[dict] = []
    seen: set[str] = set()

    for cell in nb["cells"]:
        if not is_autograded_test(cell):
            continue
        ng = cell["metadata"]["nbgrader"]
        gid = ng["grade_id"]

        if gid in seen:
            # nbgrader guarantees unique ids, so a duplicate means the student
            # copy-pasted a test cell. Refuse rather than silently overwrite.
            raise ValueError(f"duplicate grade_id in submission: {gid!r}")
        seen.add(gid)

        max_points = float(ng.get("points", 0))
        error = cell_error(cell)

        if cell.get("execution_count") is None:
            # The run died before reaching this cell. Not an answer, so not a pass.
            status, message, exception = "fail", "cell was never executed", None
        elif error is None:
            status, message, exception = "pass", "", None
        elif error["ename"] == "KeyboardInterrupt":
            # The per-cell timeout fired. Not a wrong answer -- a hung one.
            status = "timeout"
            message = "cell timed out"
            exception = "KeyboardInterrupt"
        else:
            status = "fail"
            message = error["evalue"]
            exception = error["ename"]

        passed = status == "pass"
        results.append(
            {
                "id": gid,
                "passed": passed,
                "status": status,
                "description": describe(gid),
                "points": max_points if passed else 0.0,
                "maxPoints": max_points,
                "message": message,
                "exception": exception,
                "output": cell_stdout(cell, output_limit),
            }
        )

    return results
