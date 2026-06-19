/**
 * @file StatutDrawer.jsx
 * @description Drawer partagé pour la modification de statut d'un acteur (Enseignant / Étudiant).
 * Permet soit la suspension avec saisie de motif obligatoire, soit la réactivation directe.
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';

// API Services
import { changerStatutProfil } from '@/api/acteurs';

// UI Components
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

// --- SCHEMAS DE VALIDATION ZOD ---

const suspendSchema = z.object({
  motif_suspension: z
    .string()
    .min(5, "Motif requis (5 car. min.)")
    .max(255, "Le motif est trop long (255 car. max.)"),
});

const reactivateSchema = z.object({});

export default function StatutDrawer({ open, onClose, profil, queryKeyToInvalidate }) {
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState(null);

  // Détermination du mode d'action selon le statut actuel du profil
  const isSuspension = profil?.statut === 'actif';
  const currentSchema = isSuspension ? suspendSchema : reactivateSchema;

  // Configuration de React Hook Form
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm({
    resolver: zodResolver(currentSchema),
    defaultValues: {
      motif_suspension: '',
    },
  });

  // Reset de l'état du formulaire à l'ouverture/changement de profil
  useEffect(() => {
    if (open) {
      reset({ motif_suspension: '' });
      setServerError(null);
    }
  }, [open, profil, reset]);

  // --- MUTATION TANSTACK QUERY V5 ---

  const mutation = useMutation({
    mutationFn: (payload) => changerStatutProfil(profil?.user_id, payload),
    onSuccess: () => {
      // Invalidation dynamique du cache selon le contexte parent
      if (queryKeyToInvalidate) {
        queryClient.invalidateQueries({ queryKey: queryKeyToInvalidate });
      }
      onClose();
    },
    onError: (error) => {
      setServerError(parseApiError(error));
    },
  });

  // --- HANDLER DE SOUMISSION ---

  const onSubmit = (data) => {
    setServerError(null);

    if (isSuspension) {
      mutation.mutate({
        statut: 'suspendu',
        motif_suspension: data.motif_suspension,
      });
    } else {
      mutation.mutate({
        statut: 'actif',
      });
    }
  };

  return (
    <Drawer open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DrawerContent>
        <div className="mx-auto w-full max-w-md p-6">
          
          <DrawerHeader className="px-0">
            <DrawerTitle>
              {isSuspension ? 'Suspendre le profil' : 'Réactiver le profil'}
            </DrawerTitle>
            <DrawerDescription className="text-base font-semibold text-foreground pt-1">
              {profil?.nom_complet || 'Utilisateur'}
            </DrawerDescription>
          </DrawerHeader>

          {/* Conteneur de formulaire sans balise HTML <form> suite aux contraintes */}
          <div className="space-y-4 py-4">
            {serverError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded text-sm font-medium">
                {serverError}
              </div>
            )}

            {isSuspension ? (
              // Mode Suspension : Formulaire de saisie obligatoire
              <div className="grid gap-2">
                <Label htmlFor="motif_suspension">Motif de la suspension</Label>
                <Input
                  id="motif_suspension"
                  placeholder="Ex: Absences répétées non justifiées..."
                  {...register('motif_suspension')}
                  disabled={mutation.isPending}
                />
                {errors.motif_suspension && (
                  <p className="text-xs font-medium text-destructive">
                    {errors.motif_suspension.message}
                  </p>
                )}
              </div>
            ) : (
              // Mode Réactivation : Lecture seule informative
              <div className="space-y-3 text-sm text-muted-foreground">
                <p>Le profil est actuellement suspendu pour le motif suivant :</p>
                <blockquote className="border-l-2 border-red-500 pl-3 italic bg-muted p-2.5 rounded text-foreground">
                  {profil?.motif_suspension || 'Aucun motif renseigné.'}
                </blockquote>
                <p className="text-xs">
                  La réactivation rétablira instantanément tous les accès de cet utilisateur à la plateforme.
                </p>
              </div>
            )}
          </div>

          <DrawerFooter className="flex-row justify-end gap-2 px-0 pt-4 border-t">
            <Button 
              variant="outline" 
              onClick={onClose} 
              disabled={mutation.isPending}
            >
              Annuler
            </Button>
            
            <Button
              onClick={handleSubmit(onSubmit)}
              disabled={mutation.isPending}
              variant={isSuspension ? 'destructive' : 'default'}
              className={!isSuspension ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
            >
              {mutation.isPending 
                ? 'Traitement...' 
                : isSuspension 
                ? 'Confirmer la suspension' 
                : 'Confirmer la réactivation'
              }
            </Button>
          </DrawerFooter>

        </div>
      </DrawerContent>
    </Drawer>
  );
}

// --- FONCTION LOCALE D'ANALYSE DES ERREURS API ---

/**
 * Extrait un message d'erreur propre depuis la réponse Django REST Framework.
 * @param {Object} error - L'objet d'erreur intercepté par Axios.
 * @returns {string} Message d'erreur utilisateur.
 */
function parseApiError(error) {
  if (error?.response?.data) {
    const data = error.response.data;
    
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    if (data.message) return data.message;
    
    // Si Django renvoie des erreurs de validation par champ ({ motif_suspension: ["..."] })
    const firstKey = Object.keys(data)[0];
    if (firstKey) {
      const fieldError = data[firstKey];
      return Array.isArray(fieldError) ? fieldError[0] : fieldError;
    }
  }
  return error?.message || "Une erreur réseau ou serveur est survenue.";
}