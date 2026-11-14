---
name: test-evidence
description: >
  Turn real test execution into auditable evidence: chaptered test-run videos
  with verdicts, subtitles and narration; annotated bug-reproduction videos;
  a traceable bug list; and a filled test report. Use when the user asks to
  test a system end to end, record a test run, reproduce or annotate a defect,
  assemble acceptance evidence, or write/fill a test report. Do not use for
  promotional videos or for claiming results that were not actually observed.
---

# 测试取证

把一次真实测试转成可复核的证据链：**用例 → 步骤 → 断言 → 证据时间点 → 缺陷 → 报告结论**。视频只是证据的一种，不能替代完整测试或验收。

## 1. 先确定能证明什么

开始录制前必须拿到并核对：

- 被测地址、版本/构建号、测试时间、环境类型（演示/测试/生产镜像）。
- 账号、角色、权限和数据前置条件；只使用授权的测试账号与合成数据。
- 用例文档（用例 ID、步骤、预期）与报告模板。
- 本轮范围：哪些用例执行、哪些因数据/时间/入口不可用而不执行。

将用例整理成可执行矩阵：`用例ID | 模块 | 角色 | 前置条件 | 步骤 | 预期 | 数据 | 可执行性`。无法执行的用例先标记，不要等到写报告时才补“未执行”。

## 2. 证据规则（不可违反）

1. **断言驱动**：只有实际观察到预期结果才能记 PASS。不能从代码、接口返回、日志或“应该会”推断通过。
2. **未执行不等于通过**：必须区分 `PASS / FAIL / BLOCKED / UNEXECUTED`。阻塞和未执行要写原因，报告中的数量必须与之对得上。
3. **保留原始素材**：原始录屏、截图、控制台/网络错误和证据 JSON 不覆盖、不删改；成片是派生物。
4. **不剪掉失败**：失败画面必须保留并标注；禁止通过剪接、改 DOM、伪造响应或事后补录把 FAIL 说成 PASS。
5. **一缺陷一证据**：每个缺陷至少包含触发步骤、实际结果、预期结果、稳定复现方法和视频时间点；观察项与缺陷分开统计。
6. **保密**：密码、令牌、Key、客户隐私和真实生产数据不得出现在画面、日志、字幕或提交物中。输入提示对敏感字段默认隐藏。
7. **报告自洽**：总数 = 通过 + 失败 + 阻塞 + 未执行；缺陷数与 BUG 清单一致；结论与最高级别缺陷一致。

## 3. 交付物

| 交付物 | 内容 |
|---|---|
| 完整测试记录视频 | 按用例/章节推进，含章节大纲、判定、字幕、解说 |
| 缺陷复现视频 | 最短复现路径，红框+编号标注出错位置，展示预期与实际 |
| BUG 清单 | 编号、级别、模块、用例映射、复现步骤、证据时间点、修复建议 |
| 项目测试报告 | 按模板填写范围、环境、执行、覆盖、缺陷、结论、变更记录 |
| 证据索引 | `test-run.json`、截图、原始录屏、SRT、章节时间 |
| 验证结果 | 解码、音轨、字幕边界、报告数字一致性检查 |

## 4. 工作流

### 4.1 无录像试跑

先不录屏跑通账号、数据、关键入口和断言，确认每个预期都能被观察到。冻结被测版本，记录未提交改动；不要边改代码边录制。

### 4.2 采集测试证据

使用项目已有的 E2E 工具；没有时可用 Playwright + `scripts/evidence.js`。按用例/章节独立录制，保留原始视频；每步记录时间点、断言结果、截图、控制台错误和失败请求。固定 `sleep` 不能代替断言。

详细约定见 [references/capture.md](references/capture.md)。

### 4.3 判定与缺陷

逐条对照预期与实际给出 `PASS/FAIL/BLOCKED/UNEXECUTED`。FAIL 必须创建缺陷并回填用例 ID；BLOCKED/UNEXECUTED 必须写原因。级别建议：阻塞、严重、一般、轻微；观察项不计入缺陷数。

### 4.4 缺陷复现视频

只录制最短复现路径；画面必须同时出现触发动作、实际结果和可核对的审计/日志证据。用红框和编号标出出错位置，顶部写预期与实际。标注脚本见 `scripts/annotate.py`，规范见 [references/bug-video.md](references/bug-video.md)。

### 4.5 解说完片

为每章写可核验的短句，逐句 TTS，按实际语音时长给画面留时间；不加速、不截断。合成时左侧常驻用例/章节与判定，右侧真实录屏，底部字幕。清单格式与命令见 [references/composition.md](references/composition.md)。

### 4.6 填写测试报告

先读模板结构和样式，再按矩阵和 BUG 清单填表；不要凭印象改数字。填写规则与一致性检查见 [references/reporting.md](references/reporting.md)。DOCX 操作优先使用 `office-docx` 技能。

### 4.7 交付前验证

```bash
python3 scripts/verify.py --manifest evidence/manifest.json \
  --video out/test-evidence.mp4 --srt out/subtitles.srt \
  --evidence evidence/test-run.json
```

再人工抽查每章开头、关键操作和结尾，听开头/关键操作/结尾；检查字幕遮挡、红框位置、长文本、鼠标可见性和敏感信息。脚本检查不能代替视听复核。

## 5. 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/interaction.js` | Playwright 鼠标、点击涟漪、输入提示覆盖层 |
| `scripts/evidence.js` | 记录步骤、断言、截图、时间点、控制台/网络错误，输出 `test-run.json` |
| `scripts/annotate.py` | 给缺陷视频加顶部说明带、红框、编号标注 |
| `scripts/compose.py` | 合成章节视频、判定侧栏、字幕、解说、SRT、章节元数据 |
| `scripts/mimo_tts.py` | MiMo 逐句配音；Key 只从 `MIMO_API_KEY` 读取 |
| `scripts/verify.py` | 校验视频/音轨/字幕/清单/证据 JSON 的一致性 |

示例清单在 `templates/`。依赖：Python 3、Pillow、支持中文的字体、ffmpeg/ffprobe；MiMo 脚本只用标准库。

## 6. 边界

- 视频证明的是“录到的这一次”，不证明没录到的分支、性能、安全或全部数据状态。
- 演示环境、预置数据、模拟接口和未实现能力必须在交付说明中写清。
- 录屏失败或断言失败时先修复并重录，不能靠剪辑掩盖。
- 外部写操作（发消息、改生产数据、审批真实单据）只在明确授权范围内执行。