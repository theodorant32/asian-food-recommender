#!/usr/bin/env python3
"""Run both API and Streamlit on the same port for Railway deployment."""

import os
import subprocess
import sys
import threading
import time
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from starlette.responses import Response

from src.api.main import app

STREAMLIT_PORT = 8501
STREAMLIT_HOST = "127.0.0.1"

streamlit_ready: bool = False


def run_streamlit() -> None:
    """Run Streamlit in background thread."""
    global streamlit_ready

    logger.info(f"Starting Streamlit on {STREAMLIT_HOST}:{STREAMLIT_PORT}")

    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(STREAMLIT_PORT)
    env["STREAMLIT_SERVER_ADDRESS"] = STREAMLIT_HOST
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_ENABLEXSRFPROTECTION"] = "false"
    env["STREAMLIT_SERVER_RUNONSAVE"] = "false"

    try:
        proc = subprocess.Popen(
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
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for Streamlit to start
        for _ in range(60):  # 30 seconds max
            time.sleep(0.5)
            try:
                resp = httpx.get(f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}/healthz", timeout=2)
                if resp.status_code == 200:
                    logger.info("Streamlit started successfully")
                    streamlit_ready = True
                    break
            except httpx.ConnectError:
                continue

        if not streamlit_ready:
            logger.warning("Streamlit startup timeout")
            # Log any error output
            if proc.stderr:
                for line in proc.stderr:
                    logger.error(f"Streamlit: {line.strip()}")

        proc.wait()
    except Exception as e:
        logger.exception(f"Streamlit failed: {e}")


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
    if not streamlit_ready:
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend is starting up, please refresh in a few seconds"},
        )

    async with httpx.AsyncClient() as client:
        url = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}/{path}" if path else f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}/"

        try:
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
            return JSONResponse(
                status_code=503,
                content={"error": "Frontend unavailable, please refresh"},
            )
        except Exception as e:
            logger.exception(f"Proxy error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal proxy error"},
            )


@app.get("/api/status")
async def api_status():
    """Return service status for debugging."""
    return {
        "api": "ok",
        "streamlit": "ready" if streamlit_ready else "starting",
        "streamlit_port": STREAMLIT_PORT,
    }


if __name__ == "__main__":
    logger.info("Starting Asian Food Intelligence Explorer...")

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"API will be on port {port}")
    logger.info(f"Streamlit will be accessible at /app path")

    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()

    # Give Streamlit time to start before accepting connections
    time.sleep(5)

    # Run API in foreground
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
