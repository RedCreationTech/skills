#!/usr/bin/env python3
"""
Bilibili 一键自动上传脚本
自动分析视频 → 生成标题/简介/标签 → 调用 biliup 上传

用法:
    # 全自动（基于文件名生成所有元数据）
    python auto_upload.py ~/Videos/my_video.mp4

    # 手动指定标题，其余自动生成
    python auto_upload.py ~/Videos/my_video.mp4 --title "Rust 异步编程深度解析"

    # 仅预览生成的元数据，不上传
    python auto_upload.py ~/Videos/my_video.mp4 --dry-run

    # 添加额外标签
    python auto_upload.py ~/Videos/my_video.mp4 --extra-tags "爆款,必看"

    # 定时发布
    python auto_upload.py ~/Videos/my_video.mp4 --dtime "2025-04-20 18:00"
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 导入同目录下的模块
sys.path.insert(0, str(Path(__file__).parent))
from auto_generate_meta import generate_meta


def confirm(message: str) -> bool:
    """询问确认"""
    try:
        resp = input(f"{message} [y/N]: ").strip().lower()
        return resp == 'y'
    except (EOFError, KeyboardInterrupt):
        return False


def main():
    parser = argparse.ArgumentParser(description="Bilibili 一键自动上传")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("--title", help="手动指定标题（默认从文件名解析）")
    parser.add_argument("--desc", help="手动指定简介（默认自动生成）")
    parser.add_argument("--tags", help="手动指定标签，逗号分隔（默认自动推测）")
    parser.add_argument("--extra-tags", help="额外追加的标签，逗号分隔")
    parser.add_argument("--tid", type=int, help="投稿分区 ID（默认自动推测）")
    parser.add_argument("--cover", help="封面图片路径")
    parser.add_argument("--dtime", help="定时发布时间（YYYY-MM-DD HH:MM）")
    parser.add_argument("--copyright", type=int, choices=[1, 2], default=1, help="1=自制, 2=转载")
    parser.add_argument("--no-reprint", type=int, choices=[0, 1], default=1)
    parser.add_argument("--dynamic", help="空间动态文案")
    parser.add_argument("--config", help="biliup 配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览元数据，不上传")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认直接上传")
    args = parser.parse_args()

    # 1. 自动生成元数据
    print("📊 正在分析视频并生成元数据...")
    meta = generate_meta(args.video, custom_title=args.title)

    # 2. 应用手动覆盖
    if args.desc:
        meta["desc"] = args.desc
    if args.tags:
        meta["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.extra_tags:
        extra = [t.strip() for t in args.extra_tags.split(",") if t.strip()]
        meta["tags"] = list(dict.fromkeys(meta["tags"] + extra))[:12]
    if args.tid:
        meta["tid"] = args.tid

    # 3. 显示预览
    print("\n" + "=" * 60)
    print("📝 投稿预览")
    print("=" * 60)
    print(f"视频: {args.video}")
    print(f"标题: {meta['title']}")
    print(f"分区: {meta['tid']}")
    print(f"标签: {', '.join(meta['tags'])}")
    print(f"时长: {meta.get('duration', 0)//60:.0f}分{meta.get('duration', 0)%60:.0f}秒")
    print(f"分辨率: {meta.get('width', 0)}x{meta.get('height', 0)}")
    print("-" * 60)
    print("简介:")
    print(meta['desc'])
    print("=" * 60)

    if args.dry_run:
        print("\n🏁 Dry-run 模式，已退出")
        return

    # 4. 确认上传
    if not args.yes:
        if not confirm("\n确认使用以上信息上传？"):
            print("已取消")
            return

    # 5. 构建上传命令
    uploader = Path(__file__).parent / "bilibili_uploader.py"
    cmd = [
        sys.executable, str(uploader), "upload", args.video,
        "--title", meta["title"],
        "--desc", meta["desc"],
        "--tags", ",".join(meta["tags"]),
        "--tid", str(meta["tid"]),
        "--copyright", str(args.copyright),
        "--no-reprint", str(args.no_reprint),
    ]

    if args.cover:
        cmd.extend(["--cover", args.cover])
    if args.dtime:
        cmd.extend(["--dtime", args.dtime])
    if args.dynamic:
        cmd.extend(["--dynamic", args.dynamic])
    if args.config:
        cmd.extend(["--config", args.config])

    # 6. 执行上传
    print("\n🚀 开始上传...\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
