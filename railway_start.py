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
from fastapi.responses import JSONResponse, Response
from loguru import logger

from src.api.main import app

STREAMLIT_PORT = 8501
STREAMLIT_HOST = "0.0.0.0"

streamlit_ready: bool = False
streamlit_process: Optional[subprocess.Popen] = None


def run_streamlit() -> None:
    """Run Streamlit in background thread."""
    global streamlit_ready, streamlit_process

    logger.info(f"Starting Streamlit on {STREAMLIT_HOST}:{STREAMLIT_PORT}")

    env = os.environ.copy()
    env["PORT"] = str(STREAMLIT_PORT)
    env["STREAMLIT_SERVER_PORT"] = str(STREAMLIT_PORT)
    env["STREAMLIT_SERVER_ADDRESS"] = STREAMLIT_HOST
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_ENABLEXSRFPROTECTION"] = "false"
    env["STREAMLIT_SERVER_FILE_WATCHER"] = "none"
    env["STREAMLIT_SERVER_FOLDER_WATCH"] = "false"
    env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    env["STREAMLIT_GLOBAL_LOG_LEVEL"] = "error"
    env["STREAMLIT_BROWSER_SERVER_ADDRESS"] = "localhost"
    env["STREAMLIT_SERVER_RUNONSAVE"] = "false"
    env["STREAMLIT_SERVER_ENABLE_CORS"] = "false"

    try:
        streamlit_process = subprocess.Popen(
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
        )

        for _ in range(60):
            time.sleep(0.5)
            try:
                resp = httpx.get(f"http://localhost:{STREAMLIT_PORT}/_stcore/health", timeout=2)
                if resp.status_code == 200:
                    logger.info("Streamlit started successfully")
                    streamlit_ready = True
                    return
            except Exception:
                continue

        logger.warning("Streamlit startup timeout")

    except Exception as e:
        logger.exception(f"Streamlit failed to start: {e}")


def _proxy_to_streamlit(request: Request, path: str, method: str) -> Response:
    """Forward request to Streamlit backend."""
    if not streamlit_ready:
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend is starting up, please refresh"},
        )

    try:
        # Proxy /app/* to Streamlit's root /
        url = f"http://localhost:{STREAMLIT_PORT}/{path}" if path else f"http://localhost:{STREAMLIT_PORT}/"

        proxy_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ["host", "content-length", "content-type", "origin", "referer", "connection", "accept-encoding"]
        }

        body = None
        if method in ["POST", "PUT", "PATCH"]:
            body = bytes(request.body())

        with httpx.Client() as client:
            response = client.request(
                method=method,
                url=url,
                headers=proxy_headers,
                content=body,
                params=dict(request.query_params),
                follow_redirects=True,
                timeout=30.0,
            )

        # Return response as-is, preserving compression
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding", "content-encoding"]},
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
            content={"error": f"Proxy error: {str(e)}"},
        )


@app.get("/app/{path:path}")
@app.get("/app")
async def proxy_streamlit_get(request: Request, path: str = "") -> Response:
    """Proxy GET requests to Streamlit."""
    return _proxy_to_streamlit(request, path, "GET")


@app.post("/app/{path:path}")
@app.post("/app")
async def proxy_streamlit_post(request: Request, path: str = "") -> Response:
    """Proxy POST requests to Streamlit."""
    return _proxy_to_streamlit(request, path, "POST")


@app.get("/healthz")
async def healthz():
    """Liveness probe for Railway."""
    return {
        "status": "ok",
        "api": "ready",
        "streamlit": "ready" if streamlit_ready else "starting",
    }


@app.get("/debug/streamlit")
async def debug_streamlit():
    """Debug endpoint to test Streamlit connectivity."""
    if not streamlit_ready:
        return {"error": "Streamlit not ready"}
    try:
        with httpx.Client() as client:
            resp = client.get(f"http://localhost:{STREAMLIT_PORT}/_stcore/health", timeout=5)
            return {
                "status": "ok",
                "streamlit_health": resp.status_code,
                "content": resp.text[:200] if resp.text else "empty",
            }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("Starting Asian Food Intelligence Explorer...")

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"API will be on port {port}")
    logger.info(f"Streamlit will be accessible at /app path")

    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()

    time.sleep(10)

    if not streamlit_ready:
        logger.warning("Streamlit not ready, starting API anyway")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
