// Scénario 7 — Code glissé dans les données : un module, un document et le
// prénom d'un enseignant s'appellent `<img src=x onerror=...>`. Chaque page
// doit afficher ce nom comme du texte, sans jamais exécuter le code (qui
// incrémenterait window.__xss) ni ouvrir de boîte de dialogue.
import { test, expect } from '@playwright/test';
import { lireEtat, ouvrirSession } from './outils.js';

const PAGES = [
  ['etudiant', '/etudiant/planning'],
  ['etudiant', '/etudiant/enseignants'],
  ['etudiant', '/etudiant/progression'],
  ['etudiant', '/etudiant/documents'],
  ['chef_reel', '/chef/contenu'],
  ['chef_reel', '/chef/enseignants'],
];

for (const [session, chemin] of PAGES) {
  test(`aucun code exécuté : ${chemin}`, async ({ page }) => {
    const dialogues = [];
    page.on('dialog', (d) => { dialogues.push(d.message()); d.dismiss(); });
    await ouvrirSession(page, session, chemin);
    await page.waitForLoadState('networkidle');
    expect(await page.evaluate(() => window.__xss ?? 0)).toBe(0);
    expect(dialogues).toEqual([]);
    // Aucune balise <img src="x"> n'a été fabriquée à partir des données.
    expect(await page.locator('img[src="x"]').count()).toBe(0);
  });
}

test('le nom piégé est bien affiché, comme du texte, sur le planning', async ({ page }) => {
  await ouvrirSession(page, 'etudiant', '/etudiant/planning');
  await expect(page.getByText(lireEtat().donnees.code_piege).first()).toBeVisible();
});

test("l'export PDF du planning n'exécute pas le code", async ({ page }) => {
  await ouvrirSession(page, 'etudiant', '/etudiant/planning');
  await expect(page.getByText(lireEtat().donnees.code_piege).first()).toBeVisible();
  const telechargement = page.waitForEvent('download', { timeout: 30_000 });
  await page.getByText('Générer PDF').click();
  await telechargement;
  expect(await page.evaluate(() => window.__xss ?? 0)).toBe(0);
  expect(await page.locator('img[src="x"]').count()).toBe(0);
});
