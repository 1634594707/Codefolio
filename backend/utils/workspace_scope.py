import re


WORKSPACE_HEADER = "X-Codefolio-Workspace"
DEFAULT_WORKSPACE_SCOPE = "global"
_WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{5,63}$")


def normalize_workspace_scope(raw_value: str | None) -> str:
    candidate = (raw_value or "").strip()
    if not candidate:
        return DEFAULT_WORKSPACE_SCOPE
    if not _WORKSPACE_PATTERN.fullmatch(candidate):
        return DEFAULT_WORKSPACE_SCOPE
    return candidate


def scoped_cache_key(base_key: str, workspace_scope: str) -> str:
    normalized_scope = normalize_workspace_scope(workspace_scope)
    if normalized_scope == DEFAULT_WORKSPACE_SCOPE:
        return base_key
    return f"ws:{normalized_scope}:{base_key}"
