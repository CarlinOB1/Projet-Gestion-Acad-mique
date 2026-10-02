/**
 * @file creneau.js
 * @description Créneau réel d'une séance (celui du report quand elle a été
 * reportée) et recherche du prochain cours, pour les pages de l'étudiant.
 */
import { formatDate } from './utils';

/**
 * Jour et heures où la séance a réellement lieu : une séance reportée se
 * tient au créneau du report, pas à son créneau d'origine.
 * @param {Object} seance
 * @returns {{ date: string, debut: string, fin: string }}
 */
export function creneauEffectif(seance) {
  if (seance?.statut === 'Reportée' && seance.date_report) {
    return {
      date: seance.date_report,
      debut: seance.heure_debut_report || seance.heure_debut,
      fin: seance.heure_fin_report || seance.heure_fin,
    };
  }
  return { date: seance?.date_seance, debut: seance?.heure_debut, fin: seance?.heure_fin };
}

/** "AAAA-MM-JJ" (+ "HH:MM[:SS]") lu en heure locale. */
export function enDate(jour, heure = '00:00') {
  if (!jour) return null;
  const date = new Date(`${jour}T${(heure || '00:00').slice(0, 5)}`);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Lundi 0 h de la semaine qui contient `jour`. */
export function debutDeSemaine(jour = new Date()) {
  const lundi = new Date(jour);
  lundi.setHours(0, 0, 0, 0);
  lundi.setDate(lundi.getDate() - ((lundi.getDay() + 6) % 7));
  return lundi;
}

/**
 * Prochain cours parmi `seances` : le plus tôt qui n'est ni annulé ni déjà
 * fini (un cours en train d'avoir lieu compte encore).
 * @param {Array} seances - séances de l'API
 * @param {Date} [maintenant]
 * @returns {{ seance: Object, date: string, debut: string, fin: string }|null}
 */
export function prochaineSeance(seances = [], maintenant = new Date()) {
  let prochaine = null;
  let debutProchaine = null;
  seances.forEach((seance) => {
    if (!seance || seance.statut === 'Annulée') return;
    const creneau = creneauEffectif(seance);
    const fin = enDate(creneau.date, creneau.fin);
    if (!fin || fin <= maintenant) return;
    const debut = enDate(creneau.date, creneau.debut);
    if (!prochaine || debut < debutProchaine) {
      prochaine = { seance, ...creneau };
      debutProchaine = debut;
    }
  });
  return prochaine;
}

/** « Aujourd'hui », « Demain » ou « Lun. 6 oct. ». */
export function formatJourProche(jour, maintenant = new Date()) {
  const date = enDate(jour);
  if (!date) return '';
  const aujourdhui = new Date(maintenant);
  aujourdhui.setHours(0, 0, 0, 0);
  // Arrondi : un passage à l'heure d'été ou d'hiver donne des jours de 23 ou 25 h.
  const ecart = Math.round((date - aujourdhui) / 86_400_000);
  if (ecart === 0) return "Aujourd'hui";
  if (ecart === 1) return 'Demain';
  return formatDate(jour);
}
