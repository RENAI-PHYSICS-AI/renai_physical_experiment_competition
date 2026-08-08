const { chromium } = require('C:/Users/junmo/AppData/Local/OpenAI/Codex/runtimes/cua_node/f1bf3cd3a5929acd/bin/node_modules/playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    args: ['--disable-gpu'],
  });
  const context = await browser.newContext({
    viewport: { width: 1362, height: 1001 },
    deviceScaleFactor: 1.25,
    colorScheme: 'dark',
  });
  const page = await context.newPage();
  page.on('console', (msg) => {
    if (msg.type() === 'error') console.error(`browser-console: ${msg.text()}`);
  });
  page.on('pageerror', (err) => console.error(`page-error: ${err.message}`));

  await page.goto('http://127.0.0.1:8601', {
    waitUntil: 'domcontentloaded',
    timeout: 120000,
  });
  await page.getByText('声速测量实验智能助教', { exact: true }).waitFor({
    state: 'visible',
    timeout: 120000,
  });
  await page.getByRole('tab', { name: '智能问答', exact: true }).click();
  await page.getByPlaceholder('询问声速理论、文献或实验问题').waitFor({
    state: 'visible',
    timeout: 30000,
  });
  await page.locator('img[alt="音叉振动与纵向声波传播示意图"]').evaluate((img) => {
    if (!img.complete || img.naturalWidth === 0) {
      return new Promise((resolve, reject) => {
        img.addEventListener('load', resolve, { once: true });
        img.addEventListener('error', reject, { once: true });
      });
    }
  });
  await page.waitForTimeout(1200);
  await page.screenshot({
    path: 'D:\\OneDrive\\文档\\我的文件\\git\\仁爱物理竞赛\\tmp\\sound_web_recolor\\sound_qa_interface_new.png',
    fullPage: false,
  });
  console.log(JSON.stringify({
    title: await page.title(),
    url: page.url(),
    heroImageWidth: await page.locator('img[alt="音叉振动与纵向声波传播示意图"]').evaluate((img) => img.naturalWidth),
  }));
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
