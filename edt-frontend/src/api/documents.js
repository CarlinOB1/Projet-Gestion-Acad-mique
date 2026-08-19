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

export const deleteDocument = async (id) => {
  const response = await apiClient.delete(`/documents/${id}/`);
  return response.data;
};
