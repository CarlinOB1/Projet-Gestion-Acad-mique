import apiClient from '@/api/client';

// ==========================================
// ENSEIGNANTS
// ==========================================

/**
 * Récupère la liste des enseignants avec filtres optionnels.
 * @param {Object} [params] - Paramètres de filtrage et de pagination.
 * @returns {Promise<Array>} Liste des enseignants.
 */
export const getEnseignants = async (params) => {
  const response = await apiClient.get('/enseignants/', { params });
  return response.data;
};

/**
 * Récupère un enseignant par son identifiant.
 * @param {string|number} id - Identifiant de l'enseignant.
 * @returns {Promise<Object>} Détails de l'enseignant.
 */
export const getEnseignantById = async (id) => {
  const response = await apiClient.get(`/enseignants/${id}/`);
  return response.data;
};

/**
 * Crée un nouvel enseignant.
 * @param {Object} data - Données de l'enseignant à créer.
 * @returns {Promise<Object>} Enseignant créé.
 */
export const createEnseignant = async (data) => {
  const response = await apiClient.post('/enseignants/', data);
  return response.data;
};

/**
 * Met à jour partiellement un enseignant (PATCH).
 * @param {string|number} id - Identifiant de l'enseignant.
 * @param {Object} data - Données à modifier.
 * @returns {Promise<Object>} Enseignant mis à jour.
 */
export const updateEnseignant = async (id, data) => {
  const response = await apiClient.patch(`/enseignants/${id}/`, data);
  return response.data;
};

/**
 * Supprime un enseignant.
 * @param {string|number} id - Identifiant de l'enseignant.
 * @returns {Promise<void>}
 */
export const removeEnseignant = async (id) => {
  const response = await apiClient.delete(`/enseignants/${id}/`);
  return response.data;
};


// ==========================================
// ÉTUDIANTS
// ==========================================

/**
 * Récupère la liste des étudiants avec filtres optionnels.
 * @param {Object} [params] - Paramètres de filtrage et de pagination.
 * @returns {Promise<Array>} Liste des étudiants.
 */
export const getEtudiants = async (params) => {
  const response = await apiClient.get('/etudiants/', { params });
  return response.data;
};

/**
 * Récupère un étudiant par son identifiant.
 * @param {string|number} id - Identifiant de l'étudiant.
 * @returns {Promise<Object>} Détails de l'étudiant.
 */
export const getEtudiantById = async (id) => {
  const response = await apiClient.get(`/etudiants/${id}/`);
  return response.data;
};

/**
 * Crée un nouvel étudiant.
 * @param {Object} data - Données de l'étudiant à créer.
 * @returns {Promise<Object>} Étudiant créé.
 */
export const createEtudiant = async (data) => {
  const response = await apiClient.post('/etudiants/', data);
  return response.data;
};

/**
 * Met à jour partiellement un étudiant (PATCH).
 * @param {string|number} id - Identifiant de l'étudiant.
 * @param {Object} data - Données à modifier.
 * @returns {Promise<Object>} Étudiant mis à jour.
 */
export const updateEtudiant = async (id, data) => {
  const response = await apiClient.patch(`/etudiants/${id}/`, data);
  return response.data;
};

/**
 * Supprime un étudiant.
 * @param {string|number} id - Identifiant de l'étudiant.
 * @returns {Promise<void>}
 */
export const removeEtudiant = async (id) => {
  const response = await apiClient.delete(`/etudiants/${id}/`);
  return response.data;
};


// ==========================================
// PROFILS
// ==========================================

/**
 * Récupère la liste des profils avec filtres optionnels.
 * @param {Object} [params] - Paramètres de filtrage et de pagination.
 * @returns {Promise<Array>} Liste des profils.
 */
export const getProfils = async (params) => {
  const response = await apiClient.get('/profils/', { params });
  return response.data;
};

/**
 * Récupère un profil par son identifiant.
 * @param {string|number} id - Identifiant du profil.
 * @returns {Promise<Object>} Détails du profil.
 */
export const getProfilById = async (id) => {
  const response = await apiClient.get(`/profils/${id}/`);
  return response.data;
};

/**
 * Crée un nouveau profil.
 * @param {Object} data - Données du profil à créer.
 * @returns {Promise<Object>} Profil créé.
 */
export const createProfil = async (data) => {
  const response = await apiClient.post('/profils/', data);
  return response.data;
};

/**
 * Met à jour partiellement un profil (PATCH).
 * @param {string|number} id - Identifiant du profil.
 * @param {Object} data - Données à modifier.
 * @returns {Promise<Object>} Profil mis à jour.
 */
export const updateProfil = async (id, data) => {
  const response = await apiClient.patch(`/profils/${id}/`, data);
  return response.data;
};

/**
 * Supprime un profil.
 * @param {string|number} id - Identifiant du profil.
 * @returns {Promise<void>}
 */
export const removeProfil = async (id) => {
  const response = await apiClient.delete(`/profils/${id}/`);
  return response.data;
};

/**
 * Action spéciale : Change le statut d'un profil (ex: actif, suspendu).
 * @param {string|number} profilId - Identifiant du profil concerné.
 * @param {Object} data - Payload de modification du statut.
 * @param {"actif"|"suspendu"} data.statut - Le nouveau statut du profil.
 * @param {string} [data.motif_suspension] - Motif obligatoire si le statut est "suspendu".
 * @returns {Promise<Object>} Le profil mis à jour retourné par le serveur.
 */
export const changerStatutProfil = async (profilId, data) => {
  const response = await apiClient.patch(`/profils/${profilId}/changer_statut/`, data);
  return response.data;
};