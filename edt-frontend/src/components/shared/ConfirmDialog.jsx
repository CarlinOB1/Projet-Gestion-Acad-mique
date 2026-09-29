/**
 * src/components/shared/ConfirmDialog.jsx
 *
 * Hôte de la boîte de confirmation ouverte par confirmer() (@/lib/confirmer),
 * en remplacement de window.confirm() : fenêtre du navigateur, hors charte,
 * sans bouton distinct pour une action destructive. À monter une fois
 * (AppShell).
 */
import { useEffect, useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { brancherHoteConfirmation } from '@/lib/confirmer';

export function ConfirmDialogHost() {
  const [demande, setDemande] = useState(null);

  useEffect(() => {
    brancherHoteConfirmation(setDemande);
    return () => brancherHoteConfirmation(null);
  }, []);

  // resolve() n'agit qu'une fois : le second appel (fermeture déclenchée par
  // Radix juste après le clic sur « Confirmer ») est sans effet.
  const repondre = (valeur) => {
    demande?.resolve(valeur);
    setDemande(null);
  };

  return (
    <AlertDialog open={!!demande} onOpenChange={(ouvert) => { if (!ouvert) repondre(false); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{demande?.titre}</AlertDialogTitle>
          {demande?.description && (
            <AlertDialogDescription className="whitespace-pre-line">
              {demande.description}
            </AlertDialogDescription>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{demande?.libelleAnnuler ?? 'Annuler'}</AlertDialogCancel>
          <AlertDialogAction
            variant={demande?.destructif ? 'destructive' : 'default'}
            onClick={() => repondre(true)}
          >
            {demande?.libelleConfirmer ?? 'Confirmer'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
