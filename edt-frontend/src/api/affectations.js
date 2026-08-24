/**
 * @file api/affectations.js
 * @description Fonctions d'accès à l'endpoint /affectations/
 */
import apiClient from '@/api/client';

const extractList = (response) => {
  const data = response.data;
  return Array.isArray(data) ? data : (data?.results ?? []);
};

/**
 * Récupère les affectations d'un module.
 * @param {Object} params - ex: { module_id, enseignant_id }
 */
export const getAffectations = async (params = {}) => {
  const response = await apiClient.get('/affectations/', { params });
  return extractList(response);
};

/**
 * Crée une nouvelle affectation.
 * @param {{ module_id, enseignant_id, type_seance, heures_prevues }} data
 */
export const createAffectation = async (data) => {
  const response = await apiClient.post('/affectations/', data);
  return response.data;
};

/**
 * Met à jour partiellement une affectation.
 * @param {number} id
 * @param {Object} data
 */
export const updateAffectation = async (id, data) => {
  const response = await apiClient.patch(`/affectations/${id}/`, data);
  return response.data;
};

/**
 * Supprime une affectation.
 * @param {number} id
 */
export const deleteAffectation = async (id) => {
  const response = await apiClient.delete(`/affectations/${id}/`);
  return response.data;
};
