import axios from 'axios';
import useAuthStore from '@/store/authStore';


const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
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
        { refresh: refreshToken }
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

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._isRetry) {
      originalRequest._isRetry = true;

      try {
        const newAccessToken = await rafraichirLesJetons();

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);

      } catch (refreshError) {
        console.error('Échec du refresh token — déconnexion forcée.', refreshError);
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
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
 * @param {string} url
 * @param {object} [params]
 * @returns {Promise<any>}
 */
export const fetchAllPages = async (url, params = {}) => {
  let response = await apiClient.get(url, { params });
  const data = response.data;

  if (!data || typeof data !== 'object' || !Array.isArray(data.results)) {
    return data;
  }

  let results = data.results;
  let next = data.next;
  while (next) {
    response = await apiClient.get(next);
    results = results.concat(response.data?.results ?? []);
    next = response.data?.next;
  }
  return results;
};

export default apiClient;

