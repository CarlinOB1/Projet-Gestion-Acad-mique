/**
 * @file EtudiantsPage.jsx
 * @description Page de gestion des étudiants — CRUD, filtres, gestion de statut.
 */
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { UserX, UserCheck, Plus, SlidersHorizontal, School, GraduationCap } from 'lucide-react';
import { getEtudiants, createEtudiant, updateEtudiant, removeEtudiant } from '@/api/acteurs';
import { getClasses, getParcours, getFilieres } from '@/api/academique';
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
  genre: '', telephone: '', matricule: '',
  parcours_id: '', filiere_id: '', classe_id: '',
};

export default function EtudiantsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const [isModalOpen,         setIsModalOpen]         = useState(false);
  const [editingEtudiant,     setEditingEtudiant]     = useState(null);
  const [serverError,         setServerError]         = useState(null);
  const [isStatutDrawerOpen,  setIsStatutDrawerOpen]  = useState(false);
  const [etudiantForStatut,   setEtudiantForStatut]   = useState(null);
  const [selectedClasseId,    setSelectedClasseId]    = useState('all');
  const [selectedStatut,      setSelectedStatut]      = useState('all');
  const [formData,            setFormData]            = useState(INITIAL_FORM);

  const { data: allClasses = [] } = useQuery({
    queryKey: ['classes'],
    queryFn: () => getClasses(),
  });

  const { data: parcoursList = [] } = useQuery({
    queryKey: ['parcours'],
    queryFn: getParcours,
    enabled: isModalOpen,
  });

  const { data: filieresList = [] } = useQuery({
    queryKey: ['filieres'],
    queryFn: getFilieres,
    enabled: isModalOpen,
  });

  const { data: formClasses = [] } = useQuery({
    queryKey: ['classes', 'form', formData.parcours_id, formData.filiere_id],
    queryFn: () => getClasses({
      parcours_id: formData.parcours_id || undefined,
      filiere_id:  formData.filiere_id  || undefined,
    }),
    enabled: isModalOpen,
  });

  const queryParams = {};
  if (selectedClasseId !== 'all') queryParams.classe_id = selectedClasseId;
  if (selectedStatut   !== 'all') queryParams.statut    = selectedStatut;

  const { data: etudiants = [], isLoading, isError } = useQuery({
    queryKey: ['etudiants', selectedClasseId, selectedStatut],
    queryFn: () => getEtudiants(queryParams),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['etudiants'] });

  const createMutation = useMutation({
    mutationFn: createEtudiant,
    onSuccess: () => { invalidate(); handleCloseModal(); },
    onError: (err) => setServerError(
      Object.values(err?.response?.data || {}).flat()[0] || 'Erreur serveur.'
    ),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateEtudiant(id, data),
    onSuccess: () => { invalidate(); handleCloseModal(); },
    onError: (err) => setServerError(
      Object.values(err?.response?.data || {}).flat()[0] || 'Erreur serveur.'
    ),
  });

  const deleteMutation = useMutation({
    mutationFn: removeEtudiant,
    onSuccess: invalidate,
  });

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingEtudiant(null);
    setServerError(null);
    setFormData(INITIAL_FORM);
  };

  const handleEdit = (row) => {
    setEditingEtudiant(row);
    setFormData({
      username:    '',
      first_name:  row.profil?.user?.first_name    ?? '',
      last_name:   row.profil?.user?.last_name     ?? '',
      email:       row.profil?.user?.email         ?? '',
      genre:       row.profil?.genre               ?? '',
      telephone:   row.profil?.telephone           ?? '',
      matricule:   row.matricule                   ?? '',
      parcours_id: row.parcours?.id?.toString()    ?? '',
      filiere_id:  row.filiere?.id?.toString()     ?? '',
      classe_id:   row.classe?.id?.toString()      ?? '',
    });
    setServerError(null);
    setIsModalOpen(true);
  };

  const handleConfirm = () => {
    setServerError(null);
    const payload = { ...formData };
    if (payload.parcours_id) payload.parcours_id = parseInt(payload.parcours_id, 10);
    if (payload.filiere_id)  payload.filiere_id  = parseInt(payload.filiere_id,  10);
    if (payload.classe_id)   payload.classe_id   = parseInt(payload.classe_id,   10);

    if (editingEtudiant) {
      delete payload.username;
      updateMutation.mutate({ id: editingEtudiant.profil_id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleSelect = (name, value) =>
    setFormData((p) => {
      const updated = { ...p, [name]: value };
      if (name === 'parcours_id' || name === 'filiere_id') updated.classe_id = '';
      return updated;
    });

  const handleInput = (e) =>
    setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));

  // CORRECTION : format { key, label, render } compatible avec notre DataTable
  const columns = [
    { key: 'matricule',  label: 'Matricule',  render: (r) => r.matricule },
    {
      key: 'nom_complet', label: 'Nom complet',
      render: (r) => {
        const u = r.profil?.user;
        return u ? `${u.last_name} ${u.first_name}` : '-';
      },
    },
    { key: 'parcours', label: 'Parcours', render: (r) => r.parcours?.libelle || '-' },
    { key: 'filiere',  label: 'Filière',  render: (r) => r.filiere?.libelle  || '-' },
    { key: 'classe',   label: 'Classe',   render: (r) => r.classe?.libelle   || '-' },
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
  ];

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Classes & Étudiants</h1>
          <p className="text-sm text-muted-foreground mt-1">Gérez les classes et la liste des étudiants de votre département.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-muted/50 p-2 rounded-lg border border-border">
            <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
            <Select value={selectedClasseId} onValueChange={setSelectedClasseId}>
              <SelectTrigger className="w-[160px] bg-background h-8">
                <SelectValue placeholder="Toutes les classes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes les classes</SelectItem>
                {allClasses.map((c) => (
                  <SelectItem key={c.id} value={c.id.toString()}>{c.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedStatut} onValueChange={setSelectedStatut}>
              <SelectTrigger className="w-[140px] bg-background h-8">
                <SelectValue placeholder="Tous statuts" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les statuts</SelectItem>
                <SelectItem value="actif">Actif</SelectItem>
                <SelectItem value="suspendu">Suspendu</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* ── Onglets de Navigation Classes / Étudiants ── */}
      <Tabs value="etudiants" onValueChange={(val) => {
        if (val === 'classes') {
          navigate('/chef/classes');
        }
      }} className="w-fit">
        <TabsList variant="line">
          <TabsTrigger value="classes" title="Classes"><School className="h-4 w-4" /></TabsTrigger>
          <TabsTrigger value="etudiants" title="Étudiants"><GraduationCap className="h-4 w-4" /></TabsTrigger>
        </TabsList>
      </Tabs>

      <DataTable
        columns={columns} data={etudiants}
        isLoading={isLoading} isError={isError}
        emptyMessage="Aucun étudiant enregistré."
      />

      {/* CORRECTION : props open/onClose/onConfirm/isPending */}
      <FormModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleConfirm}
        title={editingEtudiant ? "Modifier l'étudiant" : "Inscrire un étudiant"}
        isPending={createMutation.isPending || updateMutation.isPending}
      >
        {/* CORRECTION : <div> au lieu de <form> */}
        <div className="space-y-4">
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20">
              {serverError}
            </div>
          )}

          {!editingEtudiant && (
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

          <div className="space-y-2">
            <Label>Matricule</Label>
            <Input name="matricule" value={formData.matricule} onChange={handleInput} placeholder="ETU-XXXXX" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Parcours</Label>
              <Select value={formData.parcours_id} onValueChange={(v) => handleSelect('parcours_id', v)}>
                <SelectTrigger><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {parcoursList.map((p) => (
                    <SelectItem key={p.id} value={p.id.toString()}>{p.libelle}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Filière</Label>
              <Select value={formData.filiere_id} onValueChange={(v) => handleSelect('filiere_id', v)}>
                <SelectTrigger><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {filieresList.map((f) => (
                    <SelectItem key={f.id} value={f.id.toString()}>{f.libelle}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Classe</Label>
            <Select value={formData.classe_id} onValueChange={(v) => handleSelect('classe_id', v)}
              disabled={!formData.parcours_id && !formData.filiere_id}>
              <SelectTrigger>
                <SelectValue placeholder="Choisir parcours/filière d'abord" />
              </SelectTrigger>
              <SelectContent>
                {formClasses.map((c) => (
                  <SelectItem key={c.id} value={c.id.toString()}>{c.libelle}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </FormModal>

      {/* CORRECTION : props open/profil/queryKeyToInvalidate */}
      <StatutDrawer
        open={isStatutDrawerOpen}
        onClose={() => { setIsStatutDrawerOpen(false); setEtudiantForStatut(null); }}
        profil={etudiantForStatut ? {
          user_id:          etudiantForStatut.profil_id,
          nom_complet:      `${etudiantForStatut.profil?.user?.last_name} ${etudiantForStatut.profil?.user?.first_name}`.trim(),
          statut:           etudiantForStatut.profil?.statut,
          motif_suspension: etudiantForStatut.profil?.motif_suspension,
        } : null}
        queryKeyToInvalidate={['etudiants']}
      />
    </div>
  );
}