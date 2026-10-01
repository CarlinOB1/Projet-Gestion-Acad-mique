// Outils partagés par les scénarios navigateur.
import { readFileSync } from 'node:fs';

export const API = 'http://127.0.0.1:8011/api';

// Réponses qui valent refus : non connecté, interdit ou masqué.
export const REFUS = [401, 403, 404];

let etat;
/** Comptes, sessions et identifiants préparés par preparer_base.py. */
export function lireEtat() {
  etat ??= JSON.parse(readFileSync(process.env.E2E_ETAT, 'utf-8'));
  return etat;
}

/**
 * Ouvre l'application déjà connectée avec la session `nom` (voir
 * preparer_base.py), comme après une connexion réussie. `modifier` permet de
 * trafiquer la session avant de la poser (rôle falsifié, jeton expiré...).
 */
export async function ouvrirSession(page, nom, chemin = '/', modifier = (s) => s) {
  const session = modifier(structuredClone(lireEtat().sessions[nom]));
  await page.goto('/login');
  await page.evaluate((valeur) => {
    localStorage.setItem('edt-auth', JSON.stringify({ state: valeur, version: 0 }));
  }, session);
  await page.goto(chemin);
  return session;
}

/** En-têtes d'appel direct à l'API au nom de la session `nom`. */
export function entetes(nom) {
  return { Authorization: `Bearer ${lireEtat().sessions[nom].accessToken}` };
}

/**
 * Faille connue (équivalent de @faille_connue côté serveur) : le scénario
 * décrit le comportement voulu, qui n'est pas encore celui de l'application.
 * Playwright signale une erreur le jour où il passe : il suffit alors de
 * retirer l'appel.
 */
export function failleConnue(test, numero) {
  test.fail(true, `CORRECTIONS_A_FAIRE.md point ${numero}`);
}

/** Compte les appels de la page dont l'adresse contient `morceau`. */
export function compterAppels(page, morceau) {
  const appels = [];
  page.on('request', (r) => {
    if (r.url().includes(morceau)) appels.push(r.url());
  });
  return appels;
}
