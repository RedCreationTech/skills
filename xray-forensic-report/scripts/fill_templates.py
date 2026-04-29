#!/usr/bin/env python3
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_ROOT / "assets" / "templates"

AI_FILE_PATTERNS = [
    re.compile(r"\.stories\.[^.]+$"),
    re.compile(r"(^|/)storybook(/|$)"),
    re.compile(r"(^|/).*Benchmark\.[^.]+$"),
    re.compile(r"(^|/).*Generated\.[^.]+$"),
    re.compile(r"(^|/)generated(/|$)", re.IGNORECASE),
    re.compile(r"(^|/).*fixture.*\.[^.]+$", re.IGNORECASE),
]

TEMPLATE_FILES = [
    "template-forensic-analysis.md",
    "template-management-summary.md",
    "template-technical-plan.md",
    "template-refactoring-guide.md",
]

CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".clj",
    ".cljs",
    ".cljc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".less",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".scss",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fmt_int(value: int | float | None) -> str:
    if value is None:
        return "N/A"
    return f"{int(value):,}"


def fmt_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def code(text: str | None) -> str:
    return f"`{text}`" if text else "`N/A`"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No data available for this section._"
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator_line, *body])


def markdown_bullets(items: list[str]) -> str:
    if not items:
        return "- 暂无可用数据。"
    return "\n".join(f"- {item}" for item in items)


def repo_name_from_data(data: dict, override: str | None) -> str:
    if override:
        return override
    repo_root = data.get("repo", {}).get("root")
    if repo_root:
        return Path(repo_root).name
    return "Unknown Repo"


def analysis_path(data: dict) -> str:
    return data.get("params", {}).get("path") or "."


def date_range(data: dict) -> str:
    params = data.get("params", {})
    raw = data.get("raw", {})
    since = params.get("since") or raw.get("min_day")
    until = params.get("until") or raw.get("max_day")
    if since and until:
        return f"{since} 到 {until}"
    if since:
        return f"{since} 到 latest available commit"
    if until:
        return f"repo start 到 {until}"
    return "全部可用历史"


def collect_author_stats(data: dict) -> list[dict]:
    commits = data.get("raw", {}).get("commits", [])
    stats = defaultdict(lambda: {"commits": 0, "churn": 0})
    for commit in commits:
        author = commit.get("author") or "UNKNOWN"
        stats[author]["commits"] += 1
        for file_stat in commit.get("files", []):
            stats[author]["churn"] += int(file_stat.get("added", 0) or 0) + int(
                file_stat.get("deleted", 0) or 0
            )
    result = [
        {"author": author, "commits": values["commits"], "churn": values["churn"]}
        for author, values in stats.items()
    ]
    result.sort(key=lambda row: (-row["commits"], -row["churn"], row["author"]))
    return result


def collect_ownership_summary(data: dict) -> list[dict]:
    hotspot_map = {row.get("path"): row for row in data.get("hotspots", [])}
    grouped = defaultdict(list)
    for row in data.get("ownership_long", []):
        grouped[row.get("path")].append(row)
    summary = []
    for path, rows in grouped.items():
        rows.sort(key=lambda item: (-float(item.get("churn_pct", 0.0)), -int(item.get("churn_lines", 0) or 0)))
        top = rows[0]
        summary.append(
            {
                "path": path,
                "top_author": top.get("author") or "UNKNOWN",
                "top1_pct": float(top.get("churn_pct", 0.0) or 0.0),
                "top1_churn": int(top.get("churn_lines", 0) or 0),
                "change_count": int(hotspot_map.get(path, {}).get("change_count", 0) or 0),
                "churn_lines": int(hotspot_map.get(path, {}).get("churn_lines", 0) or 0),
            }
        )
    summary.sort(
        key=lambda row: (-row["top1_pct"], -row["change_count"], -row["top1_churn"], row["path"])
    )
    return summary


def top_directory(data: dict) -> dict | None:
    directories = data.get("hotspots_dirs", [])
    return directories[0] if directories else None


def is_noise_path(path: str | None) -> bool:
    if not path:
        return True
    normalized = path.strip().lower()
    if normalized.endswith(".gitkeep"):
        return True
    return False


def is_probably_code_path(path: str | None) -> bool:
    if not path:
        return False
    suffix = Path(path).suffix.lower()
    return suffix in CODE_EXTENSIONS


def filtered_risk_rows(data: dict, actionable: bool = False) -> list[dict]:
    rows = []
    for item in data.get("risk", []):
        path = item.get("path")
        change_count = int(item.get("change_count", 0) or 0)
        churn_lines = int(item.get("churn_lines", 0) or 0)
        if is_noise_path(path):
            continue
        if churn_lines <= 0:
            continue
        if actionable and (not is_probably_code_path(path) or change_count <= 1):
            continue
        rows.append(item)
    if rows:
        return rows
    return [item for item in data.get("risk", []) if not is_noise_path(item.get("path"))]


def actionable_ownership_rows(data: dict) -> list[dict]:
    rows = []
    for item in collect_ownership_summary(data):
        if is_noise_path(item.get("path")):
            continue
        if not is_probably_code_path(item.get("path")):
            continue
        if int(item.get("change_count", 0) or 0) <= 1:
            continue
        rows.append(item)
    if rows:
        return rows
    return [item for item in collect_ownership_summary(data) if not is_noise_path(item.get("path"))]


def top_risk(data: dict) -> dict | None:
    risks = filtered_risk_rows(data, actionable=True)
    return risks[0] if risks else None


def top_coupling(data: dict) -> dict | None:
    pairs = data.get("coupling_pairs", [])
    return pairs[0] if pairs else None


def total_churn(data: dict) -> int:
    return sum(
        int(bucket.get("lines_added", 0) or 0) + int(bucket.get("lines_deleted", 0) or 0)
        for bucket in data.get("timeseries", [])
    )


def total_commits(data: dict) -> int:
    raw_commits = data.get("raw", {}).get("commits")
    if raw_commits is not None:
        return len(raw_commits)
    return sum(int(bucket.get("commits", 0) or 0) for bucket in data.get("timeseries", []))


def total_authors(data: dict) -> int | None:
    raw_authors = data.get("raw", {}).get("authors")
    if raw_authors is None:
        return None
    return len(raw_authors)


def detect_ai_files(data: dict) -> list[dict]:
    candidates = []
    by_path = {row.get("path"): row for row in data.get("risk", [])}
    for hotspot in data.get("hotspots", []):
        path = hotspot.get("path", "")
        if any(pattern.search(path) for pattern in AI_FILE_PATTERNS):
            risk_row = by_path.get(path, {})
            candidates.append(
                {
                    "path": path,
                    "change_count": int(hotspot.get("change_count", 0) or 0),
                    "churn_lines": int(hotspot.get("churn_lines", 0) or 0),
                    "risk_score": float(risk_row.get("risk_score", 0.0) or 0.0),
                }
            )
    candidates.sort(key=lambda row: (-row["risk_score"], -row["change_count"], row["path"]))
    return candidates


def build_overview_stats_table(data: dict) -> str:
    rows = [
        ["仓库", code(repo_name_from_data(data, None))],
        ["路径范围", code(analysis_path(data))],
        ["时间窗口", date_range(data)],
        ["提交数", fmt_int(total_commits(data))],
        ["作者数", fmt_int(total_authors(data)) if total_authors(data) is not None else "N/A"],
        ["总 churn", fmt_int(total_churn(data))],
        ["热点文件数", fmt_int(len(data.get("hotspots", [])))],
        ["风险文件数", fmt_int(len(data.get("risk", [])))],
    ]
    return markdown_table(["指标", "数值"], rows)


def build_hotspot_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in data.get("hotspots", [])[:limit]:
        rows.append(
            [
                code(item.get("path")),
                fmt_int(item.get("change_count")),
                fmt_int(item.get("churn_lines")),
                item.get("last_touched_at") or "N/A",
            ]
        )
    return markdown_table(["文件", "变更次数", "Churn", "最后触达"], rows)


def build_risk_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in filtered_risk_rows(data)[:limit]:
        rows.append(
            [
                code(item.get("path")),
                fmt_float(float(item.get("risk_score", 0.0) or 0.0)),
                fmt_int(item.get("cc_sum")),
                fmt_int(item.get("change_count")),
                fmt_int(item.get("churn_lines")),
                fmt_pct(float(item.get("top1_pct", 0.0) or 0.0)),
            ]
        )
    return markdown_table(["文件", "风险分数", "复杂度", "变更次数", "Churn", "Top1 占比"], rows)


def build_directory_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in data.get("hotspots_dirs", [])[:limit]:
        rows.append(
            [
                code(item.get("dir")),
                fmt_int(item.get("file_count")),
                fmt_int(item.get("change_count")),
                fmt_int(item.get("churn_lines")),
            ]
        )
    return markdown_table(["目录", "文件数", "变更次数", "Churn"], rows)


def build_author_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in collect_author_stats(data)[:limit]:
        rows.append(
            [
                code(item.get("author")),
                fmt_int(item.get("commits")),
                fmt_int(item.get("churn")),
            ]
        )
    return markdown_table(["作者", "提交数", "Churn"], rows)


def build_ownership_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in actionable_ownership_rows(data)[:limit]:
        rows.append(
            [
                code(item.get("path")),
                code(item.get("top_author")),
                fmt_pct(item.get("top1_pct")),
                fmt_int(item.get("change_count")),
                fmt_int(item.get("top1_churn")),
            ]
        )
    return markdown_table(["文件", "主贡献者", "Top1 占比", "变更次数", "Top1 Churn"], rows)


def build_coupling_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in data.get("coupling_pairs", [])[:limit]:
        rows.append(
            [
                code(item.get("a")),
                code(item.get("b")),
                fmt_int(item.get("co_change_count")),
                fmt_pct(float(item.get("support_pct", 0.0) or 0.0)),
            ]
        )
    return markdown_table(["文件 A", "文件 B", "共变更次数", "支持度"], rows)


def build_staleness_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in data.get("staleness", [])[:limit]:
        rows.append(
            [
                code(item.get("path")),
                fmt_int(item.get("age_days")),
                item.get("last_touched_at") or "N/A",
                fmt_int(item.get("change_count")),
            ]
        )
    return markdown_table(["文件", "距截止日天数", "最后触达", "窗口内变更次数"], rows)


def build_knowledge_loss_table(data: dict, limit: int = 10) -> str:
    rows = []
    for item in data.get("knowledge_loss", [])[:limit]:
        rows.append(
            [
                code(item.get("path")),
                code(item.get("top_author")),
                fmt_pct(float(item.get("top1_pct", 0.0) or 0.0)),
                item.get("last_seen") or "N/A",
                fmt_int(item.get("loss_days")),
            ]
        )
    return markdown_table(["文件", "主贡献者", "Top1 占比", "最后触达", "知识流失天数"], rows)


def build_overview_bullets(data: dict) -> str:
    bullets = []
    risk_item = top_risk(data)
    if risk_item:
        bullets.append(
            f"最高风险文件是 {code(risk_item.get('path'))}，风险分数 {fmt_float(float(risk_item.get('risk_score', 0.0) or 0.0))}，"
            f"时间窗内变更 {fmt_int(risk_item.get('change_count'))} 次。"
        )
    directory_item = top_directory(data)
    if directory_item:
        bullets.append(
            f"最活跃目录是 {code(directory_item.get('dir'))}，累计 churn {fmt_int(directory_item.get('churn_lines'))}，"
            f"涉及文件 {fmt_int(directory_item.get('file_count'))} 个。"
        )
    authors = collect_author_stats(data)
    if authors:
        top_author_item = authors[0]
        bullets.append(
            f"最活跃作者是 {code(top_author_item.get('author'))}，提交 {fmt_int(top_author_item.get('commits'))} 次，"
            f"累计 churn {fmt_int(top_author_item.get('churn'))}。"
        )
    coupling_item = top_coupling(data)
    if coupling_item:
        bullets.append(
            f"最强时间耦合配对是 {code(coupling_item.get('a'))} 与 {code(coupling_item.get('b'))}，"
            f"共变更 {fmt_int(coupling_item.get('co_change_count'))} 次，支持度 {fmt_pct(float(coupling_item.get('support_pct', 0.0) or 0.0))}。"
        )
    return markdown_bullets(bullets)


def probability_label(score: float) -> str:
    if score >= 0.65:
        return "高"
    if score >= 0.35:
        return "中"
    return "低"


def impact_label(score: float) -> str:
    if score >= 0.65:
        return "高"
    if score >= 0.35:
        return "中"
    return "低"


def build_management_risk_table(data: dict, ai_analysis: bool) -> str:
    rows = []
    risk_item = top_risk(data)
    if risk_item:
        score = float(risk_item.get("risk_score", 0.0) or 0.0)
        rows.append(
            [
                "高风险热点文件回归",
                probability_label(score),
                impact_label(score),
                f"聚焦 {code(risk_item.get('path'))}，先拆职责再补回归测试。",
            ]
        )
    ownership_items = actionable_ownership_rows(data)
    if ownership_items:
        top_owner = ownership_items[0]
        owner_score = float(top_owner.get("top1_pct", 0.0) or 0.0)
        rows.append(
            [
                "知识孤岛",
                probability_label(owner_score),
                "高" if owner_score >= 0.75 else "中",
                f"针对 {code(top_owner.get('path'))} 建立备份 owner 和轮换 review。",
            ]
        )
    coupling_item = top_coupling(data)
    if coupling_item:
        support = float(coupling_item.get("support_pct", 0.0) or 0.0)
        rows.append(
            [
                "模块时间耦合",
                probability_label(support),
                "中",
                f"优先拆分 {code(coupling_item.get('a'))} 与 {code(coupling_item.get('b'))} 的共同变更路径。",
            ]
        )
    stale_items = data.get("staleness", [])
    if stale_items:
        rows.append(
            [
                "陈旧代码唤醒风险",
                "中",
                "中",
                "对高陈旧且仍被依赖的文件先补测试，再做触碰式修改。",
            ]
        )
    if ai_analysis:
        ai_files = detect_ai_files(data)
        rows.append(
            [
                "AI 生成代码维护债务",
                "中" if ai_files else "低",
                "中",
                "对生成式代码建立标记、清理和 review 规则，避免样例文件长期漂移。",
            ]
        )
    return markdown_table(["风险项", "概率", "影响", "建议"], rows)


def build_management_resource_notes(data: dict) -> str:
    bullets = []
    authors = collect_author_stats(data)
    if authors:
        top_two = authors[:2]
        commit_total = max(1, total_commits(data))
        covered = sum(item["commits"] for item in top_two)
        bullets.append(
            f"前两位活跃作者合计承担了约 {covered / commit_total * 100:.1f}% 的提交，说明变更负载可能集中。"
        )
    directory_item = top_directory(data)
    if directory_item:
        bullets.append(
            f"最活跃目录 {code(directory_item.get('dir'))} 可优先配置专项 owner、回归脚本和 review 门槛。"
        )
    ownership_items = actionable_ownership_rows(data)
    if ownership_items:
        bullets.append(
            f"单点拥有最明显的文件是 {code(ownership_items[0].get('path'))}，应尽快安排结对和备份 owner。"
        )
    return markdown_bullets(bullets)


def build_management_decisions(data: dict) -> str:
    actions = []
    risk_item = top_risk(data)
    if risk_item:
        actions.append(
            f"批准对 {code(risk_item.get('path'))} 的专项整改窗口，至少覆盖职责拆分、测试补齐和 review 升级。"
        )
    actions.append("将高风险热点文件纳入发布前变更清单，增加回归检查和 reviewer 级别要求。")
    actions.append("为单点拥有文件建立 backup owner，避免关键模块只掌握在单人手中。")
    actions.append("把 XRay 报告纳入迭代复盘，按月追踪风险分数、耦合度和 ownership 变化。")
    return markdown_bullets(actions)


def build_followup_metrics(data: dict) -> str:
    metrics = [
        "最高风险文件的 `risk_score` 是否下降。",
        "Top 耦合配对的 `support_pct` 是否回落。",
        "Top1 owner 占比过高的文件数量是否减少。",
        "热点目录的 churn 是否回归到更可控的水平。",
    ]
    if detect_ai_files(data):
        metrics.append("AI 生成或样例性质文件是否被标记、隔离或定期清理。")
    return markdown_bullets(metrics)


def build_technical_goals(data: dict) -> str:
    rows = []
    risk_item = top_risk(data)
    if risk_item:
        rows.append(
            [
                "最高风险文件分数",
                fmt_float(float(risk_item.get("risk_score", 0.0) or 0.0)),
                "下降到更低水平并补齐测试",
            ]
        )
    coupling_item = top_coupling(data)
    if coupling_item:
        rows.append(
            [
                "最高耦合支持度",
                fmt_pct(float(coupling_item.get("support_pct", 0.0) or 0.0)),
                "拆分共同变更路径，降低共改概率",
            ]
        )
    ownership_items = actionable_ownership_rows(data)
    if ownership_items:
        rows.append(
            [
                "单点拥有",
                fmt_pct(float(ownership_items[0].get("top1_pct", 0.0) or 0.0)),
                "降低关键文件的单人控制比例",
            ]
        )
    rows.append(["整改节奏", "当前无", "形成月度复盘与回归验证节奏"])
    return markdown_table(["目标", "当前观察", "整改方向"], rows)


def risk_action(item: dict) -> str:
    cc_sum = int(item.get("cc_sum", 0) or 0)
    top1_pct = float(item.get("top1_pct", 0.0) or 0.0)
    if cc_sum >= 40:
        return "拆职责并补单元测试"
    if top1_pct >= 0.75:
        return "安排结对开发和轮换 review"
    return "收敛改动面并建立回归基线"


def build_technical_tasks(data: dict) -> str:
    lines = []
    for index, item in enumerate(filtered_risk_rows(data, actionable=True)[:5], start=1):
        priority = "P0" if index <= 2 else "P1"
        lines.append(
            f"### {priority}-T{index}: {code(item.get('path'))}\n"
            f"- 证据：风险分数 {fmt_float(float(item.get('risk_score', 0.0) or 0.0))}，复杂度 {fmt_int(item.get('cc_sum'))}，"
            f"变更次数 {fmt_int(item.get('change_count'))}。\n"
            f"- 建议动作：{risk_action(item)}。\n"
            f"- 最低验收：关键路径补测试，发布前有人做二次 review。"
        )
    if not lines:
        lines.append("### P0-T1: 暂无足够数据\n- 请先生成包含有效 `risk` 数据的报告。")
    return "\n\n".join(lines)


def build_technical_acceptance(data: dict) -> str:
    bullets = [
        "P0 文件完成职责边界梳理，避免继续把新增需求堆进同一热点文件。",
        "高风险文件补充回归测试或最小 smoke 覆盖。",
        "热点目录建立 reviewer 轮换机制，不再依赖单个 owner。",
        "整改后重新生成 XRay 报告，对比风险、耦合和 ownership 是否下降。",
    ]
    return markdown_bullets(bullets)


def build_technical_dependencies(data: dict) -> str:
    bullets = [
        "需要业务 owner 确认哪些热点文件属于核心链路，避免误拆。",
        "需要测试资源支持高风险热点文件的回归用例补齐。",
        "如果报告覆盖的是子目录，整改时仍要检查跨目录依赖和隐式耦合。",
    ]
    if detect_ai_files(data):
        bullets.append("若启用了 AI 辅助开发，需要把生成式代码纳入统一 review 与标记规范。")
    return markdown_bullets(bullets)


def build_refactoring_tasks(data: dict) -> str:
    lines = []
    for index, item in enumerate(filtered_risk_rows(data, actionable=True)[:5], start=1):
        lines.append(
            f"### T{index}: {code(item.get('path'))}\n"
            f"- 为什么现在处理：风险分数 {fmt_float(float(item.get('risk_score', 0.0) or 0.0))}，"
            f"窗口内变更 {fmt_int(item.get('change_count'))} 次。\n"
            f"- 先做什么：先画出调用入口、依赖对象、测试缺口，再决定拆分方式。\n"
            f"- 完成标准：减少同文件反复叠加修改，保证关键路径可回归。"
        )
    if not lines:
        lines.append("### T1: 暂无足够数据\n- 请先生成包含有效风险结果的报告。")
    return "\n\n".join(lines)


def build_coupling_actions(data: dict) -> str:
    bullets = []
    for item in data.get("coupling_pairs", [])[:5]:
        bullets.append(
            f"{code(item.get('a'))} 与 {code(item.get('b'))} 共变更 {fmt_int(item.get('co_change_count'))} 次，"
            f"建议检查是否存在共享状态、重复参数传递或职责混杂。"
        )
    return markdown_bullets(bullets)


def build_ai_analysis_section(data: dict, ai_analysis: bool) -> str:
    if not ai_analysis:
        return "未启用 AI 分析模式。若仓库中存在大量样例、生成或基准测试文件，可在下次生成时开启 `--ai-analysis`。"

    ai_files = detect_ai_files(data)
    if not ai_files:
        return "已启用 AI 分析模式，但当前没有识别出明显的 AI/样例/生成式文件模式。"

    rows = []
    for item in ai_files[:10]:
        rows.append(
            [
                code(item.get("path")),
                fmt_int(item.get("change_count")),
                fmt_int(item.get("churn_lines")),
                fmt_float(float(item.get("risk_score", 0.0) or 0.0)),
            ]
        )
    table = markdown_table(["文件", "变更次数", "Churn", "风险分数"], rows)
    bullets = markdown_bullets(
        [
            "这些文件模式更可能是样例、生成、storybook、benchmark 或 fixture 资产，建议确认是否需要长期维护。",
            "若文件本身不是核心业务逻辑，应考虑隔离目录、降低耦合、减少进入核心风险排行的噪声。",
            "若文件由 AI 批量生成，建议在提交规范中显式标记，并要求人工补充所有权和退出策略。",
        ]
    )
    return f"{table}\n\n{bullets}"


def build_priority_actions(data: dict) -> str:
    actions = []
    for item in filtered_risk_rows(data, actionable=True)[:3]:
        actions.append(
            f"优先检查 {code(item.get('path'))}，因为它同时具备高风险分数、较高 churn 或较高复杂度。"
        )
    coupling_item = top_coupling(data)
    if coupling_item:
        actions.append(
            f"为 {code(coupling_item.get('a'))} / {code(coupling_item.get('b'))} 建立共同变更原因清单，判断是否值得拆模块边界。"
        )
    ownership_items = actionable_ownership_rows(data)
    if ownership_items:
        actions.append(
            f"对 {code(ownership_items[0].get('path'))} 安排 backup owner 和轮换 review，降低单点风险。"
        )
    return markdown_bullets(actions)


def build_method_notes() -> str:
    return markdown_bullets(
        [
            "热点来自时间窗口内文件变更频次与 churn 聚合。",
            "风险分数综合考虑 churn、复杂度和 ownership 分散度。",
            "时间耦合的支持度口径为 `co_change_count / min(change_count[a], change_count[b])`。",
            "陈旧度与知识流失都相对于报告截止日期计算。",
        ]
    )


def build_ai_delivery_guide(data: dict) -> str:
    bullets = [
        "AI 生成补丁进入热点文件前，先让人工明确边界和回归点，避免直接堆叠到同一大文件。",
        "对生成式代码增加目录约束和命名约束，方便后续统计、清理和 ownership 分配。",
        "把 AI 产出的样例、benchmark、storybook 资产和核心业务代码分层管理。"
    ]
    if not detect_ai_files(data):
        bullets.append("当前未识别出明显的生成式文件模式，但仍建议保留上述提交规范。")
    return markdown_bullets(bullets)


def build_refactoring_validation() -> str:
    return markdown_bullets(
        [
            "每次重构前后都跑同一组 smoke 或回归测试，避免只做结构调整却没有行为验证。",
            "重构完成后重新生成 XRay 报告，观察风险、耦合和 ownership 是否向预期方向变化。",
            "若热点文件仍继续快速升温，说明拆分动作没有触到真实边界，需要复盘模块划分。 ",
        ]
    )


def build_placeholders(data: dict, repo_name_override: str | None, ai_analysis: bool) -> dict[str, str]:
    repo_name = repo_name_from_data(data, repo_name_override)
    return {
        "REPORT_TITLE": f"{repo_name} 代码演化分析报告",
        "REPO_NAME": repo_name,
        "ANALYSIS_PATH": analysis_path(data),
        "DATE_RANGE": date_range(data),
        "GENERATED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "OVERVIEW_BULLETS": build_overview_bullets(data),
        "OVERVIEW_STATS_TABLE": build_overview_stats_table(data),
        "HOTSPOT_TABLE": build_hotspot_table(data),
        "RISK_TABLE": build_risk_table(data),
        "DIRECTORY_TABLE": build_directory_table(data),
        "AUTHOR_TABLE": build_author_table(data),
        "OWNERSHIP_TABLE": build_ownership_table(data),
        "COUPLING_TABLE": build_coupling_table(data),
        "STALENESS_TABLE": build_staleness_table(data),
        "KNOWLEDGE_LOSS_TABLE": build_knowledge_loss_table(data),
        "AI_ANALYSIS_SECTION": build_ai_analysis_section(data, ai_analysis),
        "PRIORITY_ACTIONS": build_priority_actions(data),
        "METHOD_NOTES": build_method_notes(),
        "EXECUTIVE_SUMMARY_BULLETS": build_overview_bullets(data),
        "MANAGEMENT_RISK_TABLE": build_management_risk_table(data, ai_analysis),
        "MANAGEMENT_RESOURCE_NOTES": build_management_resource_notes(data),
        "MANAGEMENT_DECISIONS": build_management_decisions(data),
        "FOLLOWUP_METRICS": build_followup_metrics(data),
        "TECHNICAL_GOALS": build_technical_goals(data),
        "TECHNICAL_TASKS": build_technical_tasks(data),
        "TECHNICAL_ACCEPTANCE": build_technical_acceptance(data),
        "TECHNICAL_DEPENDENCIES": build_technical_dependencies(data),
        "REFACTORING_TASKS": build_refactoring_tasks(data),
        "COUPLING_ACTIONS": build_coupling_actions(data),
        "AI_DELIVERY_GUIDE": build_ai_delivery_guide(data),
        "REFACTORING_VALIDATION": build_refactoring_validation(),
    }


def fill_template(content: str, placeholders: dict[str, str]) -> str:
    output = content
    for key, value in placeholders.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


def ensure_all_placeholders_resolved(content: str, template_name: str) -> None:
    unresolved = sorted(set(re.findall(r"{{[A-Z0-9_]+}}", content)))
    if unresolved:
        joined = ", ".join(unresolved)
        raise SystemExit(f"Unresolved placeholders in {template_name}: {joined}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill bundled forensic markdown templates from XRay data.json")
    parser.add_argument("--data", required=True, help="Path to XRay data.json")
    parser.add_argument("--output", required=True, help="Output directory for generated markdown reports")
    parser.add_argument("--repo-name", help="Optional repository display name")
    parser.add_argument("--ai-analysis", action="store_true", help="Enable AI-oriented heuristics")
    args = parser.parse_args()

    data_path = Path(args.data).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_json(data_path)
    placeholders = build_placeholders(data, args.repo_name, args.ai_analysis)

    for template_name in TEMPLATE_FILES:
        template_path = TEMPLATES_DIR / template_name
        if not template_path.is_file():
            raise SystemExit(f"Missing template: {template_path}")
        content = template_path.read_text(encoding="utf-8")
        rendered = fill_template(content, placeholders)
        ensure_all_placeholders_resolved(rendered, template_name)
        output_name = template_name.replace("template-", "report-")
        (output_dir / output_name).write_text(rendered, encoding="utf-8")
        print(f"[OK] generated={output_dir / output_name}")


if __name__ == "__main__":
    main()
