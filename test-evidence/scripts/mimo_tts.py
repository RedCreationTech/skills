#!/usr/bin/env python3
"""Generate one narration line with MiMo TTS.

The API key is read only from MIMO_API_KEY. It is never written to disk,
echoed, logged, or passed on the command line. HTTP errors report the status
code only; response bodies are not printed.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
DEFAULT_MODEL = "mimo-v2.5-tts"
DEFAULT_VOICE = "冰糖"
DEFAULT_STYLE = "中文技术解说，口齿清晰，语速适中，语气平稳。"


def read_text(args):
    if args.text_file:
        return args.text_file.read_text(encoding="utf-8").strip()
    return (args.text or "").strip()


def cache_path(directory, model, voice, style, text):
    digest = hashlib.sha256(
        ("%s|%s|%s|%s" % (model, voice, style, text)).encode("utf-8")).hexdigest()[:20]
    return directory / ("mimo-%s.wav" % digest)


def synthesize(api_key, model, voice, style, text, timeout):
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "user", "content": style},
            {"role": "assistant", "content": text},
        ],
        "audio": {"format": "wav", "voice": voice},
    }).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={
        "authorization": "Bearer " + api_key,
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit("MiMo HTTP error: status %s" % error.code)
    except urllib.error.URLError as error:
        raise SystemExit("MiMo request failed: %s" % type(error.reason).__name__)
    except (TimeoutError, json.JSONDecodeError):
        raise SystemExit("MiMo request failed: timeout or invalid JSON")

    choices = payload.get("choices") or []
    audio = ((choices[0] if choices else {}).get("message") or {}).get("audio") or {}
    data = audio.get("data")
    if not data:
        raise SystemExit("MiMo response did not include audio data")
    try:
        return base64.b64decode(data, validate=True)
    except ValueError:
        raise SystemExit("MiMo audio payload is not valid base64")


def normalize(raw, output):
    if shutil.which("ffmpeg") is None:
        output.write_bytes(raw)
        return
    temp = output.with_suffix(".raw.wav")
    temp.write_bytes(raw)
    proc = subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(temp),
        "-af", ("silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB:detection=peak,"
                "areverse,silenceremove=start_periods=1:start_silence=0.08:start_threshold=-45dB:detection=peak,"
                "areverse,loudnorm=I=-16:TP=-1.5:LRA=11"),
        "-ar", "48000", "-ac", "1", str(output),
    ], capture_output=True, text=True)
    temp.unlink(missing_ok=True)
    if proc.returncode:
        sys.stderr.write((proc.stderr or "")[-1000:] + "\n")
        raise SystemExit("ffmpeg failed to normalize the MiMo audio")
    return


def duration(path):
    if shutil.which("ffprobe") is None:
        return None
    proc = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], capture_output=True, text=True)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--text-file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--style", default=DEFAULT_STYLE)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--raw", action="store_true", help="skip silence trim and loudness normalization")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    text = read_text(args)
    if not text:
        raise SystemExit("Narration text is empty")
    if len(text) > 300:
        raise SystemExit("Narration line is %d characters; split it into shorter lines" % len(text))

    if args.output.exists() and not args.force:
        raise SystemExit("Output exists; pass --force to replace: %s" % args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.cache_dir and not args.force:
        cached = cache_path(args.cache_dir, args.model, args.voice, args.style, text)
        if cached.is_file() and cached.stat().st_size > 1000:
            if cached != args.output:
                shutil.copyfile(cached, args.output)
            print("Cached %s" % args.output)
            return

    api_key = os.environ.get("MIMO_API_KEY", "").strip()
    if args.dry_run:
        print("Dry run: model=%s voice=%s chars=%d output=%s key=%s"
              % (args.model, args.voice, len(text), args.output, "set" if api_key else "missing"))
        return
    if not api_key:
        raise SystemExit("MIMO_API_KEY is not set")

    raw = synthesize(api_key, args.model, args.voice, args.style, text, args.timeout)

    if args.raw or shutil.which("ffmpeg") is None:
        args.output.write_bytes(raw)
    else:
        normalize(raw, args.output)

    if args.cache_dir:
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        cached = cache_path(args.cache_dir, args.model, args.voice, args.style, text)
        if cached != args.output:
            shutil.copyfile(args.output, cached)

    length = duration(args.output)
    print("Created %s%s (%d bytes)" % (
        args.output, "" if length is None else " (%.2fs)" % length, args.output.stat().st_size))


if __name__ == "__main__":
    main()