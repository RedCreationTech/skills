# bilibili-uploader-skill

Kimi Code CLI Skill —— Bilibili (B站) 视频自动上传工具集。

## 功能

- **一键上传**：分析视频 → 自动生成标题/简介/标签/分区 → 调用 biliup-rs 投稿
- **智能元数据**：基于文件名和 ffprobe 提取的信息，自动推测合适的标签和分区
- **定时发布**：支持预约投稿时间
- **批量处理**：可脚本化批量上传

## 快速开始

### 安装

```bash
# 1. 安装 biliup-rs (Rust 命令行投稿工具)
# macOS x86_64
curl -L -o biliup.tar.xz "https://github.com/biliup/biliup-rs/releases/latest/download/biliupR-v0.2.4-x86_64-macos.tar.xz"
tar -xf biliup.tar.xz
mv biliup*/biliup /usr/local/bin/

# 2. 安装 skill 到 Kimi
make install
# 或手动复制到 ~/.config/agents/skills/
```

### 登录 B 站

```bash
biliup -u ./cookies.json login
```

扫码登录一次即可，cookie 长期有效。

### 上传视频

```bash
# 全自动（推荐）
python scripts/auto_upload.py ~/Videos/my_video.mp4 --extra-tags "精华" -y

# 手动指定元数据
python scripts/auto_upload.py ~/Videos/my_video.mp4 \
  --title "【电影解说】千与千寻" \
  --extra-tags "宫崎骏,吉卜力" \
  --tid 228 \
  --dtime "2025-04-20 18:00" \
  -y
```

## 文件结构

```
.
├── SKILL.md                      # Skill 主文件（Kimi 读取）
├── README.md                     # 本文件
├── scripts/
│   ├── auto_upload.py            # 一键上传入口
│   ├── auto_generate_meta.py     # 自动生成投稿元数据
│   └── bilibili_uploader.py      # biliup-rs 的 Python 封装
└── Makefile
```

## 维护

### 更新 skill

修改 `scripts/` 或 `SKILL.md` 后，重新打包：

```bash
make package
```

### 发布到 Kimi

```bash
make install
```

## 依赖

- [biliup-rs](https://github.com/biliup/biliup-rs) ≥ v0.2.4
- Python ≥ 3.9
- ffmpeg / ffprobe（可选，用于自动提取视频信息）

## License

MIT
