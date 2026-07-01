/**
 * @file planningFilters.js
 * @description Filtrage client des événements de planning (FullCalendar) et
 * dérivation des listes d'options disponibles (enseignants) pour peupler
 * dynamiquement les filtres, sans appel réseau supplémentaire.
 */

export const DEFAULT_CRITERIA = {
    search: '',
    typeSeance: 'all',
    enseignantId: 'all',
    statut: 'all',
};

/**
 * Filtre une liste d'événements selon des critères combinés.
 * Un critère vide ou "all" est ignoré.
 *
 * @param {Array} events
 * @param {{ search?: string, typeSeance?: string, enseignantId?: string, statut?: string }} criteria
 * @returns {Array}
 */
export function filterPlanningEvents(events = [], criteria = DEFAULT_CRITERIA) {
    const { search = '', typeSeance = 'all', enseignantId = 'all', statut = 'all' } = criteria;
    const normalizedSearch = search.trim().toLowerCase();

    return events.filter((event) => {
        const seance = event?.extendedProps || {};

        if (normalizedSearch) {
            const libelle = seance.module?.libelle?.toLowerCase() || '';
            if (!libelle.includes(normalizedSearch)) return false;
        }

        if (typeSeance !== 'all' && seance.type_seance !== typeSeance) {
            return false;
        }

        if (
            enseignantId !== 'all' &&
            String(seance.enseignant?.profil_id) !== String(enseignantId)
        ) {
            return false;
        }

        if (statut !== 'all' && seance.statut !== statut) {
            return false;
        }

        return true;
    });
}

/**
 * Dérive la liste des enseignants distincts présents dans les événements,
 * pour peupler le select "Enseignant" sans appel réseau supplémentaire.
 *
 * @param {Array} events
 * @returns {Array<{ id, nom_complet }>}
 */
export function getEnseignantsFromEvents(events = []) {
    const map = new Map();

    events.forEach((event) => {
        const enseignant = event?.extendedProps?.enseignant;
        if (!enseignant?.profil_id) return;
        if (!map.has(enseignant.profil_id)) {
            map.set(enseignant.profil_id, {
                id: enseignant.profil_id,
                nom_complet: enseignant.nom_complet || 'Enseignant',
            });
        }
    });

    return Array.from(map.values()).sort((a, b) =>
        a.nom_complet.localeCompare(b.nom_complet)
    );
}