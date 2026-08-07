"""Dev entry point for the dashboard: python serve.py.

Exists because some macOS setups hide the .pth file the editable install
writes (see README); this puts src on the path itself before importing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from universe.web.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
