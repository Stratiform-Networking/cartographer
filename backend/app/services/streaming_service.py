"""
Streaming service for SSE (Server-Sent Events) proxy.

Handles streaming responses from downstream services, particularly for
AI chat completions that stream tokens back to the client.

Features:
- Async HTTP client lifecycle management
- Error response parsing for upstream errors
- SSE-formatted error responses for stream errors
- Automatic resource cleanup
"""

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse


@dataclass
class StreamingError:
    """Represents an error from an upstream streaming service."""

    status_code: int
    detail: str
    headers: dict[str, str] | None = None


async def parse_error_response(response: httpx.Response, default_message: str) -> str:
    """
    Parse error detail from an HTTP response.

    Args:
        response: The httpx response to parse
        default_message: Default message if parsing fails

    Returns:
        The error detail message
    """
    try:
        error_body = await response.aread()
        error_data = json.loads(error_body)
        return error_data.get("detail", default_message)
    except Exception:
        return default_message


async def check_streaming_response_errors(
    response: httpx.Response,
    client: httpx.AsyncClient,
) -> StreamingError | None:
    """
    Check for error status codes in a streaming response and handle cleanup.

    This should be called before iterating over a streaming response to catch
    upstream errors and convert them to appropriate HTTP exceptions.

    Args:
        response: The httpx streaming response
        client: The httpx client (for cleanup on error)

    Returns:
        StreamingError if there was an error, None if response is OK
    """
    if response.status_code == 429:
        detail = await parse_error_response(
            response, "Daily chat limit exceeded. Please try again tomorrow."
        )
        await response.aclose()
        await client.aclose()
        return StreamingError(
            status_code=429,
            detail=detail,
            headers={"Retry-After": response.headers.get("Retry-After", "86400")},
        )

    if response.status_code == 401:
        await response.aclose()
        await client.aclose()
        return StreamingError(status_code=401, detail="Not authenticated")

    if response.status_code >= 400:
        detail = await parse_error_response(
            response, f"Upstream service error: {response.status_code}"
        )
        await response.aclose()
        await client.aclose()
        return StreamingError(status_code=response.status_code, detail=detail)

    return None


def raise_streaming_error(error: StreamingError) -> None:
    """
    Raise an HTTPException from a StreamingError.

    Args:
        error: The streaming error to convert

    Raises:
        HTTPException with the error details
    """
    raise HTTPException(
        status_code=error.status_code,
        detail=error.detail,
        headers=error.headers,
    )


def format_sse_error(error: str) -> bytes:
    """
    Format an error as an SSE event.

    Args:
        error: The error message

    Returns:
        SSE-formatted error as bytes
    """
    # Escape quotes in error message for JSON safety
    safe_error = error.replace('"', '\\"').replace("\n", "\\n")
    return f'data: {{"type": "error", "error": "{safe_error}"}}\n\n'.encode()


async def create_stream_generator(
    response: httpx.Response,
    client: httpx.AsyncClient,
) -> AsyncGenerator[bytes, None]:
    """
    Create an async generator that yields chunks from a streaming response.

    Handles cleanup of the response and client when streaming completes or fails.
    On stream errors, yields an SSE-formatted error event before closing.

    Args:
        response: The httpx streaming response
        client: The httpx client

    Yields:
        Chunks of bytes from the response
    """
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    except Exception as e:
        yield format_sse_error(str(e))
    finally:
        await response.aclose()
        await client.aclose()


async def proxy_streaming_request(
    url: str,
    method: str = "POST",
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 300.0,
) -> StreamingResponse:
    """
    Proxy a streaming request to an upstream service and return a StreamingResponse.

    This is the main entry point for streaming proxy operations. It:
    1. Creates an httpx client for the streaming request
    2. Sends the request with streaming enabled
    3. Checks for error responses before streaming
    4. Returns a StreamingResponse that yields chunks from upstream

    Args:
        url: Full URL to the upstream streaming endpoint
        method: HTTP method (default POST)
        json_body: JSON body to send
        headers: Headers to forward (e.g., Authorization)
        timeout: Request timeout in seconds (default 300s for long AI operations)

    Returns:
        FastAPI StreamingResponse with SSE content

    Raises:
        HTTPException: On upstream errors (429, 401, 4xx, 5xx)
        HTTPException(503): If upstream service is unavailable
        HTTPException(504): If upstream service times out
        HTTPException(500): On unexpected errors
    """
    # Create client without context manager - it needs to stay open for streaming
    client = httpx.AsyncClient(timeout=timeout)

    try:
        request = client.build_request(method, url, json=json_body, headers=headers)
        response = await client.send(request, stream=True)

        # Check for error responses before streaming
        error = await check_streaming_response_errors(response, client)
        if error:
            raise_streaming_error(error)

        # Return streaming response - generator handles cleanup
        return StreamingResponse(
            create_stream_generator(response, client),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except httpx.ConnectError:
        await client.aclose()
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
    except httpx.TimeoutException:
        await client.aclose()
        raise HTTPException(status_code=504, detail="Upstream service timeout")
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=500, detail=str(e))
