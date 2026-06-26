import apiClient, { extractData } from '@/api/client';

export const getSeances = async (params = {}) => {
  const response = await apiClient.get('/seances/', { params });
  return response.data?.results ?? response.data;
};

export const getMonPlanningEnseignant = async (params = {}) => {
  const response = await apiClient.get('/enseignants/mon_planning/', { params });
  return response.data?.results ?? response.data;
};

export const getMonPlanningEtudiant = async (params = {}) => {
  const response = await apiClient.get('/etudiants/mon_planning/', { params });
  return response.data?.results ?? response.data;
};

/**
 * Crée une nouvelle séance.
 * @param {Object} data
 * @returns {Promise<Object>}
 */
export const createSeance = async (data) => {
  const response = await apiClient.post('/seances/', data);
  return response.data;
};

/**
 * Met à jour partiellement une séance existante.
 * @param {string|number} id
 * @param {Object} data
 * @returns {Promise<Object>}
 */
export const updateSeance = async (id, data) => {
  const response = await apiClient.patch(`/seances/${id}/`, data);
  return response.data;
};

/**
 * Supprime une séance.
 * @param {string|number} id
 * @returns {Promise<any>}
 */
export const deleteSeance = async (id) => {
  const response = await apiClient.delete(`/seances/${id}/`);
  return response.data;
};

/**
 * Reporte une séance vers un nouveau créneau.
 * @param {string|number} id
 * @param {{ date_report, heure_debut_report, heure_fin_report }} data
 * @returns {Promise<Object>}
 */
export const reporterSeance = async (id, data) => {
  const response = await apiClient.patch(`/seances/${id}/reporter/`, data);
  return response.data;
};