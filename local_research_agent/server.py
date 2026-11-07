from __future__ import annotations

import uvicorn

from .api import app
from .config import Settings


def main() -> None:
    settings: Settings = app.state.settings
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
