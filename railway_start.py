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


def _proxy_to_streamlit(request: Request, path: str, method: str) -> Response:
    """Forward request to Streamlit backend."""
    if not streamlit_ready:
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend is starting up, please refresh"},
        )

    try:
        # Proxy /app/* to Streamlit's root /
        # For _stcore endpoints, we need to strip the /app prefix
        if path.startswith("_stcore/"):
            url = f"http://localhost:{STREAMLIT_PORT}/{path}"
        else:
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


@app.get("/app")
@app.get("/app/{path:path}")
async def proxy_streamlit_get(request: Request, path: str = "") -> Response:
    """Proxy GET requests to Streamlit."""
    return _proxy_to_streamlit(request, path, "GET")


@app.post("/app")
@app.post("/app/{path:path}")
async def proxy_streamlit_post(request: Request, path: str = "") -> Response:
    """Proxy POST requests to Streamlit."""
    return _proxy_to_streamlit(request, path, "POST")


@app.get("/static/{path:path}")
async def proxy_static_assets(request: Request, path: str) -> Response:
    """Proxy static assets (JS, CSS, images) from Streamlit."""
    return _proxy_to_streamlit(request, f"static/{path}", "GET")


@app.get("/favicon.png")
async def proxy_favicon(request: Request) -> Response:
    """Proxy favicon from Streamlit."""
    return _proxy_to_streamlit(request, "favicon.png", "GET")


@app.websocket("/app/_stcore/stream")
@app.websocket("/app/_stcore/_main")
async def websocket_proxy(ws: WebSocket):
    """Proxy WebSocket connections to Streamlit."""
    import asyncio
    import socket

    await ws.accept()

    # Create raw TCP socket connection to Streamlit
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)

    try:
        sock.connect(("127.0.0.1", STREAMLIT_PORT))

        # Send WebSocket handshake
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        handshake = (
            f"GET /_stcore/stream HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{STREAMLIT_PORT}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Sec-WebSocket-Protocol: streamlit\r\n"
            "Origin: http://localhost\r\n"
            "\r\n"
        ).encode()

        sock.sendall(handshake)
        response = sock.recv(4096)  # Read handshake response

        async def forward_to_streamlit():
            try:
                while True:
                    data = await ws.receive_text()
                    # Send as WebSocket text frame (opcode 0x01)
                    frame = bytearray()
                    frame.append(0x81)  # FIN + text opcode
                    payload = data.encode('utf-8')
                    if len(payload) <= 125:
                        frame.append(len(payload))
                        frame.append(0x00)  # Unmasked
                        frame.extend(payload)
                    else:
                        frame.append(0x7E)
                        frame.extend(len(payload).to_bytes(2, 'big'))
                        frame.append(0x00)
                        frame.extend(payload)
                    sock.sendall(frame)
            except Exception:
                pass

        async def forward_from_streamlit():
            try:
                while True:
                    # Read WebSocket frame from Streamlit
                    header = sock.recv(2)
                    if len(header) < 2:
                        break
                    opcode = header[0] & 0x0F
                    length = header[1] & 0x7F

                    if length == 126:
                        length = int.from_bytes(sock.recv(2), 'big')
                    elif length == 127:
                        length = int.from_bytes(sock.recv(8), 'big')

                    payload = sock.recv(length) if length > 0 else b''

                    if opcode == 0x01:  # Text
                        await ws.send_text(payload.decode('utf-8'))
                    elif opcode == 0x02:  # Binary
                        await ws.send_bytes(payload)
                    elif opcode == 0x08:  # Close
                        break
            except Exception:
                pass

        await asyncio.gather(forward_to_streamlit(), forward_from_streamlit())
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
    finally:
        try:
            sock.close()
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass


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
    try:
        with httpx.Client() as client:
            # With baseUrlPath=app, health endpoint is at /app/_stcore/health
            resp = client.get(f"http://localhost:{STREAMLIT_PORT}/app/_stcore/health", timeout=5)
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

    # Wait longer for Streamlit to fully initialize with baseUrlPath
    time.sleep(20)

    if not streamlit_ready:
        logger.warning("Streamlit not ready, starting API anyway")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
