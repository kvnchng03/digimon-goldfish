import { mkdir, readFile } from 'node:fs/promises';
import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';

// Run after editing public/icon.svg; commit the generated icons with that source.
const svg = await readFile(new URL('../public/icon.svg', import.meta.url), 'utf8');
const output = new URL('../public/icons/', import.meta.url);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: process.env.CI ? undefined : 'chrome' });
try {
  for (const [name, size] of [
    ['icon-192.png', 192], ['icon-512.png', 512],
    ['icon-maskable-512.png', 512], ['apple-touch-icon.png', 180],
  ] as const) {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await page.setContent(`<style>html,body{margin:0;width:100%;height:100%}svg{display:block;width:100%;height:100%}</style>${svg}`);
    await page.screenshot({ path: fileURLToPath(new URL(name, output)) });
    await page.close();
  }
} finally {
  await browser.close();
}
