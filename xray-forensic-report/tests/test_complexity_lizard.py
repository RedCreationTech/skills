#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
HELPER = SKILL_ROOT / "tools" / "xray" / "scripts" / "complexity_lizard.py"


SAMPLES = {
    "plain.js": """
export function choose(flag) {
  if (flag) return 1;
  return 0;
}
""",
    "Component.jsx": """
export function Component({ok}) {
  return ok ? <div>yes</div> : <span>no</span>;
}
""",
    "plain.ts": """
export function choose(flag: boolean): number {
  if (flag) return 1;
  return 0;
}
""",
    "Component.tsx": """
type Props = { ok: boolean };
export function Component(props: Props) {
  return props.ok ? <div>yes</div> : <span>no</span>;
}
""",
    "Component.vue": """
<script setup lang="ts">
function choose(flag: boolean): number {
  if (flag) return 1;
  return 0;
}
</script>
<template><div>demo</div></template>
""",
    "Example.java": """
class Example {
  int choose(boolean flag) {
    if (flag) return 1;
    return 0;
  }
}
""",
    "Example.cs": """
class Example {
  int Choose(bool flag) {
    if (flag) return 1;
    return 0;
  }
}
""",
}


EXPECTED_LANG = {
    "plain.js": "javascript",
    "Component.jsx": "javascript",
    "plain.ts": "typescript",
    "Component.tsx": "typescript",
    "Component.vue": "vue",
    "Example.java": "java",
    "Example.cs": "csharp",
}


class ComplexityLizardSmokeTest(unittest.TestCase):
    def test_supported_languages_emit_function_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            for path, content in SAMPLES.items():
                (repo / path).write_text(content.strip() + "\n", encoding="utf-8")

            file_list = repo / "files.txt"
            file_list.write_text("\n".join(SAMPLES) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(HELPER),
                    "--repo",
                    str(repo),
                    "--file-list",
                    str(file_list),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            payload = json.loads(proc.stdout)
            self.assertEqual(payload["errors"], [])

            by_path = {}
            for row in payload["functions"]:
                by_path.setdefault(row["path"], []).append(row)

            for path, expected_lang in EXPECTED_LANG.items():
                self.assertIn(path, by_path, f"no function rows for {path}")
                self.assertTrue(
                    any(row["lang"] == expected_lang for row in by_path[path]),
                    f"wrong language mapping for {path}: {by_path[path]}",
                )
                self.assertTrue(
                    all(int(row["cc"]) >= 1 for row in by_path[path]),
                    f"invalid CCN for {path}: {by_path[path]}",
                )
                self.assertTrue(
                    all("cognitive_complexity" in row for row in by_path[path]),
                    f"missing CogC for {path}: {by_path[path]}",
                )
                self.assertTrue(
                    any(int(row["cognitive_complexity"]) >= 1 for row in by_path[path]),
                    f"invalid CogC for {path}: {by_path[path]}",
                )


if __name__ == "__main__":
    unittest.main()
