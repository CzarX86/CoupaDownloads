#!/usr/bin/env python3
"""Legacy CSV feedback CLI placeholder."""
from __future__ import annotations

import sys
from textwrap import dedent

MESSAGE = dedent(
    """
    The CSV-based feedback CLI has been removed.
    Use the PDF annotation interface to review and train models directly on rendered documents.
    """
).strip()


def main() -> int:
    sys.stderr.write(MESSAGE + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
