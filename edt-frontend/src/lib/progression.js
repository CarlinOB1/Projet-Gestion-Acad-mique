/**
 * @file progression.js
 * @description Dérive la progression pédagogique (heures faites / heures max)
 * de chaque module à partir des séances déjà chargées côté planning.
 */

/**
 * Regroupe les événements de planning par module et calcule leur progression.
 * @param {Array} events - Événements FullCalendar (extendedProps = séance complète)
 * @returns {Array<{
 *   id, libelle, matiere, credits,
 *   heuresMax, heuresConsommees, heuresRestantes,
 *   pourcentage, statutAvancement
 * }>}
 */
export function buildProgression(events = []) {
    const map = new Map();

    events.forEach((event) => {
        const module = event?.extendedProps?.module;
        if (!module || !module.id) return;
        if (map.has(module.id)) return; // déjà traité — les valeurs viennent du serializer, pas besoin de cumul

        const heuresMax = Number(module.heures_max) || 0;
        const heuresConsommees = Number(module.heures_consommees) || 0;
        const heuresRestantes = Number(module.heures_restantes) || 0;

        const pourcentage =
            heuresMax > 0
                ? Math.min(100, Math.round((heuresConsommees / heuresMax) * 100))
                : 0;

        map.set(module.id, {
            id: module.id,
            libelle: module.libelle,
            matiere: module.matiere?.libelle || "",
            credits: module.credits,
            heuresMax,
            heuresConsommees,
            heuresRestantes,
            pourcentage,
            statutAvancement: getStatutAvancement(pourcentage),
        });
    });

    return Array.from(map.values()).sort((a, b) =>
        a.libelle.localeCompare(b.libelle),
    );
}

/**
 * Catégorise l'avancement d'un module pour le code couleur.
 * @param {number} pourcentage
 * @returns {'a_venir'|'en_cours'|'termine'}
 */
function getStatutAvancement(pourcentage) {
    if (pourcentage <= 0) return "a_venir";
    if (pourcentage >= 100) return "termine";
    return "en_cours";
}

export const AVANCEMENT_STYLES = {
    a_venir: {
        label: "Pas encore commencé",
        barColor: "bg-slate-300 dark:bg-slate-600",
        badge: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    },
    en_cours: {
        label: "En cours",
        barColor: "bg-blue-500",
        badge: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    },
    termine: {
        label: "Terminé",
        barColor: "bg-emerald-500",
        badge:
            "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    },
};
