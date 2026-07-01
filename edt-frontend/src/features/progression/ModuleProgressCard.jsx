/**
 * @file ModuleProgressCard.jsx
 * @description Carte affichant la progression d'un module : barre de complétion,
 * heures faites / max, badge de statut.
 */
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AVANCEMENT_STYLES } from '@/lib/progression';

/**
 * @param {{ module: Object }} props
 */
export default function ModuleProgressCard({ module }) {
    const {
        libelle, matiere, credits,
        heuresMax, heuresConsommees,
        pourcentage, statutAvancement,
    } = module;

    const style = AVANCEMENT_STYLES[statutAvancement];

    return (
        <Card>
            <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                    <div>
                        <h3 className="font-semibold text-sm text-foreground leading-snug">
                            {libelle}
                        </h3>
                        {matiere && (
                            <p className="text-xs text-muted-foreground mt-0.5">{matiere}</p>
                        )}
                    </div>
                    <Badge className={`${style.badge} shrink-0`}>{style.label}</Badge>
                </div>

                <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                        <span>{heuresConsommees}h / {heuresMax}h</span>
                        <span>{pourcentage}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all duration-300 ${style.barColor}`}
                            style={{ width: `${pourcentage}%` }}
                        />
                    </div>
                </div>

                {credits != null && (
                    <p className="text-[11px] text-muted-foreground">{credits} crédit{credits > 1 ? 's' : ''}</p>
                )}
            </CardContent>
        </Card>
    );
}