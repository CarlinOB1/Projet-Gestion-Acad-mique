/**
 * @file features/affectations/AffectationsPanel.jsx
 * @description Panneau de gestion des affectations pour un module donné.
 * Affiche la liste des affectations existantes, permet d'en ajouter/modifier/supprimer.
 * Destiné à être intégré dans la page détail d'un module.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, Plus, AlertTriangle, CheckCircle2, Pencil } from 'lucide-react';
import {
  getAffectations,
  createAffectation,
  updateAffectation,
  deleteAffectation,
} from '@/api/affectations';
import { getEnseignants } from '@/api/acteurs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const TYPE_LABELS = { CM: 'CM', TD: 'TD', TP: 'TP', null: 'Générique' };

/** Badge coloré selon le ratio heures consommées/prévues */
function HeuresBadge({ consommees, prevues }) {
  const ratio = prevues > 0 ? consommees / prevues : 0;
  let cls = 'text-green-700 bg-green-100';
  if (ratio >= 1) cls = 'text-red-700 bg-red-100';
  else if (ratio >= 0.8) cls = 'text-orange-700 bg-orange-100';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {consommees}h / {prevues}h
    </span>
  );
}

/** Indicateur global de dépassement de volume du module */
function VolumeWarning({ affectations, module }) {
  const totalPrevues = affectations.reduce((s, a) => s + a.heures_prevues, 0);
  const max = module?.heures_max ?? 0;
  if (totalPrevues <= max) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      <span>
        Le total des heures prévues ({totalPrevues}h) dépasse le volume max du module ({max}h).
        <br />
        <span className="text-xs text-amber-600">L'enregistrement reste possible (avertissement non bloquant).</span>
      </span>
    </div>
  );
}

/** Formulaire de création/édition d'une affectation */
function AffectationForm({ moduleId, departementId, affectation = null, onSuccess, onCancel }) {
  const queryClient = useQueryClient();
  const [enseignantId, setEnseignantId] = useState(
    affectation ? String(affectation.enseignant?.profil?.user?.id ?? '') : ''
  );
  const [typeSeance, setTypeSeance] = useState(affectation?.type_seance || 'GENERIQUE');
  const [heuresPrevues, setHeuresPrevues] = useState(
    affectation ? String(affectation.heures_prevues) : ''
  );
  const [serverError, setServerError] = useState(null);

  const { data: enseignants = [], isLoading: loadingEns } = useQuery({
    queryKey: ['enseignants', departementId],
    queryFn: async () => {
      const response = await import('@/api/client').then(m => m.default);
      const res = await response.get('/enseignants/', { params: { departement_id: departementId } });
      return res.data?.results ?? res.data;
    },
    enabled: !!departementId,
  });

  const mutation = useMutation({
    mutationFn: (data) =>
      affectation
        ? updateAffectation(affectation.id, data)
        : createAffectation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['affectations', moduleId] });
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      setServerError(null);
      onSuccess();
    },
    onError: (err) => {
      const detail = err.response?.data;
      if (typeof detail === 'object') {
        const msg = Object.values(detail).flat().join(' ');
        setServerError(msg);
      } else {
        setServerError("Une erreur est survenue.");
      }
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setServerError(null);
    if (!enseignantId || !heuresPrevues) {
      setServerError("Veuillez remplir tous les champs obligatoires.");
      return;
    }
    mutation.mutate({
      module_id: moduleId,
      enseignant_id: Number(enseignantId),
      type_seance: typeSeance === 'GENERIQUE' ? null : typeSeance,
      heures_prevues: Number(heuresPrevues),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Enseignant */}
      <div className="space-y-1.5">
        <Label>Enseignant *</Label>
        <Select
          disabled={loadingEns}
          value={enseignantId}
          onValueChange={setEnseignantId}
        >
          <SelectTrigger>
            <SelectValue placeholder="Sélectionnez un enseignant" />
          </SelectTrigger>
          <SelectContent>
            {enseignants.map((e) => (
              <SelectItem key={e.profil.user.id} value={String(e.profil.user.id)}>
                {e.grade ? `[${e.grade}] ` : ''}{e.nom_complet}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Type de séance */}
      <div className="space-y-1.5">
        <Label>Type de séance</Label>
        <Select value={typeSeance} onValueChange={setTypeSeance}>
          <SelectTrigger>
            <SelectValue placeholder="Générique (tous types)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="GENERIQUE">Générique (tous types)</SelectItem>
            <SelectItem value="CM">CM</SelectItem>
            <SelectItem value="TD">TD</SelectItem>
            <SelectItem value="TP">TP</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-[11px] text-muted-foreground">
          Laisser vide = affectation générique (couvre tous les types de séances).
        </p>
      </div>

      {/* Heures prévues */}
      <div className="space-y-1.5">
        <Label>Heures prévues *</Label>
        <Input
          type="number"
          min="0"
          step="0.5"
          placeholder="Ex: 12"
          value={heuresPrevues}
          onChange={(e) => setHeuresPrevues(e.target.value)}
        />
      </div>

      {/* Erreur serveur */}
      {serverError && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          {serverError}
        </div>
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>Annuler</Button>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Enregistrement...' : affectation ? 'Modifier' : 'Ajouter'}
        </Button>
      </DialogFooter>
    </form>
  );
}

/** Composant principal : panneau d'affectations d'un module */
export default function AffectationsPanel({ module }) {
  const moduleId = module?.id;
  const departementId = module?.matiere?.departement?.id;
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const { data: affectations = [], isLoading } = useQuery({
    queryKey: ['affectations', moduleId],
    queryFn: () => getAffectations({ module_id: moduleId }),
    enabled: !!moduleId,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAffectation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['affectations', moduleId] });
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      setDeleteTarget(null);
    },
  });

  const totalPrevues = affectations.reduce((s, a) => s + a.heures_prevues, 0);
  const heuresMax = module?.heures_max ?? 0;

  if (!moduleId) return null;

  return (
    <div className="space-y-4">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Affectations des enseignants</h3>
          <p className="text-xs text-muted-foreground">
            Volume total prévu : <span className="font-medium">{totalPrevues}h</span>
            {' / '}{heuresMax}h max
          </p>
        </div>
        <Button size="sm" onClick={() => { setEditTarget(null); setShowForm(true); }}>
          <Plus className="h-4 w-4 mr-1" /> Affecter
        </Button>
      </div>

      {/* Avertissement dépassement */}
      <VolumeWarning affectations={affectations} module={module} />

      {/* Liste */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground py-4 text-center">Chargement…</p>
      ) : affectations.length === 0 ? (
        <div className="flex flex-col items-center gap-1 py-8 text-muted-foreground">
          <CheckCircle2 className="h-8 w-8 opacity-30" />
          <p className="text-sm">Aucune affectation pour ce module.</p>
          <p className="text-xs">Les séances seront acceptées sans restriction d'enseignant.</p>
        </div>
      ) : (
        <div className="divide-y rounded-md border">
          {affectations.map((aff) => (
            <div key={aff.id} className="flex items-center justify-between p-3 hover:bg-muted/30">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  {aff.enseignant?.nom_complet ?? '—'}
                  {aff.enseignant?.grade && (
                    <span className="ml-1.5 text-xs text-muted-foreground">[{aff.enseignant.grade}]</span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  {aff.type_seance ? `Type: ${aff.type_seance}` : 'Générique'}
                  {' · '}
                  <span className="inline-block">
                    <HeuresBadge consommees={aff.heures_consommees} prevues={aff.heures_prevues} />
                  </span>
                </p>
              </div>
              <div className="flex gap-1.5 ml-2 shrink-0">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  onClick={() => { setEditTarget(aff); setShowForm(true); }}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7 text-destructive hover:text-destructive"
                  onClick={() => setDeleteTarget(aff)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Dialog création/édition */}
      <Dialog open={showForm} onOpenChange={(open) => { if (!open) { setShowForm(false); setEditTarget(null); } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editTarget ? 'Modifier une affectation' : 'Nouvelle affectation'}
            </DialogTitle>
          </DialogHeader>
          <AffectationForm
            moduleId={moduleId}
            departementId={departementId}
            affectation={editTarget}
            onSuccess={() => { setShowForm(false); setEditTarget(null); }}
            onCancel={() => { setShowForm(false); setEditTarget(null); }}
          />
        </DialogContent>
      </Dialog>

      {/* Dialog confirmation suppression */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer cette affectation ?</AlertDialogTitle>
            <AlertDialogDescription>
              L'affectation de <strong>{deleteTarget?.enseignant?.nom_complet}</strong>
              {deleteTarget?.type_seance ? ` (${deleteTarget.type_seance})` : ' (Générique)'}
              {' '}sera définitivement supprimée. Les séances déjà planifiées ne seront pas affectées.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteMutation.mutate(deleteTarget.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Suppression...' : 'Supprimer'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
