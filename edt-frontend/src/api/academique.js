import apiClient from "@/api/client";

/**
 * Extrait le tableau de données depuis une réponse DRF,
 * qu'elle soit paginée ({ results: [...] }) ou non ([...]).
 */
const extractList = (response) => {
  const data = response.data;
  return Array.isArray(data) ? data : (data?.results ?? []);
};

// =========================================================================
// FACULTÉS
// =========================================================================

export const getFacultes = async (params) => {
  const response = await apiClient.get("/facultes/", { params });
  return extractList(response);
};

export const getFaculteById = async (id) => {
  const response = await apiClient.get(`/facultes/${id}/`);
  return response.data;
};

export const createFaculte = async (data) => {
  const response = await apiClient.post("/facultes/", data);
  return response.data;
};

export const updateFaculte = async (id, data) => {
  const response = await apiClient.patch(`/facultes/${id}/`, data);
  return response.data;
};

export const removeFaculte = async (id) => {
  const response = await apiClient.delete(`/facultes/${id}/`);
  return response.data;
};

// =========================================================================
// DÉPARTEMENTS
// =========================================================================

export const getDepartements = async (params) => {
  const response = await apiClient.get("/departements/", { params });
  return extractList(response);
};

export const getDepartementById = async (id) => {
  const response = await apiClient.get(`/departements/${id}/`);
  return response.data;
};

export const createDepartement = async (data) => {
  const response = await apiClient.post("/departements/", data);
  return response.data;
};

export const updateDepartement = async (id, data) => {
  const response = await apiClient.patch(`/departements/${id}/`, data);
  return response.data;
};

export const removeDepartement = async (id) => {
  const response = await apiClient.delete(`/departements/${id}/`);
  return response.data;
};

// =========================================================================
// FILIÈRES
// =========================================================================

export const getFilieres = async (params) => {
  const response = await apiClient.get("/filieres/", { params });
  return extractList(response);
};

export const getFiliereById = async (id) => {
  const response = await apiClient.get(`/filieres/${id}/`);
  return response.data;
};

export const createFiliere = async (data) => {
  const response = await apiClient.post("/filieres/", data);
  return response.data;
};

export const updateFiliere = async (id, data) => {
  const response = await apiClient.patch(`/filieres/${id}/`, data);
  return response.data;
};

export const removeFiliere = async (id) => {
  const response = await apiClient.delete(`/filieres/${id}/`);
  return response.data;
};

// =========================================================================
// PARCOURS
// =========================================================================

export const getParcours = async (params) => {
  const response = await apiClient.get("/parcours/", { params });
  return extractList(response);
};

export const getParcoursById = async (id) => {
  const response = await apiClient.get(`/parcours/${id}/`);
  return response.data;
};

export const createParcours = async (data) => {
  const response = await apiClient.post("/parcours/", data);
  return response.data;
};

export const updateParcours = async (id, data) => {
  const response = await apiClient.patch(`/parcours/${id}/`, data);
  return response.data;
};

export const removeParcours = async (id) => {
  const response = await apiClient.delete(`/parcours/${id}/`);
  return response.data;
};

// =========================================================================
// ANNÉES ACADÉMIQUES
// =========================================================================

export const getAnnees = async (params) => {
  const response = await apiClient.get("/annees/", { params });
  return extractList(response);
};

export const getAnneeById = async (id) => {
  const response = await apiClient.get(`/annees/${id}/`);
  return response.data;
};

export const createAnnee = async (data) => {
  const response = await apiClient.post("/annees/", data);
  return response.data;
};

export const updateAnnee = async (id, data) => {
  const response = await apiClient.patch(`/annees/${id}/`, data);
  return response.data;
};

export const removeAnnee = async (id) => {
  const response = await apiClient.delete(`/annees/${id}/`);
  return response.data;
};

export const archiverAnnee = async (id) => {
  const response = await apiClient.post(`/annees/${id}/archiver/`);
  return response.data;
};

// =========================================================================
// SEMESTRES
// =========================================================================

export const getSemestres = async (params) => {
  const response = await apiClient.get("/semestres/", { params });
  return response.data?.results ?? response.data;
};

export const getSemestreById = async (id) => {
  const response = await apiClient.get(`/semestres/${id}/`);
  return response.data;
};

export const createSemestre = async (data) => {
  const response = await apiClient.post("/semestres/", data);
  return response.data;
};

export const updateSemestre = async (id, data) => {
  const response = await apiClient.patch(`/semestres/${id}/`, data);
  return response.data;
};

export const removeSemestre = async (id) => {
  const response = await apiClient.delete(`/semestres/${id}/`);
  return response.data;
};

// =========================================================================
// CLASSES
// =========================================================================

export const getClasses = async (params) => {
  const response = await apiClient.get("/classes/", { params });
  return extractList(response);
};

export const getClasseById = async (id) => {
  const response = await apiClient.get(`/classes/${id}/`);
  return response.data;
};

export const createClasse = async (data) => {
  const response = await apiClient.post("/classes/", data);
  return response.data;
};

export const updateClasse = async (id, data) => {
  const response = await apiClient.patch(`/classes/${id}/`, data);
  return response.data;
};

export const removeClasse = async (id) => {
  const response = await apiClient.delete(`/classes/${id}/`);
  return response.data;
};

export const passerSemestre = async (classeId, semestreCibleId) => {
  const response = await apiClient.post(
    `/classes/${classeId}/passer_semestre/`,
    {
      semestre_cible_id: semestreCibleId,
    },
  );
  return response.data;
};

// =========================================================================
// MATIÈRES
// =========================================================================

export const getMatieres = async (params) => {
  const response = await apiClient.get("/matieres/", { params });
  return extractList(response);
};

export const getMatiereById = async (id) => {
  const response = await apiClient.get(`/matieres/${id}/`);
  return response.data;
};

export const createMatiere = async (data) => {
  const response = await apiClient.post("/matieres/", data);
  return response.data;
};

export const updateMatiere = async (id, data) => {
  const response = await apiClient.patch(`/matieres/${id}/`, data);
  return response.data;
};

export const removeMatiere = async (id) => {
  const response = await apiClient.delete(`/matieres/${id}/`);
  return response.data;
};

// =========================================================================
// MODULES
// =========================================================================

export const getModules = async (params) => {
  const response = await apiClient.get("/modules/", { params });
  return extractList(response);
};

export const getModuleById = async (id) => {
  const response = await apiClient.get(`/modules/${id}/`);
  return response.data;
};

export const createModule = async (data) => {
  const response = await apiClient.post("/modules/", data);
  return response.data;
};

export const updateModule = async (id, data) => {
  const response = await apiClient.patch(`/modules/${id}/`, data);
  return response.data;
};

export const removeModule = async (id) => {
  const response = await apiClient.delete(`/modules/${id}/`);
  return response.data;
};
