import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import puzzles from '../src/puzzles.json' with { type: 'json' };

test('turn checklist and matchup filters remain usable; print includes every matchup', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('#learn')).toBeVisible();
  const checks = page.locator('.check-row input');
  for (const checkbox of await checks.all()) await checkbox.check();
  await expect(page.locator('#check-count')).toHaveText('6 of 6 checked');
  await page.getByRole('button', { name: 'Reset turn' }).click();
  await expect(page.locator('#check-count')).toHaveText('0 of 6 checked');
  await page.getByRole('link', { name: 'Matchups', exact: true }).click();
  for (const matchup of ['jupiter', 'toho', 'merva', 'dats']) {
    await page.locator(`[data-match="${matchup}"]`).click();
    await expect(page.locator('.matchup:visible')).toHaveCount(1);
    await expect(page.locator(`[data-opponent="${matchup}"]`)).toBeVisible();
  }
  await page.emulateMedia({ media: 'print' });
  await expect(page.locator('.matchup:visible')).toHaveCount(4);
  await expect(page.locator('#puzzles')).toBeHidden();
  await page.emulateMedia({ media: 'screen' });
  await page.getByRole('button', { name: 'All four' }).click();
  await expect(page.locator('.matchup:visible')).toHaveCount(4);
  await page.getByRole('link', { name: 'Learn', exact: true }).click();
  await page.locator('a.source-link[href="#source-playbook"]').first().click();
  await expect(page.locator('#source-playbook')).toHaveAttribute('open', '');
  await page.getByRole('link', { name: 'Practice', exact: true }).click();
  await page.getByRole('button', { name: 'Copy command', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Copied to clipboard.');
  expect(errors).toEqual([]);
});

test('each puzzle scores only its first answer, reveals evidence, and can restart', async ({ page }) => {
  await page.goto('/#puzzles');
  await expect(page.locator('#puzzle-select option')).toHaveCount(puzzles.length);
  let correct = 0;
  for (const [index, puzzle] of puzzles.entries()) {
    await page.selectOption('#puzzle-select', String(index));
    await expect(page.locator('#quiz-question')).toHaveText(puzzle.question);
    const answerIndex = 'ABCD'.indexOf(puzzle.answer);
    const chooseCorrect = index % 2 === 0;
    const pick = chooseCorrect ? answerIndex : (answerIndex + 1) % puzzle.options.length;
    await page.locator('.quiz-option').nth(pick).click();
    if (chooseCorrect) correct++;
    await expect(page.locator('#quiz-score')).toHaveText(`${correct} / ${index + 1}`);
    await expect(page.locator('.quiz-option.correct')).toContainText(puzzle.options[answerIndex]!);
    await expect(page.locator('#quiz-feedback')).toContainText(puzzle.why);
    await expect(page.locator('#quiz-feedback')).toContainText(puzzle.evidence);
    await expect(page.locator('.quiz-option:enabled')).toHaveCount(0);
  }
  await page.locator('#quiz-prev').click();
  await expect(page.locator('#quiz-score')).toHaveText(`${correct} / ${puzzles.length}`);
  await page.locator('#quiz-next').click();
  await page.getByRole('button', { name: 'Practise again' }).click();
  await expect(page.locator('#quiz-score')).toHaveText('0 / 0');
  await expect(page.locator('#quiz-feedback')).toBeHidden();
  await expect(page.locator('#quiz-prev')).toBeDisabled();
});

for (const width of [320, 390, 768, 1440]) {
  for (const theme of ['light', 'dark'] as const) {
    test(`${width}px ${theme}: readable layout, no horizontal overflow`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: width < 500 ? 844 : 1000 });
      await page.emulateMedia({ colorScheme: theme });
      await page.goto('/');
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      await expect(page.locator('#learn')).toBeVisible();
      const overflow = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>('body *')]
        .filter(el => {
          if (el.classList.contains('skip') || !el.getClientRects().length) return false;
          const rect = el.getBoundingClientRect();
          return rect.right > innerWidth + 1 || rect.left < -1;
        }).map(el => `${el.tagName}.${el.className}`));
      expect(overflow).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath('top.png') });
      await page.getByRole('link', { name: 'Practice', exact: true }).click();
      await page.locator('.quiz-option').nth(0).click();
      await page.screenshot({ path: testInfo.outputPath('puzzle.png') });
      const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(pageWidth).toBeLessThanOrEqual(width);
      await page.getByRole('link', { name: 'Improve', exact: true }).click();
      await expect(page.locator('#fundamentals')).toBeVisible();
      await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
      await page.screenshot({ path: testInfo.outputPath('improve.png'), fullPage: true });
      await page.getByRole('link', { name: 'I run out of memory', exact: false }).click();
      await expect(page.locator('#improve-memory')).toHaveAttribute('open', '');
      await page.screenshot({ path: testInfo.outputPath('memory-lesson.png') });
      const lessonOverflow = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>('body *')]
        .filter(el => {
          if (el.classList.contains('skip') || !el.checkVisibility()) return false;
          const rect = el.getBoundingClientRect();
          return rect.right > innerWidth + 1 || rect.left < -1;
        }).map(el => `${el.tagName}.${el.className}`));
      expect(lessonOverflow).toEqual([]);
    });
  }
}

test('export runs offline from a local file, including persisted theme and quiz', async ({ page, context }) => {
  const errors: string[] = [];
  const requests: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (/^https?:/.test(request.url())) requests.push(request.url());
  });
  await context.setOffline(true);
  const file = fileURLToPath(new URL('../../.lavish/glowing-dawn-guide.html', import.meta.url));
  await page.goto(`file://${file}`);
  await expect(page.locator('#learn')).toBeVisible();
  await expect.poll(() => page.locator('.card-fan img').evaluateAll(images => images.every(img => img instanceof HTMLImageElement && img.complete && img.naturalWidth > 0))).toBe(true);
  await page.getByRole('button', { name: 'Switch to dark mode' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('link', { name: 'Practice', exact: true }).click();
  await page.locator('.quiz-option').nth(1).click();
  await expect(page.locator('#quiz-score')).toHaveText('1 / 1');
  await page.getByRole('link', { name: 'Improve', exact: true }).click();
  await page.getByRole('link', { name: 'I lose from ahead', exact: false }).click();
  await expect(page.locator('#improve-finish .lesson-body')).toBeVisible();
  expect(requests).toEqual([]);
  expect(errors).toEqual([]);
});

test('general lessons open through discovery, deep links, repeated links and browser history', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Explore the general Digimon guide' }).click();
  await expect(page.getByRole('link', { name: 'Improve', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#learn')).toBeHidden();
  await page.getByRole('link', { name: 'I run out of memory', exact: false }).click();
  await expect(page.locator('#improve-memory .lesson-body')).toBeVisible();
  await page.locator('#improve-memory summary').click();
  await expect(page.locator('#improve-memory .lesson-body')).toBeHidden();
  await page.getByRole('link', { name: 'I run out of memory', exact: false }).click();
  await expect(page.locator('#improve-memory .lesson-body')).toBeVisible();
  await page.getByRole('link', { name: 'Sources & rules', exact: true }).click();
  await expect(page.locator('#source-improve')).toHaveAttribute('open', '');
  await expect(page.locator('#source-drawer')).toHaveAttribute('open', '');
  await expect(page.locator('#fundamentals')).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/#improve-memory$/);
  await page.reload();
  await expect(page.locator('#improve-memory .lesson-body')).toBeVisible();
  await expect(page.locator('#matchups')).toBeHidden();
  await page.goto('/#improve-finish');
  await expect(page.locator('#improve-finish .lesson-body')).toBeVisible();
  await page.getByRole('link', { name: 'Practise attack decisions in the puzzles' }).click();
  await expect(page.locator('#puzzles')).toBeVisible();
  await page.goBack();
  await expect(page.locator('#improve-finish .lesson-body')).toBeVisible();
  // Every lesson must also be usable with a keyboard, including its content links.
  for (const lesson of await page.locator('.lesson').all()) {
    const summary = lesson.locator('summary');
    await summary.focus();
    if (await lesson.getAttribute('open') === null) await page.keyboard.press('Enter');
    await expect(lesson.locator('.lesson-drill')).toBeVisible();
  }
});

test('printing includes collapsed lessons and restores the reading state afterwards', async ({ page }) => {
  await page.goto('/#fundamentals');
  await expect(page.locator('.lesson[open]')).toHaveCount(1);
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
  await page.emulateMedia({ media: 'print' });
  await expect(page.locator('.lesson[open]')).toHaveCount(8);
  await expect(page.locator('#improve-list .lesson-body')).toBeVisible();
  await expect(page.locator('#puzzles')).toBeHidden();
  await page.emulateMedia({ media: 'screen' });
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await expect(page.locator('.lesson[open]')).toHaveCount(1);
  await expect(page.locator('#improve-plan')).toHaveAttribute('open', '');
  await expect(page.locator('#source-drawer')).not.toHaveAttribute('open', '');
});

test('official card images enlarge, close with Escape, and work inside puzzles', async ({ page }, testInfo) => {
  await page.goto('/');
  const inspect = page.getByRole('button', { name: 'Inspect Atratusmon (ST23-09)', exact: true });
  await inspect.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.locator('#card-dialog-title')).toHaveText('Atratusmon');
  await expect.poll(() => page.locator('#card-dialog-image').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('card-viewer.png') });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(inspect).toBeFocused();
  await page.getByRole('link', { name: 'Practice', exact: true }).click();
  await page.locator('#quiz-cards summary').click();
  await page.locator('#quiz-card-shelf .digimon-card').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Close card', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await page.getByRole('link', { name: 'Matchups', exact: true }).click();
  await expect(page.locator('#matchups')).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollHeight - (document.querySelector('footer')!.getBoundingClientRect().bottom + scrollY))).toBeLessThan(50);
  await page.screenshot({ path: testInfo.outputPath('matchups.png'), fullPage: true });
  await page.goBack();
  await expect(page.locator('#quiz')).toBeVisible();
  await expect.poll(() => page.locator('img').evaluateAll(images => images.every(img => img instanceof HTMLImageElement && img.complete && img.naturalWidth > 0))).toBe(true);
});
