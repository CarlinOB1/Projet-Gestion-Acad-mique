/**
 * @file SeanceForm.jsx
 * @description Formulaire création/édition d'une séance — la classe est déjà
 * fixée par le contexte (onglet actif du planning, ou séance modifiée) et
 * s'affiche en lecture seule ; le formulaire enchaîne module → enseignant en
 * cascade, avec validation Zod et indicateur d'heures restantes du module.
 */
import { useEffect } from 'react';
import { useForm, useWatch, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useCascadeSelects } from '@/hooks/useCascadeSelects';
import { TYPE_SEANCE, HEURE_MIN, HEURE_MAX } from '@/lib/constants';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { AlertTriangle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { formatNombreHeures } from '@/lib/utils';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';

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
  onCancel,
  isPending,
  serverError = null,
}) {
  const { register, handleSubmit, control, setValue, formState: { errors } } = useForm({
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

  // Type de séance lu de façon réactive (useWatch) plutôt que via
  // control._formValues (lecture figée au dernier rendu) : sans ça, le
  // panneau « Solde affectation » pouvait continuer d'afficher le solde de
  // l'ANCIEN type après un changement de champ, alors que le NOUVEAU type est
  // ce qui part réellement au serveur (CORRECTIONS_A_FAIRE.md, point 4).
  const typeSeance = useWatch({ control, name: 'type_seance' });
  const moduleIdCourant = useWatch({ control, name: 'module_id' });

  // En modification, les soldes renvoyés par le serveur comptent déjà la
  // séance qu'on modifie : sans correction, une séance tout à fait valable
  // affichait « 0h restantes » en rouge. On rajoute sa durée tant que le
  // module (et, pour l'affectation, l'enseignant et le type) n'ont pas changé.
  const estEdition = !!defaultValues?.module_id;
  const dureeInitiale = (() => {
    if (!estEdition || !defaultValues.heure_debut || !defaultValues.heure_fin) return 0;
    const enMinutes = (t) => {
      const [h, m] = t.split(':').map(Number);
      return h * 60 + (m || 0);
    };
    return Math.max(0, enMinutes(defaultValues.heure_fin) - enMinutes(defaultValues.heure_debut)) / 60;
  })();

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
    if (!aff) return null;
    const memeAffectation =
      estEdition &&
      String(selectedEnseignantId) === String(defaultValues.enseignant_id) &&
      String(moduleIdCourant) === String(defaultValues.module_id) &&
      typeSeance === defaultValues.type_seance;
    return {
      restantes: Number(aff.heures_restantes) + (memeAffectation ? dureeInitiale : 0),
      prevues: aff.heures_prevues,
      type: aff.type_seance,
    };
  };

  const heuresRestantesModule = moduleSelectionne
    ? Number(moduleSelectionne.heures_restantes) +
      (estEdition && String(moduleIdCourant) === String(defaultValues.module_id) ? dureeInitiale : 0)
    : null;

  const getHeuresColor = (h) => {
    if (h > 4) return 'text-green-600 dark:text-green-400';
    if (h >= 1) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  const soldeAffectation = selectedEnseignantId ? getSoldeAffectation(typeSeance) : null;
  const classeSolde = !soldeAffectation ? ''
    : soldeAffectation.restantes > 2 ? 'text-green-600 dark:text-green-400'
    : soldeAffectation.restantes > 0 ? 'text-orange-600 dark:text-orange-400'
    : 'text-red-600 dark:text-red-400';

  // Chaque étiquette est reliée à son champ (htmlFor / id) : un clic sur
  // l'étiquette place le curseur dans le champ, et le lecteur d'écran lit le
  // nom du champ. Listes déroulantes en pleine largeur, comme les autres champs.
  return (
    <form
      noValidate
      onSubmit={handleSubmit(onFormSubmit)}
      className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5"
    >

      {/* Classe — déjà fixée par l'onglet actif du planning, ou par la séance modifiée */}
      <p className="md:col-span-2 text-sm text-muted-foreground">
        Classe : <span className="font-medium text-foreground">{classe?.libelle || '—'}</span>
        {errors.classe_id && <span className="block text-xs text-destructive">{errors.classe_id.message}</span>}
      </p>

      {/* Module */}
      <div className="space-y-2">
        <Label htmlFor="seance-module">Module</Label>
        <Controller name="module_id" control={control} render={({ field }) => (
          <Select disabled={isLoadingModules} value={field.value}
            onValueChange={(v) => {
              field.onChange(v);
              setSelectedModuleId(v);
              setValue('enseignant_id', '');
            }}>
            <SelectTrigger id="seance-module" className="w-full"><SelectValue placeholder="Sélectionnez un module" /></SelectTrigger>
            <SelectContent>
              {modules.map((m) => (
                <SelectItem key={m.id} value={String(m.id)}>{m.libelle}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.module_id && <p className="text-xs text-destructive">{errors.module_id.message}</p>}
        {moduleSelectionne && (
          <p className={`text-xs font-medium tabular-nums ${getHeuresColor(heuresRestantesModule)}`}>
            Reste à planifier : {formatNombreHeures(heuresRestantesModule)} sur {formatNombreHeures(moduleSelectionne.heures_max)}
          </p>
        )}
      </div>

      {/* Enseignant */}
      <div className="space-y-2">
        <Label htmlFor="seance-enseignant">Enseignant</Label>
        <Controller name="enseignant_id" control={control} render={({ field }) => (
          <Select disabled={isLoadingEnseignants} value={field.value}
            onValueChange={(v) => {
              field.onChange(v);
              setSelectedEnseignantId(v);
            }}>
            <SelectTrigger id="seance-enseignant" className="w-full">
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
        {soldeAffectation && (
          <p className={`text-xs font-medium flex items-center gap-1 tabular-nums ${classeSolde}`}>
            {soldeAffectation.restantes <= 0 && <AlertTriangle className="size-3 shrink-0" aria-hidden />}
            {soldeAffectation.restantes < 0
              ? `Dépassement de ${formatNombreHeures(-soldeAffectation.restantes)} sur ses ${formatNombreHeures(soldeAffectation.prevues)} de ${soldeAffectation.type ?? 'cours'} prévues`
              : `Il lui reste ${formatNombreHeures(soldeAffectation.restantes)} de ${soldeAffectation.type ?? 'cours'} sur ${formatNombreHeures(soldeAffectation.prevues)} prévues`}
          </p>
        )}
      </div>

      {/* Type de séance */}
      <div className="space-y-2">
        <Label htmlFor="seance-type">Type de séance</Label>
        <Controller name="type_seance" control={control} render={({ field }) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger id="seance-type" className="w-full"><SelectValue placeholder="Sélectionnez un type" /></SelectTrigger>
            <SelectContent>
              {Object.values(TYPE_SEANCE).map((type) => (
                <SelectItem key={type} value={type}>{type}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
        {errors.type_seance && <p className="text-xs text-destructive">{errors.type_seance.message}</p>}
      </div>

      {/* Date */}
      <div className="space-y-2">
        <Label htmlFor="seance-date">Date de la séance</Label>
        <Input id="seance-date" type="date"
          min={new Date().toISOString().split('T')[0]}
          {...register('date_seance')} />
        {errors.date_seance && <p className="text-xs text-destructive">{errors.date_seance.message}</p>}
      </div>

      {/* Heures de début et de fin, côte à côte */}
      <div className="space-y-2">
        <Label htmlFor="seance-debut">Heure de début</Label>
        <Input id="seance-debut" type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_debut')} />
        {errors.heure_debut && <p className="text-xs text-destructive">{errors.heure_debut.message}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="seance-fin">Heure de fin</Label>
        <Input id="seance-fin" type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_fin')} />
        {errors.heure_fin && <p className="text-xs text-destructive">{errors.heure_fin.message}</p>}
      </div>

      {/* Erreur serveur (conflit, dépassement…), juste au-dessus des boutons */}
      <div className="md:col-span-2 empty:hidden">
        <ErreurFormulaire message={serverError} />
      </div>

      <div className="md:col-span-2 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={isPending}>
            Annuler
          </Button>
        )}
        <Button type="submit" disabled={isPending}>
          {isPending ? 'Enregistrement…' : 'Enregistrer la séance'}
        </Button>
      </div>

    </form>
  );
}
