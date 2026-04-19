---
name: bilibili-uploader
description: >
  Automate video uploads to Bilibili (B站) with metadata generation,
  tag suggestion, and one-click publishing workflows.
  Use when the user wants to: (1) upload a video to Bilibili,
  (2) auto-fill title/description/tags/zone for a Bilibili投稿,
  (3) batch upload videos to B站, (4) set up automated Bilibili publishing.
  Requires biliup-rs (Rust CLI) to be installed.
---

# Bilibili Uploader

Automate Bilibili video uploads with metadata auto-generation.

## Prerequisites

1. **biliup-rs** must be installed and available in `PATH`.
   - Download from https://github.com/biliup/biliup-rs/releases
   - Place the `biliup` binary in `/usr/local/bin/` or `~/.local/bin/`
2. **ffprobe** (optional, bundled with ffmpeg) for automatic metadata extraction.
3. **Login once**: `biliup -u <cookie-path> login` (scan QR or SMS).
   - Cookie file is reused for all subsequent uploads.

## Scripts

All scripts live in `scripts/`:

| Script | Purpose |
|--------|---------|
| `bilibili_uploader.py` | Low-level wrapper around `biliup upload`. Use for precise control. |
| `auto_generate_meta.py` | Analyze a video with ffprobe and generate title/description/tags/zone. |
| `auto_upload.py` | **One-click workflow**: analyze → generate metadata → confirm → upload. |

## Quick Workflow

### 1. One-click auto upload (recommended)

```bash
python scripts/auto_upload.py /path/to/video.mp4 \
  --title "Custom title" \
  --extra-tags "tag1,tag2" \
  --tid 228 \
  -y
```

Flags:
- `--dry-run` — preview metadata without uploading
- `-y` — skip confirmation prompt
- `--dtime "YYYY-MM-DD HH:MM"` — scheduled publish
- `--cover ./cover.jpg` — custom thumbnail
- `--config ./bili_config.json` — load defaults from config

### 2. Manual upload (fine-grained control)

```bash
python scripts/bilibili_uploader.py upload video.mp4 \
  --title "Title" \
  --desc "Description" \
  --tags "tag1,tag2" \
  --tid 228 \
  --copyright 1 \
  --cookie ./cookies.json
```

### 3. Generate metadata only

```bash
python scripts/auto_generate_meta.py video.mp4 --json
```

## Auto-Metadata Rules

`auto_generate_meta.py` performs the following:

1. **Title**: cleans the filename (removes extensions, resolution codes, etc.) and title-cases it.
2. **Tags & Zone**: keyword-maps against a built-in dictionary.
   - `rust`, `python`, `docker`, `k8s` → `编程/技术` tags, zone `231`
   - `game`, `lol`, `fps` → `游戏` tags, zone `171/172`
   - `music`, `吉他`, `钢琴` → `音乐` tags, zone `31`
   - `vlog` → `生活` tags, zone `21`
   - `开箱`, `评测` → `数码` tags, zone `232`
   - fallback → `教程,分享,原创`, zone `231`
3. **Description**: auto-generated with duration, resolution, codec, file size, upload date.
4. **Override priority**: CLI arguments override auto-generated values.

## Common Zone TID Values

| TID | Zone |
|-----|------|
| 228 | 电影 |
| 230 | 电视剧 |
| 231 | 计算机技术 |
| 232 | 软件应用 |
| 171 | 电子竞技 |
| 172 | 单机游戏 |
| 31  | 音乐综合 |
| 130 | 音乐现场 |
| 28  | 原创音乐 |
| 160 | 搞笑 |

## Important CLI Quirk

In biliup-rs v0.2.4, `--user-cookie` is a **global flag** and must come **before** the subcommand:

```bash
# CORRECT
biliup -u ./cookies.json upload video.mp4 ...

# INCORRECT (will error)
biliup upload video.mp4 --user-cookie ./cookies.json ...
```

`bilibili_uploader.py` already handles this correctly.

## Troubleshooting

- **"Login required" / 未登录**: run `biliup -u <path> login` first.
- **"Tag cannot be empty"**: ensure `--tags` has ≤12 tags, each ≤20 chars. Scripts enforce this.
- **Upload speed slow**: try `--line qn` or `--line tx` in `bilibili_uploader.py`.
