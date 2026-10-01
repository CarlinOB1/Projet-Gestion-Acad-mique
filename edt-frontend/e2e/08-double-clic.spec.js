// Scénario 8 — Double clic sur « Enregistrer la séance » : une seule séance
// doit être créée. (La séance créée est effacée par preparer_base.py
// nettoyer : elle appartient à l'enseignant de test.)
import { test, expect } from '@playwright/test';
import { failleConnue, lireEtat, ouvrirSession } from './outils.js';

test('double clic sur Enregistrer : une seule séance créée', async ({ page }) => {
  failleConnue(test, 43);
  const { donnees } = lireEtat();
  const creations = [];
  page.on('response', (r) => {
    if (r.request().method() === 'POST' && /\/api\/seances\/$/.test(r.url())) creations.push(r.status());
  });

  await ouvrirSession(page, 'chef_reel', '/chef/planning');
  await expect(page.getByRole('heading', { name: new RegExp(donnees.classe_libelle) })).toBeVisible();
  // Semaine suivante : toute la semaine est à venir, donc saisissable.
  await page.getByRole('button', { name: 'Semaine suivante' }).click();
  await page.locator('td > button[type="button"]').first().click();

  const fenetre = page.getByRole('dialog');
  await expect(fenetre.getByText('Nouvelle séance')).toBeVisible();
  await fenetre.locator('#seance-module').click();
  await page.getByRole('option', { name: donnees.code_piege }).click();
  await fenetre.locator('#seance-enseignant').click();
  await page.getByRole('option', { name: /Piégé/ }).click();

  await fenetre.getByRole('button', { name: 'Enregistrer la séance' }).dblclick();
  await expect(fenetre).toBeHidden({ timeout: 15_000 });
  await page.waitForTimeout(2000);

  expect(creations.filter((code) => code === 201)).toHaveLength(1);
});
