// Scénario 4 — Compte suspendu pendant qu'il est connecté : l'action suivante
// est refusée, avec un message qui dit pourquoi.
import { test, expect } from '@playwright/test';
import { API, entetes, lireEtat, ouvrirSession } from './outils.js';

test.afterEach(async ({ request }) => {
  // Réactive le compte, pour pouvoir rejouer le scénario.
  await request.patch(`${API}/profils/${lireEtat().donnees.suspendu_profil_id}/changer_statut/`, {
    headers: entetes('admin'), data: { statut: 'actif' },
  });
});

test("suspendu en cours de session : l'action suivante est refusée avec un message clair", async ({ page, request }) => {
  await ouvrirSession(page, 'suspendu', '/etudiant/planning');
  await expect(page.getByRole('heading', { name: /^Planning/ })).toBeVisible();

  const reponse = await request.patch(
    `${API}/profils/${lireEtat().donnees.suspendu_profil_id}/changer_statut/`,
    { headers: entetes('admin'), data: { statut: 'suspendu', motif_suspension: 'Test navigateur' } },
  );
  expect(reponse.ok(), await reponse.text()).toBeTruthy();

  // Action suivante : ouvrir une autre page, qui interroge le serveur.
  const refus = page.waitForResponse((r) => r.url().includes('/api/') && r.status() === 403);
  await page.getByRole('link', { name: 'Mes enseignants' }).click();
  await refus;

  // Le serveur refuse ; l'interface doit dire que le compte est suspendu,
  // pas « rafraîchissez la page ».
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText(/suspendu/i)).toBeVisible();
});
