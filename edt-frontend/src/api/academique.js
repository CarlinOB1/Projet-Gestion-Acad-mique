import apiClient from '@/api/client';

// =========================================================================
// FACULTÉS
// =========================================================================

/**
 * Récupère la liste des facultés.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des facultés.
 */
export const getFacultes = async (params) => {
  const response = await apiClient.get('/facultes/', { params });
  return response.data;
};

/**
 * Récupère une faculté spécifique par son identifiant.
 * @param {number|string} id - L'identifiant de la faculté.
 * @returns {Promise<any>} Données de la faculté.
 */
export const getFaculteById = async (id) => {
  const response = await apiClient.get(`/facultes/${id}/`);
  return response.data;
};

/**
 * Crée une nouvelle faculté.
 * @param {Object} data - Les données de la faculté à créer.
 * @returns {Promise<any>} La faculté créée.
 */
export const createFaculte = async (data) => {
  const response = await apiClient.post('/facultes/', data);
  return response.data;
};

/**
 * Modifie partiellement une faculté existante.
 * @param {number|string} id - L'identifiant de la faculté.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} La faculté mise à jour.
 */
export const updateFaculte = async (id, data) => {
  const response = await apiClient.patch(`/facultes/${id}/`, data);
  return response.data;
};

/**
 * Supprime une faculté.
 * @param {number|string} id - L'identifiant de la faculté à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeFaculte = async (id) => {
  const response = await apiClient.delete(`/facultes/${id}/`);
  return response.data;
};


// =========================================================================
// DÉPARTEMENTS
// =========================================================================

/**
 * Récupère la liste des départements.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des départements.
 */
export const getDepartements = async (params) => {
  const response = await apiClient.get('/departements/', { params });
  return response.data;
};

/**
 * Récupère un département spécifique par son identifiant.
 * @param {number|string} id - L'identifiant du département.
 * @returns {Promise<any>} Données du département.
 */
export const getDepartementById = async (id) => {
  const response = await apiClient.get(`/departements/${id}/`);
  return response.data;
};

/**
 * Crée un nouveau département.
 * @param {Object} data - Les données du département à créer.
 * @returns {Promise<any>} Le département créé.
 */
export const createDepartement = async (data) => {
  const response = await apiClient.post('/departements/', data);
  return response.data;
};

/**
 * Modifie partiellement un département existant.
 * @param {number|string} id - L'identifiant du département.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} Le département mis à jour.
 */
export const updateDepartement = async (id, data) => {
  const response = await apiClient.patch(`/departements/${id}/`, data);
  return response.data;
};

/**
 * Supprime un département.
 * @param {number|string} id - L'identifiant du département à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeDepartement = async (id) => {
  const response = await apiClient.delete(`/departements/${id}/`);
  return response.data;
};


// =========================================================================
// FILIÈRES
// =========================================================================

/**
 * Récupère la liste des filières.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des filières.
 */
export const getFilieres = async (params) => {
  const response = await apiClient.get('/filieres/', { params });
  return response.data;
};

/**
 * Récupère une filière spécifique par son identifiant.
 * @param {number|string} id - L'identifiant de la filière.
 * @returns {Promise<any>} Données de la filière.
 */
export const getFiliereById = async (id) => {
  const response = await apiClient.get(`/filieres/${id}/`);
  return response.data;
};

/**
 * Crée une nouvelle filière.
 * @param {Object} data - Les données de la filière à créer.
 * @returns {Promise<any>} La filière créée.
 */
export const createFiliere = async (data) => {
  const response = await apiClient.post('/filieres/', data);
  return response.data;
};

/**
 * Modifie partiellement une filière existante.
 * @param {number|string} id - L'identifiant de la filière.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} La filière mise à jour.
 */
export const updateFiliere = async (id, data) => {
  const response = await apiClient.patch(`/filieres/${id}/`, data);
  return response.data;
};

/**
 * Supprime une filière.
 * @param {number|string} id - L'identifiant de la filière à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeFiliere = async (id) => {
  const response = await apiClient.delete(`/filieres/${id}/`);
  return response.data;
};


// =========================================================================
// PARCOURS
// =========================================================================

/**
 * Récupère la liste des parcours.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des parcours.
 */
export const getParcours = async (params) => {
  const response = await apiClient.get('/parcours/', { params });
  return response.data;
};

/**
 * Récupère un parcours spécifique par son identifiant.
 * @param {number|string} id - L'identifiant du parcours.
 * @returns {Promise<any>} Données du parcours.
 */
export const getParcoursById = async (id) => {
  const response = await apiClient.get(`/parcours/${id}/`);
  return response.data;
};

/**
 * Crée un nouveau parcours.
 * @param {Object} data - Les données du parcours à créer.
 * @returns {Promise<any>} Le parcours créé.
 */
export const createParcours = async (data) => {
  const response = await apiClient.post('/parcours/', data);
  return response.data;
};

/**
 * Modifie partiellement un parcours existant.
 * @param {number|string} id - L'identifiant du parcours.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} Le parcours mis à jour.
 */
export const updateParcours = async (id, data) => {
  const response = await apiClient.patch(`/parcours/${id}/`, data);
  return response.data;
};

/**
 * Supprime un parcours.
 * @param {number|string} id - L'identifiant du parcours à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeParcours = async (id) => {
  const response = await apiClient.delete(`/parcours/${id}/`);
  return response.data;
};


// =========================================================================
// ANNÉES ACADÉMIQUES
// =========================================================================

/**
 * Récupère la liste des années académiques.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des années académiques.
 */
export const getAnnees = async (params) => {
  const response = await apiClient.get('/annees/', { params });
  return response.data;
};

/**
 * Récupère une année académique spécifique par son identifiant.
 * @param {number|string} id - L'identifiant de l'année.
 * @returns {Promise<any>} Données de l'année académique.
 */
export const getAnneeById = async (id) => {
  const response = await apiClient.get(`/annees/${id}/`);
  return response.data;
};

/**
 * Crée une nouvelle année académique.
 * @param {Object} data - Les données de l'année à créer.
 * @returns {Promise<any>} L'année académique créée.
 */
export const createAnnee = async (data) => {
  const response = await apiClient.post('/annees/', data);
  return response.data;
};

/**
 * Modifie partiellement une année académique existante.
 * @param {number|string} id - L'identifiant de l'année.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} L'année académique mise à jour.
 */
export const updateAnnee = async (id, data) => {
  const response = await apiClient.patch(`/annees/${id}/`, data);
  return response.data;
};

/**
 * Supprime une année académique.
 * @param {number|string} id - L'identifiant de l'année à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeAnnee = async (id) => {
  const response = await apiClient.delete(`/annees/${id}/`);
  return response.data;
};

/**
 * Archive une année académique spécifique.
 * @param {number|string} id - L'identifiant de l'année à archiver.
 * @returns {Promise<any>} Données renvoyées par l'action d'archivage.
 */
export const archiverAnnee = async (id) => {
  const response = await apiClient.post(`/annees/${id}/archiver/`);
  return response.data;
};


// =========================================================================
// SEMESTRES
// =========================================================================

/**
 * Récupère la liste des semestres.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des semestres.
 */
export const getSemestres = async (params) => {
  const response = await apiClient.get('/semestres/', { params });
  return response.data;
};

/**
 * Récupère un semestre spécifique par son identifiant.
 * @param {number|string} id - L'identifiant du semestre.
 * @returns {Promise<any>} Données du semestre.
 */
export const getSemestreById = async (id) => {
  const response = await apiClient.get(`/semestres/${id}/`);
  return response.data;
};

/**
 * Crée un nouveau semestre.
 * @param {Object} data - Les données du semestre à créer.
 * @returns {Promise<any>} Le semestre créé.
 */
export const createSemestre = async (data) => {
  const response = await apiClient.post('/semestres/', data);
  return response.data;
};

/**
 * Modifie partiellement un semestre existant.
 * @param {number|string} id - L'identifiant du semestre.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} Le semestre mis à jour.
 */
export const updateSemestre = async (id, data) => {
  const response = await apiClient.patch(`/semestres/${id}/`, data);
  return response.data;
};

/**
 * Supprime un semestre.
 * @param {number|string} id - L'identifiant du semestre à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeSemestre = async (id) => {
  const response = await apiClient.delete(`/semestres/${id}/`);
  return response.data;
};


// =========================================================================
// CLASSES
// =========================================================================

/**
 * Récupère la liste des classes.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des classes.
 */
export const getClasses = async (params) => {
  const response = await apiClient.get('/classes/', { params });
  return response.data;
};

/**
 * Récupère une classe spécifique par son identifiant.
 * @param {number|string} id - L'identifiant de la classe.
 * @returns {Promise<any>} Données de la classe.
 */
export const getClasseById = async (id) => {
  const response = await apiClient.get(`/classes/${id}/`);
  return response.data;
};

/**
 * Crée une nouvelle classe.
 * @param {Object} data - Les données de la classe à créer.
 * @returns {Promise<any>} La classe créée.
 */
export const createClasse = async (data) => {
  const response = await apiClient.post('/classes/', data);
  return response.data;
};

/**
 * Modifie partiellement une classe existante.
 * @param {number|string} id - L'identifiant de la classe.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} La classe mise à jour.
 */
export const updateClasse = async (id, data) => {
  const response = await apiClient.patch(`/classes/${id}/`, data);
  return response.data;
};

/**
 * Supprime une classe.
 * @param {number|string} id - L'identifiant de la classe à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeClasse = async (id) => {
  const response = await apiClient.delete(`/classes/${id}/`);
  return response.data;
};

/**
 * Fait passer une classe à un semestre cible spécifique.
 * @param {number|string} classeId - L'identifiant de la classe concernée.
 * @param {number|string} semestreCibleId - L'identifiant du semestre de destination.
 * @returns {Promise<any>} Données renvoyées après la transition de semestre.
 */
export const passerSemestre = async (classeId, semestreCibleId) => {
  const response = await apiClient.post(`/classes/${classeId}/passer_semestre/`, {
    semestre_cible_id: semestreCibleId,
  });
  return response.data;
};


// =========================================================================
// MATIÈRES
// =========================================================================

/**
 * Récupère la liste des matières.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des matières.
 */
export const getMatieres = async (params) => {
  const response = await apiClient.get('/matieres/', { params });
  return response.data;
};

/**
 * Récupère une matière spécifique par son identifiant.
 * @param {number|string} id - L'identifiant de la matière.
 * @returns {Promise<any>} Données de la matière.
 */
export const getMatiereById = async (id) => {
  const response = await apiClient.get(`/matieres/${id}/`);
  return response.data;
};

/**
 * Crée une nouvelle matière.
 * @param {Object} data - Les données de la matière à créer.
 * @returns {Promise<any>} La matière créée.
 */
export const createMatiere = async (data) => {
  const response = await apiClient.post('/matieres/', data);
  return response.data;
};

/**
 * Modifie partiellement une matière existante.
 * @param {number|string} id - L'identifiant de la matière.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} La matière mise à jour.
 */
export const updateMatiere = async (id, data) => {
  const response = await apiClient.patch(`/matieres/${id}/`, data);
  return response.data;
};

/**
 * Supprime une matière.
 * @param {number|string} id - L'identifiant de la matière à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeMatiere = async (id) => {
  const response = await apiClient.delete(`/matieres/${id}/`);
  return response.data;
};


// =========================================================================
// MODULES
// =========================================================================

/**
 * Récupère la liste des modules.
 * @param {Object} [params] - Paramètres de recherche, filtrage ou pagination.
 * @returns {Promise<any>} Liste des modules.
 */
export const getModules = async (params) => {
  const response = await apiClient.get('/modules/', { params });
  return response.data;
};

/**
 * Récupère un module spécifique par son identifiant.
 * @param {number|string} id - L'identifiant du module.
 * @returns {Promise<any>} Données du module.
 */
export const getModuleById = async (id) => {
  const response = await apiClient.get(`/modules/${id}/`);
  return response.data;
};

/**
 * Crée un nouveau module.
 * @param {Object} data - Les données du module à créer.
 * @returns {Promise<any>} Le module créé.
 */
export const createModule = async (data) => {
  const response = await apiClient.post('/modules/', data);
  return response.data;
};

/**
 * Modifie partiellement un module existant.
 * @param {number|string} id - L'identifiant du module.
 * @param {Object} data - Les modifications à appliquer.
 * @returns {Promise<any>} Le module mis à jour.
 */
export const updateModule = async (id, data) => {
  const response = await apiClient.patch(`/modules/${id}/`, data);
  return response.data;
};

/**
 * Supprime un module.
 * @param {number|string} id - L'identifiant du module à supprimer.
 * @returns {Promise<any>} Données de confirmation de suppression.
 */
export const removeModule = async (id) => {
  const response = await apiClient.delete(`/modules/${id}/`);
  return response.data;
};