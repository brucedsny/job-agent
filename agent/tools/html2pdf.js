#!/usr/bin/env node
// Render a local HTML file to a Letter-size PDF with headless Chromium.
// Usage: node agent/tools/html2pdf.js IN.html OUT.pdf [scale]   (e.g. 0.95)
// Browser: $CHROMIUM_PATH, else $PLAYWRIGHT_BROWSERS_PATH/chromium when it
// exists, else Playwright's own download.
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

function chromiumPath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const launcher = path.join(process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers', 'chromium');
  return fs.existsSync(launcher) ? launcher : undefined;
}

(async () => {
  const [, , inp, out, scale] = process.argv;
  if (!inp || !out) {
    console.error('usage: node html2pdf.js IN.html OUT.pdf [scale]');
    process.exit(2);
  }
  const browser = await chromium.launch({ executablePath: chromiumPath() });
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(path.resolve(inp)).href, { waitUntil: 'load' });
    await page.pdf({
      path: out,
      format: 'Letter',
      printBackground: true,
      scale: scale ? parseFloat(scale) : 1,
      margin: { top: '0.5in', bottom: '0.5in', left: '0.5in', right: '0.5in' },
    });
  } finally {
    await browser.close();
  }
  console.log(out);
})().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
