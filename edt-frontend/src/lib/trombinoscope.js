/**
 * @file trombinoscope.js
 * @description Utilitaires de transformation des séances en liste d'enseignants
 * distincts avec leurs matières, pour l'affichage du trombinoscope étudiant.
 */

/**
 * Regroupe les événements de planning (FullCalendar) par enseignant.
 * Chaque événement porte la séance complète dans `extendedProps`.
 *
 * @param {Array} events - Événements retournés par useSeances (transformSeanceToEvent)
 * @returns {Array<{ id, nom_complet, grade, departement, matieres: string[] }>}
 */
export function buildTrombinoscope(events = []) {
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
        matieres: new Set(),
      });
    }

    const entry = map.get(id);
    if (module?.libelle) {
      entry.matieres.add(module.libelle);
    }
  });

  return Array.from(map.values())
    .map((entry) => ({
      ...entry,
      matieres: Array.from(entry.matieres).sort((a, b) => a.localeCompare(b)),
    }))
    .sort((a, b) => a.nom_complet.localeCompare(b.nom_complet));
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
