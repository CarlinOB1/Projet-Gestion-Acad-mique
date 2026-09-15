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
import { Badge } from '@/components/ui/badge';

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
  const [horsDepartement, setHorsDepartement] = useState(affectation?.hors_departement ?? false);
  const [serverError, setServerError] = useState(null);

  const { data: enseignants = [], isLoading: loadingEns } = useQuery({
    queryKey: ['enseignants', horsDepartement ? 'tous' : departementId],
    queryFn: () => getEnseignants(
      horsDepartement ? { tous_departements: 1 } : { departement_id: departementId }
    ),
    enabled: horsDepartement || !!departementId,
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
      hors_departement: horsDepartement,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 pt-2">
      {/* Intervention inter-départements */}
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-3">
        <input
          type="checkbox"
          id="hors-departement"
          className="mt-0.5 h-4 w-4 rounded border-border"
          checked={horsDepartement}
          onChange={(e) => setHorsDepartement(e.target.checked)}
        />
        <Label htmlFor="hors-departement" className="text-sm font-normal leading-snug cursor-pointer">
          Intervention inter-départements — ce module est enseigné dans cette classe par un enseignant d'un autre département
        </Label>
      </div>

      {/* Enseignant */}
      <div className="space-y-2">
        <Label className="text-sm font-semibold">Enseignant <span className="text-destructive">*</span></Label>
        <Select
          disabled={loadingEns}
          value={enseignantId}
          onValueChange={setEnseignantId}
        >
          <SelectTrigger className="h-11">
            <SelectValue placeholder={loadingEns ? 'Chargement...' : 'Sélectionnez un enseignant'} />
          </SelectTrigger>
          <SelectContent>
            {enseignants.map((e) => (
              <SelectItem key={e.profil.user.id} value={String(e.profil.user.id)}>
                <span className="font-medium">{e.nom_complet}</span>
                {e.grade && <span className="ml-2 text-muted-foreground text-xs">[{e.grade}]</span>}
                {horsDepartement && e.departement?.libelle && (
                  <span className="ml-2 text-muted-foreground text-xs">— {e.departement.libelle}</span>
                )}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Type de séance */}
      <div className="space-y-2">
        <Label className="text-sm font-semibold">Type de séance</Label>
        <Select value={typeSeance} onValueChange={setTypeSeance}>
          <SelectTrigger className="h-11">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="GENERIQUE">
              <span className="font-medium">Générique</span>
              <span className="ml-2 text-xs text-muted-foreground">— couvre tous les types</span>
            </SelectItem>
            <SelectItem value="CM">CM — Cours Magistral</SelectItem>
            <SelectItem value="TD">TD — Travaux Dirigés</SelectItem>
            <SelectItem value="TP">TP — Travaux Pratiques</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground pl-0.5">
          Une affectation générique s'applique à tous les types de séances.
        </p>
      </div>

      {/* Heures prévues */}
      <div className="space-y-2">
        <Label className="text-sm font-semibold">Heures prévues <span className="text-destructive">*</span></Label>
        <Input
          type="number"
          min="0"
          step="0.5"
          placeholder="Ex : 16"
          className="h-11"
          value={heuresPrevues}
          onChange={(e) => setHeuresPrevues(e.target.value)}
        />
        <p className="text-xs text-muted-foreground pl-0.5">
          Volume horaire alloué à cet enseignant pour ce module.
        </p>
      </div>

      {/* Erreur serveur */}
      {serverError && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          {serverError}
        </div>
      )}

      <DialogFooter className="pt-2 gap-2">
        <Button type="button" variant="outline" onClick={onCancel} className="flex-1 sm:flex-none">Annuler</Button>
        <Button type="submit" disabled={mutation.isPending} className="flex-1 sm:flex-none bg-blue-600 hover:bg-blue-700 text-white">
          {mutation.isPending ? 'Enregistrement...' : affectation ? 'Enregistrer les modifications' : 'Ajouter l\'affectation'}
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
        <div className="space-y-2">
          {affectations.map((aff) => (
            <div key={aff.id} className="flex items-center justify-between p-4 rounded-lg border border-border bg-card hover:bg-muted/20 transition-colors">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-semibold text-card-foreground">
                    {aff.enseignant?.nom_complet ?? '—'}
                  </p>
                  {aff.enseignant?.grade && (
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{aff.enseignant.grade}</span>
                  )}
                  {aff.hors_departement && (
                    <Badge variant="outline" className="text-xs">Inter-département</Badge>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-xs font-medium text-muted-foreground bg-muted/60 px-2 py-0.5 rounded">
                    {aff.type_seance ? aff.type_seance : 'Générique'}
                  </span>
                  <HeuresBadge consommees={aff.heures_consommees} prevues={aff.heures_prevues} />
                </div>
              </div>
              <div className="flex gap-2 ml-3 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 px-3 text-xs"
                  onClick={() => { setEditTarget(aff); setShowForm(true); }}
                >
                  <Pencil className="h-3 w-3 mr-1" /> Modifier
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
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
        <DialogContent className="sm:max-w-lg">
          <DialogHeader className="pb-2 border-b border-border">
            <DialogTitle className="text-lg">
              {editTarget ? 'Modifier une affectation' : 'Nouvelle affectation'}
            </DialogTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {editTarget
                ? `Modifiez les détails de l'affectation de ${editTarget.enseignant?.nom_complet}.`
                : `Affectez un enseignant à ce module pour le semestre en cours.`}
            </p>
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
