#!/usr/bin/env python3
"""Verify a composed test-evidence video against its manifest and evidence JSON.

Checks resolution, codecs, chapters, full decode, SRT boundaries, narration
timing and verdict/report consistency. It cannot judge whether the recorded
actions are truthful; that still needs human review.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

VERDICTS = ("pass", "fail", "blocked", "unexecuted")
EXPECTED_W = 1920
EXPECTED_H = 1080
EXPECTED_FPS = 25.0


class Report:
    def __init__(self):
        self.items = []

    def ok(self, message):
        self.items.append(("OK", message))

    def warn(self, message):
        self.items.append(("WARN", message))

    def fail(self, message):
        self.items.append(("FAIL", message))

    def errors(self):
        return sum(1 for level, _ in self.items if level == "FAIL")

    def warnings(self):
        return sum(1 for level, _ in self.items if level == "WARN")

    def print(self):
        for level, message in self.items:
            print("%-4s %s" % (level, message))


def run(args, timeout=None):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def probe(path):
    proc = run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels,duration",
        "-show_entries", "format=duration", "-show_chapters", "-of", "json", str(path),
    ])
    if proc.returncode:
        raise SystemExit("ffprobe failed for %s:\n%s" % (path, proc.stderr[-2000:]))
    return json.loads(proc.stdout)


def audio_duration(path):
    proc = run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path),
    ])
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def parse_srt(path):
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    blocks = re.split(r"\n\s*\n", text)
    cues = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            raise ValueError("SRT block is too short: %r" % block[:80])
        index = int(lines[0].strip())
        match = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1].strip())
        if not match:
            raise ValueError("SRT timing is invalid: %r" % lines[1])
        start = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000
        end = int(match.group(5)) * 3600 + int(match.group(6)) * 60 + int(match.group(7)) + int(match.group(8)) / 1000
        cues.append({"index": index, "start": start, "end": end, "text": "\n".join(lines[2:]).strip()})
    return cues


def normalize(text):
    return re.sub(r"\s+", "", str(text))


def verify_manifest(manifest, report):
    base = manifest["_base"]
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        report.fail("manifest has no scenes")
        return [], 0.0

    ids, offset = set(), 0.0
    expected_cues = []
    for index, scene in enumerate(scenes, 1):
        where = "scene %d" % index
        missing = [key for key in ("id", "title", "verdict", "capture", "lines") if key not in scene]
        if missing:
            report.fail("%s missing %s" % (where, ", ".join(missing)))
            continue
        if scene["id"] in ids:
            report.fail("duplicate scene id: %s" % scene["id"])
        ids.add(scene["id"])

        verdict = scene["verdict"]
        if verdict not in VERDICTS:
            report.fail("%s has invalid verdict %r" % (where, verdict))
        if verdict == "fail" and not scene.get("defect"):
            report.fail("%s is fail without defect id" % where)
        if verdict in ("blocked", "unexecuted") and not scene.get("reason"):
            report.fail("%s is %s without reason" % (where, verdict))
        if verdict == "pass" and scene.get("defect"):
            report.warn("%s is pass but references defect %s" % (where, scene["defect"]))

        capture = (base / scene["capture"]).resolve()
        if not capture.is_file():
            report.fail("%s capture missing: %s" % (where, capture))
            continue
        info = probe(capture)
        duration = float(info["format"]["duration"])
        report.ok("%s capture %.2fs" % (scene["id"], duration))

        previous_end = -1.0
        for line_index, line in enumerate(scene.get("lines") or [], 1):
            line_where = "%s line %d" % (where, line_index)
            text = str(line.get("text") or "").strip()
            if not text:
                report.fail("%s has empty text" % line_where)
            audio = (base / line.get("audio", "")).resolve()
            if not audio.is_file():
                report.fail("%s audio missing: %s" % (line_where, audio))
                continue
            length = audio_duration(audio)
            if length is None:
                report.fail("%s audio duration is unreadable" % line_where)
                continue
            start = float(line.get("start", -1))
            if start < 0 or not math.isfinite(start):
                report.fail("%s has invalid start" % line_where)
                continue
            if start < previous_end - 0.001:
                report.fail("%s (%.2fs) overlaps previous line ending %.2fs"
                            % (line_where, start, previous_end))
            if start + length > duration + 0.05:
                report.fail("%s ends at %.2fs beyond capture %.2fs"
                            % (line_where, start + length, duration))
            previous_end = start + length
            expected_cues.append((offset + start, offset + start + length, text, line_where))

        offset += math.ceil(duration * EXPECTED_FPS - 1e-6) / EXPECTED_FPS
    return expected_cues, offset


def verify_video(path, report, expected_duration):
    if not path.is_file():
        report.fail("video missing: %s" % path)
        return None
    info = probe(path)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration = float(info["format"]["duration"])

    if not video:
        report.fail("no video stream")
    else:
        if int(video.get("width", 0)) != EXPECTED_W or int(video.get("height", 0)) != EXPECTED_H:
            report.fail("resolution is %sx%s, expected %dx%d"
                        % (video.get("width"), video.get("height"), EXPECTED_W, EXPECTED_H))
        else:
            report.ok("resolution %dx%d" % (EXPECTED_W, EXPECTED_H))
        if video.get("codec_name") != "h264":
            report.fail("video codec is %r, expected h264" % video.get("codec_name"))
        try:
            num, den = str(video.get("avg_frame_rate", "0/1")).split("/")
            fps = float(num) / float(den) if float(den) else 0
        except (ValueError, ZeroDivisionError):
            fps = 0
        if abs(fps - EXPECTED_FPS) > 0.1:
            report.fail("frame rate is %.3f, expected %.1f" % (fps, EXPECTED_FPS))
        else:
            report.ok("frame rate %.2f" % fps)

    if not audio:
        report.fail("no audio stream")
    else:
        if audio.get("codec_name") != "aac":
            report.warn("audio codec is %r (aac expected)" % audio.get("codec_name"))
        report.ok("audio %s, %s Hz, %s ch" % (
            audio.get("codec_name"), audio.get("sample_rate"), audio.get("channels")))

    if abs(duration - expected_duration) > 1.5:
        report.warn("video duration %.2fs differs from planned %.2fs" % (duration, expected_duration))
    else:
        report.ok("duration %.2fs matches the plan" % duration)

    chapters = info.get("chapters") or []
    if not chapters:
        report.fail("no chapters embedded in the video")
    else:
        report.ok("%d chapters embedded" % len(chapters))
        last = -1.0
        for chapter in sorted(chapters, key=lambda item: float(item["start_time"])):
            start = float(chapter["start_time"])
            if start < last - 0.05:
                report.fail("chapter order is invalid at %s" % chapter.get("tags", {}).get("title"))
            last = start
    return duration


def verify_srt(path, report, expected, video_duration):
    if not path.is_file():
        report.fail("SRT missing: %s" % path)
        return
    try:
        cues = parse_srt(path)
    except (ValueError, OSError) as error:
        report.fail("SRT parse error: %s" % error)
        return

    if len(cues) != len(expected):
        report.fail("SRT has %d cues, manifest has %d narration lines" % (len(cues), len(expected)))
    else:
        report.ok("%d SRT cues" % len(cues))

    previous = -1.0
    for position, (cue, (start, end, text, where)) in enumerate(zip(cues, expected), 1):
        if cue["index"] != position:
            report.fail("SRT cue numbering is not sequential at %d" % cue["index"])
        if cue["start"] < previous - 0.001:
            report.fail("SRT cue %d starts before the previous cue" % cue["index"])
        previous = cue["start"]
        if abs(cue["start"] - start) > 0.02 or abs(cue["end"] - end) > 0.02:
            report.fail("SRT cue %d (%.2f-%.2f) != narration (%.2f-%.2f)"
                        % (cue["index"], cue["start"], cue["end"], start, end))
        if normalize(cue["text"]) != normalize(text):
            report.fail("SRT cue %d text differs from %s" % (cue["index"], where))
        if cue["end"] > video_duration + 0.05:
            report.fail("SRT cue %d ends after the video" % cue["index"])
    if len(cues) == len(expected):
        report.ok("SRT text and timing match the manifest")


def verify_decode(path, report):
    proc = run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], timeout=3600)
    stderr = (proc.stderr or "").strip()
    if proc.returncode or stderr:
        tail = "\n".join(stderr.splitlines()[-8:])
        report.fail("full decode reported problems:\n%s" % tail)
    else:
        report.ok("full decode clean")


def verify_summary(path, manifest, report):
    if not path.is_file():
        report.fail("summary missing: %s" % path)
        return
    summary = json.loads(path.read_text(encoding="utf-8"))
    counts = {key: 0 for key in VERDICTS}
    for scene in manifest.get("scenes", []):
        if scene.get("verdict") in counts:
            counts[scene["verdict"]] += 1
    if summary.get("verdicts") != counts:
        report.fail("summary verdicts %r != manifest %r" % (summary.get("verdicts"), counts))
    else:
        report.ok("summary verdict counts match the manifest")
    defects = sorted(scene["defect"] for scene in manifest.get("scenes", []) if scene.get("defect"))
    if sorted(summary.get("defects") or []) != defects:
        report.fail("summary defects %r != manifest %r" % (summary.get("defects"), defects))


def verify_evidence(path, report):
    if not path.is_file():
        report.fail("evidence JSON missing: %s" % path)
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "test-evidence/1":
        report.fail("evidence schema is %r, expected test-evidence/1" % data.get("schema"))
    assertions = data.get("assertions") or []
    summary = data.get("summary") or {}
    passed = sum(1 for item in assertions if item.get("verdict") == "pass")
    failed = sum(1 for item in assertions if item.get("verdict") == "fail")
    if summary.get("total") != len(assertions):
        report.fail("evidence summary.total %r != assertions %d" % (summary.get("total"), len(assertions)))
    if summary.get("pass") != passed or summary.get("fail") != failed:
        report.fail("evidence summary pass/fail %r/%r != %d/%d"
                    % (summary.get("pass"), summary.get("fail"), passed, failed))
    if not failed and not assertions:
        report.warn("evidence JSON contains no assertions")
    for item in assertions:
        if item.get("verdict") == "fail" and not item.get("defect"):
            report.warn("failed assertion %s has no defect id" % item.get("id"))
    if data.get("console"):
        report.warn("evidence recorded %d console errors; review them" % len(data["console"]))
    if data.get("failedRequests"):
        report.warn("evidence recorded %d failed requests; review them" % len(data["failedRequests"]))
    report.ok("evidence JSON: %d assertions, %d failed" % (len(assertions), failed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--srt", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--no-decode", action="store_true")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("ffmpeg and ffprobe are required")
    if not args.manifest.is_file():
        raise SystemExit("manifest not found: %s" % args.manifest)

    report = Report()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest["_base"] = args.manifest.parent

    expected, planned = verify_manifest(manifest, report)
    duration = verify_video(args.video, report, planned)
    if duration is None:
        duration = planned
    srt = args.srt or args.video.with_name("subtitles.srt")
    verify_srt(srt, report, expected, duration)
    summary = args.summary or args.video.with_name("evidence-summary.json")
    if summary.is_file():
        verify_summary(summary, manifest, report)
    else:
        report.warn("no evidence-summary.json next to the video")
    if args.evidence:
        verify_evidence(args.evidence, report)
    if not args.no_decode:
        verify_decode(args.video, report)

    report.print()
    errors, warnings = report.errors(), report.warnings()
    print("\n%d checks failed, %d warnings" % (errors, warnings))

    if args.json_out:
        args.json_out.write_text(json.dumps({
            "schema": "test-evidence-verify/1",
            "errors": errors,
            "warnings": warnings,
            "checks": [{"level": level, "message": message} for level, message in report.items],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors or (args.strict and warnings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()