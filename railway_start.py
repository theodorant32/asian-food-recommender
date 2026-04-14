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
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from loguru import logger
from starlette.websockets import WebSocketDisconnect

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
    env["STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION"] = "false"
    # Force HTTP polling mode for better proxy compatibility
    env["STREAMLIT_SERVER_ENABLE_WEBSOCKET"] = "false"

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

        for i in range(60):
            time.sleep(0.5)
            try:
                resp = httpx.get(f"http://localhost:{STREAMLIT_PORT}/_stcore/health", timeout=2)
                if resp.status_code == 200:
                    logger.info(f"Streamlit started successfully (attempt {i+1})")
                    streamlit_ready = True
                    return
            except httpx.ConnectError:
                if (i + 1) % 10 == 0:
                    logger.info(f"Streamlit still starting... (attempt {i+1}/60)")
            except Exception as e:
                logger.warning(f"Health check error: {e}")

        logger.error("Streamlit failed to start after 30 seconds")

    except Exception as e:
        logger.exception(f"Streamlit failed to start: {e}")


async def _proxy_to_streamlit(request: Request, path: str, method: str) -> Response:
    """Forward request to Streamlit backend."""
    if not streamlit_ready:
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend is starting up, please refresh"},
        )

    try:
        # Proxy /app/* to Streamlit's root /
        if path.startswith("_stcore/"):
            url = f"http://localhost:{STREAMLIT_PORT}/{path}"
        else:
            url = f"http://localhost:{STREAMLIT_PORT}/{path}" if path else f"http://localhost:{STREAMLIT_PORT}/"

        proxy_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ["host", "content-length", "connection", "accept-encoding"]
        }

        body = None
        if method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

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


@app.get("/app")
@app.get("/app/{path:path}")
async def proxy_streamlit_get(request: Request, path: str = "") -> Response:
    """Proxy GET requests to Streamlit."""
    return await _proxy_to_streamlit(request, path, "GET")


@app.post("/app")
@app.post("/app/{path:path}")
async def proxy_streamlit_post(request: Request, path: str = "") -> Response:
    """Proxy POST requests to Streamlit."""
    return await _proxy_to_streamlit(request, path, "POST")


@app.get("/static/{path:path}")
async def proxy_static_assets(request: Request, path: str) -> Response:
    """Proxy static assets (JS, CSS, images) from Streamlit."""
    return await _proxy_to_streamlit(request, f"static/{path}", "GET")


@app.get("/favicon.png")
async def proxy_favicon(request: Request) -> Response:
    """Proxy favicon from Streamlit."""
    return await _proxy_to_streamlit(request, "favicon.png", "GET")


# HTTP polling endpoints for Streamlit (when WebSocket is disabled)
@app.post("/app/_stcore/message")
async def proxy_message(request: Request) -> Response:
    """Proxy HTTP polling messages."""
    return await _proxy_to_streamlit(request, "_stcore/message", "POST")


@app.get("/app/_stcore/message")
async def proxy_message_get(request: Request) -> Response:
    """Proxy HTTP polling messages GET."""
    return await _proxy_to_streamlit(request, "_stcore/message", "GET")


@app.post("/app/_stcore/_main")
async def proxy_main(request: Request) -> Response:
    """Proxy main endpoint."""
    return await _proxy_to_streamlit(request, "_stcore/_main", "POST")


@app.get("/app/_stcore/host-config")
async def proxy_host_config(request: Request) -> Response:
    """Proxy host-config endpoint."""
    return await _proxy_to_streamlit(request, "_stcore/host-config", "GET")


@app.get("/app/_stcore/health")
async def proxy_health(request: Request) -> Response:
    """Proxy health endpoint."""
    return await _proxy_to_streamlit(request, "_stcore/health", "GET")


@app.get("/healthz")
async def healthz():
    """Liveness probe for Railway."""
    return {
        "status": "ok",
        "api": "ready",
        "streamlit": "ready" if streamlit_ready else "starting",
    }


@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to avoid 500 errors."""
    return Response(content="", status_code=204, media_type="image/x-icon")


@app.get("/debug/streamlit")
async def debug_streamlit():
    """Debug endpoint to test Streamlit connectivity."""
    if not streamlit_ready:
        return {"error": "Streamlit not ready"}
    results = {}
    with httpx.Client() as client:
        for path in ["/_stcore/health", "/app/_stcore/health", "/stream"]:
            try:
                resp = client.get(f"http://localhost:{STREAMLIT_PORT}{path}", timeout=5)
                results[path] = {"status": resp.status_code, "content": resp.text[:100] if resp.text else "empty"}
            except Exception as e:
                results[path] = {"error": str(e)}
    return results


if __name__ == "__main__":
    logger.info("Starting Asian Food Intelligence Explorer...")

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"API will be on port {port}")
    logger.info(f"Streamlit will be accessible at /app path")

    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()

    # Wait longer for Streamlit to fully initialize with baseUrlPath
    time.sleep(20)

    if not streamlit_ready:
        logger.warning("Streamlit not ready, starting API anyway")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
