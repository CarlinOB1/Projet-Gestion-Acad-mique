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
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._isRetry) {
      originalRequest._isRetry = true;

      try {
        const refreshToken = useAuthStore.getState().refreshToken;

        if (!refreshToken) {
          throw new Error('Aucun refresh token disponible dans le store.');
        }

        const baseURL = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
        const response = await axios.post(
          `${baseURL}/token/refresh/`,
          { refresh: refreshToken }
        );

        const newAccessToken = response.data.access;
        useAuthStore.getState().setAccessToken(newAccessToken);

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

export default apiClient;