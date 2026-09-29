/**
 * src/lib/confirmer.js
 *
 * Remplaçant de window.confirm() qui ouvre la boîte de confirmation à la
 * charte de l'application (<ConfirmDialogHost />, monté une fois dans
 * AppShell). Séparé du composant pour que Vite puisse recharger ce dernier
 * à chaud (un fichier de composant ne doit exporter que des composants).
 *
 * Usage, depuis n'importe quel gestionnaire d'événement :
 *   if (await confirmer({ titre: 'Supprimer la séance ?', destructif: true })) { ... }
 */

// Setter d'état de l'hôte monté ; null tant qu'aucun hôte ne l'est.
let afficherDemande = null;

/** Branche (ou débranche, avec null) l'hôte chargé d'afficher les demandes. */
export function brancherHoteConfirmation(setter) {
  afficherDemande = setter;
}

/**
 * Ouvre la boîte de confirmation et résout `true` si l'utilisateur confirme,
 * `false` s'il annule (bouton, Échap ou clic hors de la boîte).
 *
 * @param {{ titre: string, description?: string, libelleConfirmer?: string,
 *           libelleAnnuler?: string, destructif?: boolean }} options
 * @returns {Promise<boolean>}
 */
export function confirmer(options) {
  if (!afficherDemande) {
    // Repli si aucun hôte n'est monté (page hors AppShell).
    return Promise.resolve(window.confirm(options.description ?? options.titre));
  }
  return new Promise((resolve) => {
    afficherDemande((precedente) => {
      // Une nouvelle demande remplace celle encore ouverte : on clôt
      // proprement la précédente plutôt que de laisser sa promesse en suspens.
      precedente?.resolve(false);
      return { ...options, resolve };
    });
  });
}
