"""Test configuration and fixtures for PAPERY backend tests."""
import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio as the async backend for tests."""
    return "asyncio"
