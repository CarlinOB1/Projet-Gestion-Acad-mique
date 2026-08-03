/**
 * @file seanceTableColumns.js
 * @description Définition centralisée des colonnes DataTable pour l'affichage
 * des séances dans la Liste des séances (groupées par classe/jour).
 */
import { CalendarClock, Pencil, CalendarCog, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SEANCE_COLORS, STATUT_COLORS } from '@/lib/constants';
import { formatHeure, getDureeLabel } from '@/lib/utils';

/**
 * Construit la liste des colonnes pour le DataTable des séances.
 *
 * @param {{
 *   onEdit: (seance: Object) => void,
 *   onReport: (seance: Object) => void,
 *   onDelete: (seance: Object) => void,
 * }} handlers
 * @returns {Array<Object>} Colonnes compatibles avec le composant DataTable existant.
 */
export const getSeanceColumns = ({ onEdit, onReport, onDelete }) => [
    {
        key: 'horaire',
        label: 'Horaire',
        render: (row) => (
            <div className="flex flex-col leading-tight">
                <span className="font-medium text-foreground">
                    {formatHeure(row.heure_debut)} → {formatHeure(row.heure_fin)}
                </span>
                <span className="text-xs text-muted-foreground">
                    {getDureeLabel(row.heure_debut, row.heure_fin)}
                </span>
            </div>
        ),
    },
    {
        key: 'module',
        label: 'Module',
        render: (row) => (
            <div className="flex items-center gap-1.5">
                <span>{row.module?.libelle || 'Sans module'}</span>
            </div>
        ),
    },
    {
        key: 'enseignant',
        label: 'Enseignant',
        render: (row) => row.enseignant?.nom_complet || 'Non assigné',
    },
    {
        key: 'type_seance',
        label: 'Type',
        render: (row) => {
            const c = SEANCE_COLORS[row.type_seance] || {};
            return (
                <Badge className={`${c.bg} ${c.text} ${c.border}`}>
                    {row.type_seance}
                </Badge>
            );
        },
    },
    {
        key: 'statut',
        label: 'Statut',
        render: (row) => {
            const c = STATUT_COLORS[row.statut] || {};
            return (
                <Badge className={`${c.bg} ${c.text} ${c.border} gap-1`}>
                    {row.statut === 'Reportée' && <CalendarClock className="h-3 w-3" />}
                    {row.statut}
                </Badge>
            );
        },
    },
    {
        key: 'actions_custom',
        label: '',
        render: (row) => (
            <div className="flex items-center justify-end gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(row)}
                >
                    <Pencil className="h-4 w-4 mr-1.5" />
                    Modifier
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onReport(row)}
                >
                    <CalendarCog className="h-4 w-4 mr-1.5" />
                    Reporter
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={() => onDelete(row)}
                >
                    <Trash2 className="h-4 w-4 mr-1.5" />
                    Supprimer
                </Button>
            </div>
        ),
    },
];