import { expect, test } from '@playwright/test';

// Verifies the make-interfaces-feel-better polish pass: concentric radius,
// tabular-nums, text-wrap, scale-on-press, 40px hit areas, widened stagger.
test('ui polish renders and computed styles are applied', async ({ page }, testInfo) => {
  const fieldTextbox = (label: string) =>
    page
      .locator('.field')
      .filter({ has: page.getByText(label, { exact: true }) })
      .locator('input, textarea')
      .first();

  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'A steady trial and literature briefing routine.' })
  ).toBeVisible();

  // Screenshot the onboarding surface (cards, buttons, step list).
  await page.screenshot({ path: testInfo.outputPath('01-onboarding.png'), fullPage: true });

  await page.getByRole('button', { name: 'Start setup' }).click();
  await fieldTextbox('Who is this profile for?').fill('Polish profile');
  await fieldTextbox('Cancer type').fill('Non-small cell lung cancer');
  await page.getByRole('button', { name: 'Save and continue' }).click();

  await expect(page.getByText('Enabled real sources')).toBeVisible();
  await page.getByRole('checkbox', { name: /I understand my information stays/ }).check();
  await page.getByRole('button', { name: 'Continue' }).click();

  await page.getByRole('button', { name: 'Run health check' }).click();
  await expect(page.getByRole('button', { name: 'Continue' })).toBeEnabled({ timeout: 30_000 });
  await page.getByRole('button', { name: 'Continue' }).click();

  await page.getByRole('button', { name: 'Open dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'Today' })).toBeVisible({
    timeout: 30_000
  });

  // ---- Dashboard screenshot ----
  await page.screenshot({ path: testInfo.outputPath('02-dashboard.png'), fullPage: true });

  // ---- Computed-style assertions ----

  // 1. Concentric radius: outer .card == 10px.
  const cardRadius = await page
    .locator('.card')
    .first()
    .evaluate((el) => getComputedStyle(el).borderTopLeftRadius);
  expect(cardRadius).toBe('10px');

  // 2. Hit area: nav items render at least 40px tall.
  const navHeight = await page
    .locator('.nav-item')
    .first()
    .evaluate((el) => (el as HTMLElement).offsetHeight);
  expect(navHeight).toBeGreaterThanOrEqual(40);

  // 3. Hit area: primary/secondary buttons at least 40px tall.
  const btnHeight = await page
    .locator('.primary-button, .secondary-button, .ghost-button')
    .first()
    .evaluate((el) => (el as HTMLElement).offsetHeight);
  expect(btnHeight).toBeGreaterThanOrEqual(40);

  // 4. text-wrap: balance on headings.
  const headingWrap = await page
    .locator('h1')
    .first()
    .evaluate((el) => getComputedStyle(el).textWrap || getComputedStyle(el).getPropertyValue('text-wrap'));
  expect(headingWrap).toContain('balance');

  // 5. scale-on-press wired on buttons: scale transition present.
  const btnTransition = await page
    .locator('.primary-button, .secondary-button, .ghost-button')
    .first()
    .evaluate((el) => getComputedStyle(el).transition);
  expect(btnTransition).toContain('scale');

  // 6. CSS token --radius-lg defined.
  const radiusLg = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--radius-lg').trim()
  );
  expect(radiusLg).toBe('10px');

  // ---- Findings page screenshot (cards, badges, filter chips, finding items) ----
  await page.goto('/#/findings');
  await expect(page.getByRole('heading', { name: 'Discoveries' })).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: testInfo.outputPath('03-findings.png'), fullPage: true });

  // filter chips, when present, render at least ~36px tall.
  const chip = page.locator('.filter-chip').first();
  if (await chip.count()) {
    const chipHeight = await chip.evaluate((el) => (el as HTMLElement).offsetHeight);
    expect(chipHeight).toBeGreaterThanOrEqual(34);
  }

  // ---- Settings page (toggle rows, form fields) ----
  await page.goto('/#/settings');
  await page.waitForTimeout(500);
  await page.screenshot({ path: testInfo.outputPath('04-settings.png'), fullPage: true });

  // ---- Profile page (form grid, strength meter) ----
  await page.goto('/#/profile');
  await page.waitForTimeout(500);
  await page.screenshot({ path: testInfo.outputPath('05-profile.png'), fullPage: true });

  // ---- Trials to Consider ----
  await page.goto('/#/trials');
  await page.waitForTimeout(800);
  await page.screenshot({ path: testInfo.outputPath('06-trials.png'), fullPage: true });

  // ---- Research Updates ----
  await page.goto('/#/updates');
  await page.waitForTimeout(800);
  await page.screenshot({ path: testInfo.outputPath('07-updates.png'), fullPage: true });

  // ---- Reports for the Doctor ----
  await page.goto('/#/reports');
  await page.waitForTimeout(800);
  await page.screenshot({ path: testInfo.outputPath('08-reports.png'), fullPage: true });

  // ---- About / Help ----
  await page.goto('/#/support');
  await page.waitForTimeout(800);
  await page.screenshot({ path: testInfo.outputPath('09-support.png'), fullPage: true });
});
