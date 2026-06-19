import apiClient from './client';
import useAuthStore from '@/store/authStore';

export async function login(username, password) {
  const response = await apiClient.post('/token/', { username, password });
  return response;
}

export async function refreshAccessToken(refreshToken) {
  const response = await apiClient.post('/token/refresh/', { refresh: refreshToken });
  return response;
}

export function logout() {
  useAuthStore.getState().clearAuth();  // ← corrigé
}