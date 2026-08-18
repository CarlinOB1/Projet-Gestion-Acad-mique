/**
 * src/features/academique/ModulesPage.jsx
 * * Page de gestion des modules académiques.
 * Intègre un système de filtrage par semestre, un affichage dynamique du volume horaire
 * sous forme de barre de progression native, et le cycle complet CRUD via TanStack Query v5.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Layers } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Primitives UI de shadcn/ui
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Composants partagés
import DataTable from '@/components/shared/DataTable';
import FormModal from '@/components/shared/FormModal';

// Fonctions API
import {
  getModules,
  createModule,
  updateModule,
  removeModule,
  getMatieres,
  getSemestres,
} from '@/api/academique';

export default function ModulesPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  // États locaux de contrôle
  const [selectedSemestreId, setSelectedSemestreId] = useState('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState(null);
  const [serverError, setServerError] = useState(null);

  // États locaux du formulaire (useState simple)
  const [libelle, setLibelle] = useState('');
  const [matiereId, setMatiereId] = useState('');
  const [semestreId, setSemestreId] = useState('');
  const [credits, setCredits] = useState(1);
  const [description, setDescription] = useState('');

  // -------------------------------------------------------------------------
  // REQUÊTES TANSTACK QUERY
  // -------------------------------------------------------------------------
  
  // Chargement des semestres (utilisé pour le filtre et le formulaire)
  const { data: semestres = [] } = useQuery({
    queryKey: ['semestres'],
    queryFn: getSemestres,
  });

  // Chargement des matières (utilisé pour le formulaire)
  const { data: matieres = [] } = useQuery({
    queryKey: ['matieres'],
    queryFn: getMatieres,
    enabled: isModalOpen, // Optimisation : charge uniquement à l'ouverture du formulaire
  });

  // Chargement des modules filtrés
  const { data: modules = [], isLoading, isError } = useQuery({
    queryKey: ['modules', selectedSemestreId],
    queryFn: () => {
      const params = selectedSemestreId !== 'all' ? { semestre_id: selectedSemestreId } : {};
      return getModules(params);
    },
  });

  // -------------------------------------------------------------------------
  // MUTATIONS
  // -------------------------------------------------------------------------
  const createMutation = useMutation({
    mutationFn: createModule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      handleCloseModal();
    },
    onError: (err) => setServerError(err.message || "Erreur lors de la création du module"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateModule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      handleCloseModal();
    },
    onError: (err) => setServerError(err.message || "Erreur lors de la modification du module"),
  });

  const deleteMutation = useMutation({
    mutationFn: removeModule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['modules'] }),
  });

  // -------------------------------------------------------------------------
  // GESTIONNAIRES D'ÉVÉNEMENTS
  // -------------------------------------------------------------------------
  
  // Synchronisation des champs du formulaire lors de l'ouverture/édition
  useEffect(() => {
    if (isModalOpen) {
      if (editingModule) {
        setLibelle(editingModule.libelle || '');
        setMatiereId(editingModule.matiere?.id?.toString() || editingModule.matiere_id?.toString() || '');
        setSemestreId(editingModule.semestre?.id?.toString() || editingModule.semestre_id?.toString() || '');
        setCredits(editingModule.credits || 1);
        setDescription(editingModule.description || '');
      } else {
        // Mode création : reset par défaut
        setLibelle('');
        setMatiereId('');
        setSemestreId(selectedSemestreId !== 'all' ? selectedSemestreId : '');
        setCredits(1);
        setDescription('');
      }
    }
  }, [isModalOpen, editingModule, selectedSemestreId]);

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingModule(null);
    setServerError(null);
  };

  const handleEditClick = (moduleRow) => {
    setEditingModule(moduleRow);
    setIsModalOpen(true);
  };

  const handleFormSubmit = () => {
    const payload = {
      libelle,
      matiere_id: parseInt(matiereId, 10),
      semestre_id: parseInt(semestreId, 10),
      credits: parseInt(credits, 10),
      description: description || null,
    };

    if (editingModule) {
      updateMutation.mutate({ id: editingModule.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  // -------------------------------------------------------------------------
  // CONFIGURATION DES COLONNES DU TABLEAU
  // -------------------------------------------------------------------------
  const columns = [
    { key: 'libelle', label: 'Nom du module' },
    { 
      key: 'matiere', 
      label: 'Matière', 
      render: (row) => row.matiere?.libelle || <span className="text-muted-foreground">-</span>
    },
    { 
      key: 'semestre', 
      label: 'Semestre', 
      render: (row) => <Badge variant="outline">{row.semestre?.libelle || '-'}</Badge>
    },
    { 
      key: 'credits', 
      label: 'Crédits',
      render: (row) => <span className="font-semibold">{row.credits} ECTS</span>
    },
    {
      key: 'volume',
      label: 'Volume Horaire',
      render: (row) => {
        const consomme = row.heures_consommees || 0;
        const max = row.heures_max || 1; // Évite la division par zéro
        const percentage = Math.min((consomme / max) * 100, 100);

        // Détermination dynamique de la couleur selon le taux de consommation
        let progressBarColor = 'bg-green-500';
        if (percentage >= 80 && percentage < 100) {
          progressBarColor = 'bg-orange-500';
        } else if (percentage >= 100) {
          progressBarColor = 'bg-red-500';
        }

        return (
          <div className="flex flex-col gap-1.5 w-44">
            <div className="flex justify-between text-xs font-medium text-muted-foreground">
              <span>{consomme}h / {max}h</span>
              <span>{Math.round(percentage)}%</span>
            </div>
            {/* Barre de progression inline via div CSS natif */}
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden border border-border/30">
              <div
                className={`h-full ${progressBarColor} transition-all duration-300 rounded-full`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      }
    }
  ];

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      
      {/* SECTION EN-TÊTE & FILTRES */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-lg hidden sm:block">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Structure Académique</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              Gérez l'organisation académique (facultés, départements, filières, parcours) et les modules.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Sélecteur de filtre par semestre */}
          <div className="w-[200px]">
            <Select value={selectedSemestreId} onValueChange={setSelectedSemestreId}>
              <SelectTrigger className="bg-background shadow-sm">
                <SelectValue placeholder="Filtrer par semestre" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les semestres</SelectItem>
                {semestres.map((sem) => (
                  <SelectItem key={sem.id} value={sem.id.toString()}>
                    {sem.libelle}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button onClick={() => { setEditingModule(null); setIsModalOpen(true); }} className="shadow-sm">
            <Plus className="mr-2 h-4 w-4" />
            Ajouter un module
          </Button>
        </div>
      </div>

      {/* ── Onglets de Navigation Structure / Modules ── */}
      <Tabs value="modules" onValueChange={(val) => {
        if (val === 'organisation') {
          navigate('/chef/organisation');
        }
      }} className="w-fit">
        <TabsList variant="line">
          <TabsTrigger value="organisation">Organisation</TabsTrigger>
          <TabsTrigger value="modules">Modules (Matières)</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* TABLEAU DE DONNÉES */}
      <DataTable
        columns={columns}
        data={modules}
        isLoading={isLoading}
        isError={isError}
        onEdit={handleEditClick}
        onDelete={(row) => deleteMutation.mutate(row.id)}
        emptyMessage="Aucun module trouvé pour les critères sélectionnés."
      />

      {/* MODALE DE FORMULAIRE */}
      <FormModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleFormSubmit}
        title={editingModule ? "Modifier le module" : "Créer un nouveau module"}
        description="Renseignez les informations requises pour structurer l'unité d'enseignement."
        isPending={createMutation.isPending || updateMutation.isPending}
      >
        <div className="space-y-4 py-1">
          {/* Alerte Erreur Serveur */}
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm font-medium rounded-md border border-destructive/20 animate-shake">
              {serverError}
            </div>
          )}

          {/* Champ Libellé */}
          <div className="space-y-2">
            <Label htmlFor="mod-libelle">Nom du module</Label>
            <Input
              id="mod-libelle"
              value={libelle}
              onChange={(e) => setLibelle(e.target.value)}
              placeholder="Ex: Architecture des Systèmes d'Information"
            />
          </div>

          {/* Champ Sélection Matière */}
          <div className="space-y-2">
            <Label htmlFor="mod-matiere">Matière rattachée</Label>
            <Select value={matiereId} onValueChange={setMatiereId}>
              <SelectTrigger id="mod-matiere">
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

          {/* Champ Sélection Semestre */}
          <div className="space-y-2">
            <Label htmlFor="mod-semestre">Semestre</Label>
            <Select value={semestreId} onValueChange={setSemestreId}>
              <SelectTrigger id="mod-semestre">
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

          {/* Champ Nombre de Crédits */}
          <div className="space-y-2">
            <Label htmlFor="mod-credits">Nombre de crédits (ECTS)</Label>
            <Input
              id="mod-credits"
              type="number"
              min="1"
              max="6"
              value={credits}
              onChange={(e) => setCredits(e.target.value)}
            />
          </div>

          {/* Champ Description Optionnelle */}
          <div className="space-y-2">
            <Label htmlFor="mod-description">Description (Optionnel)</Label>
            <textarea
              id="mod-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Détaillez les compétences visées ou prérequis du module..."
              className="flex min-h-[90px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y border-border"
            />
          </div>
        </div>
      </FormModal>

    </div>
  );
}