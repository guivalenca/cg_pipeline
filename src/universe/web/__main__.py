"""Run the local administration dashboard on its fixed loopback address."""

import uvicorn

from universe.web.app import create_app


def main() -> None:
    """Start the local dashboard without a development reloader."""
    uvicorn.run(create_app(), host="127.0.0.1", port=8100, reload=False)


if __name__ == "__main__":
    main()
