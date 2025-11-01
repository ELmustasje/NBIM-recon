from __future__ import annotations

import sys
import trace
from pathlib import Path

import pytest

UTIL_MODULES = [
    Path("recon/normalization.py"),
    Path("recon/matching.py"),
    Path("recon/checks.py"),
]
THRESHOLD = 0.8


def executable_lines(path: Path) -> set[int]:
    lines = set()
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.add(lineno)
    return lines


def main() -> int:
    sys.path.insert(0, str(Path.cwd()))
    tracer = trace.Trace(count=True, trace=False,
                         ignoremods=("pytest", "pluggy", "_pytest"))
    exit_code = 0
    try:
        tracer.run("import pytest; raise SystemExit(pytest.main(['tests']))")
    except SystemExit as exc:  # pragma: no cover - invoked by pytest
        exit_code = exc.code or 0

    results = tracer.results()
    counts = results.counts

    root = Path.cwd()
    all_ok = exit_code == 0
    for module in UTIL_MODULES:
        abs_path = (root / module).resolve()
        executed = {
            lineno
            for (filename, lineno), count in counts.items()
            if Path(filename).resolve() == abs_path and count > 0
        }
        eligible = executable_lines(abs_path)
        ratio = len(executed & eligible) / len(eligible) if eligible else 1.0
        print(f"Coverage {module}: {ratio:.1%} ({
              len(executed & eligible)}/{len(eligible)})")
        if ratio < THRESHOLD:
            all_ok = False

    if not all_ok:
        print(f"Coverage below {THRESHOLD:.0%} threshold or tests failed.")
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
