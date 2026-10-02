/**
 * src/features/academique/ContenuPedagogiquePage.jsx
 *
 * Page "Contenu Pédagogique" — affiche pour chaque groupe de classe
 * (Parcours + Filière/Code + Année) les modules organisés par semestre.
 *
 * Navigation :
 *   - Liste des classes (ex: "L1 MIP · 2025-2026")
 *   - Les modules de la classe choisie, tous ses semestres sur la même page
 *     (le semestre en cours est signalé)
 *   - CRUD complet sur les modules (ajout / modification / suppression)
 *   - Panel d'affectation des enseignants (Sheet latérale)
 */

import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Users, BookOpen, AlertCircle, Inbox } from '@/components/ui/icons';

// UI primitives
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';

// Composants partagés
import DataTable from '@/components/shared/DataTable';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/badge';
import { trouverSemestreEnCours } from '@/lib/semestres';
import { formatNombreHeures } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';

// Panel d'affectation
import AffectationsPanel from '@/features/affectations/AffectationsPanel';

// API
import {
  getClasses,
  getModules,
  getMatieres,
  getSemestres,
  createModule,
  updateModule,
  removeModule,
} from '@/api/academique';

// Auth
import useAuthStore, { selectIsChefDepartement, selectDepartementId } from '@/store/authStore';

/**
 * Extrait un message lisible depuis une erreur de réponse DRF
 * (ex: {"matiere_id": ["Vous ne pouvez créer ou modifier..."]})
 * plutôt que le générique axios "Request failed with status code 400".
 */
function extractErrorMessage(err, fallback) {
  const detail = err?.response?.data;
  if (detail && typeof detail === 'object') {
    const msg = Object.values(detail).flat().join(' ');
    if (msg) return msg;
  }
  return err?.message || fallback;
}

// -----------------------------------------------------------------
// HELPERS
// -----------------------------------------------------------------

/**
 * Construit une clé unique pour un groupe (Parcours + Filière/Code + Année).
 */
function groupKey(classe) {
  const parcoursId = classe.parcours?.id ?? '';
  const filiereId  = classe.filiere?.id ?? classe.code ?? '';
  const anneeId    = classe.annee?.id ?? '';
  return `${parcoursId}_${filiereId}_${anneeId}`;
}

/**
 * Construit le libellé lisible d'un groupe.
 * Exemple : "L1 MIP · 2025-2026" — même abréviation (L1, L2, M1…) que le nom
 * des classes (« L2 S1 Informatique 2026-2027 ») affiché dans le reste de
 * l'application, au lieu de « Licence 2 ».
 */
function groupLabel(classe) {
  const { type_parcours: type, niveau } = classe.parcours ?? {};
  const parcours    = type && niveau ? `${type.charAt(0).toUpperCase()}${niveau}` : (classe.parcours?.libelle ?? '');
  const identifiant = classe.filiere?.libelle ?? classe.code ?? '';
  const annee       = classe.annee?.libelle ?? '';
  return `${parcours} ${identifiant} · ${annee}`;
}

// -----------------------------------------------------------------
// COMPOSANT : Carte d'un semestre
// -----------------------------------------------------------------

function SemestreCard({ classe, enCours = false, onAddModule, onEditModule, onDeleteModule, onAffecterModule }) {
  const { data: modules = [], isLoading, isError } = useQuery({
    queryKey: ['modules', classe?.id ? `classe-${classe.id}` : 'none'],
    queryFn: () => getModules({ classe_id: classe?.id }),
    enabled: !!classe?.id,
  });

  const totalCredits = modules.reduce((sum, m) => sum + (m.credits || 0), 0);
  const semestreLabel = classe?.semestre?.libelle ?? '—';

  // Colonne « Matière » retirée : elle affichait la même valeur sur chaque
  // ligne et poussait les actions hors de l'écran à 1366 px de large.
  const columns = [
    {
      key: 'libelle',
      label: 'Module',
      render: (row) => <span className="font-medium text-pretty">{row.libelle}</span>,
    },
    {
      key: 'credits',
      label: 'Crédit(s)',
      render: (row) => (
        <span className="text-sm font-semibold tabular-nums">{row.credits}</span>
      ),
    },
    {
      key: 'volume',
      label: 'Heures planifiées',
      render: (row) => {
        const consomme = Number(row.heures_consommees) || 0;
        const max      = Number(row.heures_max) || 1;
        const pct      = Math.min((consomme / max) * 100, 100);
        // Tout planifié = objectif atteint (barre pleine), pas une alerte. Le
        // rouge est réservé à un vrai dépassement du volume du module.
        const barColor = consomme > max ? 'bg-destructive' : 'bg-primary';
        return (
          <div className="flex flex-col gap-1 w-36">
            <div className="flex justify-between text-[11px] text-muted-foreground tabular-nums">
              <span>{formatNombreHeures(consomme)} / {formatNombreHeures(max)}</span>
              <span>{Math.round(pct)} %</span>
            </div>
            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      },
    },
  ];

  if (!classe) {
    return null;
  }

  return (
    <section aria-label={semestreLabel} className="flex-1 flex flex-col">
      {/* En-tête */}
      <div className="py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <h2 className="text-base font-semibold text-foreground">{semestreLabel}</h2>
          {enCours && (
            <Badge className="bg-primary/10 text-primary border-transparent hover:bg-primary/10">En cours</Badge>
          )}
          <span className="text-xs text-muted-foreground tabular-nums">
            {isLoading ? '…' : `${modules.length} module${modules.length > 1 ? 's' : ''}`}
            {' · '}
            {totalCredits} ECTS
          </span>
        </div>
        <Button size="sm" className="gap-1.5 rounded-md" onClick={() => onAddModule(classe)}>
          <Plus className="size-3.5" />
          Ajouter un module
        </Button>
      </div>

      {/* Corps */}
      <div className="flex-1 overflow-hidden">
        {isError ? (
          <div className="flex flex-col items-center justify-center gap-2 p-8 text-destructive">
            <AlertCircle className="h-6 w-6" />
            <p className="text-sm">Erreur lors du chargement.</p>
          </div>
        ) : isLoading ? (
          <div className="space-y-2 p-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 rounded-md bg-muted animate-pulse" />
            ))}
          </div>
        ) : modules.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 p-10 text-muted-foreground">
            <Inbox className="h-8 w-8 opacity-40" />
            <p className="text-sm">Aucun module pour ce semestre.</p>
            <Button
              size="sm"
              className="mt-1 gap-1.5"
              onClick={() => onAddModule(classe)}
            >
              <Plus className="h-3.5 w-3.5" />
              Ajouter le premier module
            </Button>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={modules}
            isLoading={false}
            isError={false}
            onEdit={onEditModule}
            onDelete={(row) => onDeleteModule(row)}
            actionsSupplementaires={[
              { libelle: 'Affecter des enseignants', icone: Users, onClick: onAffecterModule },
            ]}
            actionsEnMenu
            libelleLigne={(row) => row.libelle}
            emptyMessage="Aucun module pour ce semestre."
          />
        )}
      </div>
    </section>
  );
}

// -----------------------------------------------------------------
// COMPOSANT PRINCIPAL
// -----------------------------------------------------------------

export default function ContenuPedagogiquePage() {
  const queryClient = useQueryClient();
  const isChef = useAuthStore(selectIsChefDepartement);
  const departementId = useAuthStore(selectDepartementId);

  // Sélection du groupe de classe
  const [selectedGroupKey, setSelectedGroupKey] = useState('');

  // CRUD
  const [isModalOpen,   setIsModalOpen]   = useState(false);
  const [editingModule, setEditingModule] = useState(null);
  const [targetClasse,  setTargetClasse]  = useState(null);
  const [serverError,   setServerError]   = useState(null);

  // Champs formulaire
  const [libelle,     setLibelle]     = useState('');
  const [matiereId,   setMatiereId]   = useState('');
  const [semestreId,  setSemestreId]  = useState('');
  const [classeId,    setClasseId]    = useState('');
  const [credits,     setCredits]     = useState(1);
  const [description, setDescription] = useState('');

  // Sheet affectation
  const [moduleAffectation, setModuleAffectation] = useState(null);

  // ── Requêtes ──────────────────────────────────────────────

  const { data: classes = [], isLoading: classesLoading } = useQuery({
    queryKey: ['classes'],
    queryFn: () => getClasses(),
  });

  // Un chef de département ne peut créer/modifier des modules que pour les
  // matières de son propre département (règle appliquée côté serveur) : on
  // filtre déjà la liste ici pour ne pas lui proposer un choix qui échouera
  // en 400 à la soumission (ex : matière homonyme dans un autre département).
  const { data: matieres = [] } = useQuery({
    queryKey: ['matieres', isChef ? departementId : 'all'],
    queryFn: () => getMatieres(isChef && departementId ? { departement_id: departementId } : undefined),
    enabled: isModalOpen,
  });

  const { data: semestres = [] } = useQuery({
    queryKey: ['semestres'],
    queryFn: () => getSemestres(),
  });

  // Sert seulement à signaler le semestre en cours : tous les semestres de la
  // classe sont affichés l'un sous l'autre.
  const semestreEnCours = trouverSemestreEnCours(semestres);

  // ── Groupement des classes ─────────────────────────────────

  // Un groupe = même parcours, filière et année : il réunit les classes de
  // chaque semestre (L2 S1 Informatique, L2 S2 Informatique…).
  const groupedClasses = useMemo(() => {
    const map = new Map();
    classes.forEach((c) => {
      const key = groupKey(c);
      if (!map.has(key)) {
        map.set(key, { key, label: groupLabel(c), classes: [] });
      }
      map.get(key).classes.push(c);
    });
    map.forEach((group) => {
      group.classes.sort((a, b) =>
        (a.semestre?.libelle ?? '').localeCompare(b.semestre?.libelle ?? '', 'fr', { numeric: true }));
    });
    return Array.from(map.values());
  }, [classes]);

  // Premier groupe par défaut, calculé pendant le rendu (pas d'effet).
  const selectedGroup =
    groupedClasses.find((g) => g.key === selectedGroupKey) ?? groupedClasses[0] ?? null;

  // ── Mutations ──────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: createModule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      handleCloseModal();
    },
    onError: (err) => setServerError(extractErrorMessage(err, 'Erreur lors de la création du module')),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateModule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      handleCloseModal();
    },
    onError: (err) => setServerError(extractErrorMessage(err, 'Erreur lors de la modification du module')),
  });

  const deleteMutation = useMutation({
    mutationFn: removeModule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      toast({ title: 'Module supprimé' });
    },
    // Sans ce message, un refus du serveur (module déjà planifié…) passait
    // inaperçu : le module restait simplement dans la liste.
    onError: (err) =>
      toast({
        variant: 'destructive',
        title: "Le module n'a pas pu être supprimé",
        description: err?.response?.data?.detail ?? 'Réessayez ; si le problème persiste, rechargez la page.',
      }),
  });

  // ── Gestionnaires ──────────────────────────────────────────

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingModule(null);
    setTargetClasse(null);
    setServerError(null);
  };

  useEffect(() => {
    if (isModalOpen) {
      if (editingModule) {
        setLibelle(editingModule.libelle || '');
        setMatiereId(editingModule.matiere?.id?.toString() || '');
        setSemestreId(editingModule.semestre?.id?.toString() || '');
        setClasseId(editingModule.classe?.id?.toString() || '');
        setCredits(editingModule.credits || 1);
        setDescription(editingModule.description || '');
      } else {
        setLibelle('');
        setMatiereId('');
        setSemestreId(targetClasse?.semestre?.id?.toString() || '');
        setClasseId(targetClasse?.id?.toString() || '');
        setCredits(1);
        setDescription('');
      }
    }
  }, [isModalOpen, editingModule, targetClasse]);

  const handleAddModule = (classe) => {
    setTargetClasse(classe);
    setEditingModule(null);
    setIsModalOpen(true);
  };

  const handleEditModule = (moduleRow) => {
    setEditingModule(moduleRow);
    setTargetClasse(null);
    setIsModalOpen(true);
  };

  const handleDeleteModule = (row) => {
    deleteMutation.mutate(row.id);
  };

  const handleFormSubmit = async () => {
    const payload = {
      libelle,
      matiere_id:  parseInt(matiereId, 10),
      semestre_id: parseInt(semestreId, 10),
      classe_id:   parseInt(classeId, 10) || null,
      credits:     parseInt(credits, 10),
      description,
    };
    if (editingModule) {
      const nbSeances = editingModule.nb_seances_liees || 0;
      const nbAffectations = editingModule.nb_affectations_liees || 0;
      if (nbSeances > 0 || nbAffectations > 0) {
        const confirme = await confirmer({
          titre: 'Modifier un module déjà utilisé ?',
          description:
            `Ce module a ${nbSeances} séance(s) programmée(s) et ${nbAffectations} affectation(s) ` +
            `d'enseignant(s). Le modifier ne mettra pas à jour ces éléments existants et peut créer ` +
            `des incohérences (heures dépassées, semestre ou classe non alignés).`,
          libelleConfirmer: 'Modifier quand même',
        });
        if (!confirme) return;
      }
      updateMutation.mutate({ id: editingModule.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  // ── Rendu ──────────────────────────────────────────────────

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">

      <PageHeader
        titre="Contenu pédagogique"
        description="Les modules de chaque classe, semestre par semestre, et les enseignants qui les assurent."
      />

      <div className="flex flex-col md:flex-row gap-6 items-start">
        {/* Choix de la classe : liste verticale sur grand écran, rangée de
            boutons défilante sur mobile (la liste empilée repoussait les
            modules sous l'écran). */}
        <nav
          aria-label="Classes"
          className="w-full md:w-52 flex-shrink-0 flex md:flex-col gap-1 overflow-x-auto no-scrollbar md:border-r md:border-border md:pr-4"
        >
          <h2 className="hidden md:block text-xs font-semibold text-muted-foreground uppercase mb-2 px-3">Classes</h2>
          {classesLoading ? (
             <p className="text-sm text-muted-foreground px-3">Chargement…</p>
          ) : groupedClasses.length === 0 ? (
             <p className="text-sm text-muted-foreground px-3">Aucune classe disponible.</p>
          ) : (
              groupedClasses.map(group => (
                  <button
                      key={group.key}
                      type="button"
                      aria-current={selectedGroup?.key === group.key ? 'true' : undefined}
                      onClick={() => setSelectedGroupKey(group.key)}
                      className={`shrink-0 text-left px-3 py-2 rounded-md text-sm whitespace-nowrap md:whitespace-normal transition-colors ${
                          selectedGroup?.key === group.key
                              ? 'bg-primary/10 text-primary font-semibold'
                              : 'hover:bg-muted/60 text-muted-foreground hover:text-foreground'
                      }`}
                  >
                      {group.label}
                  </button>
              ))
          )}
        </nav>

        {/* VUE MODULES */}
        <div className="flex-1 w-full min-w-0">
          {!selectedGroup ? (
            <div className="flex flex-col items-center justify-center gap-3 py-20 text-muted-foreground border rounded-xl border-dashed">
              <BookOpen className="h-10 w-10 opacity-30" />
              <p className="text-sm">
                {classesLoading ? 'Chargement…' : 'Aucune classe disponible.'}
              </p>
            </div>
          ) : (
            <div className="space-y-8">
              {selectedGroup.classes.map((classe) => (
                <SemestreCard
                  key={classe.id}
                  classe={classe}
                  enCours={!!semestreEnCours && classe.semestre?.id === semestreEnCours.id}
                  onAddModule={handleAddModule}
                  onEditModule={handleEditModule}
                  onDeleteModule={handleDeleteModule}
                  onAffecterModule={setModuleAffectation}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* MODALE FORMULAIRE */}
      <FormModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleFormSubmit}
        title={editingModule ? 'Modifier le module' : 'Créer un nouveau module'}
        description="Renseignez les informations requises pour structurer l'unité d'enseignement."
        isPending={createMutation.isPending || updateMutation.isPending}
      >
        <div className="space-y-4 py-1">
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm font-medium rounded-md border border-destructive/20">
              {serverError}
            </div>
          )}

          {editingModule && ((editingModule.nb_seances_liees || 0) > 0 || (editingModule.nb_affectations_liees || 0) > 0) && (
            <div className="p-3 bg-amber-500/10 text-amber-700 text-sm rounded-md border border-amber-500/20">
              <AlertCircle className="inline-block h-4 w-4 mr-1.5 -mt-0.5" />
              Ce module est déjà utilisé : {editingModule.nb_seances_liees || 0} séance(s) programmée(s)
              et {editingModule.nb_affectations_liees || 0} affectation(s) d'enseignant(s). Le modifier ne
              mettra pas à jour ces éléments existants.
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="cp-libelle">Nom du module</Label>
            <Input
              id="cp-libelle"
              value={libelle}
              onChange={(e) => setLibelle(e.target.value)}
              placeholder="Ex : Architecture des Systèmes d'Information"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="cp-matiere">Matière rattachée</Label>
            <Select value={matiereId} onValueChange={setMatiereId}>
              <SelectTrigger id="cp-matiere" className="w-full">
                <SelectValue placeholder="Choisir une matière" />
              </SelectTrigger>
              <SelectContent>
                {matieres.map((mat) => (
                  <SelectItem key={mat.id} value={mat.id.toString()}>
                    {mat.libelle}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cp-semestre">Semestre</Label>
            <Select value={semestreId} onValueChange={setSemestreId}>
              <SelectTrigger id="cp-semestre" className="w-full">
                <SelectValue placeholder="Attribuer un semestre" />
              </SelectTrigger>
              <SelectContent>
                {semestres.map((sem) => (
                  <SelectItem key={sem.id} value={sem.id.toString()}>
                    {sem.libelle}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cp-credits">Nombre de crédits (ECTS)</Label>
            <Input
              id="cp-credits"
              type="number"
              min="1"
              max="6"
              value={credits}
              onChange={(e) => setCredits(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="cp-description">Description (Optionnel)</Label>
            <textarea
              id="cp-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Détaillez les compétences visées ou prérequis du module…"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y border-border"
            />
          </div>
        </div>
      </FormModal>

      {/* DIALOG AFFECTATIONS */}
      <Dialog
        open={!!moduleAffectation}
        onOpenChange={(open) => !open && setModuleAffectation(null)}
      >
        <DialogContent className="sm:max-w-2xl">
          {/* Un seul titre ; le volume est affiché une fois, par le panneau. */}
          <DialogHeader>
            <DialogTitle>Enseignants — {moduleAffectation?.libelle}</DialogTitle>
            <DialogDescription>
              Qui enseigne ce module, et combien d'heures chacun.
            </DialogDescription>
          </DialogHeader>
          <AffectationsPanel module={moduleAffectation} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
