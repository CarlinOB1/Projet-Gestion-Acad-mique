/**
 * @file useCascadeSelects.js
 * @description Hook de gestion des selects en cascade pour le formulaire séance.
 * Cascade : classe (déjà fixée par le contexte, ex. l'onglet actif du planning) → module → enseignant.
 * Phase 2+: charge aussi les affectations pour afficher le solde de l'enseignant sélectionné.
 *
 * La classe n'est plus choisie ici : elle est reçue toute faite (id) depuis
 * l'appelant, qui la tire lui-même de la liste des classes déjà autorisées
 * pour la personne connectée (chef de département, référent, ou les deux
 * cumulés). Cela évite de repasser par une filière, une notion que les
 * classes de première année (MIP/BGC/PCG) n'ont pas.
 */
import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";

/**
 * @param {{ classeId: string|number|null }} props
 */
export const useCascadeSelects = ({ classeId }) => {
  const [selectedModuleId, setSelectedModuleId] = useState(null);
  const [selectedEnseignantId, setSelectedEnseignantId] = useState(null);

  // Reset module/enseignant quand la classe change
  useEffect(() => {
    setSelectedModuleId(null);
    setSelectedEnseignantId(null);
  }, [classeId]);

  const { data: modules = [], isLoading: isLoadingModules } = useQuery({
    queryKey: ["modules", "classe", classeId],
    queryFn: async () => {
      const response = await apiClient.get("/modules/", {
        params: { classe_id: classeId },
      });
      return response.data?.results ?? response.data;
    },
    enabled: !!classeId,
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
  // que ceux qui y sont affectés, construits directement depuis les
  // affectations (pas depuis `enseignants`, qui est scopé au département de
  // la matière et exclurait donc un enseignant affecté hors département).
  // Dégradation gracieuse : si pas d'affectations, on affiche tous les
  // enseignants du département.
  const enseignantsFiltres = useMemo(() => {
    if (!affectationsModule || affectationsModule.length === 0) return enseignants;
    const map = new Map();
    affectationsModule.forEach((a) => {
      if (a.enseignant?.profil?.user?.id) {
        map.set(a.enseignant.profil.user.id, a.enseignant);
      }
    });
    return Array.from(map.values());
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
