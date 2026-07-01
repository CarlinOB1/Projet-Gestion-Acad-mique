/**
 * @file PlanningPage.jsx
 * @description Page planning — semestre, filtres, grille, actions responsable,
 * détail de séance en lecture seule pour enseignant/étudiant.
 */
import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import useAuthStore from '@/store/authStore';
import { useSeances } from '@/hooks/useSeances';
import { useDeleteSeance } from '@/hooks/useSeanceMutations';
import apiClient from '@/api/client';
import { ROLES } from '@/lib/constants';
import { applyPlanningFilters, getEnseignantsDisponibles, FILTRES_VIDES } from '@/lib/planningFilters';
import PlanningGrid from './PlanningGrid';
import PlanningFilters from './PlanningFilters';
import SeanceDetailsDialog from './SeanceDetailsDialog';
import SeanceDrawer from '@/features/seances/SeanceDrawer';
import ReportDrawer from '@/features/seances/ReportDrawer';
import { Button } from '@/components/ui/button';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover';

export default function PlanningPage() {
  const role = useAuthStore((state) => state.user?.role);

  const [selectedSemestreId, setSelectedSemestreId] = useState(null);
  const [isSeanceDrawerOpen, setIsSeanceDrawerOpen] = useState(false);
  const [selectedSeance, setSelectedSeance] = useState(null);
  const [isReportDrawerOpen, setIsReportDrawerOpen] = useState(false);
  const [seanceToReport, setSeanceToReport] = useState(null);
  const [popoverAnchor, setPopoverAnchor] = useState(null);
  const [filters, setFilters] = useState(FILTRES_VIDES);
  const [detailsSeance, setDetailsSeance] = useState(null); // ← nouveau

  const deleteSeanceMutation = useDeleteSeance();

  const { data: semestres = [], isLoading: isLoadingSemestres, isError: isErrorSemestres } =
    useQuery({
      queryKey: ['semestres'],
      queryFn: async () => (await apiClient.get('/semestres/')).data,
      staleTime: 1000 * 60 * 60,
    });

  useEffect(() => {
    if (semestres.length > 0 && !selectedSemestreId) {
      const actif = semestres.find((s) => s.annee?.statut === 'active');
      setSelectedSemestreId(String(actif ? actif.id : semestres[0].id));
    }
  }, [semestres, selectedSemestreId]);

  const handleSemestreChange = (value) => {
    setSelectedSemestreId(value);
    setFilters(FILTRES_VIDES);
  };

  const { events, isLoading: isLoadingSeances, isError: isErrorSeances } =
    useSeances({ role, filters: { semestre_id: selectedSemestreId } });

  const enseignantsDisponibles = useMemo(
    () => getEnseignantsDisponibles(events),
    [events]
  );

  const filteredEvents = useMemo(
    () => applyPlanningFilters(events, filters),
    [events, filters]
  );

  const isLoading = isLoadingSemestres || isLoadingSeances;
  const isError = isErrorSemestres || isErrorSeances;

  // CORRECTION : responsable garde le popover d'actions,
  // enseignant/étudiant obtiennent désormais le détail en lecture seule.
  const handleEventClick = (eventInfo) => {
    const seance = {
      id: eventInfo.event.id,
      ...eventInfo.event.extendedProps,
    };

    if (role === ROLES.RESPONSABLE) {
      setPopoverAnchor({
        x: eventInfo.jsEvent.clientX,
        y: eventInfo.jsEvent.clientY,
        seance,
      });
      return;
    }

    setDetailsSeance(seance);
  };

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto relative">

      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Planning</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Consultez les emplois du temps des cours.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          {role === ROLES.RESPONSABLE && (
            <Button
              onClick={() => { setSelectedSeance(null); setIsSeanceDrawerOpen(true); }}
              className="flex items-center gap-2 justify-center"
            >
              <Plus className="h-4 w-4" />
              Nouvelle séance
            </Button>
          )}
          <Select
            value={selectedSemestreId ? String(selectedSemestreId) : ''}
            onValueChange={handleSemestreChange}
            disabled={isLoadingSemestres || semestres.length === 0}
          >
            <SelectTrigger className="w-full sm:w-[280px] bg-background">
              <SelectValue placeholder="Chargement des semestres..." />
            </SelectTrigger>
            <SelectContent align="end">
              {semestres.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.libelle} — {s.annee?.libelle || 'Année inconnue'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>

      <PlanningFilters
        filters={filters}
        onChange={setFilters}
        enseignants={enseignantsDisponibles}
        showEnseignantFilter={role !== ROLES.ENSEIGNANT}
      />

      {!isLoading && !isError && events.length > 0 && filteredEvents.length !== events.length && (
        <p className="text-xs text-muted-foreground -mt-3">
          {filteredEvents.length} séance{filteredEvents.length > 1 ? 's' : ''} affichée{filteredEvents.length > 1 ? 's' : ''} sur {events.length}
        </p>
      )}

      <main className="bg-card rounded-xl border border-border/60 p-4 shadow-sm">
        <PlanningGrid
          events={filteredEvents}
          isLoading={isLoading}
          isError={isError}
          onEventClick={handleEventClick}
        />
      </main>

      {/* Menu contextuel responsable (actions) */}
      {popoverAnchor && (
        <div
          className="fixed pointer-events-none z-50"
          style={{ top: popoverAnchor.y, left: popoverAnchor.x }}
        >
          <Popover open onOpenChange={(o) => !o && setPopoverAnchor(null)}>
            <PopoverTrigger asChild>
              <div className="w-0 h-0" />
            </PopoverTrigger>
            <PopoverContent className="w-40 p-1 flex flex-col pointer-events-auto" align="start">
              <Button variant="ghost" className="justify-start h-9 px-2 text-sm font-normal"
                onClick={() => {
                  setSelectedSeance(popoverAnchor.seance);
                  setIsSeanceDrawerOpen(true);
                  setPopoverAnchor(null);
                }}>
                Modifier
              </Button>
              <Button variant="ghost" className="justify-start h-9 px-2 text-sm font-normal"
                onClick={() => {
                  setSeanceToReport(popoverAnchor.seance);
                  setIsReportDrawerOpen(true);
                  setPopoverAnchor(null);
                }}>
                Reporter
              </Button>
              <Button variant="ghost"
                className="justify-start h-9 px-2 text-sm font-normal text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => {
                  if (window.confirm('Voulez-vous vraiment supprimer cette séance ?')) {
                    deleteSeanceMutation.mutate(popoverAnchor.seance.id);
                  }
                  setPopoverAnchor(null);
                }}>
                Supprimer
              </Button>
            </PopoverContent>
          </Popover>
        </div>
      )}

      {/* Détail en lecture seule — enseignant / étudiant */}
      <SeanceDetailsDialog
        open={!!detailsSeance}
        onClose={() => setDetailsSeance(null)}
        seance={detailsSeance}
      />

      <SeanceDrawer
        open={isSeanceDrawerOpen}
        onClose={() => { setIsSeanceDrawerOpen(false); setSelectedSeance(null); }}
        semestreId={selectedSemestreId}
        seance={selectedSeance}
      />
      <ReportDrawer
        open={isReportDrawerOpen}
        onClose={() => { setIsReportDrawerOpen(false); setSeanceToReport(null); }}
        seance={seanceToReport}
      />
    </div>
  );
}