/**
 * src/components/shared/FormModal.jsx
 * * Modale de formulaire générique et réutilisable basée sur le Dialog de shadcn/ui.
 * Gère les états de validation, de chargement (pending) et les actions destructives.
 */

import React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export default function FormModal({
  open,
  onClose,
  title,
  description = null,
  children,
  onConfirm,
  confirmLabel = "Enregistrer",
  isPending = false,
  isDestructive = false,
}) {
  /**
   * Intercepte la soumission pour éviter les rechargements de page 
   * si la modale est englobée par un tag <form> natif
   */
  const handleConfirm = (e) => {
    e.preventDefault();
    if (onConfirm) {
      onConfirm();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-lg gap-6">
        
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold tracking-tight">
            {title}
          </DialogTitle>
          {description && (
            <DialogDescription className="text-sm text-muted-foreground mt-1">
              {description}
            </DialogDescription>
          )}
        </DialogHeader>

        {/* Corps de la modale avec défilement interne sécurisé pour les longs formulaires */}
        <div className="overflow-y-auto max-h-[60vh] pr-1 -mr-1 py-1">
          {children}
        </div>

        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isPending}
          >
            Annuler
          </Button>
          
          <Button
            type="button"
            variant={isDestructive ? "destructive" : "default"}
            onClick={handleConfirm}
            disabled={isPending}
            className="min-w-[100px]"
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Veuillez patienter
              </>
            ) : (
              confirmLabel
            )}
          </Button>
        </DialogFooter>

      </DialogContent>
    </Dialog>
  );
}