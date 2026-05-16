#!/usr/bin/env python3
"""Try to build ASSIGNMENT2_REPORT.pdf from docs/ASSIGNMENT2_REPORT.md using pandoc (if installed).

  py -3 scripts/build_report_pdf.py

Install pandoc: https://pandoc.org/installing.html  (or choco install pandoc on Windows)

If pandoc is missing, exits 0 after printing a short message (no failure for CI).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "ASSIGNMENT2_REPORT.md"
PDF = ROOT / "ASSIGNMENT2_REPORT.pdf"


def main() -> int:
    if not MD.is_file():
        print("Missing", MD)
        return 1
    pandoc = shutil.which("pandoc")
    if not pandoc:
        print(
            "pandoc not found on PATH - install pandoc or print docs/ASSIGNMENT2_REPORT.md to PDF from your editor."
        )
        return 0
    cmd = [
        pandoc,
        str(MD),
        "-o",
        str(PDF),
        "--from=markdown",
        "--variable=geometry:margin=1in",
    ]
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        print("pandoc failed")
        return r.returncode
    print("Wrote", PDF)
    return 0


if __name__ == "__main__":
    sys.exit(main())
