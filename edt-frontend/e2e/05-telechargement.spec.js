// Scénario 5 — Téléchargement protégé : un étudiant du module reçoit le
// document depuis la page Documents ; sans session, ou pour un étudiant
// d'une autre classe, le lien est refusé. (En local, Django sert le fichier ;
// la remise par nginx se vérifie à la mise en ligne.)
import { test, expect } from '@playwright/test';
import { API, REFUS, entetes, lireEtat, ouvrirSession } from './outils.js';

test("l'étudiant du module télécharge le document depuis la page Documents", async ({ page }) => {
  await ouvrirSession(page, 'etudiant', '/etudiant/documents');
  const ligne = page.getByText(lireEtat().donnees.code_piege, { exact: true }).first();
  await expect(ligne).toBeVisible();

  const telechargement = page.waitForEvent('download');
  await page.getByRole('button', { name: `Télécharger ${lireEtat().donnees.code_piege}` }).click();
  const fichier = await telechargement;
  expect(fichier.suggestedFilename()).toMatch(/\.pdf$/);
});

test('sans session, le lien de téléchargement est refusé', async ({ request }) => {
  const reponse = await request.get(`${API}/documents/${lireEtat().donnees.document_id}/telecharger/`);
  expect(REFUS).toContain(reponse.status());
});

test("un étudiant d'une autre classe ne peut pas télécharger", async ({ request }) => {
  const reponse = await request.get(`${API}/documents/${lireEtat().donnees.document_id}/telecharger/`, {
    headers: entetes('autre'),
  });
  expect(REFUS).toContain(reponse.status());
});
