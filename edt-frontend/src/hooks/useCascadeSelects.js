/**
 * @file useCascadeSelects.js
 * @description Hook de gestion des selects en cascade pour le formulaire séance.
 * Cascade : semestre → filière → classe → module → enseignant
 * Phase 2+: charge aussi les affectations pour afficher le solde de l'enseignant sélectionné.
 */
import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";

/**
 * @param {{ semestreId: string|number|null }} props
 */
export const useCascadeSelects = ({ semestreId }) => {
  const { data: filieres = [], isLoading: isLoadingFilieres } = useQuery({
    queryKey: ["filieres"],
    queryFn: async () => {
      const response = await apiClient.get("/filieres/");
      return response.data?.results ?? response.data;
    },
  });

  const [selectedFiliereId, setSelectedFiliereId] = useState(null);
  const [selectedClasseId, setSelectedClasseId] = useState(null);
  const [selectedModuleId, setSelectedModuleId] = useState(null);
  const [selectedEnseignantId, setSelectedEnseignantId] = useState(null);

  // CORRECTION : reset de toute la cascade quand le semestre change
  useEffect(() => {
    setSelectedFiliereId(null);
    setSelectedClasseId(null);
    setSelectedModuleId(null);
    setSelectedEnseignantId(null);
  }, [semestreId]);

  // Reset module/enseignant quand la classe change
  useEffect(() => {
    setSelectedModuleId(null);
    setSelectedEnseignantId(null);
  }, [selectedClasseId]);

  const { data: classes = [], isLoading: isLoadingClasses } = useQuery({
    queryKey: ["classes", semestreId, selectedFiliereId],
    queryFn: async () => {
      const response = await apiClient.get("/classes/", {
        params: { semestre_id: semestreId, filiere_id: selectedFiliereId },
      });
      return response.data?.results ?? response.data;
    },
    enabled: !!semestreId && !!selectedFiliereId,
  });

  const { data: modules = [], isLoading: isLoadingModules } = useQuery({
    queryKey: ["modules", "classe", selectedClasseId],
    queryFn: async () => {
      const response = await apiClient.get("/modules/", {
        params: { classe_id: selectedClasseId },
      });
      return response.data?.results ?? response.data;
    },
    enabled: !!selectedClasseId,
  });

  const moduleSelectionne = useMemo(() => {
    if (!selectedModuleId || modules.length === 0) return null;
    return modules.find((m) => m.id == selectedModuleId) || null;
  }, [modules, selectedModuleId]);

  const departementId = useMemo(
    () => moduleSelectionne?.matiere?.departement?.id || null,
    [moduleSelectionne],
  );

  const { data: enseignants = [], isLoading: isLoadingEnseignants } = useQuery({
    queryKey: ["enseignants", departementId],
    queryFn: async () => {
      const response = await apiClient.get("/enseignants/", {
        params: { departement_id: departementId },
      });
      return response.data?.results ?? response.data;
    },
    enabled: !!departementId,
  });

  // ── Phase 5 : chargement de toutes les affectations du module sélectionné ──
  // Permet de filtrer la liste des enseignants proposés : si le module a des
  // affectations, on n'affiche que les enseignants qui y figurent.
  const { data: affectationsModule = [] } = useQuery({
    queryKey: ["affectations-module", selectedModuleId],
    queryFn: async () => {
      const response = await apiClient.get("/affectations/", {
        params: { module_id: selectedModuleId },
      });
      return response.data?.results ?? response.data;
    },
    enabled: !!selectedModuleId,
  });

  // Enseignants filtrés : si le module a des affectations, on ne propose
  // que ceux qui y sont affectés (dégradation gracieuse : si pas
  // d'affectations, on affiche tous les enseignants du département).
  const enseignantsFiltres = useMemo(() => {
    if (!affectationsModule || affectationsModule.length === 0) return enseignants;
    const idsAffectes = new Set(
      affectationsModule.map((a) => a.enseignant?.profil?.user?.id)
    );
    return enseignants.filter((e) => idsAffectes.has(e.profil.user.id));
  }, [enseignants, affectationsModule]);

  const { data: affectationsEnseignant = [] } = useQuery({
    queryKey: ["affectations", selectedModuleId, selectedEnseignantId],
    queryFn: async () => {
      const response = await apiClient.get("/affectations/", {
        params: {
          module_id: selectedModuleId,
          enseignant_id: selectedEnseignantId,
        },
      });
      return response.data?.results ?? response.data;
    },
    enabled: !!selectedModuleId && !!selectedEnseignantId,
  });

  return {
    filieres,
    isLoadingFilieres,
    selectedFiliereId,
    setSelectedFiliereId,
    classes,
    isLoadingClasses,
    selectedClasseId,
    setSelectedClasseId,
    modules,
    isLoadingModules,
    selectedModuleId,
    setSelectedModuleId,
    enseignants: enseignantsFiltres, // Filtrés si affectations existent, tous sinon
    isLoadingEnseignants,
    moduleSelectionne,
    selectedEnseignantId,
    setSelectedEnseignantId,
    affectationsEnseignant,
    affectationsModule,
  };
};

