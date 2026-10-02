/**
 * @file progression.js
 * @description Dérive la progression pédagogique (heures faites / heures max)
 * de chaque module à partir des séances déjà chargées côté planning.
 */
import { TYPE_SEANCE } from './constants';
import { creneauEffectif, debutDeSemaine, enDate, prochaineSeance } from './creneau';

const parLibelle = (a, b) => a.localeCompare(b, 'fr');

/**
 * Regroupe les événements de planning par module et calcule leur progression.
 * @param {Array} events - Événements FullCalendar (extendedProps = séance complète)
 * @param {Date} [maintenant]
 * @returns {Array<{
 *   id, libelle, matiere, credits,
 *   heuresMax, heuresFaites, heuresPlanifiees, heuresRestantes,
 *   pourcentage, pourcentagePlanifie, statutAvancement,
 *   enseignants: string[], types: string[], nbAnnulees: number,
 *   prochaine: Object|null
 * }>}
 */
export function buildProgression(events = [], maintenant = new Date()) {
    const map = new Map();

    events.forEach((event) => {
        const seance = event?.extendedProps;
        const module = seance?.module;
        if (!module || !module.id) return;

        if (!map.has(module.id)) {
            // Les heures viennent du serveur et sont les mêmes sur chaque
            // séance du module : on les lit une fois, sans cumul.
            const heuresMax = Number(module.heures_max) || 0;
            const heuresPlanifiees = Number(module.heures_consommees) || 0;
            // La progression se mesure sur les heures deja dispensees. Se baser sur
            // heures_consommees (= tout le volume planifie sur le semestre) afficherait
            // 100 % des la premiere semaine de cours.
            const heuresFaites = module.heures_effectuees !== undefined
                ? Number(module.heures_effectuees) || 0
                : heuresPlanifiees;

            map.set(module.id, {
                id: module.id,
                libelle: module.libelle,
                matiere: module.matiere?.libelle || "",
                credits: module.credits,
                heuresMax,
                heuresFaites,
                heuresPlanifiees,
                heuresRestantes: Number(module.heures_restantes) || 0,
                seances: [],
                enseignants: new Set(),
                types: new Set(),
                nbAnnulees: 0,
            });
        }

        const entry = map.get(module.id);
        entry.seances.push(seance);
        if (seance.enseignant?.nom_complet) entry.enseignants.add(seance.enseignant.nom_complet);
        if (seance.type_seance) entry.types.add(seance.type_seance);
        if (seance.statut === 'Annulée') entry.nbAnnulees += 1;
    });

    return Array.from(map.values())
        .map(({ seances, enseignants, types, ...entry }) => {
            const pourcentage = enPourcentage(entry.heuresFaites, entry.heuresMax);
            return {
                ...entry,
                pourcentage,
                pourcentagePlanifie: enPourcentage(entry.heuresPlanifiees, entry.heuresMax),
                statutAvancement: getStatutAvancement(pourcentage),
                enseignants: Array.from(enseignants).sort(parLibelle),
                types: Object.values(TYPE_SEANCE).filter((type) => types.has(type)),
                prochaine: prochaineSeance(seances, maintenant),
            };
        })
        .sort((a, b) => parLibelle(a.libelle, b.libelle));
}

/**
 * Chiffres du semestre pour le bandeau de la page : avancement global,
 * crédits, modules par état, et cours de la semaine en cours.
 * @param {Array} modules - résultat de buildProgression
 * @param {Array} events - les mêmes événements de planning
 * @param {Date} [maintenant]
 */
export function resumerProgression(modules = [], events = [], maintenant = new Date()) {
    const somme = (cle) => modules.reduce((total, m) => total + (Number(m[cle]) || 0), 0);
    const heuresFaites = somme('heuresFaites');
    const heuresPrevues = somme('heuresMax');

    const parStatut = { a_venir: 0, en_cours: 0, termine: 0 };
    modules.forEach((m) => { parStatut[m.statutAvancement] += 1; });

    const lundi = debutDeSemaine(maintenant);
    const lundiSuivant = new Date(lundi);
    lundiSuivant.setDate(lundi.getDate() + 7);
    let heuresSemaine = 0;
    let seancesSemaine = 0;
    events.forEach((event) => {
        const seance = event?.extendedProps;
        if (!seance || seance.statut === 'Annulée') return;
        const jour = enDate(creneauEffectif(seance).date);
        if (!jour || jour < lundi || jour >= lundiSuivant) return;
        seancesSemaine += 1;
        heuresSemaine += Number(seance.duree_effective) || 0;
    });

    const classe = events[0]?.extendedProps?.classe;
    const semestre = [classe?.semestre?.libelle, classe?.annee?.libelle].filter(Boolean).join(' · ');

    return {
        semestre,
        heuresFaites,
        heuresPrevues,
        pourcentage: enPourcentage(heuresFaites, heuresPrevues),
        credits: somme('credits'),
        nbModules: modules.length,
        parStatut,
        heuresSemaine,
        seancesSemaine,
    };
}

/** Ordres proposés pour la liste des modules (le premier est celui par défaut). */
export const TRIS_PROGRESSION = [
    { cle: 'avancement', label: 'Avancement', comparer: (a, b) => b.pourcentage - a.pourcentage },
    { cle: 'credits', label: 'Crédits', comparer: (a, b) => (Number(b.credits) || 0) - (Number(a.credits) || 0) },
    { cle: 'nom', label: 'Nom', comparer: () => 0 },
];

function enPourcentage(heures, total) {
    return total > 0 ? Math.min(100, Math.round((heures / total) * 100)) : 0;
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
        label: "Pas commencé",
        badge: "bg-muted text-muted-foreground",
    },
    // Couleur de l'application (vert UCCB) : clair en cours, plein une fois terminé.
    en_cours: {
        label: "En cours",
        badge: "bg-primary/10 text-primary",
    },
    termine: {
        label: "Terminé",
        badge: "bg-primary text-primary-foreground",
    },
};
