"""The one place the version number is written.

It lives here rather than in `__init__.py` so that any module can import it.
`report` needs it for the JSON's `checknb_version` field, and `__init__` imports
`report` before it would get round to defining `__version__` itself -- so a
`from . import __version__` there raises ImportError on a half-built package.
A leaf module with no imports of its own cannot take part in that cycle.

setup.py reads this file with a regex, so keep the assignment a plain literal.
"""

__version__ = "0.1.4"
