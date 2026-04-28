"""Deterministic QuasarFlow stub provider for development and testing."""

from __future__ import annotations

import hashlib
from random import Random

from app.schemas.ai_job import AIJobErrorDetail, AIJobProviderResponse, AIJobRequest, AIJobStatus
from app.services.quasarflow.contracts import AIJobProcessResult, AIJobSubmissionResult, QuasarFlowClient


class QuasarFlowStubClient(QuasarFlowClient):
    """Realistic deterministic QuasarFlow-like provider implementation."""

    def __init__(self) -> None:
        self._store: dict[str, AIJobProcessResult] = {}

    def submit_job(self, request: AIJobRequest) -> AIJobSubmissionResult:
        """Create pending job envelope and cache by job_id."""
        submitted = AIJobSubmissionResult(
            job_id=request.job_id,
            status=AIJobStatus.PENDING,
            action=request.action,
            output={
                "summary": "Job accepted by development stub.",
                "citations": [],
                "tokens_used": 0,
            },
            progress=0,
            attempt=1,
            max_attempts=3,
            error=None,
        )
        self._store[request.job_id] = submitted
        return submitted

    def process_job(self, request: AIJobRequest) -> AIJobProcessResult:
        """Return deterministic realistic payload for the same job seed."""
        if request.metadata.get("simulate_failure") is True:
            failed = AIJobProcessResult(
                job_id=request.job_id,
                status=AIJobStatus.FAILED,
                action=request.action,
                output=None,
                progress=100,
                attempt=3,
                max_attempts=3,
                error=AIJobErrorDetail(
                    code="STUB_UPSTREAM_FAILURE",
                    message="Simulated upstream provider failure for development mode.",
                    retriable=False,
                    details={"provider": "quasarflow-stub", "reason": "simulate_failure"},
                ),
            )
            self._store[request.job_id] = failed
            return failed

        seed = int(hashlib.sha256(request.job_id.encode("utf-8")).hexdigest()[:8], 16)
        rng = Random(seed)

        status = AIJobStatus.SUCCEEDED
        summary = (
            f"Executive summary for action '{request.action}' on {len(request.document_ids)} "
            "document(s), generated deterministically for local development."
        )
        citations = []
        source_docs = request.document_ids or ["doc-simulated-1", "doc-simulated-2"]
        for index, document_id in enumerate(source_docs[:2], start=1):
            confidence = round(0.8 + (rng.random() * 0.19), 2)
            citations.append(
                {
                    "source_id": document_id,
                    "title": f"Source Document {index}",
                    "locator": f"p.{rng.randint(1, 12)}",
                    "snippet": (
                        "Key supporting statement extracted for UI citation rendering "
                        f"(seed={seed}, source={document_id})."
                    ),
                    "confidence": confidence,
                }
            )

        result = AIJobProcessResult(
            job_id=request.job_id,
            status=status,
            action=request.action,
            output={
                "summary": summary,
                "citations": citations,
                "tokens_used": rng.randint(180, 950),
                "latency_ms": rng.randint(300, 2200),
                "model": "qflow-stub-v1",
            },
            progress=100,
            attempt=1,
            max_attempts=3,
            error=None,
        )
        self._store[request.job_id] = result
        return result

    def get_job_status(self, job_id: str) -> AIJobProcessResult:
        """Read latest deterministic status for given job ID."""
        cached = self._store.get(job_id)
        if cached is not None:
            return cached

        return AIJobProcessResult(
            job_id=job_id,
            status=AIJobStatus.PENDING,
            action="unknown",
            output={
                "summary": "Job not processed yet in stub provider.",
                "citations": [],
                "tokens_used": 0,
            },
            progress=0,
            attempt=1,
            max_attempts=3,
            error=None,
        )
