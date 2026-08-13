/**
 * @file planningFilters.js
 * @description Filtrage côté client des événements de planning (recherche texte,
 * type de séance, enseignant, statut) + dérivation des options disponibles.
 */

/**
 * Filtre une liste d'événements FullCalendar selon des critères combinés.
 * @param {Array} events
 * @param {{ search?: string, typeSeance?: string, enseignantId?: string, classeId?: string, statut?: string }} filters
 * @returns {Array}
 */
export function applyPlanningFilters(events = [], filters = {}) {
    const { search = '', typeSeance = '', enseignantId = '', classeId = '', statut = '' } = filters;
    const searchLower = search.trim().toLowerCase();

    return events.filter((event) => {
        const seance = event.extendedProps || {};

        if (searchLower) {
            const libelle = seance.module?.libelle?.toLowerCase() || '';
            if (!libelle.includes(searchLower)) return false;
        }

        if (typeSeance && seance.type_seance !== typeSeance) return false;

        if (enseignantId && String(seance.enseignant?.profil_id) !== String(enseignantId)) {
            return false;
        }

        if (classeId && String(seance.classe?.id) !== String(classeId)) {
            return false;
        }

        if (statut && seance.statut !== statut) return false;

        return true;
    });
}

/**
 * Dérive la liste des enseignants distincts présents dans les événements,
 * pour peupler dynamiquement le select.
 * @param {Array} events
 * @returns {Array<{ id, nom_complet }>}
 */
export function getEnseignantsDisponibles(events = []) {
    const map = new Map();
    events.forEach((event) => {
        const enseignant = event.extendedProps?.enseignant;
        if (enseignant?.profil_id && !map.has(enseignant.profil_id)) {
            map.set(enseignant.profil_id, {
                id: enseignant.profil_id,
                nom_complet: enseignant.nom_complet || 'Enseignant',
            });
        }
    });
    return Array.from(map.values()).sort((a, b) => a.nom_complet.localeCompare(b.nom_complet));
}

/**
 * Dérive la liste des classes distinctes présentes dans les événements.
 * @param {Array} events
 * @returns {Array<{ id, libelle, filiere }>}
 */
export function getClassesDisponibles(events = []) {
    const map = new Map();
    events.forEach((event) => {
        const classe = event.extendedProps?.classe;
        if (classe?.id && !map.has(classe.id)) {
            map.set(classe.id, {
                id: classe.id,
                libelle: classe.libelle || classe.code || `Classe ${classe.id}`,
                filiere_id: classe.filiere?.id,
                filiere_libelle: classe.filiere?.libelle,
            });
        }
    });
    return Array.from(map.values()).sort((a, b) => a.libelle.localeCompare(b.libelle));
}

export const FILTRES_VIDES = {
    search: '',
    typeSeance: '',
    enseignantId: '',
    classeId: '',
    statut: '',
};

export function aDesFiltresActifs(filters) {
    return Object.values(filters).some((v) => v !== '');
}