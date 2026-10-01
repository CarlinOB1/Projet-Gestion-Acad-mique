// Scénario 6 — Pannes du serveur : serveur injoignable, erreur 500 (page
// HTML), serveur qui ne répond jamais. Attendu : un message lisible, jamais
// une page blanche, jamais de code HTML affiché, jamais d'attente sans fin.
import { test, expect } from '@playwright/test';
import { failleConnue, lireEtat, ouvrirSession } from './outils.js';

const PLANNING = '**/api/etudiants/mon_planning/**';
const PAGE_500 = '<!DOCTYPE html><html><body><h1>Server Error (500)</h1></body></html>';
const MESSAGE_ERREUR = /erreur est survenue/i;

async function sansCodeHtml(page) {
  const texte = await page.locator('body').innerText();
  expect(texte).not.toMatch(/<!DOCTYPE|<html|<\/?body|<h1>/i);
}

test('serveur injoignable : message lisible sur le planning', async ({ page }) => {
  await page.route(PLANNING, (route) => route.abort('connectionrefused'));
  await ouvrirSession(page, 'etudiant', '/etudiant/planning');
  await expect(page.getByText(MESSAGE_ERREUR)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('navigation').first()).toBeVisible();
});

test('erreur 500 : message lisible, pas de code HTML affiché', async ({ page }) => {
  await page.route(PLANNING, (route) =>
    route.fulfill({ status: 500, contentType: 'text/html', body: PAGE_500 }));
  await ouvrirSession(page, 'etudiant', '/etudiant/planning');
  await expect(page.getByText(MESSAGE_ERREUR)).toBeVisible({ timeout: 20_000 });
  await sansCodeHtml(page);
});

test("erreur 500 à la suspension d'un étudiant : pas de code HTML dans le message", async ({ page }) => {
  failleConnue(test, 44);
  const { donnees } = lireEtat();
  await page.route('**/changer_statut/', (route) =>
    route.fulfill({ status: 500, contentType: 'text/html', body: PAGE_500 }));
  // Suspendre un étudiant est réservé à la scolarité (le chef ne voit pas le bouton).
  await ouvrirSession(page, 'admin', '/chef/classes');
  await page.getByRole('button', { name: new RegExp(donnees.classe_libelle) }).click();
  await page.locator('div')
    .filter({ has: page.getByText('ETU-99001', { exact: true }) })
    .filter({ has: page.getByRole('button', { name: 'Suspendre' }) })
    .last()
    .getByRole('button', { name: 'Suspendre' })
    .click();
  await page.getByLabel('Motif de la suspension').fill('Essai de panne');
  await page.getByRole('button', { name: 'Confirmer la suspension' }).click();
  // Un message d'erreur s'affiche dans le panneau...
  await expect(page.getByRole('dialog').getByText(/erreur|500/i).first()).toBeVisible();
  // ...mais jamais la page HTML brute renvoyée par le serveur.
  await sansCodeHtml(page);
});

test('serveur qui ne répond jamais : un message finit par apparaître', async ({ page }) => {
  failleConnue(test, 42);
  await page.route(PLANNING, () => { /* jamais de réponse */ });
  await ouvrirSession(page, 'etudiant', '/etudiant/planning');
  await expect(page.getByText(/erreur|délai|réessayer|ne répond/i).first()).toBeVisible({ timeout: 45_000 });
});
