#!/usr/bin/env python3
"""
Server launcher for Asian Food Intelligence Explorer.

Usage:
    python run_server.py              # Start with defaults
    python run_server.py --reload     # Start with auto-reload
    python run_server.py --port 9000  # Start on custom port
"""

import argparse
import uvicorn
from src.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="Start the Asian Food Intelligence API server")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (default: from settings)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: from settings)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level",
    )

    args = parser.parse_args()
    settings = get_settings()

    host = args.host or settings.host
    port = args.port or settings.port

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     Asian Food Intelligence Explorer                      ║
║     Starting server at http://{host}:{port}                    ║
╚═══════════════════════════════════════════════════════════╝

API Documentation: http://{host}:{port}/docs
Alternative docs: http://{host}:{port}/redoc
""")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
