import asyncio
import json
import re
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncGenerator, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
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

# In-memory store for OAuth state tokens: {state: expiry_timestamp}
# Used for CSRF protection during the OAuth flow.
_oauth_state_store: dict[str, float] = {}
_OAUTH_STATE_TTL = 600  # 10 minutes


class GenerateRequestModel(BaseModel):
    username: str = Field(..., min_length=1, max_length=39)
    language: Literal["en", "zh"] = "en"
    theme: Literal["dark", "light"] = "dark"


class RepositoryAnalysisRequestModel(BaseModel):
    username: str = Field(..., min_length=1, max_length=39)
    repo_name: str = Field(..., min_length=1, max_length=200)
    language: Literal["en", "zh"] = "en"


class ExportPdfRequestModel(BaseModel):
    username: str
    language: Literal["en", "zh"] = "en"
    extra_markdown: Optional[str] = None


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
    version="1.3.0",
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
    theme: str = "dark",
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
        theme=theme,
        language=language,
    )

    return {
        "resume_markdown": resume_markdown,
        "ai_insights": asdict(ai_insights),
        "card_data": asdict(card_data),
        "social_card_html": social_card_html,
    }


def _extract_bearer_token(request: Request) -> str | None:
    """
    Extract a Bearer token from the ``Authorization`` request header.

    Returns the raw token string if the header is present and follows the
    ``Bearer <token>`` format, otherwise returns ``None``.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        return token if token else None
    return None


async def build_generation_payload(
    username: str,
    language: str,
    include_all_languages: bool = False,
    workspace_scope: str = "global",
    user_token: str | None = None,
    theme: str = "dark",
) -> dict:
    user_data = await github_service.fetch_user_data(username, user_token=user_token)
    star_history = GitHubService.compute_star_history_from_user_data(user_data)
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
                    theme=theme,
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
        "star_history": star_history,
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
    user_token = _extract_bearer_token(http_request)
    try:
        user_data = await github_service.fetch_user_data(username, user_token=user_token)
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
    user_token = _extract_bearer_token(http_request)
    try:
        return await build_generation_payload(
            username,
            request.language,
            include_all_languages=False,
            workspace_scope=workspace_scope,
            user_token=user_token,
            theme=request.theme,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise map_exception_to_http(error) from error


@app.post("/api/generate/stream")
async def generate_profile_stream(request: GenerateRequestModel, http_request: Request):
    """SSE streaming endpoint that yields progress events during profile generation."""
    username = sanitize_username(request.username)
    workspace_scope = normalize_workspace_scope(http_request.headers.get(WORKSPACE_HEADER))
    await ensure_workspace_scope(workspace_scope)
    user_token = _extract_bearer_token(http_request)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Stage 1: Fetch GitHub data
            user_data = await github_service.fetch_user_data(username, user_token=user_token)
            yield "event: github_fetched\ndata: {}\n\n"

            # Stage 2: Calculate score
            gitscore = score_engine.calculate_gitscore(user_data)
            yield "event: score_calculated\ndata: {}\n\n"

            # Stage 3: Signal AI generation starting
            yield "event: ai_generating\ndata: {}\n\n"

            # Stage 4: Run AI generation
            languages_to_generate = (request.language,)
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
                            theme=request.theme,
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
            primary_output = localized_outputs[request.language]

            result = {
                "user": asdict(user_data),
                "gitscore": asdict(gitscore),
                "resume_markdown": primary_output["resume_markdown"],
                "ai_insights": primary_output["ai_insights"],
                "card_data": primary_output["card_data"],
                "social_card_html": primary_output["social_card_html"],
                "localized_outputs": localized_outputs,
                "available_content_languages": list(localized_outputs.keys()),
                "language_trends": compute_language_trends(user_data, locale=request.language),
            }

            yield f"event: completed\ndata: {json.dumps(result)}\n\n"
        except Exception as error:
            http_error = map_exception_to_http(error)
            error_payload = json.dumps({
                "code": http_error.detail.get("code", "internal_error"),
                "message": http_error.detail.get("message", str(error)),
            })
            yield f"event: error\ndata: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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


@app.post("/api/export/pdf")
async def export_pdf_post(request: ExportPdfRequestModel, http_request: Request):
    sanitized_username = sanitize_username(request.username)
    workspace_scope = normalize_workspace_scope(http_request.headers.get(WORKSPACE_HEADER))
    await ensure_workspace_scope(workspace_scope)
    try:
        payload = await build_generation_payload(
            sanitized_username,
            request.language,
            include_all_languages=False,
            workspace_scope=workspace_scope,
        )
        resume_markdown = payload["resume_markdown"]
        if request.extra_markdown:
            resume_markdown = resume_markdown + "\n\n" + request.extra_markdown
        pdf_bytes = render_service.generate_pdf_resume(resume_markdown)
    except HTTPException:
        raise
    except Exception as error:
        raise map_exception_to_http(error) from error

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="codefolio-{sanitized_username}-{request.language}.pdf"'
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


def _purge_expired_oauth_states() -> None:
    """Remove expired state tokens from the in-memory store."""
    now = time.monotonic()
    expired = [k for k, exp in _oauth_state_store.items() if now >= exp]
    for k in expired:
        del _oauth_state_store[k]


@app.get("/api/auth/github/login")
async def github_oauth_login():
    """
    Generate a GitHub OAuth authorization URL with a CSRF-protection state token.
    The client should redirect the user to the returned URL.
    """
    _purge_expired_oauth_states()

    state = secrets.token_urlsafe(32)
    _oauth_state_store[state] = time.monotonic() + _OAUTH_STATE_TTL

    client_id = settings.GITHUB_CLIENT_ID
    redirect_uri = settings.GITHUB_OAUTH_REDIRECT_URI
    scope = "read:user,repo"

    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
    )

    return {"auth_url": auth_url}


@app.get("/api/auth/github/callback")
async def github_oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle the GitHub OAuth callback.
    Validates the state parameter (CSRF protection), exchanges the code for an
    access token, and stores the token securely in Redis.
    The raw access token is never returned in the response body or logged.
    """
    _purge_expired_oauth_states()

    # Validate state (CSRF protection)
    expiry = _oauth_state_store.pop(state, None)
    if expiry is None or time.monotonic() >= expiry:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_mismatch",
                "message": "Invalid or expired OAuth state parameter.",
            },
        )

    # Exchange code for access token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
                },
            )
            response.raise_for_status()
            token_data = response.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "oauth_exchange_failed",
                "message": "Failed to exchange OAuth code for access token.",
            },
        )

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "oauth_exchange_failed",
                "message": "GitHub did not return an access token.",
            },
        )

    # Fetch the authenticated user's login to use as the Redis key
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_response.raise_for_status()
            github_user = user_response.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "oauth_exchange_failed",
                "message": "Failed to retrieve GitHub user info after token exchange.",
            },
        )

    github_login = github_user.get("login", "unknown")

    # Store the token securely in Redis (never expose it in the response)
    token_key = f"oauth:token:{github_login}"
    await redis_client.set(
        token_key,
        {"token_type": token_data.get("token_type", "bearer"), "scope": token_data.get("scope", "")},
        ttl=28800,  # 8 hours
    )
    # Store the raw token separately under a write-only key (not returned to client)
    if redis_client.client:
        await redis_client.client.setex(
            f"oauth:access_token:{github_login}",
            28800,
            access_token,
        )

    return {
        "authenticated": True,
        "login": github_login,
        "avatar_url": github_user.get("avatar_url"),
        "name": github_user.get("name"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
