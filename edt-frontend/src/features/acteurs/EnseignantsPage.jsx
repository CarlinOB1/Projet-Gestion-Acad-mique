/**
 * @file EnseignantsPage.jsx
 * @description Page de gestion des enseignants — CRUD et gestion de statut.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { UserX, UserCheck, Plus } from 'lucide-react';
import { getEnseignants, createEnseignant, updateEnseignant, removeEnseignant } from '@/api/acteurs';
import { getDepartements } from '@/api/academique';
// CORRECTION : alias @/ correct
import DataTable from '@/components/shared/DataTable';
import FormModal from '@/components/shared/FormModal';
import StatutDrawer from './StatutDrawer';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { STATUT_COLORS } from '@/lib/constants';

const INITIAL_FORM = {
  username: '', first_name: '', last_name: '', email: '',
  genre: '', telephone: '', grade: '', contrat: '', departement_id: '',
};

export default function EnseignantsPage() {
  const queryClient = useQueryClient();

  const [isModalOpen,          setIsModalOpen]          = useState(false);
  const [editingEnseignant,    setEditingEnseignant]    = useState(null);
  const [serverError,          setServerError]          = useState(null);
  const [isStatutDrawerOpen,   setIsStatutDrawerOpen]   = useState(false);
  const [enseignantForStatut,  setEnseignantForStatut]  = useState(null);
  const [formData,             setFormData]             = useState(INITIAL_FORM);

  const { data: enseignants = [], isLoading, isError } = useQuery({
    queryKey: ['enseignants'],
    queryFn: getEnseignants,
  });

  const { data: departements = [] } = useQuery({
    queryKey: ['departements'],
    queryFn: getDepartements,
    enabled: isModalOpen,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['enseignants'] });

  const createMutation = useMutation({
    mutationFn: createEnseignant,
    onSuccess: () => { invalidate(); handleCloseModal(); },
    onError: (err) => setServerError(
      Object.values(err?.response?.data || {}).flat()[0] || 'Erreur serveur.'
    ),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateEnseignant(id, data),
    onSuccess: () => { invalidate(); handleCloseModal(); },
    onError: (err) => setServerError(
      Object.values(err?.response?.data || {}).flat()[0] || 'Erreur serveur.'
    ),
  });

  const deleteMutation = useMutation({
    mutationFn: removeEnseignant,
    onSuccess: invalidate,
  });

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingEnseignant(null);
    setFormData(INITIAL_FORM);
    setServerError(null);
  };

  const handleEdit = (row) => {
    setEditingEnseignant(row);
    setFormData({
      username:       '',
      first_name:     row.profil?.user?.first_name    ?? '',
      last_name:      row.profil?.user?.last_name     ?? '',
      email:          row.profil?.user?.email         ?? '',
      genre:          row.profil?.genre               ?? '',
      telephone:      row.profil?.telephone           ?? '',
      grade:          row.grade                       ?? '',
      contrat:        row.contrat                     ?? '',
      departement_id: row.departement?.id?.toString() ?? '',
    });
    setServerError(null);
    setIsModalOpen(true);
  };

  const handleConfirm = () => {
    setServerError(null);
    const payload = { ...formData };
    if (payload.departement_id) payload.departement_id = parseInt(payload.departement_id, 10);

    if (editingEnseignant) {
      delete payload.username;
      updateMutation.mutate({ id: editingEnseignant.profil_id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleSelect = (name, value) =>
    setFormData((p) => ({ ...p, [name]: value }));

  const handleInput = (e) =>
    setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));

  // CORRECTION : format { key, label, render } compatible avec notre DataTable
  const columns = [
    { key: 'nom_complet',  label: 'Nom complet',  render: (r) => r.nom_complet },
    { key: 'grade',        label: 'Grade',        render: (r) => r.grade || '-' },
    { key: 'contrat',      label: 'Contrat',      render: (r) => <Badge variant="outline">{r.contrat}</Badge> },
    { key: 'departement',  label: 'Département',  render: (r) => r.departement?.libelle || '-' },
    {
      key: 'statut', label: 'Statut',
      render: (r) => {
        const statut = r.profil?.statut;
        // CORRECTION : STATUT_COLORS retourne { bg, text, border }
        const c = STATUT_COLORS[statut] || {};
        return (
          <Badge className={`${c.bg} ${c.text} ${c.border}`}>
            {statut}
          </Badge>
        );
      },
    },
    {
      key: 'statut_action', label: '',
      render: (r) => {
        const isActif = r.profil?.statut === 'actif';
        return (
          <Button variant="ghost" size="sm"
            onClick={() => { setEnseignantForStatut(r); setIsStatutDrawerOpen(true); }}>
            {isActif
              ? <><UserX className="h-4 w-4 mr-1 text-destructive" />Suspendre</>
              : <><UserCheck className="h-4 w-4 mr-1 text-green-600" />Réactiver</>}
          </Button>
        );
      },
    },
  ];

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">

      <div className="flex items-center justify-between border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Enseignants</h1>
          <p className="text-sm text-muted-foreground mt-1">Gestion du corps enseignant.</p>
        </div>
        <Button onClick={() => { setEditingEnseignant(null); setFormData(INITIAL_FORM); setIsModalOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />Ajouter un enseignant
        </Button>
      </div>

      <DataTable
        columns={columns} data={enseignants}
        isLoading={isLoading} isError={isError}
        onEdit={handleEdit}
        onDelete={(r) => deleteMutation.mutate(r.profil_id)}
        emptyMessage="Aucun enseignant enregistré."
      />

      {/* CORRECTION : props open/onClose/onConfirm/isPending */}
      <FormModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleConfirm}
        title={editingEnseignant ? "Modifier l'enseignant" : "Ajouter un enseignant"}
        isPending={createMutation.isPending || updateMutation.isPending}
      >
        {/* CORRECTION : <div> au lieu de <form> */}
        <div className="space-y-4">
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20">
              {serverError}
            </div>
          )}

          {!editingEnseignant && (
            <div className="space-y-2">
              <Label>Nom d'utilisateur</Label>
              <Input name="username" value={formData.username} onChange={handleInput} />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Prénom</Label>
              <Input name="first_name" value={formData.first_name} onChange={handleInput} />
            </div>
            <div className="space-y-2">
              <Label>Nom</Label>
              <Input name="last_name" value={formData.last_name} onChange={handleInput} />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Email</Label>
            <Input name="email" type="email" value={formData.email} onChange={handleInput} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Genre</Label>
              <Select value={formData.genre} onValueChange={(v) => handleSelect('genre', v)}>
                <SelectTrigger><SelectValue placeholder="Choisir..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="M">Masculin</SelectItem>
                  <SelectItem value="F">Féminin</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Téléphone</Label>
              <Input name="telephone" value={formData.telephone} onChange={handleInput} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Grade</Label>
              <Select value={formData.grade} onValueChange={(v) => handleSelect('grade', v)}>
                <SelectTrigger><SelectValue placeholder="Aucun" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Aucun</SelectItem>
                  <SelectItem value="Ingénieur">Ingénieur</SelectItem>
                  <SelectItem value="Docteur">Docteur</SelectItem>
                  <SelectItem value="Professeur">Professeur</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Contrat</Label>
              <Select value={formData.contrat} onValueChange={(v) => handleSelect('contrat', v)}>
                <SelectTrigger><SelectValue placeholder="Choisir..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Permanent">Permanent</SelectItem>
                  <SelectItem value="Vacataire">Vacataire</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Département</Label>
            <Select value={formData.departement_id} onValueChange={(v) => handleSelect('departement_id', v)}>
              <SelectTrigger><SelectValue placeholder="Sélectionner un département" /></SelectTrigger>
              <SelectContent>
                {departements.map((d) => (
                  <SelectItem key={d.id} value={d.id.toString()}>{d.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </FormModal>

      {/* CORRECTION : props open/profil/queryKeyToInvalidate */}
      <StatutDrawer
        open={isStatutDrawerOpen}
        onClose={() => { setIsStatutDrawerOpen(false); setEnseignantForStatut(null); }}
        profil={enseignantForStatut ? {
          user_id:          enseignantForStatut.profil_id,
          nom_complet:      enseignantForStatut.nom_complet,
          statut:           enseignantForStatut.profil?.statut,
          motif_suspension: enseignantForStatut.profil?.motif_suspension,
        } : null}
        queryKeyToInvalidate={['enseignants']}
      />
    </div>
  );
}