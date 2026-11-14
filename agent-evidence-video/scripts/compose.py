#!/usr/bin/env python3
"""Compose recorded chapters with outline, timed speech and readable captions."""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, SIDE = 1920, 1080, 360

def run(args):
    subprocess.run(args, check=True)

def duration(path):
    raw = subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
                                   '-of','default=noprint_wrappers=1:nokey=1',str(path)], text=True)
    return float(raw.strip())

def font_path(requested):
    candidates = [requested, '/System/Library/Fonts/PingFang.ttc',
                  '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf',
                  'C:/Windows/Fonts/msyh.ttc']
    for item in candidates:
        if item and Path(item).is_file(): return item
    raise ValueError('No font found; specify --font with a CJK-capable font.')

def wrap(draw, text, font, width):
    lines, current = [], ''
    for char in text:
        if char == '\n':
            lines.append(current); current = ''; continue
        if current and draw.textlength(current + char, font=font) > width:
            lines.append(current); current = char
        else: current += char
    if current: lines.append(current)
    return lines

def outline(path, title, scenes, active, fontfile):
    img=Image.new('RGB',(SIDE,H),'#0c1d2e'); d=ImageDraw.Draw(img)
    brand=ImageFont.truetype(fontfile,25); small=ImageFont.truetype(fontfile,17)
    rowfont=ImageFont.truetype(fontfile,21)
    title_lines=wrap(d,title,brand,SIDE-40)
    if len(title_lines)>3: raise ValueError('Outline title is too long.')
    d.text((20,32),'WORK EVIDENCE  /  DEMO',font=small,fill='#80d7c5')
    y=72
    for line in title_lines: d.text((20,y),line,font=brand,fill='#f2f8f6'); y+=35
    y+=25; available=H-y-34; row=min(67,available//len(scenes))
    if row<38: raise ValueError('Too many chapters for one outline page; split the video.')
    for idx,scene in enumerate(scenes):
        top=y+idx*row
        if idx==active: d.rounded_rectangle((14,top,SIDE-15,top+row-5),radius=7,fill='#15506a')
        d.text((26,top+8),f'{idx+1:02}',font=small,fill='#75d6c7')
        name=scene['title']; lines=wrap(d,name,rowfont,SIDE-85)
        if len(lines)>1: raise ValueError(f'Chapter title too long for outline: {name}')
        d.text((65,top+5),name,font=rowfont,fill='#ffffff' if idx==active else '#b8c8d4')
    img.save(path)

def caption(path,text,fontfile):
    img=Image.new('RGBA',(W-SIDE-56,150),(0,0,0,0)); d=ImageDraw.Draw(img)
    font=ImageFont.truetype(fontfile,28); lines=wrap(d,text,font,img.width-52)
    if not lines or len(lines)>3: raise ValueError('Caption is empty or too long; split the narration into shorter lines.')
    h=24+len(lines)*38; y=150-h
    d.rounded_rectangle((0,y,img.width-1,149),radius=10,fill=(11,28,45,235))
    for line in lines:
        x=(img.width-d.textlength(line,font=font))/2
        d.text((x,y+10),line,font=font,fill='white',stroke_width=0); y+=38
    img.save(path)

def timestamp(seconds):
    ms=round(seconds*1000); hours,ms=divmod(ms,3600000); minutes,ms=divmod(ms,60000); sec,ms=divmod(ms,1000)
    return f'{hours:02}:{minutes:02}:{sec:02},{ms:03}'

def resolve(base,value):
    path=Path(value); return path if path.is_absolute() else base/path

def scene_input(manifest):
    scenes=manifest.get('scenes')
    if not isinstance(scenes,list) or not scenes: raise ValueError('Manifest must contain scenes.')
    for scene in scenes:
        if not scene.get('title') or not scene.get('capture'): raise ValueError('Each scene needs title and capture.')
        if not isinstance(scene.get('lines'),list) or not scene['lines']: raise ValueError('Each scene needs at least one narrated line.')
    return scenes

def render_scene(scene,index,scenes,title,root,out,fontfile,cumulative):
    capture=resolve(root,scene['capture']); length=duration(capture)
    if not math.isfinite(length) or length<=0: raise ValueError('Invalid capture duration.')
    outlinefile=out/f'outline-{index:02}.png'; outline(outlinefile,title,scenes,index,fontfile)
    lines=[]; prior_end=0
    for j,line in enumerate(scene['lines']):
        text=line['text'].strip(); audio=resolve(root,line['audio']); start=float(line['start']); end=start+duration(audio)
        if not text or not math.isfinite(start) or start<prior_end-0.001 or end>length-0.02:
            raise ValueError(f'Invalid or overlapping line timing in scene {index+1}, line {j+1}.')
        capfile=out/f'caption-{index:02}-{j:02}.png'; caption(capfile,text,fontfile)
        lines.append({'text':text,'audio':audio,'start':start,'end':end,'image':capfile});prior_end=end
    args=['ffmpeg','-v','error','-y','-i',str(capture),'-loop','1','-i',str(outlinefile)]
    for line in lines: args += ['-loop','1','-i',str(line['image'])]
    for line in lines: args += ['-i',str(line['audio'])]
    silence=2+2*len(lines); args+=['-f','lavfi','-t',f'{length:.3f}','-i','anullsrc=r=48000:cl=stereo']
    filters=[f'[0:v]scale={W-SIDE}:{H}:force_original_aspect_ratio=decrease,pad={W-SIDE}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=25[screen]',
             f'[screen]pad={W}:{H}:{SIDE}:0:color=black[base]','[base][1:v]overlay=0:0:shortest=1[v0]']
    for j,line in enumerate(lines):
        filters.append(f"[v{j}][{j+2}:v]overlay={SIDE+28}:{H-170}:enable='between(t,{line['start']:.3f},{line['end']:.3f})':shortest=1[v{j+1}]")
        delay=round(line['start']*1000); filters.append(f'[{2+len(lines)+j}:a]aresample=48000,adelay={delay}|{delay}[a{j}]')
    audio_inputs=f'[{silence}:a]'+''.join(f'[a{j}]' for j in range(len(lines)))
    filters.append(f'{audio_inputs}amix=inputs={len(lines)+1}:duration=first:normalize=0[aout]')
    target=out/f'scene-{index+1:02}.mp4'
    args+=['-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map',f'[v{len(lines)}]',
           '-map','[aout]','-t',f'{length:.3f}','-c:v','libx264','-preset','medium','-crf','23',
           '-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-movflags','+faststart',str(target)]
    run(args)
    return target,duration(target),[{'start':cumulative+l['start'],'end':cumulative+l['end'],'text':l['text']} for l in lines]

def concat_escape(path):
    return str(path.resolve()).replace("'", "'\\''")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--font')
    args=p.parse_args(); root=args.manifest.resolve().parent; out=args.output_dir.resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Output directory must be empty; existing files are preserved.')
    out.mkdir(parents=True,exist_ok=True); manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    scenes=scene_input(manifest); fontfile=font_path(args.font); total=0; captions=[]; clips=[]; chapters=[]
    for i,scene in enumerate(scenes):
        clip,length,items=render_scene(scene,i,scenes,manifest.get('title','工作成果演示'),root,out,fontfile,total)
        clips.append(clip);chapters.append((total,total+length,scene['title']));captions.extend(items);total+=length
    (out/'subtitles.srt').write_text('\n\n'.join(f"{i}\n{timestamp(x['start'])} --> {timestamp(x['end'])}\n{x['text']}" for i,x in enumerate(captions,1))+'\n',encoding='utf-8')
    (out/'concat.txt').write_text(''.join(f"file '{concat_escape(x)}'\n" for x in clips),encoding='utf-8')
    def esc(t): return re.sub(r'([=;#\\])',r'\\\1',t).replace('\n',' ')
    meta=';FFMETADATA1\n'+''.join(f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(a*1000)}\nEND={round(b*1000)}\ntitle={esc(t)}\n' for a,b,t in chapters)
    (out/'chapters.ffmeta').write_text(meta,encoding='utf-8')
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(out/'concat.txt'),'-i',str(out/'chapters.ffmeta'),'-map','0:v','-map','0:a','-map_metadata','1','-map_chapters','1','-c','copy','-movflags','+faststart',str(out/'evidence-video.mp4')])
    run(['ffmpeg','-v','error','-i',str(out/'evidence-video.mp4'),'-f','null','-'])
    print(f'Created {out / "evidence-video.mp4"} ({total:.2f}s, {len(scenes)} chapters, {len(captions)} captions).')

if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
        print(f'Composition failed: {e}',file=sys.stderr);sys.exit(1)
