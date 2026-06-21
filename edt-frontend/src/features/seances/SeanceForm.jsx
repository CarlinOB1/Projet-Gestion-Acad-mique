/**
 * @file SeanceForm.jsx
 * @description Formulaire création/édition d'une séance — selects en cascade,
 * validation Zod, indicateur heures restantes du module.
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
import { Input }  from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label }  from '@/components/ui/label';

const seanceSchema = z.object({
  semestre_id:   z.string().min(1, 'Le semestre est requis'),
  filiere_id:    z.string().min(1, 'La filière est requise'),
  classe_id:     z.string().min(1, 'La classe est requise'),
  module_id:     z.string().min(1, 'Le module est requis'),
  enseignant_id: z.string().min(1, "L'enseignant est requis"),
  date_seance:   z.string().min(1, 'La date est requise').refine((val) => {
    const day = new Date(val + 'T00:00:00').getDay();
    return day !== 0;
  }, 'Les séances ne peuvent pas avoir lieu un dimanche'),
  heure_debut: z.string().min(1, "L'heure de début est requise")
    .refine((val) => val >= HEURE_MIN, `L'heure de début doit être >= ${HEURE_MIN}`),
  heure_fin: z.string().min(1, "L'heure de fin est requise")
    .refine((val) => val <= HEURE_MAX, `L'heure de fin doit être <= ${HEURE_MAX}`),
  type_seance:   z.enum(['CM', 'TD', 'TP'], {
    errorMap: () => ({ message: 'Le type doit être CM, TD ou TP' }),
  }),
}).refine((data) => data.heure_fin > data.heure_debut, {
  message: "L'heure de fin doit être supérieure à l'heure de début",
  path: ['heure_fin'],
});

export default function SeanceForm({
  semestreId,
  defaultValues = null,
  onSubmit,
  isPending,
  serverError = null,
}) {
  const { register, handleSubmit, control, setValue, formState: { errors } } = useForm({
    resolver: zodResolver(seanceSchema),
    defaultValues: {
      semestre_id:   semestreId ? String(semestreId) : '',
      filiere_id:    '',
      classe_id:     '',
      module_id:     '',
      enseignant_id: '',
      date_seance:   '',
      heure_debut:   '09:00',
      heure_fin:     '10:30',
      type_seance:   'CM',
      ...defaultValues,
    },
  });

  const {
    filieres, isLoadingFilieres,
    selectedFiliereId, setSelectedFiliereId,
    classes, isLoadingClasses,
    setSelectedClasseId,
    modules, isLoadingModules,
    setSelectedModuleId,
    enseignants, isLoadingEnseignants,
    moduleSelectionne,
  } = useCascadeSelects({ semestreId });

  useEffect(() => {
    if (semestreId) setValue('semestre_id', String(semestreId));
  }, [semestreId, setValue]);

  useEffect(() => {
    if (defaultValues) {
      if (defaultValues.filiere_id) setSelectedFiliereId(defaultValues.filiere_id);
      if (defaultValues.classe_id)  setSelectedClasseId(defaultValues.classe_id);
      if (defaultValues.module_id)  setSelectedModuleId(defaultValues.module_id);
    }
  }, [defaultValues, setSelectedFiliereId, setSelectedClasseId, setSelectedModuleId]);

  const getHeuresColor = (h) => {
    if (h > 4)  return 'text-green-600 dark:text-green-400';
    if (h >= 1) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="space-y-5">

      {/* 1. Filière */}
      <div className="space-y-2">
        <Label>Filière</Label>
        <Controller name="filiere_id" control={control} render={({ field }) => (
          <Select disabled={isLoadingFilieres} value={field.value}
            onValueChange={(v) => {
              field.onChange(v);
              setSelectedFiliereId(v);
              setValue('classe_id', '');
              setValue('module_id', '');
              setValue('enseignant_id', '');
              setSelectedClasseId(null);
              setSelectedModuleId(null);
            }}>
            <SelectTrigger><SelectValue placeholder="Sélectionnez une filière" /></SelectTrigger>
            <SelectContent>
              {filieres.map((f) => (
                <SelectItem key={f.id} value={String(f.id)}>{f.libelle}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.filiere_id && <p className="text-xs text-destructive">{errors.filiere_id.message}</p>}
      </div>

      {/* 2. Classe */}
      <div className="space-y-2">
        <Label>Classe</Label>
        <Controller name="classe_id" control={control} render={({ field }) => (
          <Select disabled={!selectedFiliereId || isLoadingClasses} value={field.value}
            onValueChange={(v) => { field.onChange(v); setSelectedClasseId(v); }}>
            <SelectTrigger>
              <SelectValue placeholder={selectedFiliereId ? "Sélectionnez une classe" : "Choisissez d'abord une filière"} />
            </SelectTrigger>
            <SelectContent>
              {classes.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>{c.libelle}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.classe_id && <p className="text-xs text-destructive">{errors.classe_id.message}</p>}
      </div>

      {/* 3. Module */}
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

      {/* 4. Enseignant */}
      <div className="space-y-2">
        <Label>Enseignant</Label>
        <Controller name="enseignant_id" control={control} render={({ field }) => (
          <Select disabled={isLoadingEnseignants} value={field.value} onValueChange={field.onChange}>
            <SelectTrigger>
              <SelectValue placeholder={moduleSelectionne ? "Sélectionnez un enseignant" : "Choisissez d'abord un module"} />
            </SelectTrigger>
            <SelectContent>
              {enseignants.map((e) => (
                <SelectItem key={e.profil_id} value={String(e.profil_id)}>
                  {e.grade ? `[${e.grade}] ` : ''}{e.nom_complet}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.enseignant_id && <p className="text-xs text-destructive">{errors.enseignant_id.message}</p>}
      </div>

      {/* 5. Date */}
      <div className="space-y-2">
        <Label>Date de la séance</Label>
        {/* CORRECTION : min utilise la date du jour, pas HEURE_MIN */}
        <Input type="date"
          min={new Date().toISOString().split('T')[0]}
          {...register('date_seance')} />
        {errors.date_seance && <p className="text-xs text-destructive">{errors.date_seance.message}</p>}
      </div>

      {/* 6. Heure début */}
      <div className="space-y-2">
        <Label>Heure de début</Label>
        <Input type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_debut')} />
        {errors.heure_debut && <p className="text-xs text-destructive">{errors.heure_debut.message}</p>}
      </div>

      {/* 7. Heure fin */}
      <div className="space-y-2">
        <Label>Heure de fin</Label>
        <Input type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_fin')} />
        {errors.heure_fin && <p className="text-xs text-destructive">{errors.heure_fin.message}</p>}
      </div>

      {/* 8. Type séance */}
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

      {/* 9. Erreur serveur */}
      {serverError && (
        <div className="p-3 text-sm font-medium text-destructive bg-destructive/10 rounded-lg border border-destructive/20">
          {serverError}
        </div>
      )}

      {/* 10. Submit */}
      <Button className="w-full" onClick={handleSubmit(onSubmit)} disabled={isPending}>
        {isPending ? 'Enregistrement...' : 'Enregistrer'}
      </Button>

    </div>
  );
}