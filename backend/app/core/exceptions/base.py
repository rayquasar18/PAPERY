"""Base PAPERY exception — extends FastAPI's HTTPException with error_code.

All domain exceptions inherit from PaperyHTTPException. The exception handler
reads error_code to build consistent ErrorResponse JSON with request_id.
"""

from fastapi import HTTPException


class PaperyHTTPException(HTTPException):
    """Base PAPERY HTTP exception.

    Extends FastAPI's HTTPException with a machine-readable error_code.
    Subclasses set class-level defaults; constructors allow per-instance override.
    """

    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "An unexpected error occurred",
        *,
        error_code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        if error_code is not None:
            self.error_code = error_code
