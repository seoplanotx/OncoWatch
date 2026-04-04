import { expect, test } from '@playwright/test';

test('first launch onboarding reaches the dashboard and support surface', async ({ page }) => {
  const fieldTextbox = (label: string) =>
    page
      .locator('.field')
      .filter({ has: page.getByText(label, { exact: true }) })
      .getByRole('textbox');

  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Build a steady trial and literature briefing routine.' })).toBeVisible();

  await page.getByRole('button', { name: 'Start setup' }).click();

  await fieldTextbox('Profile name').fill('Smoke profile');
  await fieldTextbox('Cancer type').fill('Non-small cell lung cancer');
  await page.getByRole('button', { name: 'Save and continue' }).click();

  await expect(page.getByText('Enabled real sources')).toBeVisible();
  await page.getByRole('button', { name: 'Continue' }).click();

  await page.getByRole('button', { name: 'Run health check' }).click();
  await expect(page.getByRole('button', { name: 'Continue' })).toBeEnabled({ timeout: 30_000 });
  await page.getByRole('button', { name: 'Continue' }).click();

  await page.getByRole('button', { name: 'Open dashboard' }).click();

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('Automatic runs happen only while OncoWatch is open.')).toBeVisible();

  await page.goto('/#/support');
  await expect(page.getByRole('heading', { name: 'About / Support' })).toBeVisible();
  await expect(page.getByText('Local storage')).toBeVisible();
});
