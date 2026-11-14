#!/usr/bin/env python3
"""Compose a chaptered test-evidence video from raw captures and per-line narration.

Layout: 1920x1080, 25 fps, left verdict sidebar (380 px), right raw capture,
bottom subtitle strip. Audio comes only from the narration files; the capture
audio is discarded. Output is H.264/AAC with an SRT sidecar, chapter metadata
and a verdict summary.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.stderr.write("Pillow is required: python3 -m pip install Pillow\n")
    raise SystemExit(2)

WIDTH = 1920
HEIGHT = 1080
SIDEBAR_W = 380
CAPTION_H = 104
STAGE_W = WIDTH - SIDEBAR_W
STAGE_H = HEIGHT - CAPTION_H
FPS = 25

BG = "#0b1220"
PANEL = "#111c2e"
PANEL_ACTIVE = "#16283f"
BORDER = "#253449"
WHITE = "#f8fafc"
TEXT = "#cbd5e1"
MUTED = "#8ba0b8"
ACCENT = "#22d3ee"

VERDICTS = {
    "pass": ("通过", "#22c55e"),
    "fail": ("失败", "#ef4444"),
    "blocked": ("阻塞", "#f59e0b"),
    "unexecuted": ("未执行", "#64748b"),
}


def run(args, timeout=None):
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if proc.returncode:
        sys.stderr.write(" ".join(str(x) for x in args) + "\n" + (proc.stderr or "")[-4000:] + "\n")
        raise SystemExit(1)
    return proc.stdout


def probe(path):
    data = json.loads(run([
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,width,height,avg_frame_rate",
        "-show_entries", "format=duration", "-of", "json", str(path),
    ]))
    info = {"duration": float(data["format"]["duration"]), "video": None, "audio": None}
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and info["video"] is None:
            info["video"] = stream
        if stream.get("codec_type") == "audio" and info["audio"] is None:
            info["audio"] = stream
    return info


def audio_duration(path):
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=duration", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ]).split()
    values = [float(value) for value in out if value not in ("N/A", "")]
    if not values:
        raise SystemExit("Cannot read audio duration: %s" % path)
    return max(values)


def font_file(requested):
    candidates = [
        requested,
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for item in candidates:
        if item and Path(item).is_file():
            return item
    raise SystemExit("No CJK font found; pass --font with a font file.")


def load_font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, font, width, max_lines=3):
    lines, current = [], ""
    for char in str(text).replace("\r", ""):
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        trial = current + char
        if current and draw.textlength(trial, font=font) > width:
            break_at = current.rfind(" ")
            if char != " " and break_at > len(current) * 0.6:
                lines.append(current[:break_at])
                current = current[break_at + 1:] + char
            else:
                lines.append(current)
                current = char
        else:
            current = trial
    if current or not lines:
        lines.append(current)
    return lines[:max_lines]


def ellipsize(draw, text, font, width):
    text = str(text)
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text + "…"


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    else:
        draw.rectangle(box, fill=fill, outline=outline, width=width)


def render_canvas(path):
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    image.save(path)


def render_sidebar(path, manifest, index, font_path):
    image = Image.new("RGB", (SIDEBAR_W, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    margin = 26
    title = str(manifest.get("title") or "测试证据")
    subtitle = str(manifest.get("subtitle") or "")
    scene = manifest["scenes"][index]
    verdict = scene["verdict"]
    total = len(manifest["scenes"])

    draw.rectangle((0, 0, SIDEBAR_W - 1, HEIGHT - 1), outline=BORDER, width=1)
    draw.rectangle((0, 0, SIDEBAR_W, 3), fill=ACCENT)
    draw.text((margin, 30), "TEST EVIDENCE", font=load_font(font_path, 13), fill=ACCENT)

    label, color = VERDICTS[verdict]
    draw.text((SIDEBAR_W - margin, 28), label, font=load_font(font_path, 15), fill=color, anchor="ra")
    draw.text((SIDEBAR_W - margin, 50), "%02d / %02d" % (index + 1, total),
              font=load_font(font_path, 13), fill=MUTED, anchor="ra")

    title_size = 25
    title_font = load_font(font_path, title_size)
    while title_size > 17 and len(wrap(draw, title, title_font, SIDEBAR_W - margin * 2, 3)) > 2:
        title_size -= 1
        title_font = load_font(font_path, title_size)
    y = 60
    for line in wrap(draw, title, title_font, SIDEBAR_W - margin * 2, 3):
        draw.text((margin, y), line, font=title_font, fill=WHITE)
        y += title_size + 7

    if subtitle:
        sub_font = load_font(font_path, 13)
        y += 4
        for line in wrap(draw, subtitle, sub_font, SIDEBAR_W - margin * 2, 2):
            draw.text((margin, y), line, font=sub_font, fill=MUTED)
            y += 19

    divider_y = max(206, y + 14)
    draw.rectangle((margin, divider_y, SIDEBAR_W - margin, divider_y + 1), fill=BORDER)
    list_top = divider_y + 18
    list_bottom = HEIGHT - 66

    count = len(manifest["scenes"])
    visible = min(count, 14)
    row_h = max(42, min(76, (list_bottom - list_top) // max(visible, 1)))
    if count > visible:
        start = min(max(0, index - visible // 2), count - visible)
    else:
        start = 0
    end = min(count, start + visible)

    for offset, scene_index in enumerate(range(start, end)):
        item = manifest["scenes"][scene_index]
        active = scene_index == index
        top = list_top + offset * row_h
        bottom = top + row_h - 6
        item_label, item_color = VERDICTS[item["verdict"]]

        if active:
            rounded(draw, (10, top, SIDEBAR_W - 10, bottom), 8, fill=PANEL_ACTIVE,
                    outline=item_color if item["verdict"] != "pass" else ACCENT, width=2)
            draw.rectangle((10, top + 8, 13, bottom - 8), fill=item_color)

        radius = 13 if row_h >= 58 else 11
        cx = margin + radius + 2
        cy = top + (24 if row_h >= 58 else 20)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     fill=item_color if active else "#1e293b")
        draw.text((cx, cy), str(scene_index + 1), font=load_font(font_path, 11), fill=WHITE, anchor="mm")

        text_x = cx + radius + 9
        text_w = SIDEBAR_W - text_x - margin
        name_font = load_font(font_path, 16 if row_h >= 58 else 14)
        name = ellipsize(draw, item.get("title") or item["id"], name_font, text_w)
        draw.text((text_x, cy - 15), name, font=name_font, fill=WHITE if active else TEXT)

        meta_font = load_font(font_path, 11)
        meta = "%s · %s" % (item["id"], item_label)
        if item.get("defect"):
            meta += " · " + str(item["defect"])
        draw.text((text_x, cy + 4), ellipsize(draw, meta, meta_font, text_w),
                  font=meta_font, fill=item_color if active else MUTED)

    if count > visible:
        draw.text((margin, HEIGHT - 46), "%d–%d / %d" % (start + 1, end, count),
                  font=load_font(font_path, 12), fill=MUTED)

    draw.text((margin, HEIGHT - 28), "原始录屏留存 · 字幕为逐句解说",
              font=load_font(font_path, 11), fill="#5c7189")
    image.save(path)


def render_caption(path, text, font_path):
    image = Image.new("RGBA", (STAGE_W, CAPTION_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, STAGE_W, CAPTION_H), fill=(7, 15, 27, 224))
    draw.rectangle((0, 0, STAGE_W, 2), fill=ACCENT)

    size = 36
    font = load_font(font_path, size)
    lines = wrap(draw, text, font, STAGE_W - 120, 3)
    while size > 25 and len(lines) > 2:
        size -= 2
        font = load_font(font_path, size)
        lines = wrap(draw, text, font, STAGE_W - 120, 3)
    if len(wrap(draw, text, font, STAGE_W - 120, 99)) > 3:
        raise SystemExit("Subtitle is too long for three lines: %s" % text)

    line_h = size + 8
    y = (CAPTION_H - (len(lines) * line_h - 8)) / 2
    for line in lines:
        draw.text((STAGE_W / 2, y), line, font=font, fill=WHITE, anchor="ma")
        y += line_h
    image.save(path)


def srt_time(seconds):
    ms = max(0, int(round(seconds * 1000)))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def ffmeta_time(seconds):
    return int(round(seconds * 1000))


def validate(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("manifest.scenes must be a non-empty list")

    ids = set()
    for index, scene in enumerate(scenes, 1):
        where = "scene %d" % index
        for key in ("id", "title", "verdict", "capture", "lines"):
            if key not in scene:
                raise SystemExit("%s is missing %s" % (where, key))
        if scene["id"] in ids:
            raise SystemExit("duplicate scene id: %s" % scene["id"])
        ids.add(scene["id"])
        if scene["verdict"] not in VERDICTS:
            raise SystemExit("%s has invalid verdict %r" % (where, scene["verdict"]))
        if scene["verdict"] == "fail" and not scene.get("defect"):
            raise SystemExit("%s is fail but has no defect id" % where)
        if scene["verdict"] in ("blocked", "unexecuted") and not scene.get("reason"):
            raise SystemExit("%s is %s but has no reason" % (where, scene["verdict"]))

        capture = (base / scene["capture"]).resolve()
        if not capture.is_file():
            raise SystemExit("%s capture not found: %s" % (where, capture))
        scene["_capture"] = capture
        scene["_duration"] = probe(capture)["duration"]
        if not scene["lines"]:
            raise SystemExit("%s has no narration lines" % where)

        previous_end = -1.0
        lines = []
        for line_index, line in enumerate(scene["lines"], 1):
            line_where = "%s line %d" % (where, line_index)
            if not str(line.get("text") or "").strip():
                raise SystemExit("%s has empty text" % line_where)
            audio = (base / line["audio"]).resolve()
            if not audio.is_file():
                raise SystemExit("%s audio not found: %s" % (line_where, audio))
            start = float(line["start"])
            if start < 0 or not math.isfinite(start):
                raise SystemExit("%s has invalid start" % line_where)
            duration = audio_duration(audio)
            if start < previous_end - 0.001:
                raise SystemExit("%s overlaps the previous line" % line_where)
            if start + duration > scene["_duration"] + 0.05:
                raise SystemExit(
                    "%s ends at %.2fs, after the capture (%.2fs); re-record or leave more pause"
                    % (line_where, start + duration, scene["_duration"]))
            previous_end = start + duration
            lines.append({"text": str(line["text"]).strip(), "audio": audio,
                          "start": start, "duration": duration})
        scene["_lines"] = lines
    return manifest


def scene_duration(scene):
    return math.ceil(scene["_duration"] * FPS - 1e-6) / FPS


def render_scene(manifest, index, work, font_path):
    scene = manifest["scenes"][index]
    duration = scene_duration(scene)
    tag = "%02d-%s" % (index + 1, re.sub(r"[^\w.-]+", "-", str(scene["id"]))[:40])
    canvas = work / "canvas.png"
    sidebar = work / ("sidebar-%02d.png" % (index + 1))
    render_canvas(canvas)
    render_sidebar(sidebar, manifest, index, font_path)

    inputs = [
        "-loop", "1", "-framerate", str(FPS), "-i", str(canvas),
        "-i", str(scene["_capture"]),
        "-loop", "1", "-framerate", str(FPS), "-i", str(sidebar),
    ]

    captions = []
    filters = [
        "[1:v]fps=%d,scale=%d:%d:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x0b1220,setsar=1,format=yuv420p[clip]"
        % (FPS, STAGE_W, STAGE_H, STAGE_W, STAGE_H),
        "[0:v][clip]overlay=%d:0[v0]" % SIDEBAR_W,
        "[v0][2:v]overlay=0:0[vside]",
    ]
    previous = "[vside]"
    for line_index, line in enumerate(scene["_lines"]):
        png = work / ("caption-%02d-%02d.png" % (index + 1, line_index + 1))
        render_caption(png, line["text"], font_path)
        captions.append(png)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(png)]
        current = "[vc%d]" % (line_index + 1)
        filters.append(
            "%s[%d:v]overlay=%d:%d:enable='between(t,%.3f,%.3f)'%s"
            % (previous, 3 + line_index, SIDEBAR_W, STAGE_H,
               line["start"], line["start"] + line["duration"], current))
        previous = current

    audio_start = 3 + len(captions)
    if scene["_lines"]:
        mix_inputs = []
        for line_index, line in enumerate(scene["_lines"]):
            inputs += ["-i", str(line["audio"])]
            stream = "[%d:a]" % (audio_start + line_index)
            label = "[a%d]" % (line_index + 1)
            filters.append(
                "%saresample=48000,adelay=%d|%d,apad=whole_dur=%.3f%s"
                % (stream, int(round(line["start"] * 1000)), int(round(line["start"] * 1000)),
                   duration, label))
            mix_inputs.append(label)
        if len(mix_inputs) == 1:
            filters.append("%satrim=0:%.3f,asetpts=N/SR/TB[aout]" % (mix_inputs[0], duration))
        else:
            filters.append(
                "%samix=inputs=%d:duration=longest:normalize=0,atrim=0:%.3f,asetpts=N/SR/TB[aout]"
                % ("".join(mix_inputs), len(mix_inputs), duration))
    else:
        inputs += ["-f", "lavfi", "-t", "%.3f" % duration,
                   "-i", "anullsrc=channel_layout=mono:sample_rate=48000"]
        filters.append("[%d:a]atrim=0:%.3f,asetpts=N/SR/TB[aout]" % (audio_start, duration))

    output = work / ("scene-%s.mp4" % tag)
    run([
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", previous, "-map", "[aout]", "-t", "%.3f" % duration, "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "1",
        "-video_track_timescale", "90000", "-movflags", "+faststart", str(output),
    ])
    return output, duration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--font")
    parser.add_argument("--force", action="store_true", help="allow a non-empty output directory")
    args = parser.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise SystemExit("%s not found" % tool)
    if not args.manifest.is_file():
        raise SystemExit("manifest not found: %s" % args.manifest)

    out_dir = args.output_dir
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit("Output directory is not empty (pass --force to reuse): %s" % out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = validate(args.manifest)
    font_path = font_file(args.font)
    work = out_dir / ".work"
    work.mkdir(exist_ok=True)

    scenes, srt_cues, chapters, offset = [], [], [], 0.0
    for index, scene in enumerate(manifest["scenes"]):
        print("Rendering %d/%d %s ..." % (index + 1, len(manifest["scenes"]), scene["id"]))
        output, duration = render_scene(manifest, index, work, font_path)
        scenes.append(output)
        scene["_start"] = offset
        scene["_end"] = offset + duration
        for line in scene["_lines"]:
            srt_cues.append((offset + line["start"], offset + line["start"] + line["duration"], line["text"]))
        chapters.append((offset, offset + duration, "%s %s" % (scene["id"], scene["title"])))
        offset += duration

    list_file = work / "scenes.txt"
    list_file.write_text("".join("file '%s'\n" % item.name for item in scenes), encoding="utf-8")

    ffmeta = out_dir / "chapters.ffmeta"
    def meta_text(value):
        return str(value).replace("\r", " ").replace("\n", " ").strip()
    lines = [";FFMETADATA1", "title=%s" % meta_text(manifest.get("title", "test evidence"))]
    if manifest.get("subtitle"):
        lines.append("comment=%s" % meta_text(manifest["subtitle"]))
    for start, end, title in chapters:
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", "START=%d" % ffmeta_time(start),
                  "END=%d" % ffmeta_time(end), "title=%s" % meta_text(title)]
    ffmeta.write_text("\n".join(lines) + "\n", encoding="utf-8")

    video = out_dir / "test-evidence.mp4"
    run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-i", str(ffmeta),
        "-map", "0:v:0", "-map", "0:a:0", "-map_metadata", "1", "-map_chapters", "1",
        "-c", "copy", "-movflags", "+faststart", str(video),
    ])

    srt = out_dir / "subtitles.srt"
    blocks = []
    for index, (start, end, text) in enumerate(srt_cues, 1):
        blocks.append("%d\n%s --> %s\n%s\n" % (index, srt_time(start), srt_time(end), text))
    srt.write_text("\n".join(blocks), encoding="utf-8")

    counts = {key: 0 for key in VERDICTS}
    for scene in manifest["scenes"]:
        counts[scene["verdict"]] += 1
    summary = {
        "schema": "test-evidence-video/1",
        "title": manifest.get("title"),
        "subtitle": manifest.get("subtitle"),
        "video": str(video),
        "duration": round(offset, 3),
        "verdicts": counts,
        "scenes": [
            {"id": scene["id"], "title": scene["title"], "verdict": scene["verdict"],
             "defect": scene.get("defect"), "reason": scene.get("reason"),
             "start": round(scene["_start"], 3), "end": round(scene["_end"], 3),
             "lines": len(scene["_lines"])}
            for scene in manifest["scenes"]
        ],
        "defects": [scene["defect"] for scene in manifest["scenes"] if scene.get("defect")],
    }
    (out_dir / "evidence-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Created %s (%.2fs, %d scenes, %d cues)" % (video, offset, len(scenes), len(srt_cues)))
    print("SRT: %s" % srt)
    print("Chapters: %s" % ffmeta)
    print("Summary: %s" % (out_dir / "evidence-summary.json"))


if __name__ == "__main__":
    main()