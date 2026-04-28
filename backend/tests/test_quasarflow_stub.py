"""Contract and stub behavior tests for QuasarFlow boundary."""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError


def test_contract_exposes_typed_submit_process_status_methods() -> None:
    """Contract must define submit/process/status methods for AI jobs."""
    from app.services.quasarflow.contracts import QuasarFlowClient

    assert inspect.isabstract(QuasarFlowClient)

    submit_sig = inspect.signature(QuasarFlowClient.submit_job)
    process_sig = inspect.signature(QuasarFlowClient.process_job)
    status_sig = inspect.signature(QuasarFlowClient.get_job_status)

    assert list(submit_sig.parameters) == ["self", "request"]
    assert list(process_sig.parameters) == ["self", "request"]
    assert list(status_sig.parameters) == ["self", "job_id"]


@pytest.mark.contract

def test_contract_module_stays_provider_decoupled() -> None:
    """Contract types can be imported without loading concrete providers."""
    import sys

    from app.services.quasarflow.contracts import (
        AIJobProcessResult,
        AIJobSubmissionResult,
        QuasarFlowClient,
    )

    assert QuasarFlowClient.__name__ == "QuasarFlowClient"
    assert AIJobSubmissionResult.__name__ == "AIJobSubmissionResult"
    assert AIJobProcessResult.__name__ == "AIJobProcessResult"
    assert "app.services.quasarflow.stub_client" not in sys.modules


@pytest.mark.schema

def test_schema_accepts_expected_provider_payload_shape() -> None:
    from app.schemas.ai_job import AIJobErrorDetail, AIJobProviderResponse, AIJobStatus

    payload = AIJobProviderResponse(
        job_id="job-001",
        status=AIJobStatus.SUCCEEDED,
        action="summarize",
        output={
            "summary": "Detailed summary",
            "citations": [
                {
                    "source_id": "doc-1",
                    "title": "Document A",
                    "locator": "p.2",
                    "snippet": "Evidence text",
                    "confidence": 0.93,
                }
            ],
            "tokens_used": 412,
        },
        progress=100,
        attempt=1,
        max_attempts=3,
        error=None,
    )

    assert payload.status is AIJobStatus.SUCCEEDED
    assert payload.output["tokens_used"] == 412

    failed = AIJobProviderResponse(
        job_id="job-err",
        status=AIJobStatus.FAILED,
        action="summarize",
        output=None,
        progress=100,
        attempt=3,
        max_attempts=3,
        error=AIJobErrorDetail(
            code="UPSTREAM_TIMEOUT",
            message="Provider timed out",
            retriable=False,
            details={"timeout_seconds": 30},
        ),
    )
    assert failed.error is not None
    assert failed.error.code == "UPSTREAM_TIMEOUT"


@pytest.mark.schema

def test_schema_rejects_malformed_provider_payload() -> None:
    from app.schemas.ai_job import AIJobProviderResponse

    with pytest.raises(ValidationError):
        AIJobProviderResponse(
            job_id="",
            status="done",
            action="",
            output="invalid",
            progress=101,
            attempt=0,
            max_attempts=0,
            error={"code": "E"},
        )


@pytest.mark.stub

def test_stub_returns_deterministic_payload_for_same_job_seed() -> None:
    from app.schemas.ai_job import AIJobRequest
    from app.services.quasarflow.stub_client import QuasarFlowStubClient

    client = QuasarFlowStubClient()
    request = AIJobRequest(
        job_id="job-deterministic",
        action="summarize",
        document_ids=["doc-a", "doc-b"],
        prompt="Summarize these docs",
        metadata={"locale": "en"},
    )

    first = client.process_job(request)
    second = client.process_job(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


@pytest.mark.stub

def test_stub_output_contains_realistic_summary_citations_and_status_metadata() -> None:
    from app.schemas.ai_job import AIJobRequest
    from app.services.quasarflow.stub_client import QuasarFlowStubClient

    client = QuasarFlowStubClient()
    request = AIJobRequest(
        job_id="job-realistic",
        action="summarize",
        document_ids=["doc-42"],
        prompt="Create an executive summary",
    )

    result = client.process_job(request)

    assert result.status.value in {"running", "succeeded", "failed", "timed_out", "pending"}
    assert result.output is not None
    assert "summary" in result.output
    assert isinstance(result.output.get("summary"), str)
    citations = result.output.get("citations")
    assert isinstance(citations, list)
    assert citations
    assert citations[0]["source_id"]
    assert citations[0]["snippet"]
    assert result.max_attempts >= result.attempt


@pytest.mark.stub

def test_stub_failure_mode_returns_canonical_error_shape() -> None:
    from app.schemas.ai_job import AIJobRequest, AIJobStatus
    from app.services.quasarflow.stub_client import QuasarFlowStubClient

    client = QuasarFlowStubClient()
    request = AIJobRequest(
        job_id="job-failure",
        action="summarize",
        document_ids=["doc-err"],
        prompt="Trigger error",
        metadata={"simulate_failure": True},
    )

    failed = client.process_job(request)

    assert failed.status is AIJobStatus.FAILED
    assert failed.error is not None
    assert failed.error.code
    assert failed.error.message
    assert isinstance(failed.error.retriable, bool)
