#!/usr/bin/env python3
"""Annotate a bug-reproduction recording with a header band, red boxes and numbered callouts.

The source video is never modified. Box coordinates use the source frame, excluding
the header band that this script adds on top.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.stderr.write("Pillow is required: python3 -m pip install Pillow\n")
    raise SystemExit(2)

BAND_BG = "#0f172a"
ACCENT = "#22d3ee"
RED = "#ef4444"
WHITE = "#f8fafc"
MUTED = "#94a3b8"
AMBER = "#fbbf24"


def run(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        sys.stderr.write(" ".join(str(x) for x in args) + "\n" + (proc.stderr or "")[-2000:] + "\n")
        raise SystemExit(1)
    return proc.stdout


def probe(path):
    data = json.loads(run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-show_entries", "format=duration", "-of", "json", str(path),
    ]))
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(data["format"]["duration"])


def font_file(requested):
    candidates = [
        requested,
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for item in candidates:
        if item and Path(item).is_file():
            return item
    raise SystemExit("No CJK font found; pass --font with a font file.")


def wrap(draw, text, font, width):
    lines, current = [], ""
    for char in str(text):
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        if current and draw.textlength(current + char, font=font) > width:
            lines.append(current)
            current = char
        else:
            current += char
    if current:
        lines.append(current)
    return lines


def draw_band(path, width, height, spec, font):
    image = Image.new("RGB", (width, height), BAND_BG)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(font, 30)
    right_font = ImageFont.truetype(font, 16)
    note_font = ImageFont.truetype(font, 15)
    detail_font = ImageFont.truetype(font, 16)

    title = str(spec.get("title") or "缺陷复现")
    while draw.textlength(title, font=title_font) > width - 380 and title_font.size > 20:
        title_font = ImageFont.truetype(font, title_font.size - 1)
    draw.text((28, 20), title, font=title_font, fill=WHITE)

    right = str(spec.get("right") or "")
    if right:
        draw.text((width - 28, 28), right, font=right_font, fill=MUTED, anchor="ra")

    note = str(spec.get("note") or "")
    if note:
        draw.text((28, 76), note, font=note_font, fill=AMBER)

    expected = str(spec.get("expected") or "")
    actual = str(spec.get("actual") or "")
    if expected or actual:
        line = "预期：%s    实际：%s" % (expected or "-", actual or "-")
        while draw.textlength(line, font=detail_font) > width - 56 and detail_font.size > 12:
            detail_font = ImageFont.truetype(font, detail_font.size - 1)
        draw.text((28, height - 38), line, font=detail_font, fill="#e2e8f0")

    draw.rectangle((0, height - 2, width, height), fill=ACCENT)
    image.save(path)


def draw_mark(path, width, height, band_h, mark, font):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x, y, w, h = [int(v) for v in mark["box"]]
    top = y + band_h
    if w < 8 or h < 8:
        raise SystemExit("Mark box is too small: %r" % (mark["box"],))

    draw.rounded_rectangle((x, top, x + w, top + h), radius=6, outline=RED, width=4)

    label = str(mark.get("label") or "")
    if label:
        radius = 17
        cx = max(radius + 3, x - 2)
        cy = max(band_h + radius + 3, top - 2)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=RED)
        label_font = ImageFont.truetype(font, 16 if len(label) <= 2 else 12)
        draw.text((cx, cy), label, font=label_font, fill=WHITE, anchor="mm")

    text = str(mark.get("text") or "")
    if text:
        text_font = ImageFont.truetype(font, 16)
        lines = wrap(draw, text, text_font, 600)
        if len(lines) > 2:
            text_font = ImageFont.truetype(font, 14)
            lines = wrap(draw, text, text_font, 620)
        lines = lines[:2]
        line_h = text_font.size + 7
        box_w = max(int(draw.textlength(line, font=text_font)) for line in lines) + 18
        box_h = len(lines) * line_h + 10
        tx = min(max(8, x), width - box_w - 8)
        ty = top - box_h - 8
        if ty < band_h + 6:
            ty = min(height - box_h - 8, top + h + 8)
        draw.rounded_rectangle((tx, ty, tx + box_w, ty + box_h), radius=6, fill=(8, 20, 34, 235))
        for index, line in enumerate(lines):
            draw.text((tx + 9, ty + 5 + index * line_h), line, font=text_font, fill=WHITE)

    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font")
    parser.add_argument("--band-height", type=int, default=140)
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.video.is_file():
        raise SystemExit("Source video not found: %s" % args.video)
    if args.output.exists() and not args.force:
        raise SystemExit("Output exists; pass --force to replace: %s" % args.output)
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    width, height, duration = probe(args.video)
    band_h = args.band_height
    font = font_file(args.font)

    marks = spec.get("marks") or []
    if not isinstance(marks, list) or not marks:
        raise SystemExit("spec.marks must contain at least one mark")
    for index, mark in enumerate(marks, 1):
        if "box" not in mark or not isinstance(mark["box"], list) or len(mark["box"]) != 4:
            raise SystemExit("mark %d needs box=[x,y,w,h]" % index)
        start = float(mark.get("start", -1))
        end = float(mark.get("end", -1))
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise SystemExit("mark %d has invalid start/end" % index)
        if end > duration + 0.05:
            raise SystemExit("mark %d ends after the source video" % index)
        x, y, w, h = [int(v) for v in mark["box"]]
        if x < 0 or y < 0 or x + w > width or y + h > height:
            raise SystemExit("mark %d box is outside the source frame" % index)

    out_dir = args.output.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / (".annotate-" + args.output.stem)
    work.mkdir(parents=True, exist_ok=True)

    band = work / "band.png"
    draw_band(band, width, band_h, spec, font)

    inputs = ["-i", str(args.video), "-loop", "1", "-framerate", "25", "-i", str(band)]
    filters = [
        "[0:v]pad=%d:%d:0:%d:color=%s[v0]" % (width, height + band_h, band_h, BAND_BG),
        "[v0][1:v]overlay=0:0[v1]",
    ]
    previous = "[v1]"
    for index, mark in enumerate(sorted(marks, key=lambda item: float(item["start"])), 1):
        png = work / ("mark-%02d.png" % index)
        draw_mark(png, width, height + band_h, band_h, mark, font)
        inputs += ["-loop", "1", "-framerate", "25", "-i", str(png)]
        current = "[v%d]" % (index + 1)
        filters.append(
            "%s[%d:v]overlay=0:0:enable='between(t,%.3f,%.3f)'%s"
            % (previous, index + 1, float(mark["start"]), float(mark["end"]), current)
        )
        previous = current

    args_ffmpeg = [
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", previous, "-map", "0:a?", "-t", "%.3f" % duration,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(args.output),
    ]
    run(args_ffmpeg)
    print("Created %s (%dx%d, %.2fs, %d marks)" % (
        args.output, width, height + band_h, duration, len(marks)))


if __name__ == "__main__":
    main()