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
- By default the wrapper uses the bundled `tools/xray`.
- If the user explicitly provides `xray-tool-root` or `XRAY_TOOL_ROOT`, that location overrides the bundled tool. Both an `xray` directory and its parent repo root are accepted.
- By default it writes into `<repo>/target/xray-forensic-report-<timestamp>/`.
- The markdown reports are generated from `data.json`, not by parsing HTML.
