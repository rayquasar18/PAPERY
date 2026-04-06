"""PAPERY exception utilities.

PAPERY uses FastAPI's built-in HTTPException directly.
No custom exception subclasses — keep it standard.

Usage:
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="User not found")

The global exception handler in main.py automatically adds
request_id to all error responses.
"""
