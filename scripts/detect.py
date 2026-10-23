#!/usr/bin/env python3
"""Public blind detector CLI; it has no expected-answer argument."""

from app.detector_worker import main


if __name__ == "__main__":
    raise SystemExit(main())
