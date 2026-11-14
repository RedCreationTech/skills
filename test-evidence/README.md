# test-evidence

把一次真实测试转成可复核的证据链：**用例 → 步骤 → 断言 → 证据时间点 → 缺陷 → 报告结论**。

适用于端到端测试、验收取证、缺陷复现和测试报告填写；不适用于宣传片或未实际执行的能力展示。

## 交付物

| 交付物 | 内容 |
|---|---|
| 完整测试记录视频 | 按用例/章节推进，左侧判定侧栏、右侧真实录屏、底部字幕、逐句解说 |
| 缺陷复现视频 | 最短复现路径，顶部预期/实际，红框和编号标注出错位置 |
| BUG 清单 | 编号、级别、模块、用例映射、复现步骤、证据时间点、修复建议 |
| 项目测试报告 | 按模板填写范围、环境、执行、覆盖、缺陷、结论、变更记录 |
| 证据索引 | `test-run.json`、截图、原始录屏、SRT、章节时间、判定汇总 |

## 核心规则

1. **断言驱动**：只有实际观察到预期结果才记 PASS。
2. **未执行不等于通过**：区分 `PASS / FAIL / BLOCKED / UNEXECUTED`，报告数字必须对得上。
3. **保留原始素材**：原始录屏、截图、控制台错误和证据 JSON 不覆盖、不删改。
4. **不剪掉失败**：禁止通过剪接、改 DOM 或伪造响应把 FAIL 说成 PASS。
5. **一缺陷一证据**：触发步骤、实际结果、预期结果、稳定复现和视频时间点齐全。
6. **保密**：密码、令牌、Key、客户隐私和真实生产数据不进入画面、日志和提交物。
7. **报告自洽**：总数 = 通过 + 失败 + 阻塞 + 未执行；缺陷数与 BUG 清单一致。

## 依赖

- Python 3 + Pillow（`python3 -m pip install Pillow`）
- ffmpeg / ffprobe
- 支持中文的字体（macOS 可用 `Arial Unicode.ttf` 或 `PingFang.ttc`）
- Playwright 仅在需要辅助录屏和证据采集时使用
- MiMo 配音只用 Python 标准库；Key 只从 `MIMO_API_KEY` 读取

## 快速开始

```bash
# 1. 采集证据（Playwright，可选）
node record.js            # 使用 scripts/evidence.js + scripts/interaction.js

# 2. 逐句生成配音（可选）
export MIMO_API_KEY="..."   # 在用户自己的安全环境中设置
python3 scripts/mimo_tts.py --text-file narration/01-01.txt \
  --output audio/01-01.wav --voice 冰糖

# 3. 合成带判定侧栏、字幕和章节的成片
python3 scripts/compose.py evidence/manifest.json \
  --output-dir out \
  --font "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

# 4. 校验视频、音轨、章节、字幕和证据一致性
python3 scripts/verify.py --manifest evidence/manifest.json \
  --video out/test-evidence.mp4 --srt out/subtitles.srt \
  --evidence evidence/test-run.json
```

示例清单和文档模板见 [`templates/`](templates/)：

- `manifest.json`：章节、判定、缺陷、录屏和逐句解说
- `test-run.json`：`test-evidence/1` 证据格式
- `bug-list.md`：BUG/观察项清单
- `report-checklist.md`：报告数字与证据交付检查

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/interaction.js` | Playwright 鼠标、点击涟漪、输入提示覆盖层；敏感字段默认隐藏 |
| `scripts/evidence.js` | 记录步骤、断言、截图、时间点、控制台/网络错误，输出 `test-run.json` |
| `scripts/annotate.py` | 缺陷视频顶部说明带、红框、编号文字标注 |
| `scripts/compose.py` | 合成判定侧栏、录屏、字幕、解说、SRT、章节和判定汇总 |
| `scripts/mimo_tts.py` | MiMo 逐句配音；仅从环境变量认证 |
| `scripts/verify.py` | 校验分辨率、编码、章节、完整解码、字幕边界、清单与证据一致性 |

## 详细说明

- [SKILL.md](SKILL.md)：完整工作流与边界
- [references/capture.md](references/capture.md)：录制、证据 JSON、多角色与数据安全
- [references/bug-video.md](references/bug-video.md)：缺陷判定、复现视频最小内容、标注规范
- [references/composition.md](references/composition.md)：清单格式、旁白写法、合成与检查
- [references/reporting.md](references/reporting.md)：报告结构、覆盖表一致性和结论措辞

## 边界

视频证明的是“录到的这一次”，不证明没录到的分支、性能、安全或全部数据状态。演示环境、预置数据、模拟接口和未实现能力必须在交付说明中写清；脚本检查不能代替人工视听复核。