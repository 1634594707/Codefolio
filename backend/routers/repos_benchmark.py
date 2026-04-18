"""
Repository Benchmarking API Router.
"""
from __future__ import annotations

import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Literal

import fastapi
import starlette
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from benchmark_models import BenchmarkReport, BenchmarkSuggestion, FeatureMatrix
from cache_keys import repo_profile_cache_key, repository_profile_cache_key
from database import ARTIFACT_BENCHMARK_REPORT, snapshot_store
from services.ai_service import AIService
from services.benchmark_analysis_service import BenchmarkAnalysisService
from services.benchmark_recommendation_service import BenchmarkRecommendationService
from services.github_service import GitHubService
from services.repository_profile_service import RepositoryProfileService
from utils.rate_limiter import benchmark_rate_limiter
from utils.redis_client import redis_client
from utils.workspace_scope import WORKSPACE_HEADER, normalize_workspace_scope

try:
    router = APIRouter(prefix="/api/repos", tags=["repository-benchmarking"])
except TypeError as error:
    if "on_startup" not in str(error):
        raise
    raise RuntimeError(
        "FastAPI and Starlette are incompatible in the current environment. "
        f"Detected fastapi={fastapi.__version__}, starlette={starlette.__version__}. "
        "Reinstall backend dependencies with: pip install -r requirements.txt"
    ) from error

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


def _require_rate_limit(request: fastapi.Request) -> None:
    """FastAPI dependency that enforces per-IP rate limiting on benchmark endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    if not benchmark_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limit_exceeded",
                "message": "Too many requests. Please wait before retrying.",
            },
        )


profile_service = RepositoryProfileService()
benchmark_service = BenchmarkAnalysisService(
    profile_service=profile_service,
    ai_service=AIService(),
)
recommendation_service = BenchmarkRecommendationService(profile_service=profile_service)


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
async def fetch_repository_profile(request: RepositoryProfileRequestModel, _rl: None = fastapi.Depends(_require_rate_limit)):
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
async def benchmark_repositories(
    request: RepositoryBenchmarkRequestModel,
    http_request: fastapi.Request,
    _rl: None = fastapi.Depends(_require_rate_limit),
):
    mine = sanitize_repository_full_name(request.mine)
    benchmarks = [sanitize_repository_full_name(item) for item in request.benchmarks]
    workspace_scope = normalize_workspace_scope(http_request.headers.get(WORKSPACE_HEADER))
    if workspace_scope != "global":
        await snapshot_store.ensure_workspace(workspace_scope)
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
            max_readme_chars=request.options.max_readme_chars_per_repo,
            workspace_scope=workspace_scope,
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
    mine = sanitize_repository_full_name(mine)
    try:
        suggestions = await recommendation_service.suggest_benchmarks(mine, limit, language)
        return {
            "suggestions": [
                {
                    "full_name": s.full_name,
                    "reason_code": s.reason_code,
                    "reason_params": s.reason_params,
                    "stars": s.stars,
                    "reason_title": s.reason_title,
                    "reason_summary": s.reason_summary,
                    "learn_from": s.learn_from,
                    "badges": s.badges,
                }
                for s in suggestions
            ],
            "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise map_exception_to_http(error) from error


@router.delete("/cache/{owner}/{repo}")
async def invalidate_repository_cache(owner: str, repo: str):
    """Clear all cache keys for a specific repository (profile + benchmark results)."""
    owner_lower = owner.strip().lower()
    repo_lower = repo.strip().lower()

    deleted = 0

    # Delete the v1 profile cache key
    profile_key = repo_profile_cache_key(owner_lower, repo_lower)
    if await redis_client.delete(profile_key):
        deleted += 1

    # Delete the legacy profile cache key
    legacy_profile_key = repository_profile_cache_key(f"{owner_lower}/{repo_lower}")
    if await redis_client.delete(legacy_profile_key):
        deleted += 1

    # Delete any benchmark cache keys that reference this repo
    deleted += await redis_client.delete_pattern(f"benchmark:v1:*")
    deleted += await redis_client.delete_pattern(f"benchmark:v2:*")
    deleted += await redis_client.delete_pattern(f"ws:*:benchmark:v1:*")
    deleted += await redis_client.delete_pattern(f"ws:*:benchmark:v2:*")
    deleted += await snapshot_store.delete_artifact_all_rows(ARTIFACT_BENCHMARK_REPORT)

    return {"deleted_keys": deleted, "repository": f"{owner_lower}/{repo_lower}"}
