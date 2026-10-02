/**
 * @file BarreAvancement.jsx
 * @description Barre à deux niveaux : heures déjà faites (plein) devant les
 * heures planifiées (clair), sur le volume prévu du module ou du semestre.
 */
import { cn } from '@/lib/utils';

/**
 * @param {{ faites: number, planifiees?: number, label: string, valeur: string, className?: string }} props
 *   `faites` et `planifiees` en pourcentage du volume prévu ; `valeur` est lu
 *   par les lecteurs d'écran à la place du pourcentage.
 */
export default function BarreAvancement({ faites, planifiees = 0, label, valeur, className }) {
    return (
        <div
            role="progressbar"
            aria-label={label}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={faites}
            aria-valuetext={valeur}
            className={cn('relative h-2 w-full overflow-hidden rounded-full bg-muted', className)}
        >
            <div
                className="absolute inset-y-0 left-0 rounded-full bg-primary/25"
                style={{ width: `${Math.max(planifiees, faites)}%` }}
            />
            <div
                className="absolute inset-y-0 left-0 rounded-full bg-primary"
                style={{ width: `${faites}%` }}
            />
        </div>
    );
}

/** Légende des deux niveaux de la barre. */
export function LegendeAvancement({ className }) {
    return (
        <div className={cn('flex items-center gap-3 text-xs text-muted-foreground', className)} aria-hidden="true">
            <span className="inline-flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-primary" />
                faites
            </span>
            <span className="inline-flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-primary/25" />
                planifiées
            </span>
        </div>
    );
}
