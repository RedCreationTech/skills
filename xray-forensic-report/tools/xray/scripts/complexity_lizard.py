#!/usr/bin/env python3
"""Function-level complexity adapter for XRay.

This script intentionally keeps Lizard behind a small JSON contract so the
Babashka/Clojure core does not need Python-specific parsing logic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import lizard
    from lizard_ext.lizardcognitive import LizardExtension as CognitiveExtension
except ImportError as exc:
    print(
        "[ERROR] Python package 'lizard' is required for JS/TS/Vue/Java/C# "
        "complexity analysis. Install the pinned XRay dependency first.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


LANG_BY_SUFFIX = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".java": "java",
    ".cs": "csharp",
}

# Use Lizard's own extension assembly so the standard preprocessing, token,
# line and condition counters remain active. Injecting CognitiveExtension alone
# would drop the normal metric pipeline and produce incomplete/false results.
ANALYZER = lizard.FileAnalyzer(lizard.get_extensions(["cognitive"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze JS/TS/Vue/Java/C# files with Lizard and emit XRay JSON."
    )
    parser.add_argument("--repo", required=True, help="Absolute repository root")
    parser.add_argument(
        "--file-list",
        required=True,
        help="UTF-8 file containing one repo-relative path per line",
    )
    return parser.parse_args()


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_relative_path(repo: Path, raw_path: str) -> tuple[str, Path] | None:
    raw_path = raw_path.strip()
    if not raw_path:
        return None

    candidate = Path(raw_path)
    abs_path = candidate if candidate.is_absolute() else repo / candidate

    try:
        abs_path = abs_path.resolve()
        rel_path = abs_path.relative_to(repo).as_posix()
    except (OSError, ValueError):
        return None

    if not abs_path.is_file():
        return None
    if abs_path.suffix.lower() not in LANG_BY_SUFFIX:
        return None
    return rel_path, abs_path


def function_row(rel_path: str, suffix: str, fn: object) -> dict[str, object]:
    name = getattr(fn, "name", None) or "<anonymous>"
    long_name = getattr(fn, "long_name", None) or name
    parameters = getattr(fn, "parameters", None)
    parameter_count = getattr(fn, "parameter_count", None)
    if parameter_count is None:
        parameter_count = len(parameters or [])

    return {
        "path": rel_path,
        "fn": str(name),
        "long_name": str(long_name),
        "cc": safe_int(getattr(fn, "cyclomatic_complexity", None), 1),
        "cognitive_complexity": safe_int(
            getattr(fn, "cognitive_complexity", None), 0
        ),
        "nloc": safe_int(getattr(fn, "nloc", None), 0),
        "tokens": safe_int(getattr(fn, "token_count", None), 0),
        "params": safe_int(parameter_count, 0),
        "start_line": safe_int(getattr(fn, "start_line", None), 0),
        "end_line": safe_int(getattr(fn, "end_line", None), 0),
        "lang": LANG_BY_SUFFIX[suffix],
        "analyzer": "lizard+cognitive",
    }


def analyze_file(repo: Path, raw_path: str) -> list[dict[str, object]]:
    normalized = normalize_relative_path(repo, raw_path)
    if normalized is None:
        return []

    rel_path, abs_path = normalized
    suffix = abs_path.suffix.lower()
    result = ANALYZER(str(abs_path))
    rows = [function_row(rel_path, suffix, fn) for fn in result.function_list]
    rows.sort(
        key=lambda row: (
            safe_int(row.get("start_line"), 0),
            str(row.get("fn", "")),
        )
    )
    return rows


def main() -> None:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    file_list = Path(args.file_list).expanduser().resolve()

    if not repo.is_dir():
        print(f"[ERROR] repo is not a directory: {repo}", file=sys.stderr)
        raise SystemExit(2)
    if not file_list.is_file():
        print(f"[ERROR] file list does not exist: {file_list}", file=sys.stderr)
        raise SystemExit(2)

    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []

    for raw_path in file_list.read_text(encoding="utf-8").splitlines():
        try:
            rows.extend(analyze_file(repo, raw_path))
        except Exception as exc:
            errors.append(
                {
                    "path": raw_path.strip(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    payload = {
        "schema_version": "1.1",
        "analyzer": "lizard+cognitive",
        "functions": rows,
        "errors": errors,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
