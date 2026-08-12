/**
 * @file PlanningPage.jsx
 * @description Page planning — semestre, filtres, grille, actions responsable,
 * détail de séance en lecture seule pour enseignant/étudiant.
 */
import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Printer, Calendar, Pencil, CalendarClock, Trash2 } from 'lucide-react';
import useAuthStore from '@/store/authStore';
import { useSeances } from '@/hooks/useSeances';
import { useDeleteSeance } from '@/hooks/useSeanceMutations';
import { getMonProfil } from '@/api/acteurs';
import apiClient from '@/api/client';
import { ROLES, GESTIONNAIRE_ROLES } from '@/lib/constants';
import { applyPlanningFilters, getEnseignantsDisponibles, FILTRES_VIDES } from '@/lib/planningFilters';
import PlanningTableView from './PlanningTableView';
import PlanningFilters from './PlanningFilters';
import SeanceDetailsDialog from './SeanceDetailsDialog';
import SeanceDrawer from '@/features/seances/SeanceDrawer';
import ReportDrawer from '@/features/seances/ReportDrawer';
import { Button } from '@/components/ui/button';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue, SelectGroup, SelectLabel
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';

export default function PlanningPage() {
  const role = useAuthStore((state) => state.user?.role);

  const [selectedSemestreId, setSelectedSemestreId] = useState(null);
  const [weekStart, setWeekStart] = useState(() => {
    // Start on monday of current week
    const d = new Date();
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    return d;
  });
  const [isSeanceDrawerOpen, setIsSeanceDrawerOpen] = useState(false);
  const [selectedSeance, setSelectedSeance] = useState(null);
  const [isReportDrawerOpen, setIsReportDrawerOpen] = useState(false);
  const [seanceToReport, setSeanceToReport] = useState(null);
  const [filters, setFilters] = useState(FILTRES_VIDES);
  const [detailsSeance, setDetailsSeance] = useState(null);
  const [gestionnaireTarget, setGestionnaireTarget] = useState(null); // dialog actions gestionnaire

  const planningRef = useRef(null);
  const printRef = useRef(null);

  const deleteSeanceMutation = useDeleteSeance();

  const { data: profilEtudiant } = useQuery({
    queryKey: ['mon-profil'],
    queryFn: getMonProfil,
    enabled: role === ROLES.ETUDIANT,
  });

  const { data: semestres = [], isLoading: isLoadingSemestres, isError: isErrorSemestres } =
    useQuery({
      queryKey: ['semestres'],
      queryFn: async () => {
        const response = await apiClient.get('/semestres/');
        return response.data?.results ?? response.data;
      },
      staleTime: 1000 * 60 * 60,
    });
  useEffect(() => {
    if (semestres.length > 0 && !selectedSemestreId) {
      const actif = semestres.find((s) => s.annee?.statut === 'active');
      setSelectedSemestreId(String(actif ? actif.id : semestres[0].id));
    }
  }, [semestres, selectedSemestreId]);

  const handleSemestreChange = useCallback((value) => {
    setSelectedSemestreId(value);
    setFilters(FILTRES_VIDES);
  }, []);

  // Keep a ref to semestres so the navigation effect doesn't depend on it
  const semestresRef = useRef(semestres);
  useEffect(() => { semestresRef.current = semestres; }, [semestres]);

  // Auto-navigate whenever the selected semester changes
  const lastJumpedSemestreId = useRef(null);
  useEffect(() => {
    if (!selectedSemestreId || !semestres.length) return;
    // Only jump if the semester truly changed (not a re-render)
    if (lastJumpedSemestreId.current === selectedSemestreId) return;

    const semestre = semestres.find((s) => String(s.id) === String(selectedSemestreId));
    if (!semestre) return;

    lastJumpedSemestreId.current = selectedSemestreId;

    const debut = semestre.date_debut ? new Date(semestre.date_debut) : null;

    const getMondayOf = (d) => {
      const date = new Date(d);
      const day  = date.getDay();
      const diff = day === 0 ? -6 : 1 - day;
      date.setDate(date.getDate() + diff);
      date.setHours(0, 0, 0, 0);
      return date;
    };

    if (debut) {
      setWeekStart(getMondayOf(debut));
    }
  }, [selectedSemestreId, semestres]);

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

  // Group semesters by year for the UI
  const semestersByYear = useMemo(() => {
    const groups = {};
    semestres.forEach(s => {
      const year = s.annee?.libelle || 'Année inconnue';
      if (!groups[year]) groups[year] = [];
      groups[year].push(s);
    });
    // Optional: Sort years descending if needed, but assuming they come sorted from API
    return groups;
  }, [semestres]);

  const actifSemestre = useMemo(() => {
    return semestres.find((s) => s.annee?.statut === 'active');
  }, [semestres]);

  // Handler unique pour le clic sur une séance (table view)
  const handleSeanceClick = (seance) => {
    if (GESTIONNAIRE_ROLES.includes(role)) {
      setGestionnaireTarget(seance);
      return;
    }
    setDetailsSeance(seance);
  };

  const handleGeneratePDF = async () => {
    const element = printRef.current;
    if (!element) return;

    const html2pdf = (await import('html2pdf.js')).default;

    const semestre = semestres.find((s) => String(s.id) === String(selectedSemestreId));
    const rolePrefix = role === ROLES.ENSEIGNANT ? 'enseignant' : GESTIONNAIRE_ROLES.includes(role) ? 'chef' : 'etudiant';
    const opt = {
      margin: 10,
      filename: `emploi_du_temps_${rolePrefix}_${semestre?.libelle || 'planning'}.pdf`,
      image: { type: 'png' },
      html2canvas: { scale: 6, useCORS: true, logging: false },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
    };

    html2pdf().set(opt).from(element).save();
  };

  const planningTitle = role === ROLES.ETUDIANT && profilEtudiant?.etudiant?.classe
    ? `Emploi du temps — ${profilEtudiant.etudiant.classe.libelle || profilEtudiant.etudiant.classe.code}`
    : 'Emploi du temps';

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto relative">

      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {planningTitle.replace('Emploi du temps', 'Planning')}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Consultez les emplois du temps des cours.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          <Select
            value={selectedSemestreId ? String(selectedSemestreId) : ''}
            onValueChange={handleSemestreChange}
            disabled={isLoadingSemestres || semestres.length === 0}
          >
            <SelectTrigger className="w-full sm:w-[260px] bg-background">
              <SelectValue placeholder="Chargement des semestres..." />
            </SelectTrigger>
            <SelectContent align="end">
              {Object.entries(semestersByYear).map(([year, sems]) => (
                <SelectGroup key={year}>
                  <SelectLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{year}</SelectLabel>
                  {sems.map((s) => {
                    const isActif = actifSemestre && s.id === actifSemestre.id;
                    return (
                      <SelectItem key={s.id} value={String(s.id)}>
                        <div className="flex items-center gap-2">
                          <span>{s.libelle}</span>
                          {isActif && (
                            <span className="flex h-2 w-2 rounded-full bg-emerald-500" title="Semestre en cours" />
                          )}
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectGroup>
              ))}
            </SelectContent>
          </Select>

          <div className="flex gap-2 w-full sm:w-auto">
              <Button variant="outline" className="flex-1 sm:flex-none gap-2 bg-background" onClick={handleGeneratePDF}>
                <Printer className="h-4 w-4" />
                <span className="hidden sm:inline">Générer PDF</span>
              </Button>
              <Button variant="outline" className="flex-1 sm:flex-none gap-2 bg-background" onClick={() => alert("Le lien d'abonnement iCal a été copié dans le presse-papier ! (Fonctionnalité en cours de développement)")}>
                <Calendar className="h-4 w-4" />
                <span className="hidden sm:inline">Lier au calendrier</span>
              </Button>
            </div>
          {GESTIONNAIRE_ROLES.includes(role) && (
            <Button
              onClick={() => { setSelectedSeance(null); setIsSeanceDrawerOpen(true); }}
              className="flex items-center gap-2 justify-center"
            >
              <Plus className="h-4 w-4" />
              Nouvelle séance
            </Button>
          )}
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

      <main ref={planningRef}>
        <PlanningTableView
          events={filteredEvents}
          isLoading={isLoading}
          isError={isError}
          onSeanceClick={handleSeanceClick}
          weekStart={weekStart}
          onWeekChange={setWeekStart}
          semestre={semestres.find((s) => String(s.id) === String(selectedSemestreId))}
        />
      </main>

      {/* Dialog d'actions gestionnaire */}
      <Dialog open={!!gestionnaireTarget} onOpenChange={(o) => !o && setGestionnaireTarget(null)}>
        <DialogContent className="sm:max-w-xs p-0 overflow-hidden gap-0">
          <DialogHeader className="px-5 pt-5 pb-4 border-b border-border">
            <DialogTitle className="text-base">
              {gestionnaireTarget?.module?.libelle || 'Séance'}
            </DialogTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              {gestionnaireTarget?.date_seance} · {gestionnaireTarget?.heure_debut} – {gestionnaireTarget?.heure_fin}
            </p>
          </DialogHeader>
          <div className="flex flex-col p-2 gap-1">
            <Button variant="ghost" className="justify-start gap-3 h-10 px-3 text-sm"
              onClick={() => {
                setSelectedSeance(gestionnaireTarget);
                setIsSeanceDrawerOpen(true);
                setGestionnaireTarget(null);
              }}>
              <Pencil className="h-4 w-4 text-muted-foreground" />
              Modifier
            </Button>
            <Button variant="ghost" className="justify-start gap-3 h-10 px-3 text-sm"
              onClick={() => {
                setSeanceToReport(gestionnaireTarget);
                setIsReportDrawerOpen(true);
                setGestionnaireTarget(null);
              }}>
              <CalendarClock className="h-4 w-4 text-muted-foreground" />
              Reporter
            </Button>
            <Button variant="ghost"
              className="justify-start gap-3 h-10 px-3 text-sm text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => {
                if (window.confirm('Voulez-vous vraiment supprimer cette séance ?')) {
                  deleteSeanceMutation.mutate(gestionnaireTarget.id);
                }
                setGestionnaireTarget(null);
              }}>
              <Trash2 className="h-4 w-4" />
              Supprimer
            </Button>
          </div>
        </DialogContent>
      </Dialog>

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

      {/* Conteneur caché pour l'impression PDF */}
      <div style={{ position: 'absolute', top: '-9999px', left: '-9999px' }}>
        <div ref={printRef}>
          <PlanningTableView 
            isPrintMode={true}
            events={filteredEvents} 
            weekStart={weekStart} 
            semestre={semestres.find((s) => String(s.id) === String(selectedSemestreId))}
            title={planningTitle}
          />
        </div>
      </div>
    </div>
  );
}