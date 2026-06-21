/**
 * @file ReportDrawer.jsx
 * @description Drawer dédié au report d'une séance — 3 champs validés par Zod.
 */
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Drawer, DrawerContent, DrawerHeader,
  DrawerTitle, DrawerDescription,
} from '@/components/ui/drawer';
import { Input }  from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label }  from '@/components/ui/label';
import { useReporterSeance } from '@/hooks/useSeanceMutations';
import { HEURE_MIN, HEURE_MAX } from '@/lib/constants'; 

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

export default function ReportDrawer({ open, onClose, seance }) {
  const [serverError, setServerError] = useState(null);
  const { mutate, isPending } = useReporterSeance();

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(reportSchema),
    defaultValues: { date_report: '', heure_debut_report: HEURE_MIN, heure_fin_report: HEURE_MAX },
  });

  useEffect(() => {
    if (open) {
      setServerError(null);
      reset({ date_report: '', heure_debut_report: HEURE_MIN, heure_fin_report: HEURE_MAX });
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
    <Drawer open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DrawerContent>
        <div className="mx-auto w-full max-w-xl p-6 overflow-y-auto max-h-[85vh] space-y-5">
          <DrawerHeader className="px-0 pt-0">
            <DrawerTitle>Reporter la séance</DrawerTitle>
            <DrawerDescription>
              Module : <span className="text-foreground font-semibold">
                {seance?.module?.libelle || 'N/A'}
              </span>
            </DrawerDescription>
          </DrawerHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Nouvelle date</Label>
              <Input type="date" {...register('date_report')} />
              {errors.date_report && <p className="text-xs text-destructive">{errors.date_report.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Nouvelle heure de début</Label>
              <Input type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_debut_report')} />
              {errors.heure_debut_report && <p className="text-xs text-destructive">{errors.heure_debut_report.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Nouvelle heure de fin</Label>
              <Input type="time" min={HEURE_MIN} max={HEURE_MAX} {...register('heure_fin_report')} />
              {errors.heure_fin_report && <p className="text-xs text-destructive">{errors.heure_fin_report.message}</p>}
            </div>
          </div>

          {serverError && (
            <div className="p-3 text-sm font-medium text-destructive bg-destructive/10 rounded-lg border border-destructive/20">
              {serverError}
            </div>
          )}

          <Button className="w-full" onClick={handleSubmit(onSubmit)} disabled={isPending}>
            {isPending ? 'Report en cours...' : 'Confirmer le report'}
          </Button>
        </div>
      </DrawerContent>
    </Drawer>
  );
}