// Scénario 2 — Rôle falsifié dans le navigateur : un étudiant réécrit son
// rôle en « chef » dans le localStorage. L'interface chef peut s'afficher
// (elle ne fait que lire ce rôle), mais c'est le serveur qui décide : toute
// action de chef doit être refusée.
import { test, expect } from '@playwright/test';
import { API, REFUS, lireEtat, ouvrirSession } from './outils.js';

test("rôle falsifié : l'interface s'ouvre, le serveur refuse tout", async ({ page }) => {
  const { donnees } = lireEtat();
  const session = await ouvrirSession(page, 'etudiant', '/chef/planning', (s) => {
    s.user.role = 'chef_departement';
    return s;
  });
  await expect(page).toHaveURL(/\/chef\/planning$/);
  await expect(page.locator('body')).not.toBeEmpty();

  // Actions de chef envoyées avec le vrai jeton (celui d'un étudiant).
  const codes = await page.evaluate(async ({ api, jeton, d }) => {
    const appel = (methode, chemin, corps) =>
      fetch(api + chemin, {
        method: methode,
        headers: { Authorization: `Bearer ${jeton}`, 'Content-Type': 'application/json' },
        body: corps ? JSON.stringify(corps) : undefined,
      }).then((r) => r.status);
    return {
      creer_seance: await appel('POST', '/seances/', {
        module_id: d.module_reference_id, enseignant_id: d.enseignant_reference_id,
        classe_id: d.classe_id, date_seance: d.lundi, heure_debut: '14:15', heure_fin: '16:15',
        type_seance: 'CM',
      }),
      publier_masse: await appel('POST', '/seances/publier_masse/', { seance_ids: [1] }),
      suspendre: await appel('PATCH', `/profils/${d.suspendu_profil_id}/changer_statut/`, {
        statut: 'suspendu', motif_suspension: 'rôle falsifié',
      }),
      conflits: await appel('GET', `/seances/conflits/?semestre_id=${d.semestre_id}`),
    };
  }, { api: '/api', jeton: session.accessToken, d: donnees });

  for (const [action, code] of Object.entries(codes)) {
    expect(REFUS, `${action} accepté (${code}) pour un étudiant au rôle falsifié`).toContain(code);
  }

  // La liste des étudiants répond, mais réduite à sa propre fiche.
  const liste = await page.evaluate(async (jeton) => {
    const r = await fetch('/api/etudiants/', { headers: { Authorization: `Bearer ${jeton}` } });
    return r.json();
  }, session.accessToken);
  expect(liste.count ?? liste.length).toBe(1);
});

test('rôle falsifié : le profil réel reste étudiant côté serveur', async ({ request }) => {
  const reponse = await request.get(`${API}/profils/me/`, {
    headers: { Authorization: `Bearer ${lireEtat().sessions.etudiant.accessToken}` },
  });
  expect(reponse.ok()).toBeTruthy();
  const profil = await reponse.json();
  expect(JSON.stringify(profil)).not.toContain('chef_departement');
});
