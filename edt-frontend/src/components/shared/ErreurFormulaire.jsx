import { AlertTriangle } from '@/components/ui/icons';

/**
 * Erreur renvoyée par le serveur, affichée dans le formulaire juste au-dessus
 * des boutons. Remplace une bulle jaune qui recouvrait le bouton Enregistrer.
 */
export default function ErreurFormulaire({ message }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
    >
      <AlertTriangle className="size-4 shrink-0 mt-0.5" aria-hidden />
      <p className="text-pretty">{message}</p>
    </div>
  );
}
