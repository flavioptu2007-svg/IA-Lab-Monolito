"""Entry point: ``python -m src.drive_audit <comando>``."""

from __future__ import annotations

import sys

from src.drive_audit.cli import main

if __name__ == "__main__":
    sys.exit(main())
