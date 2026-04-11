"""
Derive monthly language-mix trends from GitHub repo language bytes and pushedAt.

For each month-end in the last 12 months, include repos whose last push is on or
before that date, sum language bytes, normalize to percentages, then keep the
top 5 languages as of the latest month and emit their series.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from models import Repository, UserData


def _parse_pushed(pushed_at: str) -> Optional[date]:
    if not pushed_at:
        return None
    try:
        return datetime.strptime(pushed_at[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _shift_month(y: int, m: int, delta: int) -> Tuple[int, int]:
    m += delta
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return y, m


def _month_end(y: int, m: int) -> date:
    last = calendar.monthrange(y, m)[1]
    return date(y, m, last)


def _rolling_month_points(n: int, locale: str) -> List[Tuple[str, date]]:
    """Oldest first: (axis label, month end date)."""
    today = date.today()
    y, m = today.year, today.month
    out: List[Tuple[str, date]] = []
    for i in range(n):
        yy, mm = _shift_month(y, m, -(n - 1 - i))
        end = _month_end(yy, mm)
        if locale == "zh":
            label = f"{yy}年{mm}月"
        else:
            label = f"{calendar.month_abbr[mm]} '{yy % 100:02d}"
        out.append((label, end))
    return out


def _mix_at_cutoff(repositories: List[Repository], cutoff: date) -> Dict[str, float]:
    langs: Dict[str, int] = {}
    for repo in repositories:
        pushed = _parse_pushed(repo.pushed_at)
        if pushed is None or pushed > cutoff:
            continue
        if not repo.languages:
            continue
        for lang, size in repo.languages.items():
            langs[lang] = langs.get(lang, 0) + size
    total = sum(langs.values())
    if total == 0:
        return {}
    return {k: 100.0 * v / total for k, v in langs.items()}


def compute_language_trends(user_data: UserData, locale: str = "en") -> List[Dict[str, Any]]:
    """
    Returns JSON-serializable list:
    [{"language": str, "data": [{"month": str, "percentage": float}, ...]}, ...]
    """
    repos = user_data.repositories
    if not repos:
        return []

    points = _rolling_month_points(12, locale if locale in ("en", "zh") else "en")
    last_cutoff = points[-1][1]
    mix_last = _mix_at_cutoff(repos, last_cutoff)
    if not mix_last:
        return []

    top5 = [name for name, _ in sorted(mix_last.items(), key=lambda x: -x[1])[:5]]

    result: List[Dict[str, Any]] = []
    for lang in top5:
        data: List[Dict[str, Any]] = []
        for label, end in points:
            mix = _mix_at_cutoff(repos, end)
            pct = mix.get(lang, 0.0)
            data.append({"month": label, "percentage": round(pct, 1)})
        result.append({"language": lang, "data": data})
    return result
