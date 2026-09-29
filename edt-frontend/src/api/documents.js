import apiClient from "./client";

export const getDocuments = async (params) => {
  const response = await apiClient.get("/documents/", { params });
  return response.data?.results ?? response.data;
};

export const createDocument = async (formData) => {
  const response = await apiClient.post("/documents/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

// Le fichier n'est plus accessible par une URL publique : on le récupère via
// l'API (avec le jeton d'authentification), puis on déclenche l'enregistrement
// depuis le navigateur. Un simple lien <a href> ne peut pas envoyer l'en-tête
// Authorization.
export const downloadDocument = async (doc) => {
  const response = await apiClient.get(`/documents/${doc.id}/telecharger/`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = doc.nom_fichier || `document-${doc.id}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const deleteDocument = async (id) => {
  const response = await apiClient.delete(`/documents/${id}/`);
  return response.data;
};
