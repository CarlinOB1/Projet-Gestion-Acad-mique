// Scénario 1 — Connexion par rôle : chacun arrive sur sa page, et un étudiant
// qui tape l'adresse de l'espace chef n'y entre pas.
import { test, expect } from '@playwright/test';
import { failleConnue, lireEtat, ouvrirSession } from './outils.js';

async function seConnecter(page, { username, password }) {
  await page.goto('/login');
  await page.getByLabel('Identifiant').fill(username);
  await page.getByLabel('Mot de passe', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Se connecter' }).click();
}

const ARRIVEES = {
  etudiant: /\/etudiant\/planning$/,
  enseignant: /\/enseignant\/planning$/,
  chef: /\/chef\/planning$/,
  admin: /\/chef\/planning$/,
};

for (const [role, arrivee] of Object.entries(ARRIVEES)) {
  test(`connexion ${role} : arrive sur sa page`, async ({ page }) => {
    await seConnecter(page, lireEtat().comptes[role]);
    await expect(page).toHaveURL(arrivee);
  });
}

test('mauvais mot de passe : message, et on reste sur la connexion', async ({ page }) => {
  failleConnue(test, 40);
  const { username } = lireEtat().comptes.etudiant;
  await seConnecter(page, { username, password: 'pas-le-bon-mot-de-passe' });
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});

test("un étudiant qui ouvre l'espace chef est renvoyé ailleurs", async ({ page }) => {
  await ouvrirSession(page, 'etudiant', '/chef/planning');
  await expect(page).not.toHaveURL(/\/chef\//);
});
