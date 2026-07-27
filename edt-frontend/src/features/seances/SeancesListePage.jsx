/**
 * @file SeancesListePage.jsx
 * @description Page "Liste des séances" — vue exhaustive filtrable, groupée
 * par classe puis par jour, avec actions modifier/reporter/supprimer.
 */
import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getSeances } from '@/api/seances';
import { getSemestres, getClasses } from '@/api/academique';
import { getEnseignants } from '@/api/acteurs';
import { useDeleteSeance } from '@/hooks/useSeanceMutations';
import { useSeancesGrouped } from '@/hooks/useSeancesGrouped';
import SeancesFiltersBar from './SeancesFiltersBar';
import ClasseGroupSection from './ClasseGroupSection';
import SeanceDrawer from './SeanceDrawer';
import ReportDrawer from './ReportDrawer';
import { Button } from '@/components/ui/button';
import { useSeanceConflits } from '@/hooks/useSeanceConflits';
import { exportToCsv } from '@/lib/exportCsv';
import { formatDate, formatHeure } from '@/lib/utils';
import { Plus, ChevronsDown, ChevronsUp, Download } from 'lucide-react';

const DEFAULT_FILTERS = {
    semestreId: '',
    classeId: 'all',
    enseignantId: 'all',
    statut: 'all',
    typeSeance: 'all',
    dateDebut: '',
    dateFin: '',
};

/** Construit les query params API à partir des filtres (ignore les valeurs "all"/vides). */
const buildApiParams = (filters) => {
    const params = {};
    if (filters.semestreId) params.semestre_id = filters.semestreId;
    if (filters.classeId !== 'all') params.classe_id = filters.classeId;
    if (filters.enseignantId !== 'all') params.enseignant_id = filters.enseignantId;
    if (filters.statut !== 'all') params.statut = filters.statut;
    if (filters.dateDebut) params.date_debut = filters.dateDebut;
    if (filters.dateFin) params.date_fin = filters.dateFin;
    return params;
};

export default function SeancesListePage() {
    const [filters, setFilters] = useState(DEFAULT_FILTERS);
    const [searchTerm, setSearchTerm] = useState('');
    const [openClasseIds, setOpenClasseIds] = useState(new Set());

    const [seanceDrawerOpen, setSeanceDrawerOpen] = useState(false);
    const [selectedSeance, setSelectedSeance] = useState(null);
    const [reportDrawerOpen, setReportDrawerOpen] = useState(false);
    const [seanceToReport, setSeanceToReport] = useState(null);

    const deleteSeanceMutation = useDeleteSeance();

    // ── Données de référence pour les filtres ────────────────────────────────
    const { data: semestres = [] } = useQuery({
        queryKey: ['semestres'],
        queryFn: getSemestres,
        staleTime: 1000 * 60 * 60,
    });

    const { data: classes = [] } = useQuery({
        queryKey: ['classes'],
        queryFn: () => getClasses(),
    });

    const { data: enseignants = [] } = useQuery({
        queryKey: ['enseignants'],
        queryFn: () => getEnseignants(),
    });

    // ── Sélection automatique du semestre actif au premier chargement ───────
    useEffect(() => {
        if (semestres.length > 0 && !filters.semestreId) {
            const actif = semestres.find((s) => s.annee?.statut === 'active');
            setFilters((prev) => ({
                ...prev,
                semestreId: String(actif ? actif.id : semestres[0].id),
            }));
        }
    }, [semestres, filters.semestreId]);

    // ── Séances filtrées côté serveur ────────────────────────────────────────
    const apiParams = useMemo(() => buildApiParams(filters), [filters]);

    const { data: seances = [], isLoading, isError } = useQuery({
        queryKey: ['seances', 'liste', apiParams],
        queryFn: () => getSeances(apiParams),
        enabled: !!filters.semestreId,
    });

    const { conflitsIds } = useSeanceConflits(filters.semestreId);

    // ── Filtrage texte libre côté client ─────────────────────────────────────
    const seancesFiltrees = useMemo(() => {
        let result = seances;

        if (filters.typeSeance !== 'all') {
            result = result.filter((s) => s.type_seance === filters.typeSeance);
        }

        if (searchTerm.trim()) {
            const term = searchTerm.trim().toLowerCase();
            result = result.filter((s) =>
                s.module?.libelle?.toLowerCase().includes(term) ||
                s.enseignant?.nom_complet?.toLowerCase().includes(term)
            );
        }

        return result;
    }, [seances, filters.typeSeance, searchTerm]);

    const { classes: classesGroupees } = useSeancesGrouped(seancesFiltrees);

    const hasActiveFilters =
        filters.classeId !== 'all' ||
        filters.enseignantId !== 'all' ||
        filters.statut !== 'all' ||
        filters.typeSeance !== 'all' ||
        !!filters.dateDebut ||
        !!filters.dateFin ||
        !!searchTerm.trim();

    // ── Handlers filtres ──────────────────────────────────────────────────────
    const handleFilterChange = (key, value) =>
        setFilters((prev) => ({ ...prev, [key]: value }));

    const handleResetFilters = () => {
        setFilters((prev) => ({ ...DEFAULT_FILTERS, semestreId: prev.semestreId }));
        setSearchTerm('');
    };

    // ── Handlers déplier/replier ──────────────────────────────────────────────
    const toggleClasse = (classeId) => {
        setOpenClasseIds((prev) => {
            const next = new Set(prev);
            if (next.has(classeId)) next.delete(classeId);
            else next.add(classeId);
            return next;
        });
    };

    const handleDeplierTout = () =>
        setOpenClasseIds(new Set(classesGroupees.map((c) => c.classeId)));

    const handleReplierTout = () => setOpenClasseIds(new Set());

    // ── Handlers actions séance ───────────────────────────────────────────────
    const handleEdit = (seance) => {
        setSelectedSeance(seance);
        setSeanceDrawerOpen(true);
    };

    const handleReport = (seance) => {
        setSeanceToReport(seance);
        setReportDrawerOpen(true);
    };

    const handleDelete = (seance) => {
        if (window.confirm('Voulez-vous vraiment supprimer cette séance ?')) {
            deleteSeanceMutation.mutate(seance.id);
        }
    };

    const handleExportCsv = () => {
        const columns = [
            { key: 'classe', label: 'Classe', accessor: (s) => s.classe?.libelle },
            { key: 'date', label: 'Date', accessor: (s) => formatDate(s.date_seance) },
            { key: 'debut', label: 'Début', accessor: (s) => formatHeure(s.heure_debut) },
            { key: 'fin', label: 'Fin', accessor: (s) => formatHeure(s.heure_fin) },
            { key: 'module', label: 'Module', accessor: (s) => s.module?.libelle },
            { key: 'enseignant', label: 'Enseignant', accessor: (s) => s.enseignant?.nom_complet },
            { key: 'type', label: 'Type', accessor: (s) => s.type_seance },
            { key: 'statut', label: 'Statut', accessor: (s) => s.statut },
        ];
        exportToCsv('seances_export', seancesFiltrees, columns);
    };

    return (
        <div className="space-y-6 w-full max-w-7xl mx-auto">

            <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-foreground">
                        Liste des séances
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        Consultez et gérez l'ensemble des séances planifiées, classe par classe.
                    </p>
                </div>
                <Button
                    onClick={() => { setSelectedSeance(null); setSeanceDrawerOpen(true); }}
                    className="flex items-center gap-2 justify-center"
                >
                    <Plus className="h-4 w-4" />
                    Nouvelle séance
                </Button>
            </header>

            <SeancesFiltersBar
                filters={filters}
                onFilterChange={handleFilterChange}
                onReset={handleResetFilters}
                hasActiveFilters={hasActiveFilters}
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                semestres={semestres}
                classes={classes}
                enseignants={enseignants}
            />

            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    {seancesFiltrees.length} séance{seancesFiltrees.length > 1 ? 's' : ''} affichée{seancesFiltrees.length > 1 ? 's' : ''}
                </p>
                <div className="flex items-center gap-2">
                    {seancesFiltrees.length > 0 && (
                        <Button variant="outline" size="sm" onClick={handleExportCsv}>
                            <Download className="h-4 w-4 mr-1.5" />
                            Exporter CSV
                        </Button>
                    )}
                    {classesGroupees.length > 0 && (
                        <>
                            <Button variant="ghost" size="sm" onClick={handleDeplierTout}>
                                <ChevronsDown className="h-4 w-4 mr-1.5" />
                                Tout déplier
                            </Button>
                            <Button variant="ghost" size="sm" onClick={handleReplierTout}>
                                <ChevronsUp className="h-4 w-4 mr-1.5" />
                                Tout replier
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {isLoading && (
                <div className="w-full h-40 bg-muted/40 animate-pulse rounded-lg border border-border/60 flex items-center justify-center">
                    <span className="text-sm text-muted-foreground font-medium">
                        Chargement des séances...
                    </span>
                </div>
            )}

            {isError && (
                <div className="w-full flex flex-col items-center justify-center gap-2 border border-destructive/20 bg-destructive/5 rounded-lg p-6 text-center">
                    <p className="text-sm text-destructive font-medium">
                        Impossible de charger les séances.
                    </p>
                </div>
            )}

            {!isLoading && !isError && classesGroupees.length === 0 && (
                <div className="w-full h-32 flex items-center justify-center text-sm text-muted-foreground">
                    Aucune séance ne correspond à ces critères.
                </div>
            )}

            {!isLoading && !isError && (
                <div className="space-y-3">
                    {classesGroupees.map((groupe) => (
                        <ClasseGroupSection
                            key={groupe.classeId}
                            classeId={groupe.classeId}
                            libelle={groupe.libelle}
                            totalSeances={groupe.totalSeances}
                            jours={groupe.jours}
                            isOpen={openClasseIds.has(groupe.classeId)}
                            onToggle={toggleClasse}
                            onEdit={handleEdit}
                            onReport={handleReport}
                            onDelete={handleDelete}
                            conflitsIds={conflitsIds}
                        />
                    ))}
                </div>
            )}

            <SeanceDrawer
                open={seanceDrawerOpen}
                onClose={() => { setSeanceDrawerOpen(false); setSelectedSeance(null); }}
                semestreId={filters.semestreId}
                seance={selectedSeance}
            />
            <ReportDrawer
                open={reportDrawerOpen}
                onClose={() => { setReportDrawerOpen(false); setSeanceToReport(null); }}
                seance={seanceToReport}
            />
        </div>
    );
}