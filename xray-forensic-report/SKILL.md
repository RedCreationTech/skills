---
name: xray-forensic-report
description: Generate an offline XRay HTML report plus four forensic markdown reports for a local Git repository over a selected time window. Use this when the user wants a reusable code-forensics package for a local repo, with optional path, branch, config, topN, output, and AI-analysis overrides.
---

# XRay Forensic Report

Use this skill when the user wants the full forensic bundle, not just the HTML dashboard:

- offline `index.html`
- `data.json` and `meta.json`
- four markdown reports under `reports/`

This skill runs a bundled standalone `xray` CLI under `tools/xray` and then fills markdown templates from the generated `data.json`.
It does not depend on the original `bbtools` repository layout.

## Complexity coverage

Function-level complexity is supported for:

- Clojure: `.clj`, `.cljs`, `.cljc` via the bundled `rewrite-clj` analyzer
- JavaScript: `.js`, `.jsx`, including React JSX
- TypeScript: `.ts`, `.tsx`, including React TSX
- Vue single-file components: `.vue`
- Java: `.java`
- C#: `.cs`

The JS/TS/Vue/Java/C# backend uses the pinned Python `lizard` dependency and emits
function-level CCN, Cognitive Complexity (CogC), NLOC, token count, parameter count,
and source line ranges. Clojure/CLJS/CLJC use a Lisp-aware Cognitive Complexity
implementation built on the existing `rewrite-clj` AST path.

By default, XRay treats CogC > 15 as a function-level maintainability warning.
For file-level Risk, Cognitive Complexity uses a threshold-aware pressure metric:
`max CogC + sum(max(0, CogC - 15))`, rather than raw CogC sum. This avoids
penalizing files simply because they contain many easy functions.

The file-level complexity component used by Risk is 40% normalized CCN + 60%
normalized cognitive pressure while retaining the existing top-level risk weights.

## Required input

- `repo`: absolute path to a local Git repository

## Optional input

- `since`, `until`: `YYYY-MM-DD`
- `path`
- `branch`
- `config`
- `out`
- `topN`
- `include-raw`
- `no-merges`
- `ai-analysis`
- `repo-name`
- `xray-tool-root`

If the user does not provide `since` or `until`, the workflow may run on the repo's available history. If the user asks for a specific window, pass it through exactly.

## Workflow

1. Validate that `repo` is an absolute local Git repository path.
2. Run the bundled wrapper:

```sh
python3 scripts/run_forensic_pipeline.py /ABS/PATH/TO/REPO
```

3. Pass through any explicit overrides from the user.
4. After execution, return:
   - the report directory
   - `index.html`
   - `data.json`
   - the four generated markdown report paths

## Notes

- The wrapper requires `bb` in `PATH`.
- For repositories containing JS/TS/Vue/Java/C#, install the pinned complexity dependency with `python3 -m pip install -r xray-forensic-report/requirements.txt`.
- Smoke-test all supported non-Clojure language adapters with `python3 xray-forensic-report/tests/test_complexity_lizard.py`.
- Validate the Lisp-aware CogC rules with `cd xray-forensic-report/tools/xray && bb -cp src:test -e "(require 'xray.metrics.cognitive-test)(clojure.test/run-tests 'xray.metrics.cognitive-test)"`.
- By default the wrapper uses the bundled `tools/xray`.
- If the user explicitly provides `xray-tool-root` or `XRAY_TOOL_ROOT`, that location overrides the bundled tool. Both an `xray` directory and its parent repo root are accepted.
- By default it writes into `<repo>/target/xray-forensic-report-<timestamp>/`.
- The markdown reports are generated from `data.json`, not by parsing HTML.
