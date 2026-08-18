/**
 * src/features/academique/OrganisationPage.jsx
 * * Page principale de gestion de l'organisation académique.
 * Centralise la gestion des Facultés, Départements, Filières et Parcours.
 * Utilise des sous-composants locaux pour maintenir une architecture propre et lisible.
 * Propulsé par TanStack Query v5 pour la synchronisation d'état serveur.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';

// Primitives UI de shadcn/ui
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
    getFacultes, createFaculte, updateFaculte, removeFaculte,
    getDepartements, createDepartement, updateDepartement, removeDepartement,
    getFilieres, createFiliere, updateFiliere, removeFiliere,
    getParcours, createParcours, updateParcours, removeParcours
} from '@/api/academique';

export default function OrganisationPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const [activeTab, setActiveTab] = useState('facultes');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingItem, setEditingItem] = useState(null);
    const [serverError, setServerError] = useState(null);

    /**
     * Ferme proprement la modale et réinitialise les états contextuels
     */
    const handleCloseModal = () => {
        setIsModalOpen(false);
        setEditingItem(null);
        setServerError(null);
    };

    /**
     * Ouvre la modale en mode modification
     */
    const handleEdit = (row) => {
        setEditingItem(row);
        setIsModalOpen(true);
    };

    /**
     * Génère dynamiquement le label du bouton d'ajout selon l'onglet actif
     */
    const getButtonLabel = () => {
        switch (activeTab) {
            case 'facultes': return 'Ajouter une faculté';
            case 'departements': return 'Ajouter un département';
            case 'filieres': return 'Ajouter une filière';
            case 'parcours': return 'Ajouter un parcours';
            default: return 'Ajouter';
        }
    };

    return (
        <div className="space-y-6 p-6 max-w-7xl mx-auto">
            {/* En-tête de la page */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Structure Académique</h1>
                    <p className="text-muted-foreground mt-1">
                        Gérez l'organisation académique (facultés, départements, filières, parcours) et les modules.
                    </p>
                </div>
            </div>

            {/* ── Onglets de Navigation Structure / Modules ── */}
            <Tabs value="organisation" onValueChange={(val) => {
                if (val === 'modules') {
                    navigate('/chef/modules');
                }
            }} className="w-fit">
                <TabsList variant="line">
                    <TabsTrigger value="organisation">Organisation</TabsTrigger>
                    <TabsTrigger value="modules">Modules (Matières)</TabsTrigger>
                </TabsList>
            </Tabs>

            {/* Onglets applicatifs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-6">
                <TabsList className="grid w-full grid-cols-2 md:grid-cols-4 max-w-2xl bg-muted/60">
                    <TabsTrigger value="facultes">Facultés</TabsTrigger>
                    <TabsTrigger value="departements">Départements</TabsTrigger>
                    <TabsTrigger value="filieres">Filières</TabsTrigger>
                    <TabsTrigger value="parcours">Parcours</TabsTrigger>
                </TabsList>

                <TabsContent value="facultes" className="outline-none">
                    <FacultesTab
                        isOpen={isModalOpen && activeTab === 'facultes'}
                        onClose={handleCloseModal}
                        editingItem={editingItem}
                        onEdit={handleEdit}
                        serverError={serverError}
                        setServerError={setServerError}
                    />
                </TabsContent>

                <TabsContent value="departements" className="outline-none">
                    <DepartementsTab
                        isOpen={isModalOpen && activeTab === 'departements'}
                        onClose={handleCloseModal}
                        editingItem={editingItem}
                        onEdit={handleEdit}
                        serverError={serverError}
                        setServerError={setServerError}
                    />
                </TabsContent>

                <TabsContent value="filieres" className="outline-none">
                    <FilieresTab
                        isOpen={isModalOpen && activeTab === 'filieres'}
                        onClose={handleCloseModal}
                        editingItem={editingItem}
                        onEdit={handleEdit}
                        serverError={serverError}
                        setServerError={setServerError}
                    />
                </TabsContent>

                <TabsContent value="parcours" className="outline-none">
                    <ParcoursTab
                        isOpen={isModalOpen && activeTab === 'parcours'}
                        onClose={handleCloseModal}
                        editingItem={editingItem}
                        onEdit={handleEdit}
                        serverError={serverError}
                        setServerError={setServerError}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}

// =========================================================================
// ONGLET : FACULTÉS
// =========================================================================
function FacultesTab({ isOpen, onClose, editingItem, onEdit, serverError, setServerError }) {
    const queryClient = useQueryClient();
    const [libelle, setLibelle] = useState('');

    const { data = [], isLoading, isError } = useQuery({
        queryKey: ['facultes'],
        queryFn: getFacultes,
    });
    useEffect(() => {
        if (isOpen) {
            setLibelle(editingItem ? editingItem.libelle : '');
        }
    }, [isOpen, editingItem]);

    const createMutation = useMutation({
        mutationFn: createFaculte,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['facultes'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la création")
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, payload }) => updateFaculte(id, payload),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['facultes'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la modification")
    });

    const deleteMutation = useMutation({
        mutationFn: removeFaculte,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['facultes'] }); }
    });

    const handleConfirm = () => {
        if (editingItem) {
            updateMutation.mutate({ id: editingItem.id, payload: { libelle } });
        } else {
            createMutation.mutate({ libelle });
        }
    };

    const columns = [{ key: 'libelle', label: 'Libellé de la Faculté' }];

    return (
        <>
            <DataTable
                columns={columns} data={data} isLoading={isLoading} isError={isError}
            />
            <FormModal
                open={isOpen} onClose={onClose} onConfirm={handleConfirm}
                title={editingItem ? "Modifier la faculté" : "Ajouter une faculté"}
                isPending={createMutation.isPending || updateMutation.isPending}
            >
                <div className="space-y-4">
                    {serverError && <div className="p-3 bg-destructive/10 text-destructive text-sm rounded">{serverError}</div>}
                    <div className="space-y-2">
                        <Label htmlFor="fac-libelle">Libellé</Label>
                        <Input id="fac-libelle" value={libelle} onChange={(e) => setLibelle(e.target.value)} placeholder="Ex: Faculté des Sciences" />
                    </div>
                </div>
            </FormModal>
        </>
    );
}

// =========================================================================
// ONGLET : DÉPARTEMENTS
// =========================================================================
function DepartementsTab({ isOpen, onClose, editingItem, onEdit, serverError, setServerError }) {
    const queryClient = useQueryClient();
    const [libelle, setLibelle] = useState('');
    const [faculteId, setFaculteId] = useState('');

    const { data = [], isLoading, isError } = useQuery({
        queryKey: ['departements'],
        queryFn: getDepartements,
    });

    const { data: facultes } = useQuery({ queryKey: ['facultes'], queryFn: getFacultes, enabled: isOpen });

    useEffect(() => {
        if (isOpen) {
            setLibelle(editingItem ? editingItem.libelle : '');
            const fId = editingItem?.faculte?.id || editingItem?.faculte_id || '';
            setFaculteId(fId ? fId.toString() : '');
        }
    }, [isOpen, editingItem]);

    const createMutation = useMutation({
        mutationFn: createDepartement,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['departements'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la création")
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, payload }) => updateDepartement(id, payload),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['departements'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la modification")
    });

    const deleteMutation = useMutation({
        mutationFn: removeDepartement,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['departements'] }); }
    });

    const handleConfirm = () => {
        const payload = { libelle, faculte_id: parseInt(faculteId, 10) };
        if (editingItem) {
            updateMutation.mutate({ id: editingItem.id, payload });
        } else {
            createMutation.mutate(payload);
        }
    };

    const columns = [
        { key: 'libelle', label: 'Département' },
        { key: 'faculte', label: 'Faculté rattachée', render: (row) => row.faculte?.libelle || '-' }
    ];

    return (
        <>
            <DataTable
                columns={columns} data={data} isLoading={isLoading} isError={isError}
            />
            <FormModal
                open={isOpen} onClose={onClose} onConfirm={handleConfirm}
                title={editingItem ? "Modifier le département" : "Ajouter un département"}
                isPending={createMutation.isPending || updateMutation.isPending}
            >
                <div className="space-y-4">
                    {serverError && <div className="p-3 bg-destructive/10 text-destructive text-sm rounded">{serverError}</div>}
                    <div className="space-y-2">
                        <Label htmlFor="dep-libelle">Libellé</Label>
                        <Input id="dep-libelle" value={libelle} onChange={(e) => setLibelle(e.target.value)} placeholder="Ex: Informatique" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="dep-fac">Faculté</Label>
                        <Select value={faculteId} onValueChange={setFaculteId}>
                            <SelectTrigger id="dep-fac">
                                <SelectValue placeholder="Sélectionner une faculté" />
                            </SelectTrigger>
                            <SelectContent>
                                {facultes?.map((fac) => (
                                    <SelectItem key={fac.id} value={fac.id.toString()}>{fac.libelle}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </FormModal>
        </>
    );
}

// =========================================================================
// ONGLET : FILIÈRES
// =========================================================================
function FilieresTab({ isOpen, onClose, editingItem, onEdit, serverError, setServerError }) {
    const queryClient = useQueryClient();
    const [libelle, setLibelle] = useState('');
    const [departementId, setDepartementId] = useState('');

    const { data = [], isLoading, isError } = useQuery({
        queryKey: ['filieres'],
        queryFn: getFilieres,
    });
    const { data: departements } = useQuery({ queryKey: ['departements'], queryFn: getDepartements, enabled: isOpen });

    useEffect(() => {
        if (isOpen) {
            setLibelle(editingItem ? editingItem.libelle : '');
            const dId = editingItem?.departement?.id || editingItem?.departement_id || '';
            setDepartementId(dId ? dId.toString() : '');
        }
    }, [isOpen, editingItem]);

    const createMutation = useMutation({
        mutationFn: createFiliere,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['filieres'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la création")
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, payload }) => updateFiliere(id, payload),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['filieres'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la modification")
    });

    const deleteMutation = useMutation({
        mutationFn: removeFiliere,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['filieres'] }); }
    });

    const handleConfirm = () => {
        const payload = { libelle, departement_id: parseInt(departementId, 10) };
        if (editingItem) {
            updateMutation.mutate({ id: editingItem.id, payload });
        } else {
            createMutation.mutate(payload);
        }
    };

    const columns = [
        { key: 'libelle', label: 'Filière' },
        { key: 'departement', label: 'Département rattaché', render: (row) => row.departement?.libelle || '-' }
    ];

    return (
        <>
            <DataTable
                columns={columns} data={data} isLoading={isLoading} isError={isError}
            />
            <FormModal
                open={isOpen} onClose={onClose} onConfirm={handleConfirm}
                title={editingItem ? "Modifier la filière" : "Ajouter une filière"}
                isPending={createMutation.isPending || updateMutation.isPending}
            >
                <div className="space-y-4">
                    {serverError && <div className="p-3 bg-destructive/10 text-destructive text-sm rounded">{serverError}</div>}
                    <div className="space-y-2">
                        <Label htmlFor="fil-libelle">Libellé</Label>
                        <Input id="fil-libelle" value={libelle} onChange={(e) => setLibelle(e.target.value)} placeholder="Ex: Génie Logiciel" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="fil-dep">Département</Label>
                        <Select value={departementId} onValueChange={setDepartementId}>
                            <SelectTrigger id="fil-dep">
                                <SelectValue placeholder="Sélectionner un département" />
                            </SelectTrigger>
                            <SelectContent>
                                {departements?.map((dep) => (
                                    <SelectItem key={dep.id} value={dep.id.toString()}>{dep.libelle}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </FormModal>
        </>
    );
}

// =========================================================================
// ONGLET : PARCOURS
// =========================================================================
function ParcoursTab({ isOpen, onClose, editingItem, onEdit, serverError, setServerError }) {
    const queryClient = useQueryClient();
    const [typeParcours, setTypeParcours] = useState('');
    const [niveau, setNiveau] = useState(1);

    const { data = [], isLoading, isError } = useQuery({
        queryKey: ['parcours'],
        queryFn: getParcours,
    });

    useEffect(() => {
        if (isOpen) {
            setTypeParcours(editingItem ? editingItem.type_parcours : '');
            setNiveau(editingItem ? editingItem.niveau : 1);
        }
    }, [isOpen, editingItem]);

    const createMutation = useMutation({
        mutationFn: createParcours,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['parcours'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la création")
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, payload }) => updateParcours(id, payload),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['parcours'] }); onClose(); },
        onError: (err) => setServerError(err.message || "Erreur lors de la modification")
    });

    const deleteMutation = useMutation({
        mutationFn: removeParcours,
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['parcours'] }); }
    });

    const handleConfirm = () => {
        const payload = { type_parcours: typeParcours, niveau: parseInt(niveau, 10) };
        if (editingItem) {
            updateMutation.mutate({ id: editingItem.id, payload });
        } else {
            createMutation.mutate(payload);
        }
    };

    const columns = [
        { key: 'type_parcours', label: 'Type' },
        { key: 'niveau', label: 'Niveau' },
        { key: 'complet', label: 'Parcours Complet', render: (row) => `${row.type_parcours} ${row.niveau}` }
    ];

    return (
        <>
            <DataTable
                columns={columns} data={data} isLoading={isLoading} isError={isError}
            />
            <FormModal
                open={isOpen} onClose={onClose} onConfirm={handleConfirm}
                title={editingItem ? "Modifier le parcours" : "Ajouter un parcours"}
                isPending={createMutation.isPending || updateMutation.isPending}
            >
                <div className="space-y-4">
                    {serverError && <div className="p-3 bg-destructive/10 text-destructive text-sm rounded">{serverError}</div>}
                    <div className="space-y-2">
                        <Label htmlFor="par-type">Type de Parcours</Label>
                        <Select value={typeParcours} onValueChange={setTypeParcours}>
                            <SelectTrigger id="par-type">
                                <SelectValue placeholder="Sélectionner un cursus" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="Licence">Licence</SelectItem>
                                <SelectItem value="Master">Master</SelectItem>
                                <SelectItem value="Doctorat">Doctorat</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="par-niveau">Niveau (Année)</Label>
                        <Input
                            id="par-niveau" type="number" min="1" max="3"
                            value={niveau} onChange={(e) => setNiveau(e.target.value)}
                        />
                    </div>
                </div>
            </FormModal>
        </>
    );
}