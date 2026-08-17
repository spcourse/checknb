"""Present the results, either for a human or for another program.

Both views are built from the same lines, the way checkpy does it: the JSON
carries the rendered human output in its "output" field, so a marks importer
and a student see the same words.
"""

from __future__ import annotations

import json
import sys


class Colors:
    PASS = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    NAME = "\033[96m"
    ENDC = "\033[0m"


# checkpy's vocabulary: :) passed, :( failed, :| couldn't decide,
# :S something is wrong with the submission itself.
_STYLE = {
    "pass": (Colors.PASS, ":)"),
    "fail": (Colors.FAIL, ":("),
    "timeout": (Colors.FAIL, ":("),
    "manual": (Colors.WARNING, ":|"),
    "tampered": (Colors.WARNING, ":S"),
    "missing": (Colors.WARNING, ":S"),
}

_DESC_WIDTH = 44


def _score_column(result: dict) -> str:
    """'5/5', or '--/25' for a cell no machine can score."""
    points = result["points"]
    earned = "--" if points is None else f"{points:g}"
    return f"{earned}/{result['maxPoints']:g}"


def render_lines(results: list[dict], name: str, color: bool = True) -> list[str]:
    """The human report, one entry per line, messages indented three spaces.

    Colour is applied *after* padding -- ANSI escapes count towards len(), so
    padding a coloured string silently misaligns every column.
    """

    def paint(text: str, escape: str) -> str:
        return f"{escape}{text}{Colors.ENDC}" if color else text

    lines = [paint(f"Testing: {name}", Colors.NAME)]

    for result in results:
        escape, smiley = _STYLE.get(result["status"], (Colors.WARNING, ":S"))
        head = (
            f"{smiley} {result['description']:<{_DESC_WIDTH}}{_score_column(result):>8}"
        )
        if result["status"] == "manual":
            head += "   needs manual grading"
        lines.append(paint(head, escape))

        if result["message"]:
            lines.extend("   " + line for line in result["message"].split("\n"))

    lines.append("")
    lines.append(paint(_summary(results), Colors.NAME))
    return lines


def _summary(results: list[dict]) -> str:
    auto = [r for r in results if r["points"] is not None]
    manual = [r for r in results if r["points"] is None]
    earned = sum(r["points"] for r in auto)
    out_of = sum(r["maxPoints"] for r in auto)
    text = f"Autograded {earned:g}/{out_of:g}"
    if manual:
        text += f" · awaiting manual grading {sum(r['maxPoints'] for r in manual):g}"
    return text


def pprint(results: list[dict], name: str, color: bool | None = None) -> None:
    """Print the human report. Colour defaults to on only when stdout is a tty."""
    if color is None:
        color = sys.stdout.isatty()
    print("\n".join(render_lines(results, name, color=color)))


def build_report(
    results: list[dict], name: str, timeouts: list[dict] | None = None
) -> dict:
    """The checkpy-shaped summary for one notebook.

    `timeouts` is kept as its own field rather than folded into `results`,
    because a hung cell is usually not a graded cell -- there is no result to
    attach it to.
    """
    auto = [r for r in results if r["points"] is not None]
    manual = [r for r in results if r["points"] is None]
    nPoints = sum(r["points"] for r in auto)
    maxPoints = sum(r["maxPoints"] for r in auto)
    return {
        "name": name,
        "nTests": len(results),
        "nPassed": sum(1 for r in results if r["passed"] is True),
        "nFailed": sum(1 for r in results if r["passed"] is False),
        "nRun": len(results),
        "nPoints": nPoints,
        "maxPoints": maxPoints,
        "score": nPoints / maxPoints,
        "nManual": len(manual),
        "maxManualPoints": sum(r["maxPoints"] for r in manual),
        "nTimeouts": len(timeouts or []),
        "timeouts": timeouts or [],
        "output": render_lines(results, name, color=True),
        "results": results,
    }


def render_json(
    results: list[dict],
    name: str,
    timeouts: list[dict] | None = None,
    indent: int = 4,
) -> str:
    """The machine-readable report.

    A list of one, because checkpy emits a list (it can test several files at
    once) and staying list-shaped keeps any existing consumer working.
    """
    return json.dumps(
        [build_report(results, name, timeouts)], indent=indent, ensure_ascii=False
    )
