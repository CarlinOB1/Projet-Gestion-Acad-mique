/**
 * @file SeancesFiltersBar.jsx
 * @description Barre d'outils épurée : recherche + un seul bouton "Filtres"
 * (Popover) + chip semestre + ligne compteur/actions (CSV, déplier/replier).
 */
import { useMemo } from 'react';
import {
    Search, SlidersHorizontal, X,
    ChevronsDown, ChevronsUp,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover';
import {
    Select, SelectContent, SelectItem,
    SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { STATUT_SEANCE, TYPE_SEANCE } from '@/lib/constants';

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
    showEnseignantFilter = true,
}) {
    const activeFilterCount = useMemo(() => {
        return ['classeId', 'enseignantId', 'statut', 'typeSeance']
            .filter((key) => filters?.[key] && filters[key] !== 'all').length
            + (filters?.dateDebut ? 1 : 0)
            + (filters?.dateFin ? 1 : 0);
    }, [filters]);

    return (
        <div className="bg-card rounded-xl border border-border/60 p-4 space-y-3">

            {/* Ligne 1 : recherche + semestre + filtres */}
            <div className="flex items-center gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.target.value)}
                        placeholder="Rechercher un module ou un enseignant..."
                        className="pl-8"
                    />
                </div>

                <Select value={filters.semestreId} onValueChange={(v) => onFilterChange('semestreId', v)}>
                    <SelectTrigger className="h-9 rounded-full bg-primary/10 border-none text-primary font-medium px-4 w-auto">
                        <SelectValue placeholder="Sélectionner un semestre" />
                    </SelectTrigger>
                    <SelectContent>
                        {semestres.map((s) => (
                            <SelectItem key={s.id} value={String(s.id)}>
                                {s.libelle} — {s.annee?.libelle || 'Année inconnue'}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="outline" className="gap-1.5 shrink-0">
                            <SlidersHorizontal className="h-4 w-4" />
                            Filtres
                            {activeFilterCount > 0 && (
                                <Badge className="ml-1 h-4 min-w-4 px-1 text-[10px]">{activeFilterCount}</Badge>
                            )}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent align="end" className="w-80 space-y-4">
                        <div className="space-y-2">
                            <Label>Classe</Label>
                            <Select value={filters.classeId} onValueChange={(v) => onFilterChange('classeId', v)}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Toutes les classes</SelectItem>
                                    {classes.map((c) => (
                                        <SelectItem key={c.id} value={String(c.id)}>{c.libelle}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {showEnseignantFilter && (
                            <div className="space-y-2">
                                <Label>Enseignant</Label>
                                <Select value={filters.enseignantId} onValueChange={(v) => onFilterChange('enseignantId', v)}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Tous les enseignants</SelectItem>
                                        {enseignants.map((e) => (
                                            <SelectItem key={e.profil_id} value={String(e.profil_id)}>
                                                {e.nom_complet}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <Label>Statut</Label>
                                <Select value={filters.statut} onValueChange={(v) => onFilterChange('statut', v)}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Tous</SelectItem>
                                        {Object.values(STATUT_SEANCE).map((s) => (
                                            <SelectItem key={s} value={s}>{s}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Type</Label>
                                <Select value={filters.typeSeance} onValueChange={(v) => onFilterChange('typeSeance', v)}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Tous</SelectItem>
                                        {Object.values(TYPE_SEANCE).map((t) => (
                                            <SelectItem key={t} value={t}>{t}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <Label>Du</Label>
                                <Input
                                    type="date"
                                    value={filters.dateDebut}
                                    onChange={(e) => onFilterChange('dateDebut', e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Au</Label>
                                <Input
                                    type="date"
                                    value={filters.dateFin}
                                    onChange={(e) => onFilterChange('dateFin', e.target.value)}
                                />
                            </div>
                        </div>

                        {hasActiveFilters && (
                            <Button variant="ghost" size="sm" className="w-full" onClick={onReset}>
                                <X className="h-3.5 w-3.5 mr-1.5" />
                                Réinitialiser les filtres
                            </Button>
                        )}
                    </PopoverContent>
                </Popover>
            </div>
        </div>
    );
}