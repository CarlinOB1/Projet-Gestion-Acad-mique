/**
 * @file SeanceDrawer.jsx
 * @description Drawer shadcn/ui — orchestration création/édition d'une séance.
 */
import { useState, useEffect } from 'react';
import {
  Drawer, DrawerContent, DrawerHeader,
  DrawerTitle, DrawerDescription,
} from '@/components/ui/drawer';
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

  // Normalisation des IDs imbriqués en strings plats pour useForm
  const normalizedDefaults = seance ? {
    semestre_id:   String(seance.classe?.semestre?.id  ?? ''),
    filiere_id:    String(seance.classe?.filiere?.id   ?? ''),
    classe_id:     String(seance.classe?.id            ?? ''),
    module_id:     String(seance.module?.id            ?? ''),
    enseignant_id: String(seance.enseignant?.profil_id ?? ''),
    date_seance:   seance.date_seance ?? '',
    heure_debut:   seance.heure_debut?.slice(0, 5) ?? '09:00',
    heure_fin:     seance.heure_fin?.slice(0, 5)   ?? '10:30',
    type_seance:   seance.type_seance ?? 'CM',
  } : contextualDefaults ? {
    semestre_id:   semestreId ? String(semestreId) : '',
    filiere_id:    contextualDefaults.filiere_id ? String(contextualDefaults.filiere_id) : '',
    classe_id:     contextualDefaults.classe_id ? String(contextualDefaults.classe_id) : '',
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
    <Drawer open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DrawerContent>
        <div className="mx-auto w-full max-w-xl p-6 overflow-y-auto max-h-[85vh]">
          <DrawerHeader className="px-0 pt-0">
            <DrawerTitle>
              {isEditMode ? 'Modifier la séance' : 'Nouvelle séance'}
            </DrawerTitle>
            <DrawerDescription>
              {isEditMode
                ? 'Ajustez les détails de la séance sélectionnée.'
                : 'Renseignez les champs pour planifier ce cours.'}
            </DrawerDescription>
          </DrawerHeader>
          <SeanceForm
            semestreId={semestreId}
            defaultValues={normalizedDefaults}
            onSubmit={handleSubmit}
            isPending={activeMutation.isPending}
            serverError={serverError}
          />
        </div>
      </DrawerContent>
    </Drawer>
  );
}