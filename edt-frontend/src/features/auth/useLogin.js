// Hook de mutation login — appel API, mise à jour du store, parsing des erreurs
import { useMutation } from '@tanstack/react-query';
import useAuthStore from '@/store/authStore';
import { login } from '@/api/auth';

/**
 * Parse les erreurs d'authentification Axios/Django en message lisible en français.
 * @param {Object} error - Objet erreur Axios
 * @returns {string}
 */
export function parseLoginError(error) {
  if (error?.response?.data) {
    const { non_field_errors, detail } = error.response.data;

    if (Array.isArray(non_field_errors) && non_field_errors.length > 0) {
      return non_field_errors[0];
    }
    if (detail) {
      return detail;
    }
  }

  if (error?.request) {
    return "Impossible de joindre le serveur. Veuillez vérifier votre connexion.";
  }

  return "Une erreur inattendue est survenue lors de la connexion.";
}

/**
 * Hook de mutation pour le login.
 * Met à jour authStore via getState() — pas d'abonnement réactif dans onSuccess.
 * La navigation est gérée côté composant via la réactivité de isAuthenticated.
 * @returns {import('@tanstack/react-query').UseMutationResult}
 */
export function useLogin() {
  return useMutation({
    mutationFn: ({ username, password }) => login(username, password),

    onSuccess: (response) => {
      const { access, refresh, user } = response.data;
      // Nettoyage préventif du store avant d'écrire les nouvelles données
      // pour éviter qu'un ancien rôle en cache ne persiste
      useAuthStore.getState().clearAuth();
      useAuthStore.getState().setAuth({
        accessToken:  access,
        refreshToken: refresh,
        user,
      });
    },
  });
}