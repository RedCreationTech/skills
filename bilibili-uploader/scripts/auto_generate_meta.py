#!/usr/bin/env python3
"""
根据视频文件自动生成 B 站投稿的标题、简介、标签、分区等元数据。
依赖: ffprobe (ffmpeg)
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


# 关键词 -> (标签列表, 推荐分区tid)
KEYWORD_MAP = {
    "python": (["Python", "编程"], 231),
    "rust": (["Rust", "编程"], 231),
    "go": (["Go", "编程", "后端"], 231),
    "golang": (["Go", "编程", "后端"], 231),
    "java": (["Java", "编程", "后端"], 231),
    "javascript": (["JavaScript", "前端", "编程"], 231),
    "typescript": (["TypeScript", "前端", "编程"], 231),
    "react": (["React", "前端", "JavaScript"], 231),
    "vue": (["Vue", "前端", "JavaScript"], 231),
    "linux": (["Linux", "运维", "操作系统"], 231),
    "docker": (["Docker", "运维", "云原生"], 231),
    "kubernetes": (["K8s", "运维", "云原生"], 231),
    "ai": (["AI", "人工智能", "机器学习"], 231),
    "ml": (["机器学习", "AI", "Python"], 231),
    "game": (["游戏", "单机游戏"], 172),
    "gaming": (["游戏", "电子竞技"], 171),
    "lol": (["英雄联盟", "LOL", "电子竞技"], 171),
    "瓦": (["无畏契约", "FPS", "电子竞技"], 171),
    "cs": (["CS2", "FPS", "电子竞技"], 171),
    "fps": (["FPS", "射击游戏", "电子竞技"], 171),
    "music": (["音乐"], 31),
    "吉他": (["吉他", "音乐", "弹唱"], 31),
    "钢琴": (["钢琴", "音乐", "演奏"], 31),
    "翻唱": (["翻唱", "音乐", "VOCALOID"], 31),
    "教程": (["教程", "学习"], 231),
    "vlog": (["Vlog", "生活", "日常"], 21),
    "评测": (["测评", "数码", "科技"], 232),
    "开箱": (["开箱", "数码", "购物分享"], 232),
    "mac": (["Mac", "苹果", "数码"], 232),
    "iphone": (["iPhone", "苹果", "数码"], 232),
    "安卓": (["Android", "数码", "手机"], 232),
}


def probe_video(video_path: str) -> dict:
    """使用 ffprobe 提取视频元数据"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,bit_rate",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name",
        "-of", "json",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr}")
    return json.loads(result.stdout)


def format_duration(seconds: float) -> str:
    """格式化时长"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def parse_filename(filename: str) -> str:
    """从文件名提取干净的标题"""
    # 去掉扩展名
    name = Path(filename).stem
    # 替换常见分隔符为空格
    name = re.sub(r"[_\-\.]+", " ", name)
    # 去掉常见垃圾词/序号
    name = re.sub(r"\b(1080p|720p|4k|60fps|30fps|hdr|hevc|h264|h265|x264|x265|aac|mp4|mkv|avi)\b", "", name, flags=re.I)
    name = re.sub(r"\b(ep|episode|vol|volume|part|chapter|第)\s*\d+\b", "", name, flags=re.I)
    # 去掉多余空格
    name = re.sub(r"\s+", " ", name).strip()
    # 首字母大写（英文单词）
    name = name.title()
    return name


def guess_tags_and_tid(title: str) -> tuple:
    """根据标题关键词猜测标签和分区"""
    title_lower = title.lower()
    tags = set()
    tid = 231  # 默认：计算机技术

    for keyword, (kw_tags, kw_tid) in KEYWORD_MAP.items():
        if keyword in title_lower:
            tags.update(kw_tags)
            tid = kw_tid

    if not tags:
        tags = {"教程", "分享", "原创"}

    return list(tags)[:12], tid


def generate_meta(video_path: str, custom_title: str = None) -> dict:
    """生成完整的投稿元数据"""
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(video_path)

    # 1. 提取视频信息
    info = probe_video(video_path)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

    duration = float(fmt.get("duration", 0))
    size = int(fmt.get("size", 0))
    bit_rate = int(fmt.get("bit_rate", 0))
    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)
    codec = video_stream.get("codec_name", "unknown")

    # fps 可能是 "30000/1001" 这样的分数
    fps_str = video_stream.get("r_frame_rate", "0/1")
    try:
        num, den = map(int, fps_str.split("/"))
        fps = round(num / den, 2) if den else 0
    except Exception:
        fps = 0

    # 2. 生成标题
    title = custom_title or parse_filename(path.name)
    if not title:
        title = f"视频分享 {datetime.now().strftime('%Y-%m-%d')}"

    # 3. 猜测标签和分区
    tags, tid = guess_tags_and_tid(title)

    # 4. 生成简介
    desc_lines = [
        f"📹 {title}",
        "",
        f"⏱️ 时长: {format_duration(duration)}",
        f"🎞️ 分辨率: {width}x{height}" if width else "",
        f"🎬 编码: {codec.upper()}" if codec != "unknown" else "",
        f"📐 帧率: {fps} fps" if fps else "",
        f"💾 大小: {format_size(size)}",
        f"📊 码率: {bit_rate // 1000} kbps" if bit_rate else "",
        "",
        f"📅 自动上传于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "喜欢的话记得一键三连~",
    ]
    desc = "\n".join(line for line in desc_lines if line)

    return {
        "title": title,
        "desc": desc,
        "tags": tags,
        "tid": tid,
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": codec,
        "size": size,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="自动生成 B 站投稿元数据")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("--title", help="手动指定标题（否则从文件名解析）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    meta = generate_meta(args.video, args.title)

    if args.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print(f"标题: {meta['title']}")
        print(f"分区: {meta['tid']}")
        print(f"标签: {', '.join(meta['tags'])}")
        print("-" * 50)
        print("简介:")
        print(meta['desc'])
        print("=" * 50)


if __name__ == "__main__":
    main()
