from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import ValidationError

from app.schemas.extraction import (
    TopicApproveResponse,
    TopicExtractionResponse,
    TopicListRequest,
    TopicReviewResponse,
)
from app.services.extraction.persistence_service import ExtractPersistenceService
from app.services.extraction.topic_service import (
    approve_topics,
    extract_topics,
    get_topics,
    update_topics,
)


router = APIRouter(prefix="/extract/jobs", tags=["extract-topics"])


@router.post("/{job_id}/topics/extract", response_model=TopicExtractionResponse)
def extract_job_topics(
    job_id: str,
    offset: str = Query(default="auto"),
    split_pdf: bool = Query(default=True),
) -> TopicExtractionResponse:
    try:
        _validate_offset(offset)
        return extract_topics(
            job_id=job_id,
            offset=offset,
            split_pdf=split_pdf,
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract topics: {exc}",
        ) from exc


@router.get("/{job_id}/topics", response_model=TopicReviewResponse)
def get_job_topics(job_id: str) -> TopicReviewResponse:
    try:
        return get_topics(job_id)

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read topics: {exc}",
        ) from exc


@router.put("/{job_id}/topics", response_model=TopicReviewResponse)
def update_job_topics(
    job_id: str,
    payload: dict = Body(...),
) -> TopicReviewResponse:
    try:
        request = TopicListRequest.model_validate(payload)
        return update_topics(job_id, request.topics)

    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update topics: {exc}",
        ) from exc


@router.post("/{job_id}/topics/approve", response_model=TopicApproveResponse)
async def approve_job_topics(
    job_id: str,
    subjectMapId: str | None = Query(default=None, description="Required for first-time persistence unless AI_EXTRACT_DEFAULT_SUBJECT_MAP_ID is set."),
    classMapId: str | None = Query(default=None, description="Required when the subject does not already exist."),
    persist: bool = Query(default=True),
) -> TopicApproveResponse:
    try:
        response = approve_topics(job_id)
        if persist:
            response.persistence = await ExtractPersistenceService().persist_topics(
                job_id=job_id,
                subject_map_id=subjectMapId,
                class_map_id=classMapId,
            )
        return response

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve topics: {exc}",
        ) from exc


def _validate_offset(offset: str) -> None:
    value = str(offset).strip().lower()

    if value in {"auto", "none", "null", ""}:
        return

    try:
        int(value)
    except ValueError as exc:
        raise ValueError("offset must be 'auto', 'none', or an integer string") from exc
