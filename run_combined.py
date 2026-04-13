#!/usr/bin/env python3
"""Run both API and Streamlit on the same port using a proxy approach."""

import os
import sys
import threading
import time
import uvicorn
from src.api.main import app

def run_streamlit():
    """Run Streamlit app."""
    os.system("streamlit run frontend/app.py --server.port=8501 --server.address=0.0.0.0")

def run_api():
    """Run FastAPI app."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Streamlit in a thread
    t = threading.Thread(target=run_streamlit, daemon=True)
    t.start()

    # Give Streamlit time to start
    time.sleep(2)

    # Run API in main thread
    run_api()
