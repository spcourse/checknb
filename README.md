# checknb

Run an nbgrader notebook and report what its autograded test cells scored.

`checknb` executes a submitted notebook the way nbgrader does — through
`jupyter nbconvert` — and then reads the executed copy back to decide, per
locked test cell, whether it passed. The report is shaped like
[checkpy](https://github.com/spcourse/checkpy)'s, so students see the familiar
`:)` / `:(` lines and a marks importer sees familiar JSON.

## Install

```
pip install git+https://github.com/spcourse/checknb.git
```

Or, from a clone, for development:

```
pip install -e .
```

## Use

```
checknb notebook-1-foundations.ipynb
```

```
Testing: notebook-1-foundations
:) Test 1                                            5/5
:( Test 2                                            0/5
   assert products["price"].dtype == float
:) Test 3                                           10/10

Autograded 15/20
```

Options:

| flag | meaning |
| --- | --- |
| `-o PATH` | keep the executed notebook at `PATH` (without it, a scratch copy is written and deleted again) |
| `--cell-timeout N` | seconds per cell before the kernel is interrupted (default 3) |
| `--total-timeout N` | wall-clock seconds for the whole run (default 600) |
| `--json` | machine-readable output |

Exit status is 0 when the notebook ran, 1 when it could not be executed at all.
Failing tests are a normal result, not an error — read the score, not the exit
code.

## What counts as a test

Only cells nbgrader marks `grade: true, solution: false`: the locked cells that
contain the asserts. A cell that raised is wrong, a cell that did not is right,
all or nothing — exactly as nbgrader scores them.

Manually graded cells (`grade: true, solution: true`) are ignored. Running them
tells you nothing about what they are worth.

Two timeouts guard against student code that never finishes. The per-cell one is
enforced by nbconvert, which interrupts the kernel and carries on, so a hung
cell shows up as a `timeout` result rather than sinking the whole run. The
wall-clock one is a backstop for a kernel that stops honouring interrupts; when
it fires, nothing is written.

## Use as a library

```python
from checknb import execute_notebook, score_notebook, find_timeouts, pprint

executed = execute_notebook("submission.ipynb", "executed.ipynb")
results = score_notebook(executed)
pprint(results, name="submission")
```

The three stages are independent modules: `checknb.execute` runs the notebook,
`checknb.score` turns the executed copy into points, `checknb.report` renders
those points for a human or a program.

## Requirements

Python 3.11+, plus `nbconvert` and `ipykernel` (installed automatically). The
notebook's own dependencies — pandas, matplotlib, whatever it imports — must be
present in the environment the kernel runs in.
