#!/usr/bin/env python3
"""Generate one MiMo speech clip. Never write credentials or response bodies to logs."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = 'https://api.xiaomimimo.com/v1/chat/completions'
STYLE = '自然清晰的中文产品介绍，语速适中，准确朗读原文，不添加内容。'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--voice', default='冰糖')
    parser.add_argument('--model', default='mimo-v2.5-tts')
    args = parser.parse_args()
    key = os.environ.get('MIMO_API_KEY')
    if not key:
        parser.error('Set MIMO_API_KEY in the environment.')
    if args.output.exists():
        parser.error('Output exists; choose a new path.')
    text = args.text_file.read_text(encoding='utf-8').strip()
    if not text:
        parser.error('The text file is empty.')
    payload = {'model': args.model, 'messages': [{'role':'user','content':STYLE},
               {'role':'assistant','content':text}], 'audio': {'format':'wav','voice':args.voice}}
    req = Request(URL, data=json.dumps(payload, ensure_ascii=False).encode(),
                  headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'}, method='POST')
    try:
        with urlopen(req, timeout=180) as response:
            data = json.load(response)
        audio = base64.b64decode(data['choices'][0]['message']['audio']['data'], validate=True)
        if not audio.startswith(b'RIFF') or audio[8:12] != b'WAVE':
            raise ValueError('Invalid WAV')
    except HTTPError as exc:
        print(f'MiMo request failed: HTTP {exc.code}.', file=sys.stderr); return 1
    except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
        print('MiMo request failed or returned invalid audio; response withheld.', file=sys.stderr); return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(audio)
    print(f'Created {args.output}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
