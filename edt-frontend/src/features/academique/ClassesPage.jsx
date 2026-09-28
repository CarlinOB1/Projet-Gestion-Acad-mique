/**
 * src/features/academique/ClassesPage.jsx
 * Vue accordéon : une carte par classe, clic pour dérouler la liste des étudiants.
 */
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  GraduationCap, ChevronDown, ChevronUp, Users, ArrowRightCircle,
  CheckCircle2, Plus, UserX, UserCheck, School, Search,
} from 'lucide-react';
import PageHeader from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';
import FormModal from '@/components/shared/FormModal';
import StatutDrawer from '@/features/acteurs/StatutDrawer';
import {
  getClasses, createClasse, updateClasse, removeClasse, passerSemestre,
  getSemestres, getParcours, getFilieres, getAnnees,
} from '@/api/academique';
import { getEtudiants } from '@/api/acteurs';
import { STATUT_COLORS, STATUT_LABELS } from '@/lib/constants';
import useAuthStore from '@/store/authStore';

// ── Sous-composant : ligne étudiant ──────────────────────────────────────────
function EtudiantRow({ etudiant, onStatut, readOnly = false }) {
  const statut = etudiant.profil?.statut ?? 'actif';
  const initiale = etudiant.profil?.user?.last_name?.[0] ?? etudiant.matricule?.[0] ?? '?';
  const user = useAuthStore((state) => state.user);
  const isChefDepartement = user?.role === 'chef_departement';
  
  return (
    <div className="flex items-center justify-between px-4 py-2.5 hover:bg-muted/40 transition-colors rounded-md">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs font-bold uppercase shrink-0">
          {initiale}
        </div>
        <div>
          <p className="text-sm font-medium text-foreground leading-tight">
            {etudiant.profil?.user?.last_name} {etudiant.profil?.user?.first_name}
          </p>
          <p className="text-xs text-muted-foreground">{etudiant.matricule}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {/* Badge seulement pour un statut inhabituel : « actif » sur chaque
            ligne n'apprenait rien et noyait les vrais cas à repérer. */}
        {statut !== 'actif' && (
          <Badge variant="outline" className={`text-xs ${STATUT_COLORS[statut]?.bg} ${STATUT_COLORS[statut]?.text} ${STATUT_COLORS[statut]?.border}`}>
            {STATUT_LABELS[statut] ?? statut}
          </Badge>
        )}
        {!readOnly && !isChefDepartement && (
          <Button
            variant="ghost" size="icon" className="h-7 w-7"
            title={statut === 'actif' ? 'Suspendre' : 'Réactiver'}
            aria-label={statut === 'actif' ? 'Suspendre' : 'Réactiver'}
            onClick={() => onStatut(etudiant)}
          >
            {statut === 'actif'
              ? <UserX className="h-3.5 w-3.5 text-muted-foreground" />
              : <UserCheck className="h-3.5 w-3.5 text-emerald-500" />}
          </Button>
        )}
      </div>
    </div>
  );
}

// ── Sous-composant : carte classe accordéon ───────────────────────────────────
function ClasseCard({ classe, onPasserSemestre, readOnly = false }) {
  const [open, setOpen] = useState(false);
  const [recherche, setRecherche] = useState('');
  const [isStatutDrawerOpen, setIsStatutDrawerOpen] = useState(false);
  const [etudiantForStatut, setEtudiantForStatut] = useState(null);

  const { data: etudiants = [], isLoading } = useQuery({
    queryKey: ['etudiants', 'classe', classe.id],
    queryFn: () => getEtudiants({ classe_id: classe.id }),
    enabled: open,
    staleTime: 1000 * 30,
  });

  const terme = recherche.trim().toLowerCase();
  const etudiantsAffiches = terme
    ? etudiants.filter((et) =>
        [et.profil?.user?.last_name, et.profil?.user?.first_name, et.matricule]
          .filter(Boolean)
          .some((v) => v.toLowerCase().includes(terme)))
    : etudiants;
  const nb = classe.nombre_etudiants ?? 0;
  const panneauId = `classe-${classe.id}-etudiants`;

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card">
      {/* Le nom de la classe contient déjà filière, semestre et année : la
          sous-ligne qui les répétait a été retirée. */}
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panneauId}
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 px-5 py-4 hover:bg-muted/30 transition-colors text-left"
      >
        <p className="font-semibold text-foreground min-w-0 truncate">{classe.libelle}</p>
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground tabular-nums">
            <Users className="size-3.5" aria-hidden />
            <span>{nb} étudiant{nb !== 1 ? 's' : ''}</span>
          </div>
          {open ? <ChevronUp className="size-4 text-muted-foreground" aria-hidden /> : <ChevronDown className="size-4 text-muted-foreground" aria-hidden />}
        </div>
      </button>

      {open && (
        <div id={panneauId} className="border-t border-border/60">
          {isLoading && (
            <div className="space-y-2 p-4" aria-label="Chargement des étudiants">
              {[1, 2, 3].map((i) => <div key={i} className="h-10 rounded-md bg-muted animate-pulse" />)}
            </div>
          )}
          {!isLoading && etudiants.length === 0 && (
            <div className="py-6 text-center text-sm text-muted-foreground">Aucun étudiant dans cette classe.</div>
          )}
          {!isLoading && etudiants.length > 8 && (
            <div className="px-4 pt-3">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" aria-hidden />
                <Input
                  value={recherche}
                  onChange={(e) => setRecherche(e.target.value)}
                  placeholder="Rechercher un étudiant (nom ou matricule)…"
                  aria-label={`Rechercher un étudiant de ${classe.libelle}`}
                  className="pl-8"
                />
              </div>
            </div>
          )}
          {!isLoading && etudiants.length > 0 && etudiantsAffiches.length === 0 && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Aucun étudiant ne correspond à « {recherche} ».{' '}
              <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => setRecherche('')}>
                Effacer la recherche
              </button>
            </div>
          )}
          {!isLoading && etudiantsAffiches.length > 0 && (
            <div className="divide-y divide-border/40 px-2 py-1">
              {etudiantsAffiches.map((et) => (
                <EtudiantRow
                  key={et.profil?.user?.id ?? et.matricule}
                  etudiant={et}
                  readOnly={readOnly}
                  onStatut={(e) => { setEtudiantForStatut(e); setIsStatutDrawerOpen(true); }}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <StatutDrawer
        open={isStatutDrawerOpen}
        onClose={() => { setIsStatutDrawerOpen(false); setEtudiantForStatut(null); }}
        profil={etudiantForStatut?.profil ?? null}
        queryKeyToInvalidate={['etudiants', 'classe', classe.id]}
      />
    </div>
  );
}

export default function ClassesPage({ readOnly = false }) {
  const queryClient = useQueryClient();

  const [selectedSemestreId,        setSelectedSemestreId]        = useState('all');
  const [isCrudModalOpen,           setIsCrudModalOpen]           = useState(false);
  const [isPasserSemestreOpen,      setIsPasserSemestreOpen]      = useState(false);
  const [editingClasse,             setEditingClasse]             = useState(null);
  const [activeClasseForTransition, setActiveClasseForTransition] = useState(null);
  const [serverError,               setServerError]               = useState(null);
  const [transitionResult,          setTransitionResult]          = useState(null);

  const [parcoursId,      setParcoursId]      = useState('');
  const [filiereId,       setFiliereId]       = useState('none');
  const [code,            setCode]            = useState('');
  const [semestreId,      setSemestreId]      = useState('');
  const [anneeId,         setAnneeId]         = useState('');
  const [targetSemestreId, setTargetSemestreId] = useState('');

  const { data: semestres = [] } = useQuery({
    queryKey: ['semestres'],
    queryFn: getSemestres,
  });

  const { data: parcours = [] } = useQuery({
    queryKey: ['parcours'],
    queryFn: getParcours,
    enabled: isCrudModalOpen,
  });

  const { data: filieres = [] } = useQuery({
    queryKey: ['filieres'],
    queryFn: getFilieres,
    enabled: isCrudModalOpen,
  });

  // CORRECTION : vraies années depuis l'API
  const { data: annees = [] } = useQuery({
    queryKey: ['annees'],
    queryFn: getAnnees,
    enabled: isCrudModalOpen,
  });

  const { data: classes = [], isLoading, isError } = useQuery({
    queryKey: ['classes', selectedSemestreId],
    queryFn: () => {
      const params = selectedSemestreId !== 'all' ? { semestre_id: selectedSemestreId } : {};
      return getClasses(params);
    },
  });

  const createMutation = useMutation({
    mutationFn: createClasse,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['classes'] }); handleCloseCrudModal(); },
    onError: (err) => setServerError(err.message || 'Erreur lors de la création'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateClasse(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['classes'] }); handleCloseCrudModal(); },
    onError: (err) => setServerError(err.message || 'Erreur lors de la modification'),
  });

  const deleteMutation = useMutation({
    mutationFn: removeClasse,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['classes'] }),
  });

  const transitionMutation = useMutation({
    mutationFn: ({ classeId, semestreCibleId }) => passerSemestre(classeId, semestreCibleId),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['classes'] });
      setTransitionResult(response);
    },
    onError: (err) => setServerError(err.message || 'Erreur lors de la transition'),
  });

  useEffect(() => {
    if (isCrudModalOpen) {
      if (editingClasse) {
        setParcoursId(editingClasse.parcours?.id?.toString() ?? '');
        setFiliereId(editingClasse.filiere?.id?.toString()   ?? 'none');
        setCode(editingClasse.code ?? '');
        setSemestreId(editingClasse.semestre?.id?.toString() ?? '');
        setAnneeId(editingClasse.annee?.id?.toString()       ?? '');
      } else {
        setParcoursId('');
        setFiliereId('none');
        setCode('');
        setSemestreId(selectedSemestreId !== 'all' ? selectedSemestreId : '');
        setAnneeId('');
      }
    }
  }, [isCrudModalOpen, editingClasse, selectedSemestreId]);

  const handleCloseCrudModal = () => {
    setIsCrudModalOpen(false);
    setEditingClasse(null);
    setServerError(null);
  };

  const handleClosePasserSemestreModal = () => {
    setIsPasserSemestreOpen(false);
    setActiveClasseForTransition(null);
    setTargetSemestreId('');
    setTransitionResult(null);
    setServerError(null);
  };

  const handleCrudConfirm = () => {
    const payload = {
      parcours_id: parseInt(parcoursId, 10),
      filiere_id:  filiereId && filiereId !== 'none' ? parseInt(filiereId, 10) : null,
      code:        code || null,
      semestre_id: parseInt(semestreId, 10),
      annee_id:    parseInt(anneeId,    10),
    };
    if (editingClasse) {
      updateMutation.mutate({ id: editingClasse.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleTransitionConfirm = () => {
    if (transitionResult) { handleClosePasserSemestreModal(); return; }
    if (activeClasseForTransition && targetSemestreId) {
      transitionMutation.mutate({
        classeId: activeClasseForTransition.id,
        semestreCibleId: parseInt(targetSemestreId, 10),
      });
    }
  };


  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">

      <PageHeader
        titre="Classes & Étudiants"
        description="Les classes de votre département ; ouvrez-en une pour voir ses étudiants."
      >
        <Select value={selectedSemestreId} onValueChange={setSelectedSemestreId}>
          <SelectTrigger className="w-[200px] bg-background" aria-label="Filtrer par semestre">
            <SelectValue placeholder="Filtrer par semestre" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les semestres</SelectItem>
            {semestres.map((s) => (
              <SelectItem key={s.id} value={s.id.toString()}>{s.libelle}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </PageHeader>

      {/* Liste accordéon */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-muted/40 animate-pulse border border-border" />
          ))}
        </div>
      )}
      {isError && (
        <div className="p-6 text-center text-sm text-destructive border border-destructive/20 rounded-xl bg-destructive/5">
          Impossible de charger les classes.
        </div>
      )}
      {!isLoading && !isError && classes.length === 0 && (
        <div className="py-16 flex flex-col items-center gap-3 text-muted-foreground">
          <School className="h-10 w-10 opacity-30" />
          <p className="text-sm">Aucune classe trouvée pour ce filtre.</p>
        </div>
      )}
      {!isLoading && !isError && classes.length > 0 && (
        <div className="space-y-3">
          {classes.map((classe) => (
            <ClasseCard
              key={classe.id}
              classe={classe}
              readOnly={readOnly}
              onPasserSemestre={(c) => { setActiveClasseForTransition(c); setIsPasserSemestreOpen(true); }}
            />
          ))}
        </div>
      )}


      {/* Modale CRUD */}
      <FormModal
        open={isCrudModalOpen} onClose={handleCloseCrudModal}
        onConfirm={handleCrudConfirm}
        title={editingClasse ? 'Modifier la classe' : 'Ajouter une classe'}
        isPending={createMutation.isPending || updateMutation.isPending}
      >
        <div className="space-y-4">
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20">
              {serverError}
            </div>
          )}
          <div className="space-y-2">
            <Label>Parcours</Label>
            <Select value={parcoursId} onValueChange={setParcoursId}>
              <SelectTrigger><SelectValue placeholder="Sélectionner un parcours" /></SelectTrigger>
              <SelectContent>
                {parcours.map((p) => (
                  <SelectItem key={p.id} value={p.id.toString()}>{p.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Filière (Optionnel)</Label>
            <Select value={filiereId} onValueChange={setFiliereId}>
              <SelectTrigger><SelectValue placeholder="Sélectionner une filière" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Aucune filière</SelectItem>
                {filieres.map((f) => (
                  <SelectItem key={f.id} value={f.id.toString()}>{f.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Code de classe (Ex: MIP, BCG) — Si aucune filière</Label>
            <Input 
              type="text" 
              placeholder="Ex: MIP" 
              value={code} 
              onChange={(e) => setCode(e.target.value)} 
              disabled={filiereId !== 'none'} 
            />
          </div>
          <div className="space-y-2">
            <Label>Semestre</Label>
            <Select value={semestreId} onValueChange={setSemestreId}>
              <SelectTrigger><SelectValue placeholder="Sélectionner un semestre" /></SelectTrigger>
              <SelectContent>
                {semestres.map((s) => (
                  <SelectItem key={s.id} value={s.id.toString()}>{s.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Année académique</Label>
            {/* CORRECTION : vraies années depuis l'API */}
            <Select value={anneeId} onValueChange={setAnneeId}>
              <SelectTrigger><SelectValue placeholder="Sélectionner une année" /></SelectTrigger>
              <SelectContent>
                {annees.map((a) => (
                  <SelectItem key={a.id} value={a.id.toString()}>{a.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </FormModal>

      {/* Modale passer semestre */}
      <FormModal
        open={isPasserSemestreOpen} onClose={handleClosePasserSemestreModal}
        onConfirm={handleTransitionConfirm}
        title="Passer au semestre suivant"
        description={activeClasseForTransition
          ? `Les étudiants actifs de "${activeClasseForTransition.libelle}" seront transférés.`
          : null}
        confirmLabel={transitionResult ? 'Fermer' : 'Confirmer le transfert'}
        isPending={transitionMutation.isPending}
        isDestructive={!transitionResult}
      >
        <div className="space-y-4">
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20">
              {serverError}
            </div>
          )}
          {transitionResult ? (
            <div className="p-4 bg-green-50 dark:bg-green-950/20 text-green-800 dark:text-green-300 rounded-lg border border-green-200 dark:border-green-800 space-y-2">
              <div className="flex items-center gap-2 font-semibold text-sm">
                <CheckCircle2 className="h-5 w-5" />
                Transition terminée
              </div>
              <ul className="list-disc pl-5 text-xs space-y-1">
                {/* CORRECTION : total_passes et total_bloques (noms exacts de l'API) */}
                <li>Étudiant(s) transféré(s) : <strong>{transitionResult.total_passes ?? 0}</strong></li>
                <li>Étudiant(s) bloqué(s) : <strong>{transitionResult.total_bloques ?? 0}</strong></li>
              </ul>
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Semestre cible</Label>
              <Select value={targetSemestreId} onValueChange={setTargetSemestreId}>
                <SelectTrigger><SelectValue placeholder="Sélectionner le semestre cible" /></SelectTrigger>
                <SelectContent>
                  {semestres
                    .filter((s) => s.id !== activeClasseForTransition?.semestre?.id)
                    .map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>{s.libelle}</SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Cette action est irréversible.
              </p>
            </div>
          )}
        </div>
      </FormModal>

    </div>
  );
}