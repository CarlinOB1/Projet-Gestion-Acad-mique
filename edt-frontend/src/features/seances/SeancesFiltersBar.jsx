/**
 * @file SeancesFiltersBar.jsx
 * @description Barre de filtres pour la Liste des séances — semestre, classe,
 * enseignant, statut, type, plage de dates et recherche texte libre.
 */
import { SlidersHorizontal, X, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
    Select, SelectContent, SelectItem,
    SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { STATUT_SEANCE, TYPE_SEANCE } from '@/lib/constants';

/**
 * @param {{
 *   filters: {
 *     semestreId: string,
 *     classeId: string,
 *     enseignantId: string,
 *     statut: string,
 *     typeSeance: string,
 *     dateDebut: string,
 *     dateFin: string,
 *   },
 *   onFilterChange: (key: string, value: string) => void,
 *   onReset: () => void,
 *   hasActiveFilters: boolean,
 *   searchTerm: string,
 *   onSearchChange: (value: string) => void,
 *   semestres: Array<Object>,
 *   classes: Array<Object>,
 *   enseignants: Array<Object>,
 * }} props
 */
export default function SeancesFiltersBar({
    filters,
    onFilterChange,
    onReset,
    hasActiveFilters,
    searchTerm,
    onSearchChange,
    semestres = [],
    classes = [],
    enseignants = [],
}) {
    return (
        <div className="space-y-3 bg-muted/50 p-3 rounded-lg border border-border">
            {/* Ligne 1 : recherche texte libre */}
            <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                    value={searchTerm}
                    onChange={(e) => onSearchChange(e.target.value)}
                    placeholder="Rechercher un module ou un enseignant..."
                    className="pl-8 bg-background"
                />
            </div>

            {/* Ligne 2 : selects de filtrage */}
            <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                    <SlidersHorizontal className="h-4 w-4" />
                </div>

                <Select
                    value={filters.semestreId}
                    onValueChange={(v) => onFilterChange('semestreId', v)}
                >
                    <SelectTrigger className="w-[180px] bg-background h-8">
                        <SelectValue placeholder="Semestre" />
                    </SelectTrigger>
                    <SelectContent>
                        {semestres.map((s) => (
                            <SelectItem key={s.id} value={String(s.id)}>
                                {s.libelle} — {s.annee?.libelle || ''}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={filters.classeId}
                    onValueChange={(v) => onFilterChange('classeId', v)}
                >
                    <SelectTrigger className="w-[180px] bg-background h-8">
                        <SelectValue placeholder="Toutes les classes" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Toutes les classes</SelectItem>
                        {classes.map((c) => (
                            <SelectItem key={c.id} value={String(c.id)}>
                                {c.libelle}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={filters.enseignantId}
                    onValueChange={(v) => onFilterChange('enseignantId', v)}
                >
                    <SelectTrigger className="w-[170px] bg-background h-8">
                        <SelectValue placeholder="Tous les enseignants" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Tous les enseignants</SelectItem>
                        {enseignants.map((e) => (
                            <SelectItem key={e.profil_id} value={String(e.profil_id)}>
                                {e.nom_complet}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={filters.statut}
                    onValueChange={(v) => onFilterChange('statut', v)}
                >
                    <SelectTrigger className="w-[150px] bg-background h-8">
                        <SelectValue placeholder="Tous statuts" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Tous les statuts</SelectItem>
                        {Object.values(STATUT_SEANCE).map((s) => (
                            <SelectItem key={s} value={s}>{s}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={filters.typeSeance}
                    onValueChange={(v) => onFilterChange('typeSeance', v)}
                >
                    <SelectTrigger className="w-[130px] bg-background h-8">
                        <SelectValue placeholder="Tous types" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Tous les types</SelectItem>
                        {Object.values(TYPE_SEANCE).map((t) => (
                            <SelectItem key={t} value={t}>{t}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Input
                    type="date"
                    value={filters.dateDebut}
                    onChange={(e) => onFilterChange('dateDebut', e.target.value)}
                    className="w-[150px] bg-background h-8"
                    aria-label="Date de début"
                />
                <span className="text-xs text-muted-foreground">à</span>
                <Input
                    type="date"
                    value={filters.dateFin}
                    onChange={(e) => onFilterChange('dateFin', e.target.value)}
                    className="w-[150px] bg-background h-8"
                    aria-label="Date de fin"
                />

                {hasActiveFilters && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onReset}
                        className="text-muted-foreground"
                    >
                        <X className="h-3.5 w-3.5 mr-1" />
                        Réinitialiser
                    </Button>
                )}
            </div>
        </div>
    );
}