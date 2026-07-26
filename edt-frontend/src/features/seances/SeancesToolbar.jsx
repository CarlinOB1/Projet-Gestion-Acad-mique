/**
 * @file SeancesToolbar.jsx
 * @description Barre d'outils épurée pour la liste des séances :
 * recherche + un seul bouton "Filtres" (Popover) + chip semestre + compteur.
 */
import { useMemo } from 'react';
import { Search, SlidersHorizontal, Download, Plus, X } from 'lucide-react';
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

const ALL = '__all__';

export default function SeancesToolbar({
  search,
  onSearchChange,

  semestres = [],
  selectedSemestreId,
  onSemestreChange,

  classes = [],
  enseignants = [],

  filters,
  onFiltersChange,

  resultCount = 0,
  onExportCsv,
  allExpanded = true,
  onToggleExpandAll,
  onCreateClick,
}) {
  const activeCount = useMemo(() => {
    return ['classeId', 'enseignantId', 'statut', 'type', 'dateDebut', 'dateFin']
      .filter((key) => Boolean(filters?.[key])).length;
  }, [filters]);

  const patch = (key, value) =>
    onFiltersChange({ ...filters, [key]: value === ALL ? '' : value });

  const resetFilters = () =>
    onFiltersChange({
      classeId: '', enseignantId: '', statut: '', type: '',
      dateDebut: '', dateFin: '',
    });

  return (
    <div className="bg-card rounded-xl border border-border/60 p-4 space-y-3">

      {/* Ligne 1 : recherche + filtres + actions */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Rechercher un module ou un enseignant..."
            className="pl-8"
          />
        </div>

        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="gap-1.5 shrink-0">
              <SlidersHorizontal className="h-4 w-4" />
              Filtres
              {activeCount > 0 && (
                <Badge className="ml-1 h-4 min-w-4 px-1 text-[10px]">{activeCount}</Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-80 space-y-4">
            <div className="space-y-2">
              <Label>Classe</Label>
              <Select
                value={filters.classeId || ALL}
                onValueChange={(v) => patch('classeId', v)}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Toutes les classes</SelectItem>
                  {classes.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>{c.libelle}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Enseignant</Label>
              <Select
                value={filters.enseignantId || ALL}
                onValueChange={(v) => patch('enseignantId', v)}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Tous les enseignants</SelectItem>
                  {enseignants.map((e) => (
                    <SelectItem key={e.profil_id} value={String(e.profil_id)}>
                      {e.nom_complet}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Statut</Label>
                <Select
                  value={filters.statut || ALL}
                  onValueChange={(v) => patch('statut', v)}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>Tous</SelectItem>
                    {Object.values(STATUT_SEANCE).map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={filters.type || ALL}
                  onValueChange={(v) => patch('type', v)}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>Tous</SelectItem>
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
                  value={filters.dateDebut || ''}
                  onChange={(e) => patch('dateDebut', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Au</Label>
                <Input
                  type="date"
                  value={filters.dateFin || ''}
                  onChange={(e) => patch('dateFin', e.target.value)}
                />
              </div>
            </div>

            {activeCount > 0 && (
              <Button variant="ghost" size="sm" className="w-full" onClick={resetFilters}>
                <X className="h-3.5 w-3.5 mr-1.5" />
                Réinitialiser les filtres
              </Button>
            )}
          </PopoverContent>
        </Popover>

        {onExportCsv && (
          <Button variant="outline" size="icon" onClick={onExportCsv} aria-label="Exporter en CSV">
            <Download className="h-4 w-4" />
          </Button>
        )}

        {onCreateClick && (
          <Button onClick={onCreateClick} className="gap-1.5 shrink-0">
            <Plus className="h-4 w-4" />
            Nouvelle séance
          </Button>
        )}
      </div>

      {/* Ligne 2 : chip semestre */}
      <div className="flex items-center gap-2">
        <Select value={selectedSemestreId ? String(selectedSemestreId) : ''} onValueChange={onSemestreChange}>
          <SelectTrigger className="h-7 rounded-full bg-primary/10 border-none text-primary font-medium px-3 w-auto">
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
      </div>

      {/* Ligne 3 : compteur + déplier/replier */}
      <div className="flex items-center justify-between border-t border-border pt-3 text-sm text-muted-foreground">
        <span>{resultCount} séance{resultCount !== 1 ? 's' : ''} affichée{resultCount !== 1 ? 's' : ''}</span>
        {onToggleExpandAll && (
          <button
            type="button"
            className="text-primary font-medium hover:underline"
            onClick={() => onToggleExpandAll(!allExpanded)}
          >
            {allExpanded ? 'Tout replier' : 'Tout déplier'}
          </button>
        )}
      </div>
    </div>
  );
}