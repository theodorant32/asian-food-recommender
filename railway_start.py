#!/usr/bin/env python3
"""Run both API and Streamlit on the same port for Railway deployment."""

import os
import subprocess
import sys
import threading
import time
from typing import AsyncGenerator

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from starlette.responses import Response

from src.api.main import app

STREAMLIT_PORT = 8501
STREAMLIT_HOST = "127.0.0.1"


def run_streamlit() -> None:
    """Run Streamlit in background thread."""
    logger.info(f"Starting Streamlit on {STREAMLIT_HOST}:{STREAMLIT_PORT}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "frontend/app.py",
            "--server.port",
            str(STREAMLIT_PORT),
            "--server.address",
            STREAMLIT_HOST,
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        check=False,
    )


def wait_for_streamlit(timeout: int = 30) -> bool:
    """Wait for Streamlit to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}/healthz", timeout=2)
            if resp.status_code == 200:
                logger.info("Streamlit is ready")
                return True
        except httpx.ConnectError:
            pass
        time.sleep(0.5)
    logger.warning("Streamlit startup timeout - continuing anyway")
    return False


@app.get("/app")
@app.get("/app/{path:path}")
async def proxy_streamlit_get(request: Request, path: str = "") -> Response:
    """Proxy GET requests to Streamlit."""
    return await _proxy_request(request, path, "GET")


@app.post("/app")
@app.post("/app/{path:path}")
async def proxy_streamlit_post(request: Request, path: str = "") -> Response:
    """Proxy POST requests to Streamlit."""
    return await _proxy_request(request, path, "POST")


async def _proxy_request(request: Request, path: str, method: str) -> Response:
    """Forward request to Streamlit backend."""
    async with httpx.AsyncClient() as client:
        url = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}/{path}" if path else f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}/"

        try:
            # Forward request with filtered headers
            proxy_headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length", "content-type"]
            }

            body = await request.body() if method in ["POST", "PUT", "PATCH"] else None

            response = await client.request(
                method=method,
                url=url,
                headers=proxy_headers,
                content=body,
                params=request.query_params,
                follow_redirects=True,
                timeout=30.0,
            )

            return StreamingResponse(
                response.aiter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Streamlit: {e}")
            return Response(
                content='{"error": "Frontend is starting up, please refresh"}',
                status_code=503,
                media_type="application/json",
            )
        except Exception as e:
            logger.exception(f"Proxy error: {e}")
            return Response(
                content='{"error": "Internal proxy error"}',
                status_code=500,
                media_type="application/json",
            )


if __name__ == "__main__":
    logger.info("Starting Asian Food Intelligence Explorer...")

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"API will be on port {port}")
    logger.info(f"Streamlit will be accessible at /app path")

    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()

    # Wait for Streamlit to be ready
    wait_for_streamlit(timeout=30)

    # Run API in foreground
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
