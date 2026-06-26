/**
 * @file PlanningPage.jsx
 * @description Page planning — semestre, grille, actions responsable.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import useAuthStore from "@/store/authStore";
import { useSeances } from "@/hooks/useSeances";
import { useDeleteSeance } from "@/hooks/useSeanceMutations";
import apiClient from "@/api/client";
import { ROLES, RESPONSABLE_ROLES } from "@/lib/constants";
import PlanningGrid from "./PlanningGrid";
import SeanceDrawer from "@/features/seances/SeanceDrawer";
import ReportDrawer from "@/features/seances/ReportDrawer";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export default function PlanningPage() {
  const role = useAuthStore((state) => state.user?.role);
  const isResponsable = RESPONSABLE_ROLES.includes(role);

  const [selectedSemestreId, setSelectedSemestreId] = useState(null);
  const [isSeanceDrawerOpen, setIsSeanceDrawerOpen] = useState(false);
  const [selectedSeance, setSelectedSeance] = useState(null);
  const [isReportDrawerOpen, setIsReportDrawerOpen] = useState(false);
  const [seanceToReport, setSeanceToReport] = useState(null);
  const [popoverAnchor, setPopoverAnchor] = useState(null);

  const deleteSeanceMutation = useDeleteSeance();

  const {
    data: semestres = [],
    isLoading: isLoadingSemestres,
    isError: isErrorSemestres,
  } = useQuery({
    queryKey: ["semestres"],
    queryFn: async () => {
      const res = await apiClient.get("/semestres/");
      return res.data?.results ?? res.data;
    }
  });

    useEffect(() => {
    if (semestres.length > 0 && !selectedSemestreId) {
      const actif = semestres.find((s) => s.annee?.statut === "active");
      setSelectedSemestreId(String(actif ? actif.id : semestres[0].id));
    }
  }, [semestres, selectedSemestreId]);

  const {
    events,
    isLoading: isLoadingSeances,
    isError: isErrorSeances,
  } = useSeances({ role, filters: { semestre_id: selectedSemestreId } });

  const isLoading = isLoadingSemestres || isLoadingSeances;
  const isError = isErrorSemestres || isErrorSeances;

  // CORRECTION : extendedProps contient directement la séance (pas extendedProps.seance)
  const handleEventClick = (eventInfo) => {
    if (!isResponsable) return;
    const seance = {
      id: eventInfo.event.id,
      ...eventInfo.event.extendedProps,
    };
    setPopoverAnchor({
      x: eventInfo.jsEvent.clientX,
      y: eventInfo.jsEvent.clientY,
      seance,
    });
  };

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto relative">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Planning
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Consultez les emplois du temps des cours.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          {isResponsable && (
            <Button
              onClick={() => {
                setSelectedSeance(null);
                setIsSeanceDrawerOpen(true);
              }}
              className="flex items-center gap-2 justify-center"
            >
              <Plus className="h-4 w-4" />
              Nouvelle séance
            </Button>
          )}
          <Select
            value={selectedSemestreId ? String(selectedSemestreId) : ""}
            onValueChange={(v) => setSelectedSemestreId(v)}
            disabled={isLoadingSemestres || semestres.length === 0}
          >
            <SelectTrigger className="w-full sm:w-[280px] bg-background">
              <SelectValue placeholder="Chargement des semestres..." />
            </SelectTrigger>
            <SelectContent align="end">
              {semestres.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.libelle} — {s.annee?.libelle || "Année inconnue"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>

      <main className="bg-card rounded-xl border border-border/60 p-4 shadow-sm">
        <PlanningGrid
          events={events}
          isLoading={isLoading}
          isError={isError}
          onEventClick={handleEventClick}
        />
      </main>

      {/* Menu contextuel positionné au clic */}
      {popoverAnchor && (
        <div
          className="fixed pointer-events-none z-50"
          style={{ top: popoverAnchor.y, left: popoverAnchor.x }}
        >
          <Popover open onOpenChange={(o) => !o && setPopoverAnchor(null)}>
            <PopoverTrigger asChild>...</PopoverTrigger>
            <PopoverContent
              className="w-40 p-1 flex flex-col pointer-events-auto"
              align="start"
            >
              <Button
                variant="ghost"
                className="justify-start h-9 px-2 text-sm font-normal"
                onClick={() => {
                  setSelectedSeance(popoverAnchor.seance);
                  setIsSeanceDrawerOpen(true);
                  setPopoverAnchor(null);
                }}
              >
                Modifier
              </Button>
              <Button
                variant="ghost"
                className="justify-start h-9 px-2 text-sm font-normal"
                onClick={() => {
                  setSeanceToReport(popoverAnchor.seance);
                  setIsReportDrawerOpen(true);
                  setPopoverAnchor(null);
                }}
              >
                Reporter
              </Button>
              <Button
                variant="ghost"
                className="justify-start h-9 px-2 text-sm font-normal text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => {
                  if (
                    window.confirm(
                      "Voulez-vous vraiment supprimer cette séance ?",
                    )
                  ) {
                    deleteSeanceMutation.mutate(popoverAnchor.seance.id);
                  }
                  setPopoverAnchor(null);
                }}
              >
                Supprimer
              </Button>
            </PopoverContent>
          </Popover>
        </div>
      )}

      <SeanceDrawer
        open={isSeanceDrawerOpen}
        onClose={() => {
          setIsSeanceDrawerOpen(false);
          setSelectedSeance(null);
        }}
        semestreId={selectedSemestreId}
        seance={selectedSeance}
      />
      <ReportDrawer
        open={isReportDrawerOpen}
        onClose={() => {
          setIsReportDrawerOpen(false);
          setSeanceToReport(null);
        }}
        seance={seanceToReport}
      />
    </div>
  );
}
