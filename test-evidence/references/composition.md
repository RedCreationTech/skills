# 解说、字幕与成片

## 清单格式

`manifest.json` 描述章节、判定、原始录屏和逐句解说。路径相对 manifest 或使用绝对路径。

```json
{
  "title": "文件借阅 · 测试证据",
  "subtitle": "实例 demo-001 · 2026-11-13 · 测试环境",
  "scenes": [
    {
      "id": "CASE-01",
      "title": "发起借阅申请",
      "verdict": "pass",
      "capture": "raw/01.webm",
      "lines": [
        {"text": "登录后进入借阅台账，再打开借阅申请。", "audio": "audio/01-01.wav", "start": 1.2},
        {"text": "空表单直接提交，页面提示必填。", "audio": "audio/01-02.wav", "start": 9.0}
      ]
    },
    {
      "id": "CASE-04",
      "title": "删除文件未触发签名",
      "verdict": "fail",
      "defect": "BUG-01",
      "capture": "raw/04.webm",
      "lines": [
        {"text": "勾选文件后点击删除，文件立即消失并提示成功。", "audio": "audio/04-01.wav", "start": 2.0},
        {"text": "全程没有出现电子签名弹窗，实际结果与预期不符。", "audio": "audio/04-02.wav", "start": 8.0}
      ]
    }
  ]
}
```

规则：

- `verdict` 只能是 `pass`、`fail`、`blocked`、`unexecuted`。
- `fail` 必须有 `defect`；`blocked`/`unexecuted` 必须有 `reason`。
- `start` 是该句在**本章原始录屏**中的秒数，必须按时间递增且互不重叠。
- 音频必须在章节结束前完整播放；脚本不会自动加速、截断或丢弃旁白。
- 章节标题保持单行或两行；过长时缩短标题或拆分章节。

## 旁白写法

- 一句只讲一个可核对的事实：当前角色、动作、可见结果。
- 失败章节直接说“预期是什么、实际是什么、因此判定失败”，不要用模糊措辞。
- 不声称视频里没出现的结论；不把预置数据说成实时数据。
- 语速适中，单句建议不超过 40 个汉字；字幕最多 3 行。

## 生成配音

MiMo 使用环境变量认证，不把 Key 写入命令、文件或日志：

```bash
export MIMO_API_KEY="..."   # 由用户在自己的安全环境中设置
python3 scripts/mimo_tts.py --text-file narration/01-01.txt \
  --output audio/01-01.wav --voice 冰糖
```

脚本只支持 `MIMO_API_KEY`；HTTP 失败只报告状态码，不打印响应正文。真实调用消耗第三方额度，按用户授权范围使用。用户指定其他 TTS 时，提供逐句音频即可。

## 合成

```bash
python3 scripts/compose.py evidence/manifest.json \
  --output-dir out --font "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
```

产物：

- `test-evidence.mp4`：1920×1080、25fps、H.264/AAC；左侧 380px 判定侧栏，右侧原始画面，底部字幕。
- `subtitles.srt`：按实际音频起点和时长生成。
- `chapters.ffmeta`：章节元数据。
- `scene-XX.mp4`：每章中间产物，便于定位问题。
- `evidence-summary.json`：判定计数和章节时间，供报告核对。

左侧侧栏显示章节序号、用例 ID、标题和 `通过/失败/阻塞/未执行`；当前章节高亮。失败章节用红色标记，但**不能遮挡**右侧录屏内容。

## 合成后检查

1. `ffprobe` 确认分辨率、时长、视频/音频轨和章节数。
2. 完整解码一遍，不能有错误或重复时间戳。
3. 对照 SRT 检查首句、失败句和末句是否在画面内，是否与语音同步。
4. 抽查每章开头、关键操作、失败结果和结尾；检查侧栏判定是否与证据 JSON 一致。
5. 听取开头、至少一个关键操作和结尾；确认没有截句、爆音或长时间无声。
6. 确认原始录屏未被覆盖，成片输出目录为新目录。