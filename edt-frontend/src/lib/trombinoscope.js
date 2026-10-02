/**
 * @file trombinoscope.js
 * @description Utilitaires de transformation des séances en liste d'enseignants
 * distincts avec leurs modules, pour l'affichage du trombinoscope étudiant.
 */
import { TYPE_SEANCE } from './constants';
import { prochaineSeance } from './creneau';

const parLibelle = (a, b) => a.localeCompare(b, 'fr');

/**
 * Regroupe les événements de planning (FullCalendar) par enseignant.
 * Chaque événement porte la séance complète dans `extendedProps`.
 *
 * @param {Array} events - Événements retournés par useSeances (transformSeanceToEvent)
 * @param {Date} [maintenant]
 * @returns {Array<{
 *   id, nom_complet, grade, departement,
 *   modules: Array<{ id, libelle, types: string[] }>,
 *   prochaine: Object|null
 * }>}
 */
export function buildTrombinoscope(events = [], maintenant = new Date()) {
  const map = new Map();

  events.forEach((event) => {
    const seance = event?.extendedProps;
    const enseignant = seance?.enseignant;
    const module = seance?.module;

    if (!enseignant || !enseignant.profil_id) return;

    const id = enseignant.profil_id;

    if (!map.has(id)) {
      map.set(id, {
        id,
        nom_complet: enseignant.nom_complet || "Enseignant",
        grade: enseignant.grade || "",
        departement: enseignant.departement?.libelle || "",
        modules: new Map(),
        seances: [],
      });
    }

    const entry = map.get(id);
    entry.seances.push(seance);
    if (module?.libelle) {
      if (!entry.modules.has(module.id)) {
        entry.modules.set(module.id, { id: module.id, libelle: module.libelle, types: new Set() });
      }
      if (seance.type_seance) entry.modules.get(module.id).types.add(seance.type_seance);
    }
  });

  return Array.from(map.values())
    .map(({ modules, seances, ...entry }) => ({
      ...entry,
      // Le type (CM, TD, TP) dit à l'étudiant dans quel cadre il voit cet
      // enseignant : un même module peut être partagé entre plusieurs.
      modules: Array.from(modules.values())
        .map((m) => ({ ...m, types: Object.values(TYPE_SEANCE).filter((type) => m.types.has(type)) }))
        .sort((a, b) => parLibelle(a.libelle, b.libelle)),
      prochaine: prochaineSeance(seances, maintenant),
    }))
    .sort((a, b) => parLibelle(a.nom_complet, b.nom_complet));
}

/**
 * Extrait jusqu'à deux initiales d'un nom complet pour l'avatar de secours.
 * @param {string} nomComplet
 * @returns {string}
 */
export function getInitials(nomComplet = "") {
  return nomComplet
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((mot) => mot[0]?.toUpperCase())
    .join("");
}
