from typing import Any


class PaperyError(Exception):
    """Base exception for all PAPERY domain errors.

    Inner layers (CRUD, services) raise subclasses of this.
    The exception handler in main.py catches PaperyError and
    converts it to a consistent JSON ErrorResponse.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        detail: Any | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message
        self.detail = detail
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)
