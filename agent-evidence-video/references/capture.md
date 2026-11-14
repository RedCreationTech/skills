# 真实桌面操作录制

使用独立测试数据与最低必要权限，按项目规范准备服务、构建和账号。记录代码版本及未提交改动。按章节在独立浏览器上下文中录制实际界面，保留原始视频；常用设置为右侧 1560×1080、最终画布 1920×1080、左侧大纲 360 像素。执行关键点击、输入、提交、成功反馈、重开和状态断言，并为观察结果留出时间；固定延迟不能代替断言。

Playwright 示例，定位器、地址和断言须依项目调整：

```js
const { chromium, expect } = require('@playwright/test');
const visual = require('/path/to/agent-evidence-video/scripts/interaction.js');
const browser = await chromium.launch({ headless: true, slowMo: 120 });
const context = await browser.newContext({
  viewport: { width: 1560, height: 1080 },
  recordVideo: { dir: './private-recordings', size: { width: 1560, height: 1080 } },
});
const page = await context.newPage();
await visual.install(page, { showInput: true });
await page.goto('http://127.0.0.1:3000/'); // 使用自己的隔离服务
await visual.type(page.getByLabel('名称'), '演示数据');
await page.getByRole('button', { name: '保存' }).click();
await expect(page.getByText('保存成功')).toBeVisible();
// 继续关闭、重新打开、断言持久化；可为关键结果记录时间。
await context.close(); // 关闭后 Playwright 才完成视频文件
await browser.close();
```

`visual.type` 对普通文本逐字输入并核对最终值；对 number、date、time、datetime-local、password 使用常规 fill，对 file 使用 setInputFiles。日期等控件未必能逐字输入，应清楚展示值与结果。鼠标动画由实际鼠标事件触发，不能冒充点击。默认不显示 password、标记 `data-evidence-private` 和常见敏感字段的输入内容；这种启发式不能代替合成数据与人工审看。不要分享含敏感内容的原始录屏。

每章保留原视频、测试报告、关键断言及时间标记和对应版本。确有模拟响应时明确说明；业务或测试失败须修复后重录，不能剪掉失败画面宣称通过。可单独重录章节，并在说明中记录替换来源。
