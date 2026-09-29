/**
 * @file SeanceForm.jsx
 * @description Formulaire création/édition d'une séance — la classe est déjà
 * fixée par le contexte (onglet actif du planning, ou séance modifiée) et
 * s'affiche en lecture seule ; le formulaire enchaîne module → enseignant en
 * cascade, avec validation Zod et indicateur d'heures restantes du module.
 */
import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useCascadeSelects } from '@/hooks/useCascadeSelects';
import { TYPE_SEANCE, HEURE_MIN, HEURE_MAX } from '@/lib/constants';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover';
import { AlertTriangle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

const seanceSchema = z.object({
  semestre_id: z.string().min(1, 'Le semestre est requis'),
  classe_id: z.string().min(1, 'La classe est requise'),
  module_id: z.string().min(1, 'Le module est requis'),
  enseignant_id: z.string().min(1, "L'enseignant est requis"),
  date_seance: z.string().min(1, 'La date est requise').refine((val) => {
    const day = new Date(val + 'T00:00:00').getDay();
    return day !== 0;
  }, 'Les séances ne peuvent pas avoir lieu un dimanche'),
  heure_debut: z.string().min(1, "L'heure de début est requise")
    .refine((val) => val >= HEURE_MIN, `L'heure de début doit être >= ${HEURE_MIN}`),
  heure_fin: z.string().min(1, "L'heure de fin est requise")
    .refine((val) => val <= HEURE_MAX, `L'heure de fin doit être <= ${HEURE_MAX}`),
  type_seance: z.enum(['CM', 'TD', 'TP'], {
    errorMap: () => ({ message: 'Le type doit être CM, TD ou TP' }),
  }),
}).refine((data) => data.heure_fin > data.heure_debut, {
  message: "L'heure de fin doit être supérieure à l'heure de début",
  path: ['heure_fin'],
});

/**
 * @param {object} props
 * @param {string|number} props.semestreId
 * @param {{id: string|number, libelle: string, annee_id: string|number}|null} props.classe
 *   Classe déjà fixée par le contexte (onglet actif du planning en création,
 *   classe de la séance en édition). Affichée en lecture seule : ce n'est
 *   plus un champ à choisir dans ce formulaire.
 */
export default function SeanceForm({
  semestreId,
  classe = null,
  defaultValues = null,
  onSubmit,
  isPending,
  serverError = null,
}) {
  const { register, handleSubmit, control, setValue, watch, formState: { errors } } = useForm({
    resolver: zodResolver(seanceSchema),
    defaultValues: {
      semestre_id: semestreId ? String(semestreId) : '',
      classe_id: classe?.id ? String(classe.id) : '',
      module_id: '',
      enseignant_id: '',
      date_seance: '',
      heure_debut: '09:00',
      heure_fin: '10:30',
      type_seance: 'CM',
      ...defaultValues,
    },
  });

  const {
    modules, isLoadingModules,
    setSelectedModuleId,
    enseignants, isLoadingEnseignants,
    moduleSelectionne,
    selectedEnseignantId, setSelectedEnseignantId,
    affectationsEnseignant,
  } = useCascadeSelects({ classeId: classe?.id });

  useEffect(() => {
    if (semestreId) setValue('semestre_id', String(semestreId));
  }, [semestreId, setValue]);

  useEffect(() => {
    if (classe?.id) setValue('classe_id', String(classe.id));
  }, [classe, setValue]);

  useEffect(() => {
    if (defaultValues?.module_id) setSelectedModuleId(defaultValues.module_id);
  }, [defaultValues, setSelectedModuleId]);

  // Symétrique du useEffect ci-dessus, pour l'enseignant : sans lui, l'état
  // qui pilote le panneau "Solde affectation" (useCascadeSelects) restait
  // désynchronisé de l'enseignant réellement sélectionné en mode édition,
  // tant que l'utilisateur n'avait pas re-cliqué manuellement sur le champ
  // (CORRECTIONS_A_FAIRE.md, point 4).
  useEffect(() => {
    if (defaultValues?.enseignant_id) setSelectedEnseignantId(defaultValues.enseignant_id);
  }, [defaultValues, setSelectedEnseignantId]);

  const onFormSubmit = (formData) => {
    onSubmit({
      ...formData,
      annee_id: classe?.annee_id,
    });
  };

  /**
   * Calcule le solde (heures restantes) de l'affectation correspondant au type
   * de séance sélectionné pour l'enseignant choisi.
   * Retourne null si aucune affectation n'est trouvée (pas de contrainte).
   */
  const getSoldeAffectation = (typeSeance) => {
    if (!affectationsEnseignant || affectationsEnseignant.length === 0) return null;
    const aff =
      affectationsEnseignant.find((a) => a.type_seance === typeSeance) ??
      affectationsEnseignant.find((a) => a.type_seance === null);
    return aff ? { restantes: aff.heures_restantes, prevues: aff.heures_prevues, type: aff.type_seance } : null;
  };

  const getHeuresColor = (h) => {
    if (h > 4) return 'text-green-600 dark:text-green-400';
    if (h >= 1) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">

      {/* Classe — déjà fixée par l'onglet actif du planning, ou par la séance modifiée */}
      <div className="space-y-2 md:col-span-2">
        <Label>Classe</Label>
        <div className="flex h-10 items-center rounded-md border border-input bg-muted px-3 text-sm text-muted-foreground">
          {classe?.libelle || '—'}
        </div>
        {errors.classe_id && <p className="text-xs text-destructive">{errors.classe_id.message}</p>}
      </div>

      {/* 1. Module */}
      <div className="space-y-2">
        <Label>Module</Label>
        <Controller name="module_id" control={control} render={({ field }) => (
          <Select disabled={isLoadingModules} value={field.value}
            onValueChange={(v) => {
              field.onChange(v);
              setSelectedModuleId(v);
              setValue('enseignant_id', '');
            }}>
            <SelectTrigger><SelectValue placeholder="Sélectionnez un module" /></SelectTrigger>
            <SelectContent>
              {modules.map((m) => (
                <SelectItem key={m.id} value={String(m.id)}>{m.libelle}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.module_id && <p className="text-xs text-destructive">{errors.module_id.message}</p>}
        {moduleSelectionne && (
          <p className={`text-xs font-medium ${getHeuresColor(moduleSelectionne.heures_restantes)}`}>
            Heures restantes : {moduleSelectionne.heures_restantes}h / {moduleSelectionne.heures_max}h max
          </p>
        )}
      </div>

      {/* 2. Enseignant */}
      <div className="space-y-2">
        <Label>Enseignant</Label>
        <Controller name="enseignant_id" control={control} render={({ field }) => (
          <Select disabled={isLoadingEnseignants} value={field.value}
            onValueChange={(v) => {
              field.onChange(v);
              setSelectedEnseignantId(v);
            }}>
            <SelectTrigger>
              <SelectValue placeholder={moduleSelectionne ? "Sélectionnez un enseignant" : "Choisissez d'abord un module"} />
            </SelectTrigger>
            <SelectContent>
              {enseignants.map((e) => (
                <SelectItem key={e.profil.user.id} value={String(e.profil.user.id)}>
                  {e.grade ? `[${e.grade}] ` : ''}{e.nom_complet}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.enseignant_id && <p className="text-xs text-destructive">{errors.enseignant_id.message}</p>}
        {/* Solde d'affectation de l'enseignant sélectionné */}
        {selectedEnseignantId && (() => {
          // watch() (réactif) plutôt que control._formValues (lecture figée
          // au dernier rendu) : sans ça, ce panneau pouvait continuer
          // d'afficher le solde de l'ANCIEN type de séance après un
          // changement de champ, alors que le NOUVEAU type est ce qui part
          // réellement au serveur (CORRECTIONS_A_FAIRE.md, point 4).
          const typeSeance = watch('type_seance');
          const solde = getSoldeAffectation(typeSeance);
          if (!solde) return null;
          const cls = solde.restantes > 2 ? 'text-green-600 dark:text-green-400'
            : solde.restantes > 0 ? 'text-orange-600 dark:text-orange-400'
            : 'text-red-600 dark:text-red-400';
          return (
            <p className={`text-xs font-medium flex items-center gap-1 ${cls}`}>
              <AlertTriangle className="h-3 w-3" />
              Solde affectation ({solde.type ?? 'Générique'}) :
              {' '}{solde.restantes}h restantes / {solde.prevues}h prévues
            </p>
          );
        })()}
      </div>

      {/* 3. Date */}
      <div className="space-y-2">
        <Label>Date de la séance</Label>
        {/* CORRECTION : min utilise la date du jour, pas HEURE_MIN */}
        <Input type="date"
          min={new Date().toISOString().split('T')[0]}
          {...register('date_seance')} />
        {errors.date_seance && <p className="text-xs text-destructive">{errors.date_seance.message}</p>}
      </div>

      {/* 4. Heure début */}
      <div className="space-y-2">
        <Label>Heure de début</Label>
        <Input type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_debut')} />
        {errors.heure_debut && <p className="text-xs text-destructive">{errors.heure_debut.message}</p>}
      </div>

      {/* 5. Heure fin */}
      <div className="space-y-2">
        <Label>Heure de fin</Label>
        <Input type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_fin')} />
        {errors.heure_fin && <p className="text-xs text-destructive">{errors.heure_fin.message}</p>}
      </div>

      {/* 6. Type séance */}
      <div className="space-y-2">
        <Label>Type de séance</Label>
        <Controller name="type_seance" control={control} render={({ field }) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger><SelectValue placeholder="Sélectionnez un type" /></SelectTrigger>
            <SelectContent>
              {/* CORRECTION : Object.values() sur l'objet TYPE_SEANCE */}
              {Object.values(TYPE_SEANCE).map((type) => (
                <SelectItem key={type} value={type}>{type}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.type_seance && <p className="text-xs text-destructive">{errors.type_seance.message}</p>}
      </div>

      {/* 7. Erreur serveur / Conflit Popover */}
      <div className="md:col-span-2 pt-2">
        <Popover open={!!serverError}>
          <PopoverTrigger asChild>
            <div className="w-full">
              <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white" onClick={handleSubmit(onFormSubmit)} disabled={isPending}>
                {isPending ? 'Enregistrement...' : 'Enregistrer la séance'}
              </Button>
            </div>
          </PopoverTrigger>
          <PopoverContent className="w-80 p-3 border-amber-200 bg-amber-50" side="top" align="center" onOpenAutoFocus={(e) => e.preventDefault()}>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold text-amber-800 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                Erreur / Conflit détecté
              </p>
              <p className="text-xs text-amber-700">
                {serverError}
              </p>
            </div>
          </PopoverContent>
        </Popover>
      </div>

    </div>
  );
}
