/**
 * @file features/affectations/AffectationsPanel.jsx
 * @description Panneau de gestion des affectations pour un module donné.
 * Affiche la liste des affectations existantes, permet d'en ajouter/modifier/supprimer.
 * Destiné à être intégré dans la page détail d'un module.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, Plus, AlertTriangle, CheckCircle2, Pencil, ArrowLeft } from 'lucide-react';
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
import { DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import { confirmer } from '@/lib/confirmer';
import { toast } from '@/hooks/use-toast';
import { formatNombreHeures } from '@/lib/utils';

const TYPE_LABELS = { CM: 'CM', TD: 'TD', TP: 'TP', null: 'Générique' };

/** Badge coloré selon le ratio heures consommées/prévues */
function HeuresBadge({ consommees, prevues }) {
  const ratio = prevues > 0 ? consommees / prevues : 0;
  let cls = 'text-green-700 bg-green-100';
  if (ratio >= 1) cls = 'text-red-700 bg-red-100';
  else if (ratio >= 0.8) cls = 'text-orange-700 bg-orange-100';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {formatNombreHeures(Number(consommees) || 0)} / {formatNombreHeures(Number(prevues) || 0)}
    </span>
  );
}

/** Indicateur global de dépassement de volume du module */
function VolumeWarning({ affectations, module }) {
  const totalPrevues = affectations.reduce((s, a) => s + Number(a.heures_prevues || 0), 0);
  const max = module?.heures_max ?? 0;
  if (totalPrevues <= max) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      <span>
        Le total des heures prévues ({formatNombreHeures(totalPrevues)}) dépasse le volume du module ({formatNombreHeures(max)}).
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
    <form onSubmit={handleSubmit} className="space-y-5">
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
        <Label htmlFor="aff-enseignant" className="text-sm font-semibold">Enseignant <span className="text-destructive">*</span></Label>
        <Select
          disabled={loadingEns}
          value={enseignantId}
          onValueChange={setEnseignantId}
        >
          <SelectTrigger id="aff-enseignant" className="w-full">
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
        <Label htmlFor="aff-type" className="text-sm font-semibold">Type de séance</Label>
        <Select value={typeSeance} onValueChange={setTypeSeance}>
          <SelectTrigger id="aff-type" className="w-full">
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
        <Label htmlFor="aff-heures" className="text-sm font-semibold">Heures prévues <span className="text-destructive">*</span></Label>
        <Input
          id="aff-heures"
          type="number"
          min="0"
          step="0.5"
          placeholder="Ex : 16"
          value={heuresPrevues}
          onChange={(e) => setHeuresPrevues(e.target.value)}
        />
        <p className="text-xs text-muted-foreground pl-0.5">
          Volume horaire alloué à cet enseignant pour ce module.
        </p>
      </div>

      {/* Erreur serveur */}
      <ErreurFormulaire message={serverError} />

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel} className="flex-1 sm:flex-none">Annuler</Button>
        <Button type="submit" disabled={mutation.isPending} className="flex-1 sm:flex-none">
          {mutation.isPending ? 'Enregistrement...' : affectation ? 'Enregistrer les modifications' : 'Ajouter l\'affectation'}
        </Button>
      </DialogFooter>
    </form>
  );
}

/**
 * Composant principal : panneau d'affectations d'un module.
 * Liste et formulaire s'affichent tour à tour dans la même fenêtre : avant,
 * « Affecter » ouvrait une deuxième fenêtre par-dessus la première, et la
 * suppression une troisième.
 */
export default function AffectationsPanel({ module }) {
  const moduleId = module?.id;
  const departementId = module?.matiere?.departement?.id;
  const queryClient = useQueryClient();

  // null = liste ; { affectation: null } = nouvelle ; { affectation } = modification
  const [formulaire, setFormulaire] = useState(null);

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
      toast({ title: 'Affectation supprimée' });
    },
    onError: (err) =>
      toast({
        variant: 'destructive',
        title: "L'affectation n'a pas pu être supprimée",
        description: err?.response?.data?.detail ?? 'Réessayez ; si le problème persiste, rechargez la page.',
      }),
  });

  const supprimer = async (aff) => {
    const ok = await confirmer({
      titre: `Supprimer l'affectation de ${aff.enseignant?.nom_complet ?? 'cet enseignant'} ?`,
      description: `${aff.type_seance ?? 'Générique'} · ${formatNombreHeures(aff.heures_prevues)} prévues. Les séances déjà planifiées ne sont pas supprimées.`,
      libelleConfirmer: 'Supprimer',
      destructif: true,
    });
    if (ok) deleteMutation.mutate(aff.id);
  };

  const totalPrevues = affectations.reduce((s, a) => s + Number(a.heures_prevues || 0), 0);
  const heuresMax = module?.heures_max ?? 0;

  if (!moduleId) return null;

  if (formulaire) {
    const { affectation } = formulaire;
    const fermer = () => setFormulaire(null);
    return (
      <div className="space-y-4">
        <div>
          <Button type="button" variant="link" className="h-auto p-0 text-muted-foreground" onClick={fermer}>
            <ArrowLeft className="size-4" aria-hidden /> Retour à la liste
          </Button>
          <h3 className="mt-2 text-base font-semibold text-balance">
            {affectation
              ? `Modifier l'affectation de ${affectation.enseignant?.nom_complet ?? 'cet enseignant'}`
              : 'Nouvelle affectation'}
          </h3>
        </div>
        <AffectationForm
          moduleId={moduleId}
          departementId={departementId}
          affectation={affectation}
          onSuccess={fermer}
          onCancel={fermer}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Volume et action principale */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground tabular-nums">
          <span className="font-semibold text-foreground">{isLoading ? '… h' : formatNombreHeures(totalPrevues)}</span> affectées
          sur {formatNombreHeures(heuresMax)}
          {module?.heures_consommees != null && (
            <> · {formatNombreHeures(Number(module.heures_consommees))} planifiées</>
          )}
        </p>
        <Button size="sm" onClick={() => setFormulaire({ affectation: null })}>
          <Plus className="size-4" aria-hidden /> Affecter
        </Button>
      </div>

      {/* Avertissement dépassement */}
      <VolumeWarning affectations={affectations} module={module} />

      {/* Liste */}
      {isLoading ? (
        <div className="space-y-2" aria-hidden>
          <div className="h-16 rounded-lg bg-muted animate-pulse" />
          <div className="h-16 rounded-lg bg-muted animate-pulse" />
        </div>
      ) : affectations.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-8 text-center text-muted-foreground">
          <CheckCircle2 className="size-8 opacity-30" aria-hidden />
          <p className="text-sm">Aucun enseignant affecté à ce module.</p>
          <p className="text-xs text-pretty">Les séances sont acceptées sans restriction d'enseignant.</p>
          <Button size="sm" variant="outline" className="mt-1" onClick={() => setFormulaire({ affectation: null })}>
            <Plus className="size-4" aria-hidden /> Affecter un enseignant
          </Button>
        </div>
      ) : (
        <ul className="space-y-2">
          {affectations.map((aff) => (
            <li key={aff.id} className="flex items-center justify-between gap-3 p-3 rounded-lg border border-border bg-card">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-semibold text-card-foreground">
                    {aff.enseignant?.nom_complet ?? '—'}
                  </p>
                  {aff.enseignant?.grade && (
                    <span className="text-xs text-muted-foreground">{aff.enseignant.grade}</span>
                  )}
                  {aff.hors_departement && (
                    <Badge variant="outline" className="text-xs">Inter-département</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    {aff.type_seance ?? 'Générique'}
                  </span>
                  <HeuresBadge consommees={aff.heures_consommees} prevues={aff.heures_prevues} />
                </div>
              </div>
              <div className="flex gap-1 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setFormulaire({ affectation: aff })}
                >
                  <Pencil className="size-3.5" aria-hidden /> Modifier
                </Button>
                <Button
                  size="icon-sm"
                  variant="ghost"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  aria-label={`Supprimer l'affectation de ${aff.enseignant?.nom_complet ?? 'cet enseignant'}`}
                  onClick={() => supprimer(aff)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="size-3.5" aria-hidden />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
