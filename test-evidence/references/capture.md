# 采集测试证据

## 原则

- 每个用例或章节使用独立浏览器上下文，录屏文件单独保存，避免一个长视频里无法定位失败。
- 先做无录像试跑，确认账号、数据、入口和断言；正式录制时冻结被测版本。
- 断言必须来自页面可见结果、持久化后的重新读取或可核对的审计记录；不要用固定等待时间推断成功。
- 原始视频、截图和 `test-run.json` 保留；成片不覆盖原始素材。
- 只使用授权测试账号与合成数据；敏感输入默认隐藏。

## Playwright 辅助

```js
const { chromium, expect } = require('@playwright/test');
const visual = require('./scripts/interaction');
const { TestEvidence } = require('./scripts/evidence');

const browser = await chromium.launch({ headless: true, slowMo: 80 });
const context = await browser.newContext({
  viewport: { width: 1560, height: 1080 },
  recordVideo: { dir: 'evidence/raw', size: { width: 1560, height: 1080 } },
});
const page = await context.newPage();
const ev = new TestEvidence({
  output: 'evidence/test-run.json',
  meta: { caseSet: 'CASE', env: 'test', version: '2026-11-13', operator: 'qa' },
});
await ev.attach(page);
await visual.install(page, { showInput: true });

await ev.step('CASE-1.1', '登录并进入借阅台账', async () => {
  await page.goto('https://app.example.test/');
  await visual.type(page.locator('#account'), process.env.TEST_USER);
  await visual.type(page.locator('#pwd'), process.env.TEST_PASS); // 默认隐藏
  await visual.click(page.locator('#sign-in'));
  await expect(page.getByText('借阅台账')).toBeVisible();
});

await ev.assert('CASE-1.1-a1', '空表单提交显示必填提示', async () => {
  await page.getByRole('button', { name: '发起' }).click();
  await expect(page.getByText('请填写申请理由')).toBeVisible();
}, { caseId: 'CASE-1.1', expected: '显示必填提示' });

await ev.screenshot('empty-submit');
await ev.finish({ verdict: 'pass' });

await context.close();  // 关闭后 Playwright 才写完视频
await browser.close();
```

`TestEvidence` 的方法：

| 方法 | 作用 |
|---|---|
| `attach(page)` | 绑定页面，记录 console error、pageerror、requestfailed |
| `step(id, name, fn)` | 记录操作步骤与耗时；动作异常会记录并抛出 |
| `assert(id, name, fn, opts)` | 捕获断言结果；失败自动截图并记录，默认不中断 |
| `screenshot(label)` | 保存截图到 JSON 同目录的 `shots/` |
| `mark(label)` | 记录相对开始的毫秒时间点 |
| `finish(extra)` | 写出 JSON，包含 summary 与视频时间基准 |

`interaction` 的方法（第一个参数都是 Locator）：

| 方法 | 作用 |
|---|---|
| `install(page, { showInput, accent })` | 注入光标、涟漪、输入提示和强调框 |
| `click(locator, opts)` | 移动鼠标到元素中心、显示涟漪后点击 |
| `type(locator, value, opts)` | 逐字输入；date/number/文件等控件使用 `fill`/`setInputFiles` |
| `highlight(locator, text, ms)` | 临时框出元素并显示说明 |
| `moveTo(locator)` | 只移动指针，不点击 |

失败时可通过 `opts.defect` 绑定缺陷号；`opts.fatal: true` 让断言失败立即抛出。

## 证据 JSON

```json
{
  "schema": "test-evidence/1",
  "startedAt": "2026-11-13T20:00:00.000Z",
  "durationMs": 184230,
  "meta": {"caseSet": "CASE", "env": "test", "version": "2026-11-13"},
  "steps": [{"id": "CASE-1.1", "name": "登录并进入借阅台账", "startMs": 0, "endMs": 8200, "status": "done"}],
  "assertions": [{"id": "CASE-1.1-a1", "caseId": "CASE-1.1", "name": "空表单提交显示必填提示", "verdict": "pass", "expected": "显示必填提示", "startMs": 9000, "endMs": 10400, "screenshot": null}],
  "summary": {"pass": 12, "fail": 1, "total": 13},
  "console": [{"type": "error", "text": "..."}],
  "failedRequests": [{"url": "...", "method": "GET", "failure": "net::ERR_ABORTED"}],
  "marks": [{"label": "delete-click", "ms": 50320}]
}
```

`startMs` 是相对 `TestEvidence` 创建时刻的毫秒数；浏览器视频通常在上下文创建时开始，二者可能有数百毫秒偏差。需要精确对齐时，在页面角落显示一个累加计时器，或录屏后用画面中的动作帧人工校准。不要把估算时间当成精确断言。

## 缺陷复现录制

- 从登录/入口开始，保持最短路径；不要剪掉失败发生前的动作。
- 画面必须包含：触发动作、实际结果、预期结果（可用顶部标注带）、可核对的日志/审计记录。
- 失败后不要立即关闭页面；停留展示错误提示、列表状态或审计详情。
- 记录稳定复现次数；偶发问题写明出现条件，不要声称“必现”。
- 截图至少包含：失败前状态、触发后状态、审计/日志证据。

## 多角色流程

部门审核、批准、QA 等角色使用独立上下文或独立账号；每个角色的关键动作单独截图和时间点。电子签名、权限校验和退回分支要保留弹窗与审计活动名称。切换账号时不要把密码或会话信息留在画面中。

## 数据与素材

原始录屏放在私有目录，命名包含用例 ID 与时间；`test-run.json` 中的 `video` 字段记录文件路径和时长。提交到仓库前检查是否包含凭据、客户名称、真实业务数据或浏览器存储内容。