import { test, expect } from '@playwright/test';

test('loads homepage without console errors', async ({ page }) => {
  const messages: string[] = [];
  page.on('console', (msg) => messages.push(`${msg.type()}: ${msg.text()}`));

  await page.goto('/');

  // Basic smoke checks
  await expect(page.getByRole('heading', { name: 'Cyber Grader', level: 1 })).toBeVisible();
  await expect(page.getByText('Cybersecurity learning cockpit')).toBeVisible();

  // The login button should be visible on fresh load
  await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

  // Fail test if there are console errors
  const errorLogs = messages.filter((m) => m.startsWith('error:'));
  expect(errorLogs, `Console errors present on load:\n${errorLogs.join('\n')}`).toHaveLength(0);
});
