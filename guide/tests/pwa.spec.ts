import { test as base, expect } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

// Chrome disables installation in incognito contexts. Use isolated, temporary
// normal profiles so installability checks exercise the actual browser criteria.
const test = base.extend({
  context: async ({ playwright }, use) => {
    const profile = await mkdtemp(join(tmpdir(), 'digimon-pwa-profile-'));
    const context = await playwright.chromium.launchPersistentContext(profile, {
      channel: process.env.CI ? undefined : 'chrome',
      baseURL: 'http://127.0.0.1:4173',
      colorScheme: 'light',
      viewport: { width: 1440, height: 1000 },
    });
    try {
      await use(context);
    } finally {
      await context.close();
      await rm(profile, { recursive: true, force: true });
    }
  },
});

for (const site of ['http://127.0.0.1:4173/', 'http://127.0.0.1:4174/pages-check/']) {
  test(`install metadata and offline reopening work at ${new URL(site).pathname}`, async ({ page, context, request }, testInfo) => {
    await page.goto(`${site}#fundamentals`);
    await expect(page.locator('#offline-status')).toContainText('Ready for offline use');
    await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller?.state)).toBe('activated');
    await expect(page.locator('#update-notice')).toBeHidden();
    const scope = await page.evaluate(async () => (await navigator.serviceWorker.ready).scope);
    expect(scope).toBe(site);

    const manifestURL = await page.locator('link[rel="manifest"]').evaluate((link: HTMLLinkElement) => link.href);
    expect(manifestURL).toBe(`${site}manifest.webmanifest`);
    const manifest = await (await request.get(manifestURL)).json();
    expect(manifest).toMatchObject({ display: 'standalone', scope: './', id: './' });
    expect(new URL(manifest.start_url, manifestURL).href).toBe(`${site}#fundamentals`);
    expect(manifest.icons).toEqual(expect.arrayContaining([
      expect.objectContaining({ sizes: '192x192', purpose: 'any' }),
      expect.objectContaining({ sizes: '512x512', purpose: 'any' }),
      expect.objectContaining({ sizes: '512x512', purpose: 'maskable' }),
    ]));
    for (const icon of manifest.icons) {
      const response = await request.get(new URL(icon.src, manifestURL).href);
      expect(response.ok()).toBe(true);
      const png = await response.body();
      expect(`${png.readUInt32BE(16)}x${png.readUInt32BE(20)}`).toBe(icon.sizes);
    }
    const cdp = await context.newCDPSession(page);
    const { installabilityErrors } = await cdp.send('Page.getInstallabilityErrors');
    expect(installabilityErrors).toEqual([]);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('.install-help summary').click();
    await page.locator('#install-panel').scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath('phone-install.png') });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);

    // A fresh tab must get the document and every card from the installed worker,
    // including a card whose dialog wasn't opened before the network went away.
    await context.setOffline(true);
    await page.close();
    const offlinePage = await context.newPage();
    const navigation = await offlinePage.goto(`${site}#improve-finish`);
    expect(navigation?.fromServiceWorker()).toBe(true);
    await expect(offlinePage.locator('#improve-finish .lesson-body')).toBeVisible();
    await offlinePage.getByRole('link', { name: 'Practice', exact: true }).click();
    await offlinePage.locator('.quiz-option').nth(1).click();
    await expect(offlinePage.locator('#quiz-score')).toHaveText('1 / 1');
    await offlinePage.getByRole('link', { name: 'Matchups', exact: true }).click();
    await offlinePage.locator('[data-opponent="jupiter"] .digimon-card').click();
    await expect(offlinePage.getByRole('dialog')).toBeVisible();
    await expect.poll(() => offlinePage.locator('img').evaluateAll(images =>
      images.every(img => img instanceof HTMLImageElement && img.complete && img.naturalWidth > 0))).toBe(true);
    const reloaded = await offlinePage.reload();
    expect(reloaded?.fromServiceWorker()).toBe(true);
    await expect(offlinePage.locator('#matchups')).toBeVisible();
  });
}

test('a waiting update preserves practice until the reader chooses to reload', async ({ page }) => {
  await page.goto('/#puzzles');
  await expect(page.locator('#offline-status')).toContainText('Ready for offline use');
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);
  await page.locator('.quiz-option').nth(1).click();
  await expect(page.locator('#quiz-score')).toHaveText('1 / 1');
  // A changed worker URL triggers the real browser update lifecycle without
  // modifying generated build files or replacing service-worker APIs with mocks.
  await page.evaluate(() => navigator.serviceWorker.register(new URL('sw.js?release-test=2', document.baseURI), {
    scope: new URL('./', document.baseURI).pathname,
    updateViaCache: 'none',
  }).then(() => undefined));
  await expect(page.locator('#update-notice')).toBeVisible();
  await expect(page.locator('#quiz-score')).toHaveText('1 / 1');
  await Promise.all([
    page.waitForEvent('load'),
    page.getByRole('button', { name: 'Reload to update' }).click(),
  ]);
  await expect(page.locator('#quiz-score')).toHaveText('0 / 0');
  await expect(page.locator('#offline-status')).toContainText('Ready for offline use');
});
