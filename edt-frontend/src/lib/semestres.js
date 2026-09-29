/**
 * @file semestres.js
 * @description Semestre en cours et libellés de semestre, partagés par les
 * pages qui listent des classes (Classes & Étudiants, Contenu pédagogique,
 * Planning).
 */

/** "AAAA-MM-JJ" lu en date locale (new Date("AAAA-MM-JJ") le lirait en UTC). */
function dateLocale(s) {
  if (!s) return null;
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
}

/**
 * Semestre en cours d'après ses dates : celui qui contient aujourd'hui.
 * Entre deux semestres (vacances), le prochain à commencer ; après le
 * dernier, le plus récent. Se fonder sur les dates plutôt que sur l'année
 * « active » : les deux semestres d'une année sont actifs en même temps.
 */
export function trouverSemestreEnCours(semestres = [], aujourdhui = new Date()) {
  const jour = new Date(aujourdhui);
  jour.setHours(0, 0, 0, 0);
  const avecDates = semestres
    .map((s) => ({ s, debut: dateLocale(s.date_debut), fin: dateLocale(s.date_fin) }))
    .filter((x) => x.debut && x.fin);
  if (avecDates.length === 0) return semestres[0] ?? null;

  const enCours = avecDates.find((x) => x.debut <= jour && jour <= x.fin);
  if (enCours) return enCours.s;

  const aVenir = avecDates
    .filter((x) => x.debut > jour)
    .sort((a, b) => a.debut - b.debut)[0];
  if (aVenir) return aVenir.s;

  return avecDates.sort((a, b) => b.fin - a.fin)[0].s;
}

/** « Semestre 1 · 2026-2027 » */
export function libelleSemestre(semestre) {
  if (!semestre) return '';
  return [semestre.libelle, semestre.annee?.libelle].filter(Boolean).join(' · ');
}

/** « du 16 sept. au 1 janv. » */
export function periodeSemestre(semestre) {
  const debut = dateLocale(semestre?.date_debut);
  const fin = dateLocale(semestre?.date_fin);
  if (!debut || !fin) return '';
  const fmt = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' });
  return `du ${fmt.format(debut)} au ${fmt.format(fin)}`;
}
