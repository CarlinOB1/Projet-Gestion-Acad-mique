/**
 * @file SeanceDetailsDialog.jsx
 * @description Tiroir (Drawer) en lecture seule affichant le détail complet
 * d'une séance au clic, pour les rôles enseignant et étudiant.
 * Design premium avec code couleur, icônes et sections distinctes.
 */
import { Clock, User, Users, BookOpen, CalendarClock, MapPin, Tag } from 'lucide-react';
import {
    Dialog, DialogContent, DialogHeader,
    DialogTitle,
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
        module, enseignant, classe, salle,
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
    const estAnnulee = statut === 'Annulée';

    // Durée en minutes
    const dureeMs = heure_debut && heure_fin
        ? (() => {
            const [h1, m1] = heure_debut.split(':').map(Number);
            const [h2, m2] = heure_fin.split(':').map(Number);
            return (h2 * 60 + m2) - (h1 * 60 + m1);
        })()
        : null;

    return (
        <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
            <DialogContent className="sm:max-w-[460px] p-0 overflow-hidden gap-0">

                {/* ── Header coloré selon le type ── */}
                <div className={`px-6 pt-6 pb-5 ${typeStyle.bg} border-b border-black/5`}>
                    <div className="flex items-center gap-2 mb-3 flex-wrap">
                        <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-widest ${typeStyle.text} bg-white/50 backdrop-blur-sm`}>
                            {type_seance}
                        </span>
                        <Badge className={`${statutStyle.bg} ${statutStyle.text} border-0`}>
                            {statut}
                        </Badge>
                        {seance.is_mutualise && (
                            <Badge variant="outline" className="border-indigo-200 text-indigo-700 bg-indigo-50 ml-auto">
                                Mutualisée
                            </Badge>
                        )}
                    </div>
                    <DialogHeader>
                        <DialogTitle className={`text-xl font-bold leading-tight ${typeStyle.text} ${estAnnulee ? 'line-through opacity-70' : ''}`}>
                            {module?.libelle || 'Séance sans titre'}
                        </DialogTitle>
                        {module?.matiere?.libelle && (
                            <p className={`text-sm mt-1 opacity-75 ${typeStyle.text}`}>
                                {module.matiere.libelle}
                            </p>
                        )}
                    </DialogHeader>
                </div>

                {/* ── Corps — informations détaillées ── */}
                <div className="px-6 py-5 space-y-4">

                    {/* Date & Heure */}
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/40">
                        <div className="p-2 bg-background rounded-md border border-border/60 shrink-0">
                            <Clock className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="min-w-0">
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                                {estReportee ? 'Reporté au' : 'Date & Heure'}
                            </p>
                            {estReportee ? (
                                <>
                                    <p className="text-sm text-muted-foreground line-through">
                                        {formatDate(date_seance)} · {formatHeure(heure_debut)} – {formatHeure(heure_fin)}
                                    </p>
                                    <p className="text-sm font-semibold text-foreground flex items-center gap-1.5 mt-1">
                                        <CalendarClock className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                                        {formatDate(date_report)} · {formatHeure(heure_debut_report)} – {formatHeure(heure_fin_report)}
                                    </p>
                                </>
                            ) : (
                                <p className="text-sm font-semibold text-foreground">
                                    {formatDate(date_seance)} · {formatHeure(heure_debut)} – {formatHeure(heure_fin)}
                                    {dureeMs && (
                                        <span className="ml-2 text-xs font-normal text-muted-foreground">({dureeMs}min)</span>
                                    )}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Enseignant */}
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/40">
                        <div className="p-2 bg-background rounded-md border border-border/60 shrink-0">
                            <User className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="min-w-0">
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-0.5">Enseignant</p>
                            <p className="text-sm font-semibold text-foreground truncate">
                                {enseignant?.nom_complet || 'Non assigné'}
                            </p>
                            {enseignant?.grade && (
                                <p className="text-xs text-muted-foreground">{enseignant.grade}</p>
                            )}
                        </div>
                    </div>

                    {/* Classe & Salle côte à côte */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/40">
                            <div className="p-2 bg-background rounded-md border border-border/60 shrink-0">
                                <Users className="h-4 w-4 text-blue-500" />
                            </div>
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-0.5">Classe</p>
                                <p className="text-sm font-semibold text-foreground">
                                    {classe?.libelle || classe?.code || 'Non renseignée'}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/40">
                            <div className="p-2 bg-background rounded-md border border-border/60 shrink-0">
                                <MapPin className="h-4 w-4 text-blue-500" />
                            </div>
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-0.5">Salle</p>
                                <p className="text-sm font-semibold text-foreground">
                                    {salle?.libelle || salle?.code || 'Non renseignée'}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Module / Matière si non affiché dans le header */}
                    {module?.code && (
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/40">
                            <div className="p-2 bg-background rounded-md border border-border/60 shrink-0">
                                <Tag className="h-4 w-4 text-blue-500" />
                            </div>
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-0.5">Code module</p>
                                <p className="text-sm font-semibold text-foreground">{module.code}</p>
                            </div>
                        </div>
                    )}

                </div>
            </DialogContent>
        </Dialog>
    );
}