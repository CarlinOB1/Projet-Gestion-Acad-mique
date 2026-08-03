/**
 * @file PlanningFilters.jsx
 * @description Barre de filtres du planning — recherche texte, type de séance,
 * enseignant (masqué pour le rôle enseignant) et statut.
 */
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
    Select, SelectContent, SelectItem,
    SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { TYPE_SEANCE, STATUT_SEANCE } from '@/lib/constants';
import { aDesFiltresActifs } from '@/lib/planningFilters';

const SENTINEL_TOUS = '__tous__';

/**
 * @param {{
 *   filters: Object,
 *   onChange: (filters: Object) => void,
 *   showEnseignantFilter?: boolean,
 *   semesterSelect?: React.ReactNode,
 * }} props
 */
export default function PlanningFilters({
    filters,
    onChange,
    enseignants = [],
    showEnseignantFilter = true,
    semesterSelect = null,
}) {
    const updateField = (field, value) => {
        onChange({ ...filters, [field]: value === SENTINEL_TOUS ? '' : value });
    };

    const handleReset = () => {
        onChange({ search: '', typeSeance: '', enseignantId: '', statut: '' });
    };

    const filtresActifs = aDesFiltresActifs(filters);

    return (
        <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-3 bg-muted/40 border border-border/60 rounded-lg p-3">
            {semesterSelect && (
                <>
                    {semesterSelect}
                    <div className="w-px h-6 bg-border mx-1 hidden sm:block" />
                </>
            )}

            <div className="relative flex-1 min-w-[180px]">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                    value={filters.search}
                    onChange={(e) => updateField('search', e.target.value)}
                    placeholder="Rechercher un module..."
                    className="pl-8 bg-background"
                />
            </div>

            <Select
                value={filters.typeSeance || SENTINEL_TOUS}
                onValueChange={(v) => updateField('typeSeance', v)}
            >
                <SelectTrigger className="w-full sm:w-[130px] bg-background">
                    <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value={SENTINEL_TOUS}>Tous types</SelectItem>
                    {Object.values(TYPE_SEANCE).map((type) => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                    ))}
                </SelectContent>
            </Select>

            {showEnseignantFilter && (
                <Select
                    value={filters.enseignantId || SENTINEL_TOUS}
                    onValueChange={(v) => updateField('enseignantId', v)}
                >
                    <SelectTrigger className="w-full sm:w-[200px] bg-background">
                        <SelectValue placeholder="Enseignant" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={SENTINEL_TOUS}>Tous les enseignants</SelectItem>
                        {enseignants.map((e) => (
                            <SelectItem key={e.id} value={String(e.id)}>{e.nom_complet}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            )}

            <Select
                value={filters.statut || SENTINEL_TOUS}
                onValueChange={(v) => updateField('statut', v)}
            >
                <SelectTrigger className="w-full sm:w-[150px] bg-background">
                    <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value={SENTINEL_TOUS}>Tous statuts</SelectItem>
                    {Object.values(STATUT_SEANCE).map((statut) => (
                        <SelectItem key={statut} value={statut}>{statut}</SelectItem>
                    ))}
                </SelectContent>
            </Select>

            {filtresActifs && (
                <Button variant="ghost" size="sm" onClick={handleReset} className="gap-1.5 text-muted-foreground">
                    <X className="h-3.5 w-3.5" />
                    Réinitialiser
                </Button>
            )}
        </div>
    );
}