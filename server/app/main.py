"""Entrypoints.

Run from the server/ directory:
    poetry run python -m app.main          # reads host/port/reload from .env
    uvicorn app.main:app --reload          # equivalent, without Poetry
"""

import logging

import uvicorn

from app.config import get_settings
from app.factory import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = create_app()


def run() -> None:
    settings = get_settings()
    # An import string (not the `app` object) is required for auto-reload to work.
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )


if __name__ == "__main__":
    run()
