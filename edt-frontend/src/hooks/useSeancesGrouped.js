/**
 * @file useSeancesGrouped.js
 * @description Hook utilitaire — transforme une liste plate de séances en structure
 * groupée par classe puis par jour, triée pour l'affichage dans SeancesListePage.
 */
import { useMemo } from 'react';

/**
 * Regroupe une liste de séances par classe puis par jour.
 *
 * @param {Array<Object>} seances - Liste plate de séances (format API SeanceSerializer).
 * @returns {{
 *   classes: Array<{
 *     classeId: number,
 *     libelle: string,
 *     totalSeances: number,
 *     jours: Array<{ date: string, seances: Array<Object> }>
 *   }>
 * }}
 */
export const useSeancesGrouped = (seances = []) => {
    return useMemo(() => {
        if (!Array.isArray(seances) || seances.length === 0) {
            return { classes: [] };
        }

        // ── 1. Regroupement par classe ──────────────────────────────────────────
        const classesMap = new Map();

        for (const seance of seances) {
            const classe = seance.classe;
            if (!classe?.id) continue;

            if (!classesMap.has(classe.id)) {
                classesMap.set(classe.id, {
                    classeId: classe.id,
                    libelle: classe.libelle || 'Classe inconnue',
                    joursMap: new Map(),
                });
            }

            const groupeClasse = classesMap.get(classe.id);
            const dateKey = seance.date_seance;

            if (!groupeClasse.joursMap.has(dateKey)) {
                groupeClasse.joursMap.set(dateKey, []);
            }
            groupeClasse.joursMap.get(dateKey).push(seance);
        }

        // ── 2. Tri des jours (croissant) et des séances (par heure_debut) ───────
        const classes = Array.from(classesMap.values())
            .map((groupeClasse) => {
                const jours = Array.from(groupeClasse.joursMap.entries())
                    .map(([date, seancesDuJour]) => ({
                        date,
                        seances: [...seancesDuJour].sort((a, b) =>
                            a.heure_debut.localeCompare(b.heure_debut)
                        ),
                    }))
                    .sort((a, b) => a.date.localeCompare(b.date));

                const totalSeances = jours.reduce(
                    (total, jour) => total + jour.seances.length,
                    0
                );

                return {
                    classeId: groupeClasse.classeId,
                    libelle: groupeClasse.libelle,
                    totalSeances,
                    jours,
                };
            })
            // ── 3. Tri des classes par libellé ─────────────────────────────────────
            .sort((a, b) => a.libelle.localeCompare(b.libelle));

        return { classes };
    }, [seances]);
};