#!/usr/bin/env python3
"""Run both API and Streamlit for Railway deployment."""

import os
import subprocess
import sys
import threading
import time

def run_streamlit():
    """Run Streamlit in background."""
    port = int(os.environ.get("PORT", 8080)) + 1
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "frontend/app.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.serverAddress", f"localhost:{port}",
        "--browser.gatherUsageStats", "false"
    ])

def run_api():
    """Run FastAPI in foreground."""
    import uvicorn
    from src.api.main import app

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    print("Starting Asian Food Intelligence Explorer...")
    print(f"API will be on port {os.environ.get('PORT', 8080)}")
    print(f"Frontend will be on port {int(os.environ.get('PORT', 8080)) + 1}")

    # Start Streamlit in background thread
    t = threading.Thread(target=run_streamlit, daemon=True)
    t.start()

    # Wait for Streamlit to start
    time.sleep(3)

    # Run API in foreground
    run_api()
