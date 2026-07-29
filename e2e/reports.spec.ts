import { expect, test } from '@playwright/test';

// Runs after onboarding.spec.ts against the same backend (workers: 1), so
// onboarding is normally already complete. The guard below onboards a profile
// itself when this spec is run in isolation.
async function ensureOnboarded(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/');
  const startSetup = page.getByRole('button', { name: 'Start setup' });
  try {
    await startSetup.waitFor({ state: 'visible', timeout: 5_000 });
  } catch {
    return; // Already onboarded — the app went straight to the dashboard.
  }

  const fieldTextbox = (label: string) =>
    page
      .locator('.field')
      .filter({ has: page.getByText(label, { exact: true }) })
      .locator('input, textarea')
      .first();

  await startSetup.click();
  await fieldTextbox('Who is this profile for?').fill('Reports profile');
  await fieldTextbox('Cancer type').fill('Non-small cell lung cancer');
  await page.getByRole('button', { name: 'Save and continue' }).click();
  await expect(page.getByText('Enabled real sources')).toBeVisible();
  await page.getByRole('checkbox', { name: /I understand my information stays/ }).check();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Run health check' }).click();
  await expect(page.getByRole('button', { name: 'Continue' })).toBeEnabled({ timeout: 30_000 });
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Open dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'Today' })).toBeVisible({ timeout: 30_000 });
}

test('a report can be previewed, created, read in the app, and downloaded', async ({ page }) => {
  await ensureOnboarded(page);

  await page.goto('/#/reports');
  await expect(page.getByText('What are you preparing for?')).toBeVisible();

  // The preview is the report's real contents, fetched from the backend.
  await page.getByRole('button', { name: /a quick update to share/i }).click();
  await expect(page.getByText(/What will be in this report/)).toBeVisible();
  await expect(page.getByText('Questions for your oncology team')).toBeVisible({ timeout: 15_000 });

  await page.getByRole('button', { name: /create daily summary report/i }).click();
  await expect(page.getByText('Your report is ready')).toBeVisible({ timeout: 30_000 });

  // Outside the desktop shell the primary action is a browser download,
  // and the filename is date-stamped so repeat reports never collide.
  const downloadEvent = page.waitForEvent('download', { timeout: 20_000 });
  await page.getByRole('button', { name: /download pdf/i }).first().click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/^firstlight-daily-summary-\d{4}-\d{2}-\d{2}\.pdf$/);

  // The history row describes what is inside without opening the file.
  await expect(page.getByText(/·.*question/i).first()).toBeVisible();
});
