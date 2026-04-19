---
name: movie-commentary-video-pipeline
description: Use this skill when asked to build, extend, or run a workflow that turns a licensed film or video plus subtitles into a commentary script, TTS narration, a scene-aware clip plan, and optionally a rendered commentary video. Trigger for subtitle parsing, beat extraction, clip selection, ffmpeg composition, audio ducking, narration timing, local or configured private voice synthesis, and project scaffolding around this workflow. Do not trigger for generic video editing, unrelated TTS demos, cloud-only dubbing with no local/rendering workflow, or pure subtitle translation tasks.
---

# Purpose

Build or improve a reproducible local pipeline for:

1. subtitles -> story beats -> commentary script
2. subtitles + scene timing -> clip plan
3. configured TTS -> natural narration with a distinctive voice
4. ffmpeg -> final commentary video

This skill is optimized for movie recap, plot explanation, spoiler review, and short-form commentary videos.

# Operating principles

- **Subtitles are mandatory.** The source video must have retrievable subtitles (internal tracks or external files). The commentary script must be grounded in subtitle content and must not deviate significantly from the dialogue and confirmed story events. If no subtitles are found, halt and ask the user to provide or locate them before proceeding.
- Treat subtitle-only understanding as incomplete. Subtitles are strong for dialogue, scene order, and timing, but they do not fully describe silent actions, props, visual gags, expressions, or cinematography. If the task requires visual certainty and video frames are available, inspect keyframes or add frame-level analysis before stating visual details as facts.
- Prefer a hybrid timing strategy. Start from subtitle timestamps, then refine around shot boundaries or visible transitions when possible.
- Prefer permissive local TTS stacks by default. Use CosyVoice when GPU + naturalness are the priority, OpenVoice V2 when the user has a licensed voice reference and wants stronger voice identity, and MeloTTS as the CPU-friendly fallback. For this user's private environment, prefer Doubao SeedTTS 2.0 when the user asks for Doubao or when local CosyVoice output leaks prompt/reference audio.
- Do not default to research-only or non-commercial-weight models unless the user explicitly accepts that constraint.
- Never imitate a real person's voice without permission. Use only licensed or user-owned reference audio.
- Only process source video, subtitles, music, and posters that the user is allowed to use.

# When this skill should be used

Use this skill when the user asks for any of the following:

- Build a local movie commentary generator
- Generate narration from subtitles and render clips into a final video
- Create a project that parses SRT/ASS/VTT and aligns clips to narration
- Add a local TTS engine to a commentary or recap pipeline
- Improve pacing, naturalness, clip selection, or ffmpeg assembly for commentary videos
- Scaffold a repo for subtitle-driven recap generation

# When this skill should NOT be used

Do not use this skill for:

- Generic video editors with no subtitle/commentary workflow
- Subtitle translation only
- Voice assistants or podcast tools unrelated to film/video recap
- Cloud-only pipelines when the user explicitly wants hosted synthesis/rendering with no local subtitle/commentary/rendering workflow
- Celebrity voice cloning or impersonation requests

# Inputs to look for

Common inputs:

- video: `.mp4`, `.mkv`, `.mov`
- subtitles: `.srt`, `.ass`, `.ssa`, `.vtt` (mandatory; must be present or extractable)
- optional voice reference audio
- optional project config or style notes
- target platform: horizontal, vertical, Shorts, Reels, Bilibili, YouTube
- output duration target or compression ratio
- brand assets such as watermark, intro, outro, logo

# Outputs to produce

At minimum, generate:

- `commentary/commentary_script.md`
- `commentary/narration_manifest.json`
- `commentary/clip_plan.json`
- `commentary/project_config.yaml`

If rendering is requested and the media assets are present, also generate:

- `outputs/voiceover.wav`
- `outputs/final_commentary.mp4`
- `outputs/review_sheet.md`

# Default project structure

When starting from an empty or near-empty repo, prefer a simple Python layout like this:

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── configs/
│   └── project.yaml
├── inputs/
│   ├── movie.mp4
│   ├── subtitles.srt
│   └── voice_ref.wav
├── commentary/
│   ├── commentary_script.md
│   ├── narration_manifest.json
│   └── clip_plan.json
├── outputs/
│   ├── voiceover.wav
│   └── final_commentary.mp4
└── src/
    └── movie_commentary/
        ├── __init__.py
        ├── config.py
        ├── subtitles.py
        ├── beats.py
        ├── script_writer.py
        ├── clip_planner.py
        ├── tts/
        │   ├── base.py
        │   ├── cosyvoice_adapter.py
        │   ├── openvoice_adapter.py
        │   └── melotts_adapter.py
        ├── audio_post.py
        ├── compose.py
        └── main.py
```

Keep the dependency graph boring and explicit. Favor Python + ffmpeg subprocesses over a fragile chain of wrappers.

# Required workflow

Follow this sequence unless the repo already has a better architecture.

## 1. Intake and constraint capture

Extract or infer:

- input file paths
- target language of narration
- style/tone: documentary, suspense, dry, humorous, ironic, neutral
- target duration or compression ratio
- whether the output must be vertical or horizontal
- TTS engine preference and whether voice cloning is allowed
- whether the user wants hard subtitles burned into the video

If critical assets are missing, scaffold the repo and leave obvious placeholders instead of blocking.

## 2. Normalize subtitles

Implement robust parsing for `.srt`, `.ass`, `.ssa`, and `.vtt`.

Normalization rules:

- merge broken subtitle lines into semantic sentences
- remove hearing-impaired metadata when not needed
- preserve original start/end timestamps
- store a clean text version and a raw version
- support mixed Chinese/English tokens
- do not assume subtitle punctuation is good enough for narration

## 3. Build story beats

Group subtitle lines into higher-level beats using:

- time gaps
- speaker changes when detectable
- lexical continuity
- max beat duration limits
- optional scene boundary hints

A beat should feel like a narratable unit, not just a single subtitle row.

Each beat record should usually contain:

- `beat_id`
- `start`
- `end`
- `subtitle_text`
- `summary`
- `narration_goal`
- `confidence`

## 4. Write commentary script

Generate narration that is:

- **dense and continuous**: the narration must fill the audio timeline of each clip window with minimal dead air; if a 60-second clip has only 30 seconds of narration, the script is insufficient
- **analysis-driven, not quotation-driven**: explain what the dialogue means, why the character says it, and what it reveals about theme or motivation
- **fast-paced**: short punchy sentences, rapid-fire opinions, minimal poetic pauses
- faithful to confirmed story events
- careful about uncertain visuals

Narration rules (hard constraints):

- **Never quote or recite dialogue.** Do not use "他说..." / "她回答..." / "字幕里..." patterns. The audience can read subtitles themselves; the narrator's job is to interpret, not to read aloud.
- **Never translate dialogue lines.** Do not convert English dialogue into Chinese narration verbatim. The commentary should be a layer of analysis on top of the dialogue, not a dubbing track.
- Prefer recap language over screenplay transcription.
- Compress repetitive back-and-forth dialogue into one sentence of analysis.
- Avoid naming a visual detail unless it is visible or strongly implied by the subtitles/context.
- Split long paragraphs into sentence-level chunks suitable for TTS.
- For Chinese narration, prefer short, spoken sentences over written-style long clauses.
- Keep every narration chunk attached to a timing budget.

Produce both:

1. a human-readable `commentary_script.md`
2. a machine-readable narration manifest with chunk text, intended duration, beat mapping, and render order

## 5. Plan clip extraction

Create clip windows from the union of:

- subtitle timing
- pre/post-roll margins
- optional scene boundaries
- optional max clip length rules

Clip planning rules:

- Avoid using one long uninterrupted source span unless the user explicitly wants that style.
- Prefer 2 to 6 second clips for short-form recap content, unless the scene requires a longer hold.
- If a narration chunk spans multiple beats, combine multiple source windows rather than forcing one oversized clip.
- If the source timing is uncertain, mark the clip plan item as `needs_review`.
- Reserve room for intro cards, title cards, or ending CTA if the user asked for them.

Each clip item should normally include:

- `clip_id`
- `source_path`
- `start`
- `end`
- `narration_chunk_ids`
- `subtitle_refs`
- `transition`
- `crop_mode`
- `notes`
- `needs_review`

## 6. Local TTS selection policy

Use this default policy:

- `doubao_seedtts2`: private fast cloud TTS option for this user's environment; prefer it when the user asks for Doubao, wants faster synthesis, or CosyVoice leaks test/reference audio into generated narration
- `cosyvoice`: best local default for natural Chinese narration when GPU is available
- `openvoice_v2`: use when the user provides a licensed reference clip and wants stronger voice identity or style transfer
- `melotts`: CPU-friendly fallback and stable mixed Chinese/English narration

Only choose research/non-commercial stacks such as F5-TTS or Fish Speech when the user explicitly requests them and the repo notes the license implications.

### Private Doubao SeedTTS 2.0 setup

This block is intentionally private to this user's local skill. Do not copy these credentials into generated repos, public logs, README files, or responses unless the user explicitly asks.

Use Doubao SeedTTS 2.0 through the v2 HTTP streaming Go SDK path, not the older v1 endpoint. The working smoke-tested setup is:

```zsh
export TTS_PROVIDER=doubao
export DOUBAO_APP_ID=<YOUR_APP_ID>
export DOUBAO_ACCESS_KEY=<YOUR_ACCESS_TOKEN>
export DOUBAO_APP_KEY=<YOUR_APP_KEY>
export DOUBAO_SECRET_KEY=<YOUR_SECRET_KEY>
export DOUBAO_VOICE_TYPE=zh_male_m191_uranus_bigtts
export DOUBAO_RESOURCE_ID=seed-tts-2.0
export GOPROXY=https://goproxy.cn,direct
```

Credential notes:

- `DOUBAO_ACCESS_KEY` is the console "Access Token".
- `DOUBAO_SECRET_KEY` is recorded for account reference, but the smoke-tested v2 Go SDK command used access-token auth and did not require the secret key.
- `DOUBAO_APP_KEY` defaults to the app id in the v2 SDK.
- Default voice: `zh_male_m191_uranus_bigtts` ("Yunzhou"). Other known usable Chinese voice types include `zh_female_vv_uranus_bigtts`, `zh_female_xiaohe_uranus_bigtts`, `zh_male_taocheng_uranus_bigtts`, and role-play Saturn voices listed in the user's Volcengine console.

Smoke test a single file with:

```zsh
go run github.com/giztoy/doubao-speech-go/examples/tts_v2/http_stream@latest \
  -auth-mode access \
  -speaker "$DOUBAO_VOICE_TYPE" \
  -resource-id "$DOUBAO_RESOURCE_ID" \
  -format mp3 \
  -text "这是一段豆包语音合成测试。" \
  -output /tmp/doubao_tts_test.mp3
```

For generated commentary pipelines, keep Doubao behind a TTS adapter and read credentials from environment variables. Do not write these values into project config files. A minimal adapter can shell out chunk-by-chunk:

```python
env = os.environ.copy()
env.setdefault("GOPROXY", "https://goproxy.cn,direct")
env["DOUBAO_APP_ID"] = env["DOUBAO_APP_ID"]
env["DOUBAO_ACCESS_KEY"] = env.get("DOUBAO_ACCESS_KEY") or env["DOUBAO_TOKEN"]
env["DOUBAO_APP_KEY"] = env.get("DOUBAO_APP_KEY") or env["DOUBAO_APP_ID"]

subprocess.run([
    "go", "run", "github.com/giztoy/doubao-speech-go/examples/tts_v2/http_stream@latest",
    "-auth-mode", "access",
    "-speaker", os.environ.get("DOUBAO_VOICE_TYPE", "zh_male_m191_uranus_bigtts"),
    "-resource-id", os.environ.get("DOUBAO_RESOURCE_ID", "seed-tts-2.0"),
    "-format", "mp3",
    "-text", narration_chunk_text,
    "-output", str(output_mp3_path),
], check=True, env=env)
```

For this repo shape, run:

```zsh
python scripts/run_commentary_pipeline.py --tts-provider doubao
```

## 7. TTS rendering rules

For naturalness, do NOT synthesize one giant paragraph.

Instead:

- render chunk by chunk, usually sentence by sentence
- rewrite punctuation for speech cadence before synthesis
- insert short pauses between chunks when needed
- keep sample rates and loudness normalization consistent
- preserve a stable speaker identity across all chunks
- prefer warm, clean, documentary pacing over exaggerated emotions unless the user asked for drama

If voice cloning is used:

- validate that the reference audio is short, clean, and legally usable
- avoid clipping, music beds, reverb-heavy references, and overlapped speech
- keep a fallback neutral voice preset available

## 8. Audio post-processing

After synthesis, create a clean narration track:

- trim leading/trailing silence
- normalize loudness consistently
- optionally add gentle fades between chunks
- **background music is required.** Select the BGM from the skill's own licensed asset library (`assets/bgm/`). Match the track to the film's tone:
  - `Before_the_Curtain_Falls.mp3` — gentle, warm, suitable for romance, slice-of-life, and healing themes.
  - `The_Last_Pendulum.mp3` — suspenseful, tense, suitable for thrillers, mysteries, and plot-twist narratives.
  - `Ascent_to_the_Ridge.mp3` — uplifting, epic, suitable for inspirational, heroic, or grand-scale stories.
- mix the BGM at a low bed level (e.g., 0.06–0.10) so it supports but never competes with narration.
- duck original movie audio under the narration instead of fully muting it unless the user wants a pure voiceover cut.

Favor subtle processing. The goal is intelligibility, not radio-style heavy compression.

## 9. Video composition

Compose the final video with deterministic ffmpeg commands or a thin Python orchestrator.

Preferred composition order:

1. source clips assembled in planned order
2. crop/scale/pad for target aspect ratio
3. optional transitions
4. optional title cards
5. original audio bed lowered
6. narration mixed on top
7. optional hard subtitles or commentary captions
8. watermark or branding last

Implementation guidance:

- Use text files for captions/overlays when that avoids shell escaping problems.
- Keep intermediate files in a temp directory so the user can debug bad segments.
- Generate a manifest that maps final timeline positions back to source clip ids.

## 10. Validation loop

Before claiming success, verify:

- the narration duration roughly matches the planned visual duration
- there are no missing source clips
- subtitles parse successfully
- ffmpeg commands complete without dropped inputs or broken concat files
- TTS output sample rate/channel layout is compatible with final muxing
- the final video has audible narration and correct A/V sync

If full rendering is too expensive, at least generate:

- project scaffold
- narration manifest
- clip plan
- exact commands to run next

# Quality bar

A good result should feel like this:

- the story is coherent even if the audience never saw the original film
- the voice sounds like a narrator, not like a robotic terminal reading logs
- clip changes feel motivated by story beats
- the final timeline is debuggable through JSON manifests and review notes
- uncertain visual claims are labeled or avoided

# Legal and safety guardrails

- Do not assume the user has rights to use film footage, subtitles, music, or artwork. Use licensed, user-owned, or review/test assets where rights are clear.
- Do not clone or imitate a real person's voice without permission.
- If the user asks for copyrighted footage in a public/commercial pipeline, note that licensing review may be required.

# Preferred implementation details

- Language: Python 3.11+
- Media tool: ffmpeg via subprocess
- Subtitle parsing: a mature parser, not handwritten regex unless the scope is tiny
- Config: YAML for user-facing config, JSON for machine manifests
- Data models: `dataclasses` or Pydantic if the repo already uses it
- Logging: clear step names and emitted file paths
- Tests: at least smoke tests for subtitle parse, beat generation, and ffmpeg command construction

# Done criteria

The task is complete when these are true:

- the repo contains a clear, runnable local pipeline or a clean scaffold toward one
- the commentary script is present and chunked for speech
- the clip plan is present and traceable to source timings
- the selected TTS engine is wired or stubbed behind an adapter interface
- the render step is implemented or fully specified
- the README tells the user exactly how to run the pipeline end to end

# Default prompt patterns to respond well to

Examples:

- `Build a local movie recap pipeline from SRT + MP4 and render a final video.`
- `Use local Chinese TTS, keep the voice natural, and create a vertical short.`
- `Scaffold a repo that turns subtitles into a commentary script and clip plan first.`
- `Add OpenVoice-based voice cloning and keep a MeloTTS fallback.`
- `Given this repo, improve audio ducking and ffmpeg composition for the final commentary video.`

# Response style when using this skill

When you apply this skill:

- state the pipeline architecture briefly
- identify any blockers fast
- scaffold deterministically rather than hand-waving
- prefer shipping a working minimal path over an elaborate but brittle system
- leave explicit extension points for scene analysis, vision QA, and alternate TTS engines
