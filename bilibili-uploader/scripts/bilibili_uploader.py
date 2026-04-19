#!/usr/bin/env python3
"""
Bilibili 自动上传脚本
基于 biliup-rs (Rust) 的 Python 封装

用法:
    # 1. 先登录（只需一次，会保存 cookie）
    python bilibili_uploader.py login

    # 2. 上传视频
    python bilibili_uploader.py upload /path/to/video.mp4

    # 3. 使用配置文件上传
    python bilibili_uploader.py upload /path/to/video.mp4 --config ./my_config.json
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 默认配置
DEFAULT_CONFIG = {
    "cookie_path": str(Path(__file__).parent / "cookies.json"),
    "biliup_path": "biliup",
    "defaults": {
        "tid": 231,           # 分区ID：231=计算机技术，171=电子竞技，172=单机游戏
        "copyright": 1,       # 1=自制, 2=转载
        "source": "",         # 转载来源
        "no_reprint": 1,      # 0=允许转载, 1=禁止转载
        "open_elec": 1,       # 0=关闭充电, 1=开启
        "line": "bda2",       # 上传线路: bda2, ws, qn, tx, txa
        "limit": 3,           # 单文件并发数
        "tags": ["教程", "技术"],
        "desc_template": "{title}\n\n自动上传于 {date}",
        "dynamic": ""
    }
}


def run_cmd(cmd: list, check=True) -> subprocess.CompletedProcess:
    """执行命令并返回结果"""
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"命令执行失败，返回码: {result.returncode}")
    return result


def login(cookie_path: str, biliup_path: str = "biliup"):
    """登录 B 站并保存 cookie"""
    cookie_file = Path(cookie_path)
    if cookie_file.exists():
        print(f"警告: cookie 文件已存在 ({cookie_path})，将覆盖")
        resp = input("是否继续? [y/N]: ").strip().lower()
        if resp != 'y':
            print("取消登录")
            return

    cmd = [biliup_path, "login", "--user-cookie", cookie_path]
    run_cmd(cmd, check=False)
    print(f"\n登录信息已保存到: {cookie_path}")


def load_config(config_path: str = None) -> dict:
    """加载配置文件，若不存在则返回默认配置"""
    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            user_cfg = json.load(f)
        # 合并配置
        cfg = DEFAULT_CONFIG.copy()
        cfg.update(user_cfg)
        return cfg
    return DEFAULT_CONFIG.copy()


def build_upload_cmd(video_path: str, cfg: dict, **overrides) -> list:
    """构建 biliup upload 命令"""
    d = cfg["defaults"].copy()
    d.update(overrides)

    # 检查视频文件
    if not Path(video_path).exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 检查 cookie
    cookie_path = cfg.get("cookie_path", "cookies.json")
    if not Path(cookie_path).exists():
        raise FileNotFoundError(
            f"Cookie 文件不存在: {cookie_path}\n请先运行: python {__file__} login"
        )

    cmd = [
        cfg.get("biliup_path", "biliup"),
        "-u", cookie_path,
        "upload", video_path,
        "--title", d["title"],
        "--desc", d.get("desc", ""),
        "--tag", ",".join(d.get("tags", [])),
        "--tid", str(d.get("tid", 231)),
        "--copyright", str(d.get("copyright", 1)),
        "--no-reprint", str(d.get("no_reprint", 0)),
        "--open-elec", str(d.get("open_elec", 1)),
        "--line", d.get("line", "bda2"),
        "--limit", str(d.get("limit", 3)),
    ]

    if d.get("source"):
        cmd.extend(["--source", d["source"]])
    if d.get("cover") and Path(d["cover"]).exists():
        cmd.extend(["--cover", d["cover"]])
    if d.get("dynamic"):
        cmd.extend(["--dynamic", d["dynamic"]])
    if d.get("dtime"):
        cmd.extend(["--dtime", str(int(d["dtime"]))])
    if d.get("dolby"):
        cmd.extend(["--dolby", str(d["dolby"])])
    if d.get("hires"):
        cmd.extend(["--hires", str(d["hires"])])

    return cmd


def upload(video_path: str, config_path: str = None, **kwargs):
    """上传视频"""
    cfg = load_config(config_path)

    # 生成标题（若未提供）
    if not kwargs.get("title"):
        video_name = Path(video_path).stem
        kwargs["title"] = video_name

    # 生成简介（若使用模板且未提供）
    if not kwargs.get("desc") and cfg["defaults"].get("desc_template"):
        kwargs["desc"] = cfg["defaults"]["desc_template"].format(
            title=kwargs["title"],
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            filename=Path(video_path).name
        )

    # 标签去重、限制
    tags = kwargs.get("tags") or cfg["defaults"].get("tags", [])
    tags = [t.strip() for t in tags if t.strip()]
    tags = list(dict.fromkeys(tags))[:12]  # 去重且最多12个
    kwargs["tags"] = tags

    cmd = build_upload_cmd(video_path, cfg, **kwargs)
    result = run_cmd(cmd, check=False)

    if result.returncode == 0:
        print("\n✅ 上传成功！")
    else:
        print("\n❌ 上传失败")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Bilibili 视频自动上传工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # login
    login_parser = subparsers.add_parser("login", help="登录 B 站")
    login_parser.add_argument("--cookie", default=DEFAULT_CONFIG["cookie_path"], help="cookie 保存路径")

    # upload
    upload_parser = subparsers.add_parser("upload", help="上传视频")
    upload_parser.add_argument("video", help="视频文件路径")
    upload_parser.add_argument("--config", help="配置文件路径")
    upload_parser.add_argument("--title", help="视频标题（默认使用文件名）")
    upload_parser.add_argument("--desc", help="视频简介")
    upload_parser.add_argument("--tags", help="标签，逗号分隔")
    upload_parser.add_argument("--tid", type=int, help="投稿分区 ID")
    upload_parser.add_argument("--copyright", type=int, choices=[1, 2], help="1=自制, 2=转载")
    upload_parser.add_argument("--source", help="转载来源")
    upload_parser.add_argument("--cover", help="封面图片路径")
    upload_parser.add_argument("--dynamic", help="空间动态文案")
    upload_parser.add_argument("--dtime", help="定时发布时间（格式: YYYY-MM-DD HH:MM 或 10位时间戳）")
    upload_parser.add_argument("--no-reprint", type=int, choices=[0, 1], default=1)

    args = parser.parse_args()

    if args.command == "login":
        login(args.cookie)
    elif args.command == "upload":
        overrides = {}
        if args.title:
            overrides["title"] = args.title
        if args.desc:
            overrides["desc"] = args.desc
        if args.tags:
            overrides["tags"] = [t.strip() for t in args.tags.split(",")]
        if args.tid is not None:
            overrides["tid"] = args.tid
        if args.copyright is not None:
            overrides["copyright"] = args.copyright
        if args.source:
            overrides["source"] = args.source
        if args.cover:
            overrides["cover"] = args.cover
        if args.dynamic:
            overrides["dynamic"] = args.dynamic
        if args.no_reprint is not None:
            overrides["no_reprint"] = args.no_reprint

        # 处理定时发布时间
        if args.dtime:
            try:
                # 尝试作为时间戳
                overrides["dtime"] = int(args.dtime)
            except ValueError:
                # 尝试解析日期格式
                dt = datetime.strptime(args.dtime, "%Y-%m-%d %H:%M")
                overrides["dtime"] = int(dt.timestamp())

        upload(args.video, args.config, **overrides)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
