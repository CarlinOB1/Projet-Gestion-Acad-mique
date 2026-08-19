/**
 * src/features/academique/ClassesPage.jsx
 * Vue accordéon : une carte par classe, clic pour dérouler la liste des étudiants.
 */
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  GraduationCap, ChevronDown, ChevronUp, Users, ArrowRightCircle,
  CheckCircle2, Plus, UserX, UserCheck, School,
} from 'lucide-react';
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
import { STATUT_COLORS } from '@/lib/constants';

// ── Sous-composant : ligne étudiant ──────────────────────────────────────────
function EtudiantRow({ etudiant, onStatut, readOnly = false }) {
  const statut = etudiant.profil?.statut ?? 'actif';
  const initiale = etudiant.profil?.user?.last_name?.[0] ?? etudiant.matricule?.[0] ?? '?';
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
        <Badge variant={statut === 'actif' ? 'outline' : 'destructive'} className="text-xs">
          {statut}
        </Badge>
        {!readOnly && (
          <Button
            variant="ghost" size="icon" className="h-7 w-7"
            title={statut === 'actif' ? 'Suspendre' : 'Réactiver'}
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
  const [isStatutDrawerOpen, setIsStatutDrawerOpen] = useState(false);
  const [etudiantForStatut, setEtudiantForStatut] = useState(null);

  const { data: etudiants = [], isLoading } = useQuery({
    queryKey: ['etudiants', 'classe', classe.id],
    queryFn: () => getEtudiants({ classe_id: classe.id }),
    enabled: open,
    staleTime: 1000 * 30,
  });

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-muted/30 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <div>
            <p className="font-semibold text-foreground">{classe.libelle}</p>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-xs text-muted-foreground">{classe.filiere?.libelle || classe.code || '—'}</span>
              <span className="text-muted-foreground/40 text-xs">·</span>
              <Badge variant="secondary" className="text-xs py-0">{classe.semestre?.libelle}</Badge>
              <span className="text-muted-foreground/40 text-xs">·</span>
              <span className="text-xs text-muted-foreground">{classe.annee?.libelle}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Users className="h-3.5 w-3.5" />
            <span>{classe.nombre_etudiants ?? 0} Étudiant{(classe.nombre_etudiants ?? 0) !== 1 ? 's' : ''}</span>
          </div>
          {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-border/60">
          {isLoading && (
            <div className="py-6 flex items-center justify-center">
              <div className="animate-pulse text-sm text-muted-foreground">Chargement des étudiants…</div>
            </div>
          )}
          {!isLoading && etudiants.length === 0 && (
            <div className="py-6 text-center text-sm text-muted-foreground">Aucun étudiant dans cette classe.</div>
          )}
          {!isLoading && etudiants.length > 0 && (
            <div className="divide-y divide-border/40 px-2 py-1">
              {etudiants.map((et) => (
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

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-lg hidden sm:block">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Classes & Étudiants</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Gérez les classes et la liste des étudiants de votre département.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Select value={selectedSemestreId} onValueChange={setSelectedSemestreId}>
            <SelectTrigger className="w-[200px] bg-background">
              <SelectValue placeholder="Filtrer par semestre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les semestres</SelectItem>
              {semestres.map((s) => (
                <SelectItem key={s.id} value={s.id.toString()}>{s.libelle}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

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