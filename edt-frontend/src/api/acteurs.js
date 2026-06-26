import apiClient, { extractData } from "@/api/client";

// ==========================================
// ENSEIGNANTS
// ==========================================

export const getEnseignants = async (params) => {
  const response = await apiClient.get('/enseignants/', { params });
  return response.data?.results ?? response.data;
};

export const getEnseignantById = async (id) => {
  const response = await apiClient.get(`/enseignants/${id}/`);
  return response.data;
};

export const createEnseignant = async (data) => {
  const response = await apiClient.post("/enseignants/", data);
  return response.data;
};

export const updateEnseignant = async (id, data) => {
  const response = await apiClient.patch(`/enseignants/${id}/`, data);
  return response.data;
};

export const removeEnseignant = async (id) => {
  const response = await apiClient.delete(`/enseignants/${id}/`);
  return response.data;
};

// ==========================================
// ÉTUDIANTS
// ==========================================

export const getEtudiants = async (params) => {
  const response = await apiClient.get('/etudiants/', { params });
  return response.data?.results ?? response.data;
};

export const getEtudiantById = async (id) => {
  const response = await apiClient.get(`/etudiants/${id}/`);
  return response.data;
};

export const createEtudiant = async (data) => {
  const response = await apiClient.post("/etudiants/", data);
  return response.data;
};

export const updateEtudiant = async (id, data) => {
  const response = await apiClient.patch(`/etudiants/${id}/`, data);
  return response.data;
};

export const removeEtudiant = async (id) => {
  const response = await apiClient.delete(`/etudiants/${id}/`);
  return response.data;
};

// ==========================================
// PROFILS
// ==========================================

export const getProfils = async (params) => {
  const response = await apiClient.get('/profils/', { params });
  return response.data?.results ?? response.data;
};

export const getProfilById = async (id) => {
  const response = await apiClient.get(`/profils/${id}/`);
  return response.data;
};

export const createProfil = async (data) => {
  const response = await apiClient.post("/profils/", data);
  return response.data;
};

export const updateProfil = async (id, data) => {
  const response = await apiClient.patch(`/profils/${id}/`, data);
  return response.data;
};

export const removeProfil = async (id) => {
  const response = await apiClient.delete(`/profils/${id}/`);
  return response.data;
};

/**
 * Action spéciale : Change le statut d'un profil (ex: actif, suspendu).
 * @param {string|number} profilId
 * @param {Object} data
 * @param {"actif"|"suspendu"} data.statut
 * @param {string} [data.motif_suspension]
 * @returns {Promise<Object>}
 */
export const changerStatutProfil = async (profilId, data) => {
  const response = await apiClient.patch(
    `/profils/${profilId}/changer_statut/`,
    data,
  );
  return response.data;
};
