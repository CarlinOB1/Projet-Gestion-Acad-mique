/**
 * @file SeanceDrawer.jsx
 * @description Drawer shadcn/ui — orchestration création/édition d'une séance.
 */
import { useState, useEffect } from 'react';
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import SeanceForm from './SeanceForm';
import { useCreateSeance, useUpdateSeance } from '@/hooks/useSeanceMutations';

const parseApiError = (error) => {
  const data = error?.response?.data;
  if (data && typeof data === 'object') {
    const values = Object.values(data).flat();
    const first  = values.find((v) => v !== null && v !== undefined && v !== '');
    if (first) return String(first);
  }
  return error?.message || 'Une erreur serveur est survenue.';
};

export default function SeanceDrawer({ open, onClose, semestreId, seance, contextualDefaults = null }) {
  const [serverError, setServerError] = useState(null);

  const createMutation = useCreateSeance();
  const updateMutation = useUpdateSeance();
  const isEditMode     = !!seance;
  const activeMutation = isEditMode ? updateMutation : createMutation;

  useEffect(() => {
    if (open) setServerError(null);
  }, [open, seance]);

  // Classe déjà fixée par le contexte : celle de la séance modifiée, ou celle
  // de l'onglet actif du planning au moment de la création (contextualDefaults.classe).
  // Ce n'est plus un champ que le formulaire fait choisir.
  const classeContext = seance
    ? {
        id: seance.classe?.id,
        libelle: seance.classe?.libelle,
        annee_id: seance.classe?.annee?.id,
      }
    : (contextualDefaults?.classe ?? null);

  // Normalisation des IDs imbriqués en strings plats pour useForm
  const normalizedDefaults = seance ? {
    semestre_id:   String(seance.classe?.semestre?.id  ?? ''),
    classe_id:     String(seance.classe?.id            ?? ''),
    module_id:     String(seance.module?.id            ?? ''),
    enseignant_id: String(seance.enseignant?.profil_id ?? ''),
    date_seance:   seance.date_seance ?? '',
    heure_debut:   seance.heure_debut?.slice(0, 5) ?? '09:00',
    heure_fin:     seance.heure_fin?.slice(0, 5)   ?? '10:30',
    type_seance:   seance.type_seance ?? 'CM',
  } : contextualDefaults ? {
    semestre_id:   semestreId ? String(semestreId) : '',
    classe_id:     classeContext?.id ? String(classeContext.id) : '',
    module_id:     '',
    enseignant_id: '',
    date_seance:   contextualDefaults.date_seance ?? '',
    heure_debut:   contextualDefaults.heure_debut ?? '09:00',
    heure_fin:     contextualDefaults.heure_fin ?? '11:00',
    type_seance:   'CM',
  } : null;

  const handleSubmit = (formData) => {
    setServerError(null);
    const args = isEditMode ? { id: seance.id, data: formData } : formData;
    activeMutation.mutate(args, {
      onSuccess: () => onClose(),
      onError:   (err) => setServerError(parseApiError(err)),
    });
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-3xl w-[90vw] max-h-[90vh] overflow-y-auto p-8">
        <DialogHeader>
          <DialogTitle className="text-xl text-blue-900">
            {isEditMode ? 'Modifier la séance' : 'Nouvelle séance'}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? 'Ajustez les détails de la séance sélectionnée.'
              : 'Renseignez les champs pour planifier ce cours.'}
          </DialogDescription>
        </DialogHeader>
        <div className="mt-4">
          <SeanceForm
            semestreId={semestreId}
            classe={classeContext}
            defaultValues={normalizedDefaults}
            onSubmit={handleSubmit}
            isPending={activeMutation.isPending}
            serverError={serverError}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}