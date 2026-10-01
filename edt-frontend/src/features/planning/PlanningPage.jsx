import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Plus,
  Printer,
  Pencil,
  CalendarClock,
  Trash2,
  Layers,
  List,
} from '@/components/ui/icons';
import useAuthStore from "@/store/authStore";
import { useSeances } from "@/hooks/useSeances";
import { useDeleteSeance } from "@/hooks/useSeanceMutations";
import { getMonProfil } from "@/api/acteurs";
import apiClient from "@/api/client";
import { ROLES, GESTIONNAIRE_ROLES } from "@/lib/constants";
import {
  applyPlanningFilters,
  getClassesDisponibles,
  FILTRES_VIDES,
} from "@/lib/planningFilters";
import PlanningTableView from "./PlanningTableView";
import PlanningFilters from "./PlanningFilters";
import SeanceDetailsDialog from "./SeanceDetailsDialog";
import SeanceDrawer from "@/features/seances/SeanceDrawer";
import ReportDrawer from "@/features/seances/ReportDrawer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { confirmer } from "@/lib/confirmer";
import { toast } from "@/hooks/use-toast";
import { formatDate, formatCreneau } from "@/lib/utils";
import PageHeader from "@/components/shared/PageHeader";
import { trouverSemestreEnCours } from "@/lib/semestres";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from "@/components/ui/select";

export default function PlanningPage() {
  const role = useAuthStore((state) => state.user?.role);
  const navigate = useNavigate();
  const location = useLocation();

  // Sur /enseignant/planning, le chef doit voir son propre planning
  // (et non le planning global du département)
  const isPersonalPlanningRoute = location.pathname.startsWith(
    "/enseignant/planning",
  );
  const effectiveRole =
    isPersonalPlanningRoute && role !== ROLES.ETUDIANT
      ? ROLES.ENSEIGNANT
      : role;

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
  const [contextualDefaults, setContextualDefaults] = useState(null);
  const [isReportDrawerOpen, setIsReportDrawerOpen] = useState(false);
  const [seanceToReport, setSeanceToReport] = useState(null);
  const [filters, setFilters] = useState(FILTRES_VIDES);
  const [detailsSeance, setDetailsSeance] = useState(null);

  const planningRef = useRef(null);
  const printRef = useRef(null);

  const deleteSeanceMutation = useDeleteSeance();

  const { data: profilEtudiant } = useQuery({
    queryKey: ["mon-profil"],
    queryFn: getMonProfil,
    enabled: effectiveRole === ROLES.ETUDIANT,
  });

  const {
    data: semestres = [],
    isLoading: isLoadingSemestres,
    isError: isErrorSemestres,
  } = useQuery({
    queryKey: ["semestres"],
    queryFn: async () => {
      const response = await apiClient.get("/semestres/");
      return response.data?.results ?? response.data;
    },
    staleTime: 1000 * 60 * 60,
  });
  // Semestre par défaut calculé pendant le rendu, et non posé par un effet :
  // au retour sur la page (semestres déjà en cache), l'effet laissait passer
  // un premier affichage sans semestre ni classe (« Planning Global du
  // Département »).
  // Semestre en cours d'après ses dates : avant, le premier semestre de
  // l'année active, donc encore le S1 en plein S2.
  const semestreEnCours = useMemo(() => trouverSemestreEnCours(semestres), [semestres]);
  const semestreParDefaut = semestreEnCours ? String(semestreEnCours.id) : null;
  const semestreId = selectedSemestreId ?? semestreParDefaut;

  const handleSemestreChange = useCallback((value) => {
    setSelectedSemestreId(value);
    setFilters(FILTRES_VIDES);
  }, []);

  // Auto-navigate whenever the selected semester changes
  const lastJumpedSemestreId = useRef(null);
  useEffect(() => {
    if (!semestreId || !semestres.length) return;
    if (lastJumpedSemestreId.current === semestreId) return;

    const semestre = semestres.find(
      (s) => String(s.id) === String(semestreId),
    );
    if (!semestre) return;

    lastJumpedSemestreId.current = semestreId;

    const getMondayOf = (d) => {
      const date = new Date(d);
      const day = date.getDay();
      const diff = day === 0 ? -6 : 1 - day;
      date.setDate(date.getDate() + diff);
      date.setHours(0, 0, 0, 0);
      return date;
    };
    // "AAAA-MM-JJ" lu en date locale : new Date("AAAA-MM-JJ") le lirait en
    // UTC et pourrait décaler d'un jour selon le fuseau.
    const parseDateLocale = (s) => {
      if (!s) return null;
      const [y, m, d] = s.split("-").map(Number);
      return new Date(y, m - 1, d);
    };

    const debut = parseDateLocale(semestre.date_debut);
    const fin = parseDateLocale(semestre.date_fin);
    const aujourdhui = new Date();
    aujourdhui.setHours(0, 0, 0, 0);

    // Semestre en cours : on reste sur la semaine d'aujourd'hui. Sauter à la
    // semaine 1 ouvrait le planning sur une semaine vide ("0 h") en plein
    // semestre. Autre semestre (passé ou à venir) : on va à son début.
    const semestreEnCours = debut && fin && debut <= aujourdhui && aujourdhui <= fin;
    if (semestreEnCours) {
      setWeekStart(getMondayOf(aujourdhui));
    } else if (debut) {
      setWeekStart(getMondayOf(debut));
    }
  }, [semestreId, semestres]);

  const {
    events,
    isLoading: isLoadingSeances,
    isError: isErrorSeances,
  } = useSeances({
    role: effectiveRole,
    filters: { semestre_id: semestreId },
    // Sans semestre, la requête partait sans filtre et téléchargeait toutes
    // les séances du département (29 pages), en concurrence avec la vraie
    // requête lancée un instant plus tard avec le semestre.
    enabled: !!semestreId,
  });

  // Récupère toutes les classes du semestre pour les gestionnaires (pour afficher même celles sans séances)
  const { data: allClasses = [], isLoading: isLoadingClasses } = useQuery({
    queryKey: ["classes", { semestre_id: semestreId }],
    queryFn: async () => {
      if (!semestreId) return [];
      const response = await apiClient.get("/classes/", {
        params: { semestre_id: semestreId },
      });
      return response.data?.results ?? response.data;
    },
    enabled: GESTIONNAIRE_ROLES.includes(effectiveRole) && !!semestreId,
  });

  const classesDisponibles = useMemo(() => {
    if (GESTIONNAIRE_ROLES.includes(effectiveRole)) {
      return allClasses
        .map((c) => ({
          id: c.id,
          libelle: c.libelle || c.code || `Classe ${c.id}`,
          filiere_id: c.filiere?.id,
          filiere_libelle: c.filiere?.libelle,
        }))
        .sort((a, b) => a.libelle.localeCompare(b.libelle));
    }
    return getClassesDisponibles(events);
  }, [events, allClasses, effectiveRole]);

  // Un gestionnaire regarde toujours une classe : tant qu'il n'en a pas
  // choisi, c'est la première. Calculé pendant le rendu pour la même raison
  // que le semestre (sinon, un instant, toutes les classes et le titre
  // « Planning Global du Département »).
  const classeParDefaut =
    GESTIONNAIRE_ROLES.includes(effectiveRole) && classesDisponibles.length > 0
      ? String(classesDisponibles[0].id)
      : "";
  const filtres = useMemo(
    () => ({ ...filters, classeId: filters.classeId || classeParDefaut }),
    [filters, classeParDefaut],
  );

  const filteredEvents = useMemo(
    () => applyPlanningFilters(events, filtres),
    [events, filtres],
  );

  const isLoading = isLoadingSemestres || isLoadingSeances || isLoadingClasses;
  const isError = isErrorSemestres || isErrorSeances;

  const semestersByYear = useMemo(() => {
    const groups = {};
    semestres.forEach((s) => {
      const year = s.annee?.libelle || "Année inconnue";
      if (!groups[year]) groups[year] = [];
      groups[year].push(s);
    });
    return groups;
  }, [semestres]);

  // Lecture seule (enseignant, étudiant) : le clic ouvre le détail.
  const handleSeanceClick = (seance) => setDetailsSeance(seance);

  // Gestionnaire : le clic ouvre un menu collé à la carte. Il remplace une
  // fenêtre intermédiaire centrée, loin de la carte, qui assombrissait la page
  // avant d'ouvrir une deuxième fenêtre.
  const supprimerSeance = async (seance) => {
    const ok = await confirmer({
      titre: "Supprimer cette séance ?",
      description: [
        seance?.module?.libelle,
        seance?.date_seance &&
          `${formatDate(seance.date_seance)} · ${formatCreneau(seance.heure_debut, seance.heure_fin)}`,
      ].filter(Boolean).join("\n"),
      libelleConfirmer: "Supprimer",
      destructif: true,
    });
    if (!ok) return;
    deleteSeanceMutation.mutate(seance.id, {
      onSuccess: () => toast({ title: "Séance supprimée" }),
      onError: (err) =>
        toast({
          variant: "destructive",
          title: "La séance n'a pas pu être supprimée",
          description:
            err?.response?.data?.detail ??
            "Réessayez ; si le problème persiste, rechargez la page.",
        }),
    });
  };

  const actionsGestionnaire = [
    {
      libelle: "Modifier",
      icone: Pencil,
      onSelect: (seance) => {
        setSelectedSeance(seance);
        setContextualDefaults(null);
        setIsSeanceDrawerOpen(true);
      },
    },
    {
      libelle: "Reporter",
      icone: CalendarClock,
      onSelect: (seance) => {
        setSeanceToReport(seance);
        setIsReportDrawerOpen(true);
      },
    },
    { libelle: "Supprimer", icone: Trash2, onSelect: supprimerSeance, destructif: true },
  ];
  const actionsSeance = GESTIONNAIRE_ROLES.includes(effectiveRole)
    ? () => actionsGestionnaire
    : undefined;

  const handleEmptyCellClick = ({ date_seance, heure_debut, heure_fin }) => {
    if (!GESTIONNAIRE_ROLES.includes(effectiveRole)) return;
    // La classe est déjà fixée par l'onglet actif ("Classe :" au-dessus du
    // calendrier) : on la retrouve dans allClasses (qui porte l'année,
    // nécessaire pour enregistrer la séance) plutôt que de la refaire choisir
    // dans le formulaire.
    const classeSelectionnee = allClasses.find(
      (c) => String(c.id) === String(filtres.classeId),
    );
    setContextualDefaults({
      date_seance,
      heure_debut,
      heure_fin,
      classe: classeSelectionnee
        ? {
            id: classeSelectionnee.id,
            libelle:
              classeSelectionnee.libelle ||
              classeSelectionnee.code ||
              `Classe ${classeSelectionnee.id}`,
            annee_id: classeSelectionnee.annee?.id,
          }
        : null,
    });
    setSelectedSeance(null);
    setIsSeanceDrawerOpen(true);
  };

  const handleGeneratePDF = async () => {
    const element = printRef.current;
    if (!element) return;

    const html2pdf = (await import("html2pdf.js")).default;

    const semestre = semestres.find(
      (s) => String(s.id) === String(semestreId),
    );
    const rolePrefix =
      role === ROLES.ENSEIGNANT
        ? "enseignant"
        : GESTIONNAIRE_ROLES.includes(role)
          ? "chef"
          : "etudiant";
    // Capture ×3 (≈ 300 dpi sur un A4) en JPEG, PDF compressé : ~600 Ko en
    // 2 s. En PNG ×6 sans compression, le fichier pesait ~80 Mo (11 s).
    const opt = {
      margin: 10,
      filename: `emploi_du_temps_${rolePrefix}_${semestre?.libelle || "planning"}.pdf`,
      image: { type: "jpeg", quality: 0.95 },
      html2canvas: { scale: 3, useCORS: true, logging: false },
      jsPDF: { unit: "mm", format: "a4", orientation: "landscape", compress: true },
    };

    html2pdf().set(opt).from(element).save();
  };

  const selectedClasse = useMemo(
    () =>
      classesDisponibles.find((c) => String(c.id) === String(filtres.classeId)),
    [classesDisponibles, filtres.classeId],
  );

  const pageTitle = useMemo(() => {
    if (effectiveRole === ROLES.ETUDIANT && profilEtudiant?.etudiant?.classe) {
      return `Planning — ${profilEtudiant.etudiant.classe.libelle || profilEtudiant.etudiant.classe.code}`;
    }
    if (effectiveRole === ROLES.ENSEIGNANT && isPersonalPlanningRoute) {
      return "Mon Planning";
    }
    if (selectedClasse) {
      return `Planning — ${selectedClasse.libelle}`;
    }
    if (GESTIONNAIRE_ROLES.includes(effectiveRole)) {
      return `Planning Global du Département`;
    }
    return "Planning";
  }, [effectiveRole, isPersonalPlanningRoute, profilEtudiant, selectedClasse]);

  // Ce qui est déjà dit par le titre n'est pas répété sur chaque carte : la
  // classe sur un planning de classe (ou d'étudiant), l'enseignant sur son
  // propre planning.
  const champsMasques = useMemo(() => {
    if (effectiveRole === ROLES.ENSEIGNANT) return ["enseignant"];
    if (effectiveRole === ROLES.ETUDIANT) return ["classe"];
    if (GESTIONNAIRE_ROLES.includes(effectiveRole) && filtres.classeId) return ["classe"];
    return [];
  }, [effectiveRole, filtres.classeId]);

  return (
    <div className="space-y-4 w-full max-w-7xl mx-auto relative">
      <PageHeader
        titre={pageTitle}
        description={
          isPersonalPlanningRoute
            ? "Votre emploi du temps personnel pour ce semestre."
            : GESTIONNAIRE_ROLES.includes(effectiveRole)
              ? "Cliquez sur une case vide pour ajouter une séance, sur une séance pour la modifier."
              : "Vos cours de la semaine."
        }
      >
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
          <Select
            value={semestreId ? String(semestreId) : ""}
            onValueChange={handleSemestreChange}
            disabled={isLoadingSemestres || semestres.length === 0}
          >
            <SelectTrigger className="w-full sm:w-[260px] bg-background">
              <SelectValue placeholder="Chargement des semestres..." />
            </SelectTrigger>
            <SelectContent align="end">
              {Object.entries(semestersByYear).map(([year, sems]) => (
                <SelectGroup key={year}>
                  <SelectLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    {year}
                  </SelectLabel>
                  {sems.map((s) => {
                    const isActif = semestreEnCours && s.id === semestreEnCours.id;
                    return (
                      <SelectItem key={s.id} value={String(s.id)}>
                        <div className="flex items-center gap-2">
                          <span>{s.libelle}</span>
                          {isActif && (
                            <span
                              className="flex size-2 rounded-full bg-primary"
                              title="Semestre en cours"
                            />
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
            <Button
              variant="outline"
              className="flex-1 sm:flex-none gap-2 bg-background"
              onClick={handleGeneratePDF}
              aria-label="Générer le PDF du planning"
            >
              <Printer className="h-4 w-4 text-muted-foreground" />
              <span className="hidden sm:inline">Générer PDF</span>
            </Button>
            {/* Bouton « Lier au calendrier » retiré : il annonçait un lien iCal
                copié alors que rien n'était copié (aucun point d'accès iCal
                côté serveur). À remettre quand ce flux existera. */}
          </div>
        </div>
      </PageHeader>

      {/* Choix de la classe, recherche et filtres sur une seule barre : empilés,
          ils repoussaient la grille vers 560 px de haut. Le compteur
          « N séances affichées sur M » a été retiré : il comptait tout le
          semestre alors qu'on regarde une semaine. */}
      <PlanningFilters
        filters={filtres}
        onChange={setFilters}
        avant={
          GESTIONNAIRE_ROLES.includes(effectiveRole) &&
          classesDisponibles.length > 0 && (
            <div
              role="group"
              aria-label="Classe affichée"
              className="flex items-center gap-2 overflow-x-auto no-scrollbar min-w-0"
            >
              <Layers className="size-4 shrink-0 text-muted-foreground" aria-hidden />
              {classesDisponibles.map((c) => {
                const isSelected = String(filtres.classeId) === String(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() =>
                      setFilters((f) => ({ ...f, classeId: String(c.id) }))
                    }
                    className={`h-9 px-3 rounded-md text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer ${isSelected
                        ? "bg-primary text-primary-foreground"
                        : "bg-background text-muted-foreground hover:text-foreground border border-border"
                      }`}
                  >
                    {c.libelle}
                  </button>
                );
              })}
            </div>
          )
        }
      />

      <main ref={planningRef}>
        <PlanningTableView
          events={filteredEvents}
          isLoading={isLoading}
          isError={isError}
          masquer={champsMasques}
          onSeanceClick={handleSeanceClick}
          actionsSeance={actionsSeance}
          onEmptyCellClick={
            GESTIONNAIRE_ROLES.includes(effectiveRole) ? handleEmptyCellClick : null
          }
          weekStart={weekStart}
          onWeekChange={setWeekStart}
          semestre={semestres.find(
            (s) => String(s.id) === String(semestreId),
          )}
        />
      </main>

      {/* Détail en lecture seule — enseignant / étudiant */}
      <SeanceDetailsDialog
        open={!!detailsSeance}
        onClose={() => setDetailsSeance(null)}
        seance={detailsSeance}
      />

      {isSeanceDrawerOpen && (
        <SeanceDrawer
          key={`seance-drawer-${selectedSeance?.id ?? "new"}`}
          open
          onClose={() => {
            setIsSeanceDrawerOpen(false);
            setSelectedSeance(null);
            setContextualDefaults(null);
          }}
          semestreId={semestreId}
          seance={selectedSeance}
          contextualDefaults={contextualDefaults}
        />
      )}
      {isReportDrawerOpen && (
        <ReportDrawer
          key={`report-drawer-${seanceToReport?.id ?? "new"}`}
          open
          onClose={() => {
            setIsReportDrawerOpen(false);
            setSeanceToReport(null);
          }}
          seance={seanceToReport}
        />
      )}

      {/* Conteneur caché pour l'impression PDF */}
      <div style={{ position: "absolute", top: "-9999px", left: "-9999px" }}>
        <div ref={printRef}>
          <PlanningTableView
            isPrintMode={true}
            events={filteredEvents}
            weekStart={weekStart}
            semestre={semestres.find(
              (s) => String(s.id) === String(semestreId),
            )}
            title={pageTitle}
            masquer={champsMasques}
          />
        </div>
      </div>
    </div>
  );
}
