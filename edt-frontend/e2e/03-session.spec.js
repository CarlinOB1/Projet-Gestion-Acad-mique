// Scénario 3 — Expiration de session.
//  - Jeton d'accès expiré : plusieurs requêtes reçoivent 401 en même temps,
//    mais la session n'est renouvelée qu'une fois, et la page se charge.
//  - Renouvellement refusé : retour à la connexion, sans boucle.
import { test, expect } from '@playwright/test';
import { compterAppels, ouvrirSession } from './outils.js';

// Jeton d'accès invalide : le serveur répond 401 comme pour un jeton expiré.
const JETON_PERIME = 'eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjF9.signature-invalide';

test("jeton d'accès expiré : un seul renouvellement, la page se charge", async ({ page }) => {
  const renouvellements = compterAppels(page, '/api/token/refresh/');
  // Session à part : le renouvellement met son jeton de renouvellement en
  // liste noire, les autres scénarios gardent les leurs.
  await ouvrirSession(page, 'autre', '/etudiant/planning', (s) => ({ ...s, accessToken: JETON_PERIME }));

  await expect(page.getByText('Une erreur est survenue')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: /^Planning/ })).toBeVisible();
  await page.waitForLoadState('networkidle');
  expect(renouvellements).toHaveLength(1);
  const etat = await page.evaluate(() => JSON.parse(localStorage.getItem('edt-auth')).state);
  expect(etat.accessToken).not.toBe(JETON_PERIME);
});

test('renouvellement refusé : retour à la connexion, sans boucle', async ({ page }) => {
  const renouvellements = compterAppels(page, '/api/token/refresh/');
  await ouvrirSession(page, 'etudiant', '/etudiant/planning', (s) => ({
    ...s, accessToken: JETON_PERIME, refreshToken: JETON_PERIME,
  }));
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText('Votre session a expiré. Reconnectez-vous.')).toBeVisible();
  await page.waitForTimeout(3000);
  expect(renouvellements.length).toBeLessThanOrEqual(1);
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('edt-auth') ?? '{}').state?.accessToken ?? null))
    .toBeNull();
});
