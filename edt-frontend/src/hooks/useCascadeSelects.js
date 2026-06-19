/**
 * @file useCascadeSelects.js
 * @description Hook de gestion des selects en cascade pour le formulaire séance.
 * Cascade : semestre → filière → classe → module → enseignant
 */
import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';

/**
 * @param {{ semestreId: string|number|null }} props
 */
export const useCascadeSelects = ({ semestreId }) => {

  const { data: filieres = [], isLoading: isLoadingFilieres } = useQuery({
    queryKey: ['filieres'],
    queryFn: async () => {
      const response = await apiClient.get('/filieres/');
      return response.data;
    },
  });

  const [selectedFiliereId, setSelectedFiliereId] = useState(null);
  const [selectedClasseId,  setSelectedClasseId]  = useState(null);
  const [selectedModuleId,  setSelectedModuleId]  = useState(null);

  // CORRECTION : reset de toute la cascade quand le semestre change
  useEffect(() => {
    setSelectedFiliereId(null);
    setSelectedClasseId(null);
    setSelectedModuleId(null);
  }, [semestreId]);

  const { data: classes = [], isLoading: isLoadingClasses } = useQuery({
    queryKey: ['classes', semestreId, selectedFiliereId],
    queryFn: async () => {
      const response = await apiClient.get('/classes/', {
        params: { semestre_id: semestreId, filiere_id: selectedFiliereId },
      });
      return response.data;
    },
    enabled: !!semestreId && !!selectedFiliereId,
  });

  const { data: modules = [], isLoading: isLoadingModules } = useQuery({
    queryKey: ['modules', semestreId],
    queryFn: async () => {
      const response = await apiClient.get('/modules/', {
        params: { semestre_id: semestreId },
      });
      return response.data;
    },
    enabled: !!semestreId,
  });

  const moduleSelectionne = useMemo(() => {
    if (!selectedModuleId || modules.length === 0) return null;
    return modules.find((m) => m.id == selectedModuleId) || null;
  }, [modules, selectedModuleId]);

  const departementId = useMemo(
    () => moduleSelectionne?.matiere?.departement?.id || null,
    [moduleSelectionne]
  );

  const { data: enseignants = [], isLoading: isLoadingEnseignants } = useQuery({
    queryKey: ['enseignants', departementId],
    queryFn: async () => {
      const response = await apiClient.get('/enseignants/', {
        params: { departement_id: departementId },
      });
      return response.data;
    },
    enabled: !!departementId,
  });

  return {
    filieres,         isLoadingFilieres,
    selectedFiliereId, setSelectedFiliereId,
    classes,          isLoadingClasses,
    selectedClasseId,  setSelectedClasseId,
    modules,          isLoadingModules,
    selectedModuleId,  setSelectedModuleId,
    enseignants,      isLoadingEnseignants,
    moduleSelectionne,
  };
};