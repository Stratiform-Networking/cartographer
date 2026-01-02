"""
WebSocket proxy service for bidirectional real-time communication.

Handles proxying WebSocket connections to upstream services, particularly
for real-time metrics streaming.

Features:
- Bidirectional message forwarding
- Concurrent read/write handling
- Graceful disconnect handling
- Resource cleanup on connection close
"""

import asyncio

import websockets
from fastapi import WebSocket, WebSocketDisconnect


async def forward_to_client(
    upstream_ws: websockets.WebSocketClientProtocol,
    client_ws: WebSocket,
) -> None:
    """
    Forward messages from upstream WebSocket to the client.

    Args:
        upstream_ws: The upstream WebSocket connection
        client_ws: The FastAPI WebSocket client connection
    """
    try:
        async for message in upstream_ws:
            await client_ws.send_text(message)
    except Exception:
        # Connection closed or error - let the main handler deal with cleanup
        pass


async def forward_to_upstream(
    client_ws: WebSocket,
    upstream_ws: websockets.WebSocketClientProtocol,
) -> None:
    """
    Forward messages from client to upstream WebSocket.

    Args:
        client_ws: The FastAPI WebSocket client connection
        upstream_ws: The upstream WebSocket connection
    """
    try:
        while True:
            data = await client_ws.receive_text()
            await upstream_ws.send(data)
    except Exception:
        # Connection closed or error - let the main handler deal with cleanup
        pass


async def proxy_websocket(
    client_ws: WebSocket,
    upstream_url: str,
) -> None:
    """
    Proxy a WebSocket connection to an upstream service.

    This is the main entry point for WebSocket proxying. It:
    1. Accepts the client WebSocket connection
    2. Establishes connection to the upstream service
    3. Runs bidirectional forwarding concurrently
    4. Handles disconnects and errors gracefully

    Args:
        client_ws: The FastAPI WebSocket from the client
        upstream_url: Full WebSocket URL to the upstream service (ws:// or wss://)

    Note:
        This function handles all cleanup internally. Caller should not
        need to manage the WebSocket lifecycle.
    """
    await client_ws.accept()

    try:
        async with websockets.connect(upstream_url) as upstream_ws:
            # Run both forwarding tasks concurrently
            await asyncio.gather(
                forward_to_client(upstream_ws, client_ws),
                forward_to_upstream(client_ws, upstream_ws),
                return_exceptions=True,
            )
    except WebSocketDisconnect:
        # Client disconnected - normal operation
        pass
    except Exception:
        # Connection error or other issue - close gracefully
        try:
            await client_ws.close()
        except Exception:
            pass


def build_ws_url(http_url: str, path: str) -> str:
    """
    Build a WebSocket URL from an HTTP base URL and path.

    Converts http:// to ws:// and https:// to wss://.

    Args:
        http_url: The HTTP base URL (e.g., "http://localhost:8001")
        path: The WebSocket path (e.g., "/api/metrics/ws")

    Returns:
        Full WebSocket URL (e.g., "ws://localhost:8001/api/metrics/ws")
    """
    ws_url = http_url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{ws_url}{path}"
