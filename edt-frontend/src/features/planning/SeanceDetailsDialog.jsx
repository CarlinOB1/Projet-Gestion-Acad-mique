/**
 * @file SeanceDetailsDialog.jsx
 * @description Boîte de dialogue en lecture seule affichant le détail complet
 * d'une séance au clic, pour les rôles enseignant et étudiant.
 */
import { Clock, User, Users, BookOpen, CalendarClock } from 'lucide-react';
import {
    Dialog, DialogContent, DialogHeader,
    DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { SEANCE_COLORS, STATUT_COLORS } from '@/lib/constants';
import { formatDate, formatHeure } from '@/lib/utils';

/**
 * @param {{ open: boolean, onClose: Function, seance: Object|null }} props
 */
export default function SeanceDetailsDialog({ open, onClose, seance }) {
    if (!seance) return null;

    const {
        module, enseignant, classe,
        type_seance, statut,
        date_seance, heure_debut, heure_fin,
        date_report, heure_debut_report, heure_fin_report,
    } = seance;

    const typeStyle = SEANCE_COLORS[type_seance] || {
        bg: 'bg-slate-50', text: 'text-slate-900', border: 'border-slate-400',
    };
    const statutStyle = STATUT_COLORS[statut] || {
        bg: 'bg-slate-100', text: 'text-slate-700',
    };

    const estReportee = statut === 'Reportée';

    return (
        <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
            <DialogContent className="sm:max-w-md gap-5">

                <DialogHeader>
                    <div className="flex items-center gap-2 mb-1">
                        <span className={`px-1.5 py-0.5 rounded-sm text-xs font-semibold uppercase tracking-wide ${typeStyle.bg} ${typeStyle.text}`}>
                            {type_seance}
                        </span>
                        <Badge className={`${statutStyle.bg} ${statutStyle.text}`}>
                            {statut}
                        </Badge>
                        {seance.is_mutualise && (
                            <Badge variant="outline" className="border-indigo-200 text-indigo-700 bg-indigo-50 ml-auto">
                                Mutualisée
                            </Badge>
                        )}
                    </div>
                    <DialogTitle className="text-lg">
                        {module?.libelle || 'Séance sans titre'}
                    </DialogTitle>
                    {module?.description && (
                        <DialogDescription>{module.description}</DialogDescription>
                    )}
                </DialogHeader>

                <div className="space-y-3 text-sm">

                    <div className="flex items-start gap-2.5">
                        <Clock className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                        <div>
                            {estReportee ? (
                                <>
                                    <p className="text-muted-foreground line-through">
                                        {formatDate(date_seance)} — {formatHeure(heure_debut)} à {formatHeure(heure_fin)}
                                    </p>
                                    <p className="font-medium text-foreground flex items-center gap-1.5 mt-0.5">
                                        <CalendarClock className="h-3.5 w-3.5 text-amber-600" />
                                        {formatDate(date_report)} — {formatHeure(heure_debut_report)} à {formatHeure(heure_fin_report)}
                                    </p>
                                </>
                            ) : (
                                <p className="font-medium text-foreground">
                                    {formatDate(date_seance)} — {formatHeure(heure_debut)} à {formatHeure(heure_fin)}
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                        <User className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div>
                            <p className="font-medium text-foreground">
                                {enseignant?.nom_complet || 'Enseignant non assigné'}
                            </p>
                            {enseignant?.grade && (
                                <p className="text-xs text-muted-foreground">{enseignant.grade}</p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                        <Users className="h-4 w-4 text-muted-foreground shrink-0" />
                        <p className="font-medium text-foreground">
                            {classe?.libelle || 'Classe non renseignée'}
                        </p>
                    </div>

                    {module?.matiere?.libelle && (
                        <div className="flex items-center gap-2.5">
                            <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                            <p className="text-foreground">{module.matiere.libelle}</p>
                        </div>
                    )}

                </div>

            </DialogContent>
        </Dialog>
    );
}