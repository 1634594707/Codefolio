"""
Action generation service for repository benchmarking.
"""
from __future__ import annotations

from benchmark_models import ActionItem, DimensionScore


_ACTION_COPY = {
    "en": {
        "first_impression": (
            "Strengthen the README hero section",
            "Benchmark repositories make the project legible within a few seconds.",
            [
                "Add one screenshot, GIF, or architecture visual near the top of the README",
                "Keep the top badge set focused on trust and adoption signals",
            ],
            "S",
            4,
        ),
        "onboarding": (
            "Add a runnable quickstart path",
            "Benchmark repositories reduce setup friction and shorten time-to-value.",
            [
                "Add a Quickstart or Getting Started section with exact commands",
                "Link to one example, starter, or demo path",
            ],
            "M",
            5,
        ),
        "engineering_quality": (
            "Expose engineering trust signals",
            "Visible CI, tests, and security posture increase confidence for adopters.",
            [
                "Add or document CI workflows",
                "Surface test, typing, or security checks in the repository",
            ],
            "M",
            5,
        ),
        "releases": (
            "Make release cadence more visible",
            "Benchmarks communicate project maturity through releases and changelogs.",
            [
                "Publish releases with notes or changelog entries",
                "Document what changed between versions",
            ],
            "M",
            4,
        ),
        "community": (
            "Lower the cost of contribution",
            "Benchmarks make it easier for contributors to understand how to participate.",
            [
                "Add CONTRIBUTING, issue templates, or a code of conduct",
                "Describe the preferred way to report issues or submit changes",
            ],
            "M",
            4,
        ),
        "discovery": (
            "Improve repository discovery signals",
            "Benchmarks are easier to find and evaluate through topics and clearer metadata.",
            [
                "Add more specific GitHub topics",
                "Tighten the repository description around the actual use case",
            ],
            "S",
            4,
        ),
        "compliance": (
            "Clarify licensing and compliance posture",
            "Missing or unclear licensing reduces confidence for reuse.",
            [
                "Add a recognized license file",
                "Make the repository license explicit in the README or metadata",
            ],
            "S",
            4,
        ),
        "positioning": (
            "Sharpen project positioning",
            "Benchmark repositories explain what they are for and who they serve more clearly.",
            [
                "Rewrite the repository description as a one-line value proposition",
                "Structure the README so the core use case appears before implementation details",
            ],
            "S",
            5,
        ),
    },
    "zh": {
        "first_impression": (
            "强化 README 首屏表达",
            "标杆仓库能在很短时间内让访问者理解项目价值。",
            [
                "在 README 顶部加入截图、GIF 或架构图",
                "把徽章聚焦到可信度和采用度信号",
            ],
            "S",
            4,
        ),
        "onboarding": (
            "补齐可执行的快速上手路径",
            "标杆仓库显著降低了首次体验和配置成本。",
            [
                "增加 Quickstart 或 Getting Started，并给出准确命令",
                "提供一个可直接运行的示例、starter 或 demo 路径",
            ],
            "M",
            5,
        ),
        "engineering_quality": (
            "补足工程可信度信号",
            "CI、测试和安全策略会直接影响使用者的信任。",
            [
                "补充或公开 CI workflow",
                "在仓库中暴露测试、类型检查或安全检查方式",
            ],
            "M",
            5,
        ),
        "releases": (
            "让发布节奏更可见",
            "发布记录和变更说明会强化项目成熟度判断。",
            [
                "发布带说明的版本或 changelog",
                "清晰记录版本之间的变化",
            ],
            "M",
            4,
        ),
        "community": (
            "降低协作接入门槛",
            "标杆仓库通常更清楚地告诉贡献者如何参与。",
            [
                "补充 CONTRIBUTING、Issue Template 或行为准则",
                "说明提交问题和变更的推荐方式",
            ],
            "M",
            4,
        ),
        "discovery": (
            "增强仓库可发现性",
            "更清晰的 metadata 和 topics 会提升被搜索和判断的效率。",
            [
                "增加更具体的 GitHub topics",
                "把仓库描述聚焦到真实使用场景",
            ],
            "S",
            4,
        ),
        "compliance": (
            "明确许可与合规状态",
            "缺失或模糊的许可证会直接降低复用意愿。",
            [
                "添加标准许可证文件",
                "在 README 或仓库 metadata 中明确许可证信息",
            ],
            "S",
            4,
        ),
        "positioning": (
            "收紧项目定位表达",
            "标杆仓库通常更清晰地说明项目用途和面向对象。",
            [
                "把仓库描述改写成一句明确的价值主张",
                "调整 README 结构，让核心使用场景先于实现细节出现",
            ],
            "S",
            5,
        ),
    },
}


def _deadline_for_effort(effort: str) -> str:
    if effort == "S":
        return "7d"
    if effort == "M":
        return "30d"
    return "90d"


def _effort_value(effort: str) -> int:
    return {"S": 1, "M": 2, "L": 3}[effort]


def generate_action_items(
    mine_scores: dict[str, DimensionScore],
    benchmark_scores: dict[str, dict[str, DimensionScore]],
    language: str = "en",
) -> list[ActionItem]:
    """
    Generate prioritized actions from dimension gaps.
    """
    copy = _ACTION_COPY.get(language, _ACTION_COPY["en"])
    actions: list[ActionItem] = []

    for dimension, mine_score in mine_scores.items():
        peer_scores = benchmark_scores.get(dimension, {})
        if not peer_scores:
            continue

        peer_best = max(score.to_numeric() for score in peer_scores.values())
        mine_numeric = mine_score.to_numeric()
        if peer_best <= mine_numeric:
            continue

        title, rationale, checklist, effort, base_impact = copy[dimension]
        impact = min(5, max(base_impact, base_impact + peer_best - mine_numeric - 1))
        priority_score = round(impact / _effort_value(effort), 2)

        actions.append(
            ActionItem(
                action_id=f"action_{dimension}",
                dimension=dimension,
                title=title,
                rationale=rationale,
                effort=effort,
                impact=impact,
                priority_score=priority_score,
                checklist=checklist,
                suggested_deadline=_deadline_for_effort(effort),
            )
        )

    return sorted(actions, key=lambda item: item.priority_score, reverse=True)
