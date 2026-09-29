/**
 * @file ReportDrawer.jsx
 * @description Fenêtre de report d'une séance — 3 champs validés par Zod.
 * (Nom de fichier conservé ; c'était un tiroir sorti du bas de l'écran, seule
 * fenêtre de l'application à s'ouvrir ainsi, et sans bouton Annuler.)
 */
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { Input }  from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label }  from '@/components/ui/label';
import { useReporterSeance } from '@/hooks/useSeanceMutations';
import { HEURE_MIN, HEURE_MAX } from '@/lib/constants';
import { formatDate, formatCreneau } from '@/lib/utils';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';

const reportSchema = z.object({
  date_report:        z.string().min(1, 'La date de report est requise'),
  heure_debut_report: z.string().min(1, "L'heure de début est requise")
    .refine((v) => v >= HEURE_MIN, `L'heure de début doit être >= ${HEURE_MIN}`),
  heure_fin_report: z.string().min(1, "L'heure de fin est requise")
    .refine((v) => v <= HEURE_MAX, `L'heure de fin doit être <= ${HEURE_MAX}`),
}).refine((d) => d.heure_fin_report > d.heure_debut_report, {
  message: "L'heure de fin doit être supérieure à l'heure de début",
  path: ['heure_fin_report'],
});

const parseApiError = (error) => {
  const data = error?.response?.data;
  if (data && typeof data === 'object') {
    const values = Object.values(data).flat();
    const first  = values.find((v) => v !== null && v !== undefined && v !== '');
    if (first) return String(first);
  }
  return error?.message || 'Une erreur est survenue lors du report.';
};

// Heures de la séance reportée : un report garde le plus souvent la durée et
// le créneau d'origine. Avant, 09:00 – 16:20 (toute la journée) était proposé.
const valeursInitiales = (seance) => ({
  date_report: '',
  heure_debut_report: seance?.heure_debut?.slice(0, 5) || HEURE_MIN,
  heure_fin_report: seance?.heure_fin?.slice(0, 5) || HEURE_MAX,
});

export default function ReportDrawer({ open, onClose, seance }) {
  const [serverError, setServerError] = useState(null);
  const { mutate, isPending } = useReporterSeance();

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(reportSchema),
    defaultValues: valeursInitiales(seance),
  });

  useEffect(() => {
    if (open) {
      setServerError(null);
      reset(valeursInitiales(seance));
    }
  }, [open, seance, reset]);

  const onSubmit = (formData) => {
    if (!seance?.id) return;
    setServerError(null);
    mutate({ id: seance.id, data: formData }, {
      onSuccess: () => onClose(),
      onError:   (err) => setServerError(parseApiError(err)),
    });
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <DialogHeader>
            <DialogTitle>Reporter la séance</DialogTitle>
            <DialogDescription className="text-pretty">
              <span className="font-medium text-foreground">{seance?.module?.libelle || 'Séance'}</span>
              {seance?.date_seance && (
                <span className="block tabular-nums">
                  Actuellement : {formatDate(seance.date_seance)} · {formatCreneau(seance.heure_debut, seance.heure_fin)}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="report-date">Nouvelle date</Label>
            <Input id="report-date" type="date" {...register('date_report')} />
            {errors.date_report && <p className="text-xs text-destructive">{errors.date_report.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="report-debut">Début</Label>
              <Input id="report-debut" type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_debut_report')} />
              {errors.heure_debut_report && <p className="text-xs text-destructive">{errors.heure_debut_report.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="report-fin">Fin</Label>
              <Input id="report-fin" type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_fin_report')} />
              {errors.heure_fin_report && <p className="text-xs text-destructive">{errors.heure_fin_report.message}</p>}
            </div>
          </div>

          <ErreurFormulaire message={serverError} />

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Annuler
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Report en cours…' : 'Reporter la séance'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
