"""
Repository Benchmarking API Router.
"""
from __future__ import annotations

import re
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from benchmark_models import BenchmarkReport, FeatureMatrix
from services.benchmark_analysis_service import BenchmarkAnalysisService
from services.github_service import GitHubService
from services.repository_profile_service import RepositoryProfileService

router = APIRouter(prefix="/api/repos", tags=["repository-benchmarking"])

REPOSITORY_FULL_NAME_PATTERN = re.compile(
    r"^(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/(?P<repo>[A-Za-z0-9._-]{1,100})$"
)


class RepositoryProfileRequestModel(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=160)
    language: Literal["en", "zh"] = "en"


class BenchmarkOptionsModel(BaseModel):
    include_narrative: bool = False
    max_readme_chars_per_repo: int = Field(12000, ge=1000, le=20000)


class RepositoryBenchmarkRequestModel(BaseModel):
    mine: str = Field(..., min_length=3, max_length=160)
    benchmarks: list[str] = Field(..., min_length=1, max_length=3)
    language: Literal["en", "zh"] = "en"
    options: BenchmarkOptionsModel = Field(default_factory=BenchmarkOptionsModel)


profile_service = RepositoryProfileService()
benchmark_service = BenchmarkAnalysisService(profile_service=profile_service)


def sanitize_repository_full_name(raw_full_name: str) -> str:
    candidate = raw_full_name.strip()
    if candidate.lower().startswith(("http://", "https://", "github.com/", "www.github.com/")):
        normalized = candidate
        if normalized.lower().startswith(("github.com/", "www.github.com/")):
            normalized = f"https://{normalized}"
        try:
            from urllib.parse import urlparse

            parsed = urlparse(normalized)
            hostname = parsed.netloc.lower()
            if hostname in {"github.com", "www.github.com"}:
                segments = [segment for segment in parsed.path.split("/") if segment]
                if len(segments) >= 2:
                    candidate = f"{segments[0]}/{segments[1]}"
        except Exception:
            candidate = raw_full_name.strip()

    candidate = candidate.strip().strip("/")
    matched = REPOSITORY_FULL_NAME_PATTERN.fullmatch(candidate)
    if not matched:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_repo",
                "message": "Please provide a valid GitHub repository in owner/repo format.",
            },
        )
    return f"{matched.group('owner')}/{matched.group('repo')}".lower()


def map_exception_to_http(error: Exception) -> HTTPException:
    payload = GitHubService.create_error_response(error)
    status_code = 500

    if payload["error_type"] == "invalid_input":
        status_code = 400
    elif payload["error_type"] == "user_not_found":
        status_code = 404
    elif payload["error_type"] == "rate_limit_exceeded":
        status_code = 429
    elif payload["error_type"] == "timeout_error":
        status_code = 503

    return HTTPException(
        status_code=status_code,
        detail={
            "code": payload["error_type"],
            "message": payload["message"],
            "details": payload["details"],
        },
    )


def _encode_feature_matrix(matrix: FeatureMatrix) -> dict:
    rows = []
    score_map = {"missing": 0, "weak": 1, "medium": 2, "strong": 3}
    for row in matrix.rows:
        rows.append(
            {
                "dimension_id": row.dimension_id,
                "label_key": row.label_key,
                "label": row.label,
                "cells": [
                    {
                        "repo": cell.repo,
                        "level": cell.level,
                        "score": int(cell.raw.get("score", score_map.get(cell.level, 0))),
                        "raw": cell.raw,
                    }
                    for cell in row.cells
                ],
            }
        )
    return {"rows": rows}


def _encode_report(report: BenchmarkReport) -> dict:
    payload = jsonable_encoder(asdict(report))
    payload["feature_matrix"] = _encode_feature_matrix(report.feature_matrix)
    return payload


@router.post("/profile")
async def fetch_repository_profile(request: RepositoryProfileRequestModel):
    full_name = sanitize_repository_full_name(request.full_name)
    try:
        profile = await profile_service.get_profile(full_name)
        return jsonable_encoder(asdict(profile))
    except HTTPException:
        raise
    except Exception as error:
        if isinstance(error, ValueError):
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "repository_not_found",
                    "message": str(error),
                },
            ) from error
        raise map_exception_to_http(error) from error


@router.post("/benchmark")
async def benchmark_repositories(request: RepositoryBenchmarkRequestModel):
    mine = sanitize_repository_full_name(request.mine)
    benchmarks = [sanitize_repository_full_name(item) for item in request.benchmarks]
    unique_benchmarks = list(dict.fromkeys(item for item in benchmarks if item != mine))

    if not unique_benchmarks:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_repo",
                "message": "Please provide at least one benchmark repository different from mine.",
            },
        )

    if len(unique_benchmarks) > 3:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "too_many_benchmarks",
                "message": "Benchmark comparison supports up to 3 repositories.",
            },
        )

    try:
        report = await benchmark_service.compare_repositories(
            mine=mine,
            benchmarks=unique_benchmarks,
            language=request.language,
            include_narrative=request.options.include_narrative,
        )
        return _encode_report(report)
    except HTTPException:
        raise
    except Exception as error:
        if isinstance(error, ValueError):
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "repository_not_found",
                    "message": str(error),
                },
            ) from error
        raise map_exception_to_http(error) from error


@router.get("/suggest-benchmarks")
async def suggest_benchmarks(
    mine: str = Query(..., min_length=3, max_length=160),
    limit: int = Query(3, ge=1, le=3),
    language: Literal["en", "zh"] = Query("en"),
):
    raise HTTPException(
        status_code=501,
        detail={
            "code": "not_implemented",
            "message": f"Benchmark suggestions are not implemented yet for language={language} and limit={limit}.",
        },
    )
