/**
 * src/features/academique/ClassesPage.jsx
 * Page de gestion des classes — CRUD, filtre semestre, passage de semestre.
 */
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, ArrowRightCircle, GraduationCap, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';
import DataTable from '@/components/shared/DataTable';
import FormModal from '@/components/shared/FormModal';
import {
  getClasses, createClasse, updateClasse, removeClasse, passerSemestre,
  getSemestres, getParcours, getFilieres,
  getAnnees, // CORRECTION : import ajouté
} from '@/api/academique';

export default function ClassesPage() {
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

  const columns = [
    { key: 'libelle',  label: 'Nom de la classe' },
    { key: 'parcours', label: 'Parcours',  render: (row) => row.parcours?.libelle || '-' },
    { key: 'filiere',  label: 'Filière/Code',   render: (row) => row.filiere?.libelle || (row.code ? <Badge variant="outline">{row.code}</Badge> : '-') },
    { key: 'semestre', label: 'Semestre',  render: (row) => <Badge variant="secondary">{row.semestre?.libelle || '-'}</Badge> },
    { key: 'annee',    label: 'Année',     render: (row) => row.annee?.libelle    || '-' },
    {
      key: 'actions_custom',
      label: 'Avancement',
      render: (row) => (
        <Button variant="outline" size="sm"
          className="text-primary hover:text-primary hover:bg-primary/5 gap-1.5"
          onClick={() => { setActiveClasseForTransition(row); setIsPasserSemestreOpen(true); }}>
          <ArrowRightCircle className="h-4 w-4" />
          Passer semestre
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-lg hidden sm:block">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Classes</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Gérez les promotions et orchestrez les passages de semestres.
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
          <Button onClick={() => { setEditingClasse(null); setIsCrudModalOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Ajouter une classe
          </Button>
        </div>
      </div>

      <DataTable
        columns={columns} data={classes}
        isLoading={isLoading} isError={isError}
        onEdit={(row) => { setEditingClasse(row); setIsCrudModalOpen(true); }}
        onDelete={(row) => deleteMutation.mutate(row.id)}
        emptyMessage="Aucune classe pour ce filtre."
      />

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