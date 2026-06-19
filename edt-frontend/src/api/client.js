import axios from 'axios';
import useAuthStore from '@/store/authStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;   // ← corrigé
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
        const refreshToken = useAuthStore.getState().refreshToken;  // ← corrigé

        if (!refreshToken) {
          throw new Error('Aucun refresh token disponible dans le store.');
        }

        const baseURL = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
        const response = await axios.post(
          `${baseURL}/token/refresh/`,
          { refresh: refreshToken }
        );

        const newAccessToken = response.data.access;
        useAuthStore.getState().setAccessToken(newAccessToken);  // ← corrigé

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);

      } catch (refreshError) {
        console.error('Échec du refresh token — déconnexion forcée.', refreshError);
        useAuthStore.getState().clearAuth();  // ← corrigé
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;