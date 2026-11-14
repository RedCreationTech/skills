# 解说、字幕和合成

辅助工具依赖 Python 3、Pillow (`python3 -m pip install Pillow`)、ffmpeg/ffprobe，以及支持中文字幕的字体；执行前先检查项目已有的视频工具。无这些依赖时遵循环境安装策略，或用已有工具完成相同结果。`compose.py` 不需要 libass，可在没有 subtitles 滤镜的 ffmpeg 中工作。默认输出 1920×1080、25 fps、H.264/AAC，左侧 360 像素大纲、右侧保留原比例画面。输出画面中的字幕由实际每句音频时长控制，生成可单独使用的 SRT 和内嵌章节。辅助合成默认丢弃原录屏音轨；若需要系统声音或多人对话，使用项目已有的混音方式。

## 准备语音

每一句单独保存音频文件，录制前测量语音长度、为动作和阅读留时间。可以重复使用来源可核实的 MiMo 音频缓存。用户指定 MiMo、密钥已通过安全环境变量提供时：

```bash
python3 /path/to/agent-evidence-video/scripts/mimo_tts.py --text-file line-01.txt --output private/audio/line-01.wav
```

仅支持 `MIMO_API_KEY` 环境变量，禁将密钥写入代码、命令参数、共享文件、日志或截图。真实调用会消耗第三方额度；用户提出 MiMo 配音时可按已授权范围调用。MiMo HTTP 错误仅报告状态，不打印响应；不自动替换服务。可用 `--voice`、`--model` 适配用户要求；模型、API 服务行为可能变化，失败时检查服务官方文档，不声称错误已解决。用户要求其它语音服务时使用其授权的方式，输出可供 ffmpeg 解码的每句音频即可。

## 编写时间清单

`manifest.json` 里 `capture` 和 `audio` 支持相对 manifest 或绝对路径；`start` 是该句在该章节**录屏本身**的秒数。录屏后依据实际画面定位每句开头，再用 `ffprobe` 检查音频时长。所有句子必须按开始时间排列、互不重叠，且音频必须在片段结束前完整播放。需要延长展示时间时重新录制或有意识地延长无动作的停留画面，不可裁剪或自动加速语音。精确动作位置通过视频帧和声音人工复核，而不是仅用预估分配时长。

```json
{
  "title": "产品修改演示",
  "scenes": [
    {
      "title": "问题与修复",
      "capture": "private/01.webm",
      "lines": [
        {"text": "在此重现触发场景。", "audio": "private/line-01.wav", "start": 2.0},
        {"text": "保存后重新打开，结果保持正确。", "audio": "private/line-02.wav", "start": 9.0}
      ]
    }
  ]
}
```

不要把密码、令牌、私有音频或录屏放进共享的仓库。明确输出目录，必须不存在或为空，避免覆盖成片：

```bash
python3 /path/to/agent-evidence-video/scripts/compose.py manifest.json --output-dir ./new-video --font /path/to/CJK-font.ttc
```

产物 `evidence-video.mp4`、`subtitles.srt`、`chapters.ffmeta`，另保留每章合成素材。脚本检查时间边界、生成字幕并完整解码一次；它不能检测录屏真实性、字幕语义或所选字体缺字，也不能替代视听复核。中途失败会保留临时产物供排查；另选空目录重试。章节标题需能放在大纲单行内；太多章节或单句字幕过长时请精简标题、拆句，切勿丢失内容。
