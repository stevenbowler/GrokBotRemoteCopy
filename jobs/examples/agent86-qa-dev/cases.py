"""UI_TEST_SPEC v0.8.24 cases. Assembled from split parts for git transport."""
from pathlib import Path

_p = Path(__file__).resolve().parent
_body = "".join((_p / n).read_text() for n in ("_cases_a.py", "_cases_b1.py", "_cases_b2.py"))
exec(_body, globals())
