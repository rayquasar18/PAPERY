"""Typed QuasarFlow abstraction and transport-agnostic service contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.ai_job import AIJobProviderResponse, AIJobRequest


class AIJobSubmissionResult(AIJobProviderResponse):
    """Result type returned by provider submission calls."""


class AIJobProcessResult(AIJobProviderResponse):
    """Result type returned by provider processing/status calls."""


class QuasarFlowClient(ABC):
    """Transport-agnostic interface for QuasarFlow provider implementations."""

    @abstractmethod
    def submit_job(self, request: AIJobRequest) -> AIJobSubmissionResult:
        """Submit a new AI job to provider boundary."""

    @abstractmethod
    def process_job(self, request: AIJobRequest) -> AIJobProcessResult:
        """Process an AI job and return canonical result payload."""

    @abstractmethod
    def get_job_status(self, job_id: str) -> AIJobProcessResult:
        """Return latest status for a previously submitted job."""
