#!/usr/bin/env python3
"""
Frontend launcher for Asian Food Intelligence Explorer.

Usage:
    python run_frontend.py              # Start Streamlit app
"""

import subprocess
import sys
from pathlib import Path


def main():
    frontend_dir = Path(__file__).parent / "frontend"
    app_path = frontend_dir / "app.py"

    if not app_path.exists():
        print(f"Error: Frontend app not found at {app_path}")
        sys.exit(1)

    print("""
╔═══════════════════════════════════════════════════════════╗
║     Asian Food Intelligence Explorer - Frontend           ║
║     Starting Streamlit app...                             ║
╚═══════════════════════════════════════════════════════════╝

Note: Ensure the API server is running on http://localhost:8000
""")

    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "localhost",
        "--server.port",
        "8501",
    ])


if __name__ == "__main__":
    main()
