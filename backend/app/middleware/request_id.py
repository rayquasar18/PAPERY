"""Request ID middleware — assigns unique ID to every request for tracing."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a unique request_id to every request.

    - If the client sends X-Request-ID header, that value is used.
    - Otherwise, a new UUID4 is generated.
    - The request_id is stored in request.state.request_id.
    - The response includes X-Request-ID header.

    Note: BaseHTTPMiddleware buffers response body, which is fine
    for non-streaming endpoints. When SSE/streaming is added in later
    phases, this should be reviewed (or replaced with pure ASGI middleware).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Use client-provided ID for distributed tracing, or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
