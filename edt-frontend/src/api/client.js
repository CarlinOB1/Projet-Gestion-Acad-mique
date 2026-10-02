import axios from 'axios';
import useAuthStore from '@/store/authStore';
import { noterMessageConnexion } from '@/lib/messageConnexion';


// Délai maximal d'une requête. Sans lui, un serveur qui reçoit la demande
// sans jamais répondre laissait la page en chargement indéfiniment
// (CORRECTIONS_A_FAIRE.md point 42). Les envois et téléchargements de
// documents (jusqu'à 20 Mo) règlent un délai plus long sur leur appel.
export const DELAI_REQUETE_MS = 30_000;

/** Vrai si la requête a été abandonnée faute de réponse dans le délai. */
export const estDelaiDepasse = (error) =>
  error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: DELAI_REQUETE_MS,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
    },);

// Un seul rafraîchissement à la fois. Quand le jeton d'accès expire, une page
// lance plusieurs requêtes en parallèle : toutes reçoivent 401 en même temps.
// Le serveur blackliste l'ancien refresh token dès le premier rafraîchissement
// réussi ; sans ce partage, les appels suivants échoueraient et déconnecteraient
// l'utilisateur alors que sa session est valide.
let rafraichissementEnCours = null;

function rafraichirLesJetons() {
  if (!rafraichissementEnCours) {
    rafraichissementEnCours = (async () => {
      const refreshToken = useAuthStore.getState().refreshToken;

      if (!refreshToken) {
        throw new Error('Aucun refresh token disponible dans le store.');
      }

      const baseURL = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
      const response = await axios.post(
        `${baseURL}/token/refresh/`,
        { refresh: refreshToken },
        { timeout: DELAI_REQUETE_MS }
      );

      useAuthStore.getState().setTokens({
        accessToken: response.data.access,
        refreshToken: response.data.refresh,
      });
      return response.data.access;
    })().finally(() => {
      rafraichissementEnCours = null;
    });
  }
  return rafraichissementEnCours;
}

// Un 401 sur ces routes ne signifie pas « jeton d'accès expiré » : c'est la
// réponse elle-même (identifiants faux, renouvellement refusé). Tenter un
// renouvellement n'a pas de sens, et la redirection forcée rechargeait la
// page de connexion en effaçant son message d'erreur
// (CORRECTIONS_A_FAIRE.md point 40).
const ROUTES_AUTHENTIFICATION = ['/token/', '/token/refresh/'];

function estRouteAuthentification(url = '') {
  const chemin = url.split('?')[0].replace(/\/?$/, '/');
  return ROUTES_AUTHENTIFICATION.some((route) => chemin.endsWith(route));
}

// Compte suspendu pendant la session : le serveur refuse toute action (403)
// et tout renouvellement (401) avec le code `profil_suspendu`
// (EDT_app/permissions.py). Sans ce repérage, chaque page n'affichait qu'un
// « Une erreur est survenue » (CORRECTIONS_A_FAIRE.md point 41).
const estCompteSuspendu = (error) => error?.response?.data?.code === 'profil_suspendu';

const MESSAGE_COMPTE_SUSPENDU = 'Votre profil est suspendu. Contactez le responsable pédagogique.';
const MESSAGE_SESSION_EXPIREE = 'Votre session a expiré. Reconnectez-vous.';

/**
 * Vide la session et revient à la page de connexion, qui affiche `message`.
 * Le rechargement complet efface aussi les données gardées en mémoire.
 */
function deconnecter(message) {
  useAuthStore.getState().clearAuth();
  noterMessageConnexion(message);
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401
      && originalRequest
      && !originalRequest._isRetry
      && !estRouteAuthentification(originalRequest.url)
    ) {
      originalRequest._isRetry = true;

      try {
        const newAccessToken = await rafraichirLesJetons();

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);

      } catch (refreshError) {
        // Serveur injoignable ou trop lent pendant le renouvellement : la
        // session n'est pas en cause, on la garde ; la page affiche l'erreur.
        if (refreshError.response || !refreshError.isAxiosError) {
          console.error('Échec du refresh token — déconnexion forcée.', refreshError);
          deconnecter(estCompteSuspendu(refreshError) ? MESSAGE_COMPTE_SUSPENDU : MESSAGE_SESSION_EXPIREE);
        }
        return Promise.reject(refreshError);
      }
    }

    if (error.response?.status === 403 && estCompteSuspendu(error)) {
      deconnecter(MESSAGE_COMPTE_SUSPENDU);
    }

    return Promise.reject(error);
  }
);

/**
 * Extrait les données depuis une réponse API paginée ou non.
 * DRF renvoie { count, next, previous, results: [...] } quand la pagination est active.
 * Cette fonction retourne toujours le tableau brut ou l'objet selon le cas.
 *
 * @param {import('axios').AxiosResponse} response
 * @returns {any}
 */
export const extractData = (response) => {
  const data = response.data;
  // Réponse paginée DRF : { count, next, previous, results }
  if (data && typeof data === 'object' && Array.isArray(data.results)) {
    return response.data?.results ?? response.data;
  }
  // Réponse directe (tableau ou objet simple)
  return data;
};

/**
 * Récupère TOUTES les pages d'un endpoint DRF paginé et concatène les résultats.
 * DRF renvoie { count, next, previous, results } quand la pagination est active
 * (PAGE_SIZE=20 par défaut, cf. Gestion_edt/settings.py) : un simple
 * `apiClient.get(url)` ne renvoie que la première page et tronque
 * silencieusement le reste dès que la liste dépasse 20 éléments. Une réponse
 * non paginée (tableau direct, ou objet sans `results`) est renvoyée telle
 * quelle, sans requête supplémentaire.
 *
 * Les pages suivantes sont demandées en parallèle (par lots de
 * PAGES_EN_PARALLELE) : `count` et la taille de la 1re page suffisent à
 * connaître leur nombre. Les suivre une à une via `next` faisait attendre
 * chaque réponse avant la suivante — ~21 s pour les 14 pages du planning
 * d'un chef de département.
 *
 * @param {string} url
 * @param {object} [params]
 * @returns {Promise<any>}
 */
const PAGES_EN_PARALLELE = 6;

export const fetchAllPages = async (url, params = {}) => {
  const response = await apiClient.get(url, { params });
  const data = response.data;

  if (!data || typeof data !== 'object' || !Array.isArray(data.results)) {
    return data;
  }

  const taillePage = data.results.length;
  if (!data.next || taillePage === 0) {
    return data.results;
  }
  const nbPages = Math.ceil(data.count / taillePage);

  const pagesRestantes = [];
  for (let page = 2; page <= nbPages; page += 1) pagesRestantes.push(page);

  let results = data.results;
  for (let i = 0; i < pagesRestantes.length; i += PAGES_EN_PARALLELE) {
    const lot = pagesRestantes.slice(i, i + PAGES_EN_PARALLELE);
    const reponses = await Promise.all(
      lot.map((page) => apiClient.get(url, { params: { ...params, page } }))
    );
    // Promise.all conserve l'ordre du lot : les résultats restent triés.
    for (const r of reponses) results = results.concat(r.data?.results ?? []);
  }
  return results;
};

export default apiClient;

