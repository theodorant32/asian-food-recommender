#!/usr/bin/env python3
"""Run both API and Streamlit on the same port for Railway deployment."""

import os
import subprocess
import sys
import threading
import time
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import StreamingResponse
import httpx
from loguru import logger

from src.api.main import app

# Streamlit runs on localhost at a different internal port
STREAMLIT_PORT = 8501

def run_streamlit():
    """Run Streamlit in background."""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "frontend/app.py",
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.serverAddress", f"localhost:{STREAMLIT_PORT}",
        "--browser.gatherUsageStats", "false",
        "--server.enableXsrfProtection", "true",
    ])

# Mount Streamlit at /app path
@app.get("/app")
@app.get("/app/{path:path}")
@app.post("/app")
@app.post("/app/{path:path}")
async def proxy_streamlit(request: Request, path: str = ""):
    """Proxy requests to Streamlit."""
    async with httpx.AsyncClient() as client:
        base_url = f"http://127.0.0.1:{STREAMLIT_PORT}"
        url = f"{base_url}/{path}" if path else base_url

        try:
            # Build headers (exclude host)
            proxy_headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}

            # Make the request
            response = await client.request(
                method=request.method,
                url=url,
                headers=proxy_headers,
                content=await request.body(),
                params=request.query_params,
                follow_redirects=True,
                timeout=30.0,
            )

            return StreamingResponse(
                response.iter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.ConnectError:
            return {"error": "Streamlit is starting up, please refresh"}
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            return {"error": f"Proxy error: {str(e)}"}

if __name__ == "__main__":
    print("Starting Asian Food Intelligence Explorer...")
    print(f"API will be on port {os.environ.get('PORT', 8000)}")
    print(f"Streamlit will be accessible at /app path")

    # Start Streamlit in background thread
    t = threading.Thread(target=run_streamlit, daemon=True)
    t.start()

    # Wait for Streamlit to start
    time.sleep(5)

    # Run API in foreground
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
