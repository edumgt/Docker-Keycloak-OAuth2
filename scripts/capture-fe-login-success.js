const { chromium } = require("playwright");

const APP_URL = "http://backend:8000/app-ui";
const OUTPUT_PATH = "/work/captures/fe-login-success.png";
const USERNAME = process.env.FE_LOGIN_USER || "demo-user";
const PASSWORD = process.env.FE_LOGIN_PASS || "demo1234";

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto(APP_URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.fill("#username", USERNAME);
  await page.fill("#password", PASSWORD);
  await page.click("#login-btn");

  await page.waitForSelector("#status-badge:not(.hidden)", { timeout: 15000 });
  const statusText = await page.locator("#status-badge").innerText();
  if (!statusText.includes("로그인 성공")) {
    throw new Error(`Unexpected status text: ${statusText}`);
  }

  await page.waitForTimeout(1200);
  await page.screenshot({ path: OUTPUT_PATH, fullPage: true });
  await browser.close();
  console.log(`Saved ${OUTPUT_PATH}`);
})();

