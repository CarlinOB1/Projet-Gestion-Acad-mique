/**
 * @file ModuleProgressRow.jsx
 * @description Ligne de la liste « Par module » : module, enseignants, crédits,
 * heures faites et planifiées, prochain cours et état. Sur petit écran, les
 * colonnes s'empilent sous le nom du module.
 */
import { Badge } from '@/components/ui/badge';
import { AVANCEMENT_STYLES } from '@/lib/progression';
import { formatJourProche } from '@/lib/creneau';
import { cn, formatCreneau, formatNombreHeures } from '@/lib/utils';
import BarreAvancement from './BarreAvancement';

/** Colonnes partagées par l'en-tête et les lignes (écran moyen et plus). */
export const GRILLE_MODULES =
    'md:grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)_5rem_minmax(0,2.4fr)_7.5rem]';

const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;

/** Ce qui vient ensuite pour ce module, en une phrase. */
function texteSuite({ prochaine, heuresFaites, nbAnnulees }) {
    let texte;
    if (prochaine) {
        const quand = `${formatJourProche(prochaine.date)} · ${formatCreneau(prochaine.debut, prochaine.fin)}`;
        const precisions = [
            prochaine.seance?.type_seance,
            prochaine.seance?.statut === 'Reportée' && 'reporté',
        ].filter(Boolean).join(', ');
        const type = precisions ? ` (${precisions})` : '';
        texte = `${heuresFaites > 0 ? 'Prochain cours' : 'Premier cours'} : ${quand}${type}`;
    } else {
        texte = heuresFaites > 0 ? 'Aucun autre cours prévu' : "Aucun cours prévu pour l'instant";
    }
    if (nbAnnulees > 0) texte += ` · ${pluriel(nbAnnulees, 'cours annulé')}`;
    return texte;
}

/**
 * @param {{ module: Object }} props
 */
export default function ModuleProgressRow({ module }) {
    const {
        libelle, credits, types, enseignants,
        heuresMax, heuresFaites, heuresPlanifiees,
        pourcentage, pourcentagePlanifie, statutAvancement,
    } = module;

    const style = AVANCEMENT_STYLES[statutAvancement];
    const nbCredits = Number(credits) || 0;

    return (
        <li
            className={cn(
                'grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 px-4 py-4 sm:px-5 md:items-center',
                GRILLE_MODULES,
            )}
        >
            <div className="min-w-0">
                <h3 className="font-semibold text-foreground text-pretty leading-snug">{libelle}</h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                    <span className="md:hidden">{pluriel(nbCredits, 'crédit')}{types.length > 0 && ' · '}</span>
                    {types.join(' · ')}
                </p>
            </div>

            <ul className="col-span-2 flex flex-wrap gap-x-3 text-xs text-muted-foreground md:col-span-1 md:block md:space-y-0.5 md:text-sm">
                {enseignants.map((nom) => (
                    <li key={nom} className="md:truncate">{nom}</li>
                ))}
            </ul>

            <p className="hidden tabular-nums text-foreground md:block">{pluriel(nbCredits, 'crédit')}</p>

            <div className="col-span-2 space-y-1.5 md:col-span-1">
                <div className="flex items-baseline justify-between gap-2 text-xs text-muted-foreground tabular-nums">
                    <span>
                        <span className="font-semibold text-foreground">{formatNombreHeures(heuresFaites)}</span>
                        {' '}faites sur {formatNombreHeures(heuresMax)}
                    </span>
                    <span>{pourcentage} %</span>
                </div>
                <BarreAvancement
                    faites={pourcentage}
                    planifiees={pourcentagePlanifie}
                    label={`Avancement de ${libelle}`}
                    valeur={`${formatNombreHeures(heuresFaites)} faites et ${formatNombreHeures(heuresPlanifiees)} planifiées sur ${formatNombreHeures(heuresMax)}`}
                />
                <p className="text-xs text-muted-foreground text-pretty">{texteSuite(module)}</p>
            </div>

            <div className="col-start-2 row-start-1 md:col-start-auto md:row-start-auto">
                <Badge className={style.badge}>{style.label}</Badge>
            </div>
        </li>
    );
}
