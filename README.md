# redcreation/skills

A collection of agent skills for AI coding assistants, covering video publishing, evidence video, content pipelines, test evidence, and code forensics.

## Installation

Install individual skills using the `skills` CLI:

```bash
# Bilibili video uploader with auto metadata generation
npx skills@latest add redcreation/skills --skill bilibili-uploader

# Movie commentary pipeline: subtitles → script → TTS → rendered video
npx skills@latest add redcreation/skills --skill movie-commentary-video-pipeline

# Evidence video: real screen recording with outline, subtitles, narration
npx skills@latest add redcreation/skills --skill agent-evidence-video

# Test evidence: assertion-driven test videos, bug reproductions, reports
npx skills@latest add redcreation/skills --skill test-evidence

# Git repository forensic report generator
npx skills@latest add redcreation/skills --skill xray-forensic-report

# Frontend-to-fullstack transformation pipeline
npx skills@latest add redcreation/skills --skill frontend-to-fullstack
```

---

## Skills

### agent-evidence-video

**What it does**

Turns real software changes into verifiable demonstration videos: a persistent chapter outline on the left, actual screen recording on the right, visible pointer/input hints, synchronized Chinese subtitles and per-line narration. It emphasizes assertion-backed scenes and refuses to present mocked responses or edited-together success as real behavior.

**Deliverables**

- A chaptered MP4 with outline, subtitles, narration and embedded chapters.
- `subtitles.srt` and `chapters.ffmeta` sidecars.
- Raw chapter recordings retained separately from the composed output.

**Scripts**

| Script | Purpose |
|--------|---------|
| `scripts/interaction.js` | Optional Playwright pointer and input-hint overlay |
| `scripts/mimo_tts.py` | Per-line MiMo TTS authenticated only through `MIMO_API_KEY` |
| `scripts/compose.py` | Composes captures, narration, outline, captions, SRT and chapters |

**Use this skill when you want to**

- Demonstrate a bug fix, new feature or end-to-end flow with real on-screen actions.
- Produce a reviewable evidence video rather than a promotional or fictional clip.
- Add Chinese subtitles and narration to an existing operation recording.

**Prerequisites**

- Python 3, Pillow, a CJK font and ffmpeg/ffprobe.
- Playwright only when the optional interaction overlay is used.
- `MIMO_API_KEY` only when MiMo narration is requested; never commit it.

---

### test-evidence

**What it does**

Turns a real test run into an auditable evidence chain: case → step → assertion → evidence timestamp → defect → report conclusion. It is opinionated about not overstating results: unexecuted is not passed, failures are never edited out, and every report number must reconcile with the evidence.

**Deliverables**

- A chaptered test-run video with a persistent verdict sidebar, raw screen recording, subtitles and per-line narration.
- An annotated bug-reproduction video with the shortest repro path, expected vs. actual, red boxes and numbered callouts.
- A bug list keyed to case IDs, and a test report filled from the project template.
- `test-run.json` with steps, assertions, timestamps, screenshots, console errors and failed requests.

**Scripts**

| Script | Purpose |
|--------|---------|
| `scripts/interaction.js` | Playwright pointer, click ripple and input hint overlay; sensitive fields hidden by default |
| `scripts/evidence.js` | Records steps, assertions, screenshots, timestamps and console/network errors into `test-evidence/1` JSON |
| `scripts/annotate.py` | Adds a header band, red boxes and numbered callouts to a bug recording |
| `scripts/compose.py` | Composes 1920×1080 H.264/AAC video with verdict sidebar, captions, narration, SRT, chapters and a verdict summary |
| `scripts/mimo_tts.py` | Per-line MiMo TTS; reads `MIMO_API_KEY` from the environment only |
| `scripts/verify.py` | Checks resolution, codecs, chapters, full decode, SRT boundaries, manifest timing and evidence/report consistency |

**Use this skill when you want to**

- Run a test case set end to end and produce reviewable evidence rather than a highlight reel.
- Reproduce and annotate a defect for a bug report or developer handoff.
- Fill a project test report whose numbers are traceable to assertions and recorded evidence.
- Add Chinese subtitles and narration to test-run or bug videos.

**Prerequisites**

- Python 3, Pillow, ffmpeg/ffprobe and a CJK font.
- Playwright only for the optional capture helpers.
- `MIMO_API_KEY` only when MiMo narration is requested; never commit it.

---

### frontend-to-fullstack

**What it does**

An orchestrator skill that transforms a pure frontend project (React, Vue, or plain HTML/JS) into a production-grade full-stack product through a standardized 6-phase pipeline.

**Pipeline phases**

| Phase | What happens |
|-------|-------------|
| Pre-Flight | Detect project type, handle lightweight Node.js backends, extract embedded data from frontend code |
| C4 Architecture | Analyze business domains, data entities, and API surface using `c4-architecture-c4-architecture` skill |
| Restructuring | Split frontend/backend directories, set up Clojure backend skeleton, add file upload infrastructure |
| Backend APIs | Implement database, migrations, seed data, and REST APIs per business domain using `clojure-fullstack-development` skill |
| Integration | Browser validation, API documentation, quality gates |
| E2E Testing | Playwright test suite covering all pages and API endpoints |

**Use this skill when you want to**

- Turn a pure frontend prototype into a production-ready full-stack product
- Migrate a lightweight Node.js backend to a proper Clojure backend
- Extract hardcoded mock data from JS/TS files into SQL database migrations
- Add comprehensive Playwright E2E tests to an existing frontend project
- Establish AGENTS.md conventions and architecture documentation for a codebase

**Delegated skills**

- `c4-architecture-c4-architecture` — architecture analysis and diagram generation
- `clojure-fullstack-development` — backend API implementation (Kit framework, Integrant, SQLite)

---

### bilibili-uploader

**What it does**

A Python-based automation layer on top of [biliup-rs](https://github.com/biliup/biliup-rs) that turns a raw video file into a published Bilibili post with minimal human intervention.

**Scripts**

| Script | Purpose |
|--------|---------|
| `scripts/bilibili_uploader.py` | Low-level wrapper around `biliup upload/login`. Handles cookie paths, CLI quirks (`--user-cookie` must come before subcommands), and configurable defaults (tid, tags, copyright, upload line). |
| `scripts/auto_generate_meta.py` | Analyzes a video with `ffprobe` and cleans the filename to auto-generate a title, description, tags, and zone (tid). Contains a keyword map that routes `rust`/`docker`/`k8s` to tech zones, `lol`/`fps` to gaming, `吉他`/`钢琴` to music, etc. |
| `scripts/auto_upload.py` | **One-click workflow**: calls `auto_generate_meta` → previews metadata → asks for confirmation → uploads via `bilibili_uploader.py`. Supports `--dry-run`, `-y` (skip confirm), `--dtime` (scheduled publish), `--cover`, and `--extra-tags`. |

**Use this skill when you want to**

- Upload a video to Bilibili without manually filling title/description/tags every time.
- Batch-publish a folder of videos where metadata can be inferred from filenames.
- Schedule posts (`--dtime "2025-04-20 18:00"`) or preview metadata before committing (`--dry-run`).
- Automate a content pipeline where the AI assistant prepares the video and you only need to confirm or skip confirmation.

**Prerequisites**

- `biliup` binary installed and in `PATH`.
- `ffprobe` (bundled with ffmpeg) for automatic metadata extraction.
- Run `biliup -u <cookie-path> login` once to persist credentials.

---

### movie-commentary-video-pipeline

**What it does**

A comprehensive skill specification for building a reproducible local pipeline that transforms a film (plus its subtitles) into a commentary/recap video. It provides the architecture, file layout, processing rules, and quality guardrails—not a single monolithic script, but a blueprint the AI assistant follows to scaffold and wire the pipeline in your repo.

**Key deliverables the skill produces**

- `commentary/commentary_script.md` — analysis-driven narration script (never quotes dialogue verbatim).
- `commentary/narration_manifest.json` — machine-readable chunks with timing budgets and beat mappings.
- `commentary/clip_plan.json` — scene-aware clip windows with start/end, narration mapping, and transition notes.
- `outputs/voiceover.wav` + `outputs/final_commentary.mp4` — rendered audio and final ffmpeg-composed video.

**Included assets**

- `assets/bgm/` — three licensed background music tracks matched to film tone:
  - `Before_the_Curtain_Falls.mp3` — romance / slice-of-life
  - `The_Last_Pendulum.mp3` — thriller / mystery
  - `Ascent_to_the_Ridge.mp3` — inspirational / epic

**Use this skill when you want to**

- Build a local movie recap or plot-explanation generator from `.srt`/`.ass` subtitles + `.mp4`/`.mkv` source.
- Create a subtitle-driven commentary pipeline with scene-aware clip selection rather than uniform sampling.
- Add local TTS to a video project (supports CosyVoice, OpenVoice V2, MeloTTS, and Doubao SeedTTS 2.0).
- Produce vertical shorts or horizontal commentary videos for Bilibili, YouTube, Shorts, or Reels.
- Improve ffmpeg assembly, audio ducking, pacing, or narration timing in an existing commentary repo.

**Operating principles**

- Subtitles are mandatory and must be grounded in; the script must not deviate from confirmed dialogue/events.
- Never quote or translate dialogue in narration — the commentary is analysis layered on top.
- Clip selection is event-driven, not uniform; each clip must cover one key story beat.
- BGM is required at a low bed level; original movie audio is ducked under narration.

---

### xray-forensic-report

**What it does**

Runs a bundled Clojure/Babashka xray tool against a local Git repository to extract code metrics and commit forensics, then generates an offline HTML dashboard plus four templated Markdown reports.

**Scripts & tools**

| Component | Purpose |
|-----------|---------|
| `scripts/run_forensic_pipeline.py` | Python wrapper that validates the repo path, invokes the bundled `tools/xray` (Babashka CLI), and produces `index.html`, `data.json`, and `meta.json`. Supports `--since`/`--until`, `--branch`, `--path`, `--topN`, and custom `xray-tool-root`. |
| `tools/xray/` | Standalone Babashka/Clojure CLI that computes Git metrics: complexity, coupling, change frequency, hotspot identification, and timeline analysis. |
| `scripts/fill_templates.py` | Reads the generated `data.json`, filters out noise files (AI-generated, Storybook, fixtures, benchmarks), and fills four Markdown templates under `assets/templates/`. |
| `assets/templates/` | Four report templates: `template-forensic-analysis.md`, `template-management-summary.md`, `template-technical-plan.md`, `template-refactoring-guide.md`. |

**Use this skill when you want to**

- Generate a reusable code-forensics package for a local Git repo over a selected time window.
- Identify code hotspots, coupling hotspots, and refactoring candidates from commit history.
- Produce management-friendly summaries and technical plans from repository analytics.
- Run offline forensic reports without depending on the original `bbtools` repository layout.
- Customize analysis scope with path filters, branch selection, date ranges, or AI-analysis overrides.

**Prerequisites**

- `bb` (Babashka) must be available in `PATH`.
- Target `repo` must be a local Git repository with an absolute path.

---

## License

MIT
