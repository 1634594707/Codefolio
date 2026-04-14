import asyncio
import re
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from cache_keys import ai_cache_keys_to_clear, github_user_cache_keys_to_clear, repository_analysis_cache_prefix
from config import settings
from database import (
    ARTIFACT_AI_ROAST,
    ARTIFACT_AI_STYLE_TAGS,
    ARTIFACT_AI_TECH_SUMMARY,
    ARTIFACT_GITHUB_USER,
    ARTIFACT_REPOSITORY_ANALYSIS,
    snapshot_store,
)
from routers import repos_benchmark
from services.ai_service import AIService
from services.github_service import GitHubService
from services.language_trends import compute_language_trends
from services.render_service import RenderService
from services.score_engine import ScoreEngine
from utils.redis_client import redis_client
from utils.workspace_scope import WORKSPACE_HEADER, normalize_workspace_scope


USERNAME_PATTERN = re.compile(r"^(?=.{1,39}$)(?!-)(?!.*--)[A-Za-z0-9-]+(?<!-)$")
SUPPORTED_CONTENT_LANGUAGES = ("en", "zh")


class GenerateRequestModel(BaseModel):
    username: str = Field(..., min_length=1, max_length=39)
    language: Literal["en", "zh"] = "en"


class RepositoryAnalysisRequestModel(BaseModel):
    username: str = Field(..., min_length=1, max_length=39)
    repo_name: str = Field(..., min_length=1, max_length=200)
    language: Literal["en", "zh"] = "en"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await snapshot_store.connect()
    await redis_client.connect()
    yield
    await redis_client.close()
    await snapshot_store.close()


app = FastAPI(
    title="Codefolio API",
    description="GitHub profile analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos_benchmark.router)

github_service = GitHubService()
score_engine = ScoreEngine()
render_service = RenderService()


def sanitize_username(raw_username: str) -> str:
    username = raw_username.strip()
    if username.startswith("@"):
        username = username.lstrip("@").strip()
    elif username.lower().startswith(("http://", "https://", "github.com/", "www.github.com/")):
        candidate = username
        if candidate.lower().startswith(("github.com/", "www.github.com/")):
            candidate = f"https://{candidate}"
        try:
            from urllib.parse import urlparse

            parsed = urlparse(candidate)
            hostname = parsed.netloc.lower()
            if hostname in {"github.com", "www.github.com"}:
                segments = [segment for segment in parsed.path.split("/") if segment]
                if segments:
                    if segments[0] in {"orgs", "users"} and len(segments) > 1:
                        username = segments[1]
                    else:
                        username = segments[0]
        except Exception:
            username = raw_username.strip()

    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_username",
                "message": "Please provide a valid GitHub username.",
            },
        )
    return username


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


async def generate_localized_output(
    ai_service: AIService,
    user_data,
    gitscore,
    language: str,
    workspace_scope: str,
):
    style_tags, roast_comment, tech_summary = await asyncio.gather(
        ai_service.generate_style_tags(user_data, gitscore, language, workspace_scope=workspace_scope),
        ai_service.generate_roast_comment(user_data, gitscore, language, workspace_scope=workspace_scope),
        ai_service.generate_tech_summary(user_data, language, workspace_scope=workspace_scope),
    )

    from models import AIInsights

    ai_insights = AIInsights(
        style_tags=style_tags,
        roast_comment=roast_comment,
        tech_summary=tech_summary,
    )
    resume_markdown = render_service.generate_markdown_resume(
        user_data,
        gitscore,
        ai_insights,
        language=language,
    )
    card_data = render_service.build_card_data(user_data, gitscore, ai_insights)
    social_card_html = render_service.generate_social_card_html(
        card_data,
        tech_summary=tech_summary,
        theme="dark",
        language=language,
    )

    return {
        "resume_markdown": resume_markdown,
        "ai_insights": asdict(ai_insights),
        "card_data": asdict(card_data),
        "social_card_html": social_card_html,
    }


async def build_generation_payload(
    username: str,
    language: str,
    include_all_languages: bool = False,
    workspace_scope: str = "global",
) -> dict:
    user_data = await github_service.fetch_user_data(username)
    gitscore = score_engine.calculate_gitscore(user_data)

    languages_to_generate = SUPPORTED_CONTENT_LANGUAGES if include_all_languages else (language,)
    ai_service = AIService()
    try:
        localized_results = await asyncio.gather(
            *(
                generate_localized_output(
                    ai_service,
                    user_data,
                    gitscore,
                    content_language,
                    workspace_scope,
                )
                for content_language in languages_to_generate
            )
        )
    finally:
        await ai_service.close()

    localized_outputs = {
        content_language: result
        for content_language, result in zip(languages_to_generate, localized_results)
    }
    primary_output = localized_outputs[language]

    return {
        "user": asdict(user_data),
        "gitscore": asdict(gitscore),
        "resume_markdown": primary_output["resume_markdown"],
        "ai_insights": primary_output["ai_insights"],
        "card_data": primary_output["card_data"],
        "social_card_html": primary_output["social_card_html"],
        "localized_outputs": localized_outputs,
        "available_content_languages": list(localized_outputs.keys()),
        "language_trends": compute_language_trends(user_data, locale=language),
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "codefolio-api",
        "ai_configured": bool(settings.AI_API_KEY and settings.AI_API_KEY.strip()),
        "redis_connected": redis_client.client is not None,
        "database_ready": snapshot_store.ready,
        "database_backend": settings.database_backend,
        "database_target": settings.database_target,
    }


async def ensure_workspace_scope(workspace_scope: str) -> None:
    if workspace_scope != "global":
        await snapshot_store.ensure_workspace(workspace_scope)


@app.post("/api/repository/analyze")
async def analyze_repository(request: RepositoryAnalysisRequestModel, http_request: Request):
    username = sanitize_username(request.username)
    workspace_scope = normalize_workspace_scope(http_request.headers.get(WORKSPACE_HEADER))
    await ensure_workspace_scope(workspace_scope)
    try:
        user_data = await github_service.fetch_user_data(username)
        repository = next(
            (repo for repo in user_data.repositories if repo.name.lower() == request.repo_name.strip().lower()),
            None,
        )
        if repository is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "repository_not_found",
                    "message": f"Repository '{request.repo_name}' was not found for user '{username}'.",
                },
            )

        ai_service = AIService()
        try:
            analysis = await ai_service.generate_repository_analysis(
                user_data,
                repository,
                request.language,
                workspace_scope=workspace_scope,
            )
        finally:
            await ai_service.close()

        return {
            "repository": {
                "name": repository.name,
                "description": repository.description,
                "language": repository.language,
                "stars": repository.stars,
                "forks": repository.forks,
                "url": repository.url,
                "pushed_at": repository.pushed_at,
                "topics": list(repository.topics),
                "has_readme": repository.has_readme,
                "has_license": repository.has_license,
                "file_tree": list(repository.file_tree),
            },
            "analysis": asdict(analysis),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise map_exception_to_http(error) from error


@app.post("/api/generate")
async def generate_profile(request: GenerateRequestModel, http_request: Request):
    username = sanitize_username(request.username)
    workspace_scope = normalize_workspace_scope(http_request.headers.get(WORKSPACE_HEADER))
    await ensure_workspace_scope(workspace_scope)
    try:
        return await build_generation_payload(
            username,
            request.language,
            include_all_languages=False,
            workspace_scope=workspace_scope,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise map_exception_to_http(error) from error


@app.get("/api/export/pdf")
async def export_pdf(
    request: Request,
    username: str = Query(..., min_length=1, max_length=39),
    language: Literal["en", "zh"] = "en",
):
    sanitized_username = sanitize_username(username)
    workspace_scope = normalize_workspace_scope(request.headers.get(WORKSPACE_HEADER))
    await ensure_workspace_scope(workspace_scope)
    try:
        payload = await build_generation_payload(
            sanitized_username,
            language,
            include_all_languages=False,
            workspace_scope=workspace_scope,
        )
        pdf_bytes = render_service.generate_pdf_resume(payload["resume_markdown"])
    except HTTPException:
        raise
    except Exception as error:
        raise map_exception_to_http(error) from error

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="codefolio-{sanitized_username}-{language}.pdf"'
        },
    )


@app.delete("/api/cache/{username}")
async def clear_user_cache(username: str):
    sanitized_username = sanitize_username(username)
    try:
        keys_to_clear = github_user_cache_keys_to_clear(sanitized_username) + ai_cache_keys_to_clear(
            sanitized_username, SUPPORTED_CONTENT_LANGUAGES
        )
        for key in keys_to_clear:
            await redis_client.delete(key)
            await redis_client.delete_pattern(f"ws:*:{key}")
        deleted_repo_analysis = await redis_client.delete_pattern(
            f"{repository_analysis_cache_prefix(sanitized_username)}*"
        )
        deleted_repo_analysis += await redis_client.delete_pattern(
            f"ws:*:{repository_analysis_cache_prefix(sanitized_username)}*"
        )
        deleted_db_rows = 0
        deleted_db_rows += await snapshot_store.delete_snapshot(ARTIFACT_GITHUB_USER, sanitized_username)
        deleted_db_rows += await snapshot_store.delete_snapshot_all_scopes(ARTIFACT_AI_STYLE_TAGS, sanitized_username, "en")
        deleted_db_rows += await snapshot_store.delete_snapshot_all_scopes(ARTIFACT_AI_STYLE_TAGS, sanitized_username, "zh")
        deleted_db_rows += await snapshot_store.delete_snapshot_all_scopes(ARTIFACT_AI_ROAST, sanitized_username, "en")
        deleted_db_rows += await snapshot_store.delete_snapshot_all_scopes(ARTIFACT_AI_ROAST, sanitized_username, "zh")
        deleted_db_rows += await snapshot_store.delete_snapshot_all_scopes(ARTIFACT_AI_TECH_SUMMARY, sanitized_username, "en")
        deleted_db_rows += await snapshot_store.delete_snapshot_all_scopes(ARTIFACT_AI_TECH_SUMMARY, sanitized_username, "zh")
        deleted_db_rows += await snapshot_store.delete_scope_prefix_all_scopes(
            ARTIFACT_REPOSITORY_ANALYSIS,
            f"{sanitized_username}/",
        )

        return {
            "status": "success",
            "message": f"Cache and snapshots cleared for user: {sanitized_username}",
            "cleared_keys": keys_to_clear,
            "cleared_repo_analysis_count": deleted_repo_analysis,
            "cleared_snapshot_rows": deleted_db_rows,
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cache_clear_error",
                "message": f"Failed to clear cache: {str(error)}",
            },
        )


@app.post("/api/workspaces/ensure")
async def ensure_workspace(request: Request):
    workspace_scope = normalize_workspace_scope(request.headers.get(WORKSPACE_HEADER))
    await ensure_workspace_scope(workspace_scope)
    return {
        "workspace_id": workspace_scope,
        "registered": workspace_scope != "global",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
