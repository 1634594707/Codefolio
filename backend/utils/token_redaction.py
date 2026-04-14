"""
Token redaction utilities.

Ensures GitHub tokens are never exposed in error messages or logs.
"""
import re

# Matches common GitHub token formats:
#   ghp_...  (classic personal access tokens)
#   github_pat_...  (fine-grained personal access tokens)
#   ghs_...  (GitHub Apps installation tokens)
#   gho_...  (OAuth tokens)
#   Bearer <token>  (Authorization header value)
_TOKEN_PATTERN = re.compile(
    r"(ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{36,}|ghs_[A-Za-z0-9]{36,}|gho_[A-Za-z0-9]{36,}|Bearer\s+[A-Za-z0-9_\-\.]{20,})",
    re.IGNORECASE,
)


def redact_token(text: str) -> str:
    """Replace any GitHub token patterns in *text* with '[REDACTED]'."""
    if not text:
        return text
    return _TOKEN_PATTERN.sub("[REDACTED]", text)
