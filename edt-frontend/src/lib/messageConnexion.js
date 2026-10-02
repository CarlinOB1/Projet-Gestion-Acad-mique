// Message affiché par la page de connexion après une déconnexion forcée
// (compte suspendu, session expirée). La déconnexion recharge toute la page :
// le message passe donc par sessionStorage (cet onglet seulement), et la page
// de connexion l'efface dès qu'elle l'a affiché.
const CLE = 'edt-message-connexion';

export function noterMessageConnexion(message) {
  try {
    sessionStorage.setItem(CLE, message);
  } catch {
    // Stockage indisponible (navigation privée stricte) : pas de message.
  }
}

export function lireMessageConnexion() {
  try {
    return sessionStorage.getItem(CLE);
  } catch {
    return null;
  }
}

export function effacerMessageConnexion() {
  try {
    sessionStorage.removeItem(CLE);
  } catch {
    // Rien à effacer.
  }
}
