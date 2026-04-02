"""PAPERY middleware package."""

from app.middleware.request_id import RequestIDMiddleware

__all__ = ["RequestIDMiddleware"]
