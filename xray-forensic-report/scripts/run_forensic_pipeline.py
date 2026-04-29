#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
BUNDLED_XRAY_ROOT = SKILL_ROOT / "tools" / "xray"


def fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_tool_root(raw_root: str | Path | None) -> Path | None:
    if not raw_root:
        return None
    root = Path(raw_root).expanduser()
    candidates = [root, root / "xray"]
    for candidate in candidates:
        if (candidate / "bb.edn").is_file():
            return candidate.resolve()
    return None


def find_tool_root(raw_override: str | None) -> Path:
    candidates = []
    if raw_override:
        candidates.append(raw_override)
    env_root = os.environ.get("XRAY_TOOL_ROOT")
    if env_root:
        candidates.append(env_root)
    candidates.append(BUNDLED_XRAY_ROOT)

    for raw_root in candidates:
        root = normalize_tool_root(raw_root)
        if root:
            return root

    fail(
        "Cannot find the XRay tool root. "
        "Use the bundled tools/xray, or set XRAY_TOOL_ROOT / --xray-tool-root "
        "to either the xray directory or its parent repository root."
    )


def require_absolute_dir(raw_path: str, label: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        fail(f"{label} must be an absolute path: {raw_path}")
    if not path.exists():
        fail(f"{label} does not exist: {path}")
    if not path.is_dir():
        fail(f"{label} is not a directory: {path}")
    return path.resolve()


def ensure_git_repo(repo: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or result.stdout.strip() != "true":
        fail(f"Not a Git repository: {repo}")


def parse_bool(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        fail(f"Boolean value must be true or false, got: {value}")
    return normalized


def resolve_output_path(repo: Path, raw_out: str | None) -> Path:
    if raw_out:
        out = Path(raw_out).expanduser()
        if not out.is_absolute():
            out = repo / out
        return out.resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return (repo / "target" / f"xray-forensic-report-{stamp}").resolve()


def resolve_optional_file(repo: Path, raw_path: str | None, label: str) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = repo / path
    path = path.resolve()
    if not path.exists():
        fail(f"{label} does not exist: {path}")
    if path.is_dir():
        fail(f"{label} must be a file path: {path}")
    return path


def build_xray_command(args: argparse.Namespace, repo: Path, out_dir: Path, tool_root: Path) -> list[str]:
    command = [
        "bb",
        "-f",
        str(tool_root / "bb.edn"),
        "report",
        "--repo",
        str(repo),
        "--out",
        str(out_dir),
        "--topN",
        str(args.topN),
        "--include-raw",
        parse_bool(args.include_raw),
        "--no-merges",
        parse_bool(args.no_merges),
    ]

    if args.branch:
        command.extend(["--branch", args.branch, "--all", "false"])
    else:
        command.extend(["--all", "true"])

    if args.since:
        command.extend(["--since", args.since])
    if args.until:
        command.extend(["--until", args.until])
    if args.path:
        command.extend(["--path", args.path])

    config_path = resolve_optional_file(repo, args.config, "config")
    if not config_path:
        auto_config = repo / "xray.edn"
        if auto_config.is_file():
            config_path = auto_config.resolve()
    if config_path:
        command.extend(["--config", str(config_path)])

    return command


def build_template_command(args: argparse.Namespace, data_path: Path, reports_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "fill_templates.py"),
        "--data",
        str(data_path),
        "--output",
        str(reports_dir),
    ]
    if args.repo_name:
        command.extend(["--repo-name", args.repo_name])
    if args.ai_analysis:
        command.append("--ai-analysis")
    return command


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an XRay HTML report plus four forensic markdown reports."
    )
    parser.add_argument("repo", help="Absolute path to the target local Git repository")
    parser.add_argument(
        "--xray-tool-root",
        help="Override the XRay tool location. Accepts either the xray directory or its parent repository root.",
    )
    parser.add_argument("--out", help="Output directory. Relative paths are resolved under the repo.")
    parser.add_argument("--since", help="Since date in YYYY-MM-DD")
    parser.add_argument("--until", help="Until date in YYYY-MM-DD")
    parser.add_argument("--branch", help="Analyze only this branch. Implies --all false.")
    parser.add_argument("--path", help="Analyze only this repo subpath")
    parser.add_argument("--config", help="Explicit xray.edn path")
    parser.add_argument("--topN", type=int, default=30, help="Default report TopN")
    parser.add_argument("--include-raw", default="true", help="true or false")
    parser.add_argument("--no-merges", default="true", help="true or false")
    parser.add_argument("--repo-name", help="Display name used in generated markdown reports")
    parser.add_argument(
        "--ai-analysis",
        action="store_true",
        help="Enable AI-oriented heuristics in the markdown reports",
    )
    args = parser.parse_args()

    if shutil.which("bb") is None:
        fail("babashka is required but 'bb' was not found in PATH")

    repo = require_absolute_dir(args.repo, "repo")
    ensure_git_repo(repo)
    tool_root = find_tool_root(args.xray_tool_root)
    out_dir = resolve_output_path(repo, args.out)
    reports_dir = out_dir / "reports"

    xray_command = build_xray_command(args, repo, out_dir, tool_root)

    print(f"[INFO] repo={repo}")
    print(f"[INFO] out={out_dir}")
    print(f"[INFO] tool_root={tool_root}")
    if args.since or args.until:
        print(f"[INFO] date_window={args.since or 'BEGIN'}..{args.until or 'END'}")

    subprocess.run(xray_command, check=True)

    data_path = out_dir / "data.json"
    if not data_path.is_file():
        fail(f"Expected data.json was not generated: {data_path}")

    template_command = build_template_command(args, data_path, reports_dir)
    subprocess.run(template_command, check=True)

    report_files = [
        reports_dir / "report-forensic-analysis.md",
        reports_dir / "report-management-summary.md",
        reports_dir / "report-technical-plan.md",
        reports_dir / "report-refactoring-guide.md",
    ]
    for report_file in report_files:
        if not report_file.is_file():
            fail(f"Expected report file was not generated: {report_file}")

    print(f"[OK] report_dir={out_dir}")
    print(f"[OK] index_html={out_dir / 'index.html'}")
    print(f"[OK] data_json={data_path}")
    for report_file in report_files:
        print(f"[OK] markdown_report={report_file}")


if __name__ == "__main__":
    main()
