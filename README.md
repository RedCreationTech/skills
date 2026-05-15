# redcreation/skills

A collection of agent skills for AI coding assistants, covering video publishing, content pipelines, and code forensics.

## Installation

Install individual skills using the `skills` CLI:

```bash
# Bilibili video uploader with auto metadata generation
npx skills@latest add redcreation/skills --skill bilibili-uploader

# Movie commentary pipeline: subtitles → script → TTS → rendered video
npx skills@latest add redcreation/skills --skill movie-commentary-video-pipeline

# Git repository forensic report generator
npx skills@latest add redcreation/skills --skill xray-forensic-report
```

---

## Skills

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
