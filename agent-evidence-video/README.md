# Agent Evidence Video

一个可复用的 LLM Agent 技能：用真实操作演示 Bug 修复、新功能和端到端流程，生成带章节大纲、字幕、旁白和鼠标指向的视频。

## 功能

- 将触发条件、操作、可见结果和断言组织成可复核的分镜。
- 使用真实界面录屏展示点击、输入和结果；区分预置数据、模拟结果与实际能力。
- 提供 Playwright 鼠标与输入可视化辅助脚本，以及带左侧大纲、字幕、解说和内嵌章节的 MP4 合成脚本。
- 支持 MiMo 文本转语音，也可使用其他工具生成的逐句音频。
- 检查音视频解码、字幕时间与章节；强调人工视听复核。

视频只能证明实际演示的场景，不能代替完整测试或验收。

## 安装

从 `redcreation/skills` 安装：

```bash
npx skills@latest add redcreation/skills --skill agent-evidence-video
```

也可以直接使用独立仓库：

```bash
git clone https://github.com/RedCreationTech/agent-evidence-video.git ~/.codex/skills/agent-evidence-video
```

在新会话中使用：

```text
使用 $agent-evidence-video，录制视频展示这次 Bug 修复的触发场景、修复结果和重新验证过程。
```

也可以要求展示新增功能或指定业务流程。技能说明入口为 [SKILL.md](SKILL.md)。

## 依赖与使用

录屏可以采用项目现有工具或 Playwright。可选的通用合成脚本依赖 Python 3、Pillow、支持中文字幕的字体，以及 ffmpeg/ffprobe；MiMo 脚本使用 Python 标准库。录屏与合成的实际步骤、输入清单和参数分别见 [录制指南](references/capture.md) 和 [合成指南](references/composition.md)。

使用 MiMo 时，通过安全方式设置 `MIMO_API_KEY` 环境变量。不要把密钥、登录态、真实客户数据或私有录屏提交到仓库。

## 目录

- [SKILL.md](SKILL.md)：技能入口与验证要求。
- [scripts/interaction.js](scripts/interaction.js)：Playwright 操作可视化辅助。
- [scripts/mimo_tts.py](scripts/mimo_tts.py)：使用环境变量认证的 MiMo 逐句语音生成。
- [scripts/compose.py](scripts/compose.py)：按章节和音频时间合成视频及字幕。
- [references/](references/)：录制与合成操作指南。
