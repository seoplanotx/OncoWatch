from __future__ import annotations

import argparse

import uvicorn

from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OncoWatch local backend.")
    parser.add_argument("--host", default=settings.backend_host)
    parser.add_argument("--port", type=int, default=settings.backend_port)
    args = parser.parse_args()

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False, factory=False)


if __name__ == "__main__":
    main()
