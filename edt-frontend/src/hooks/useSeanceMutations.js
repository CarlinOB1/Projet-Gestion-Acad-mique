/**
 * @file useSeanceMutations.js
 * @description Hooks de mutation TanStack Query v5 pour les séances.
 * Invalide automatiquement le cache ['seances'] après chaque opération.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createSeance, updateSeance, deleteSeance, reporterSeance, publierSeance, depublierSeance, publierMasseSeances } from '@/api/seances';

/**
 * Invalide, en plus de ['seances'], les caches qui alimentent l'indicateur
 * "Heures restantes" du module et le panneau "Solde affectation" de
 * l'enseignant (SeanceForm.jsx) : sans ça, une séance qui consomme des
 * heures ne rafraîchissait jamais ces indicateurs, qui restaient à leurs
 * anciennes valeurs pour toute séance ouverte ensuite dans la session
 * (CORRECTIONS_A_FAIRE.md, point 7). invalidateQueries filtre par préfixe
 * de clé par défaut : ['modules'] invalide donc aussi ['modules', 'classe', id].
 */
const invaliderCachesSeance = (queryClient) => {
  queryClient.invalidateQueries({ queryKey: ['seances'] });
  queryClient.invalidateQueries({ queryKey: ['modules'] });
  queryClient.invalidateQueries({ queryKey: ['affectations'] });
  queryClient.invalidateQueries({ queryKey: ['affectations-module'] });
};

/** Crée une nouvelle séance. */
export const useCreateSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => createSeance(data),
    onSuccess: () => invaliderCachesSeance(queryClient),
  });
};

/** Met à jour partiellement une séance. */
export const useUpdateSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => updateSeance(id, data),
    onSuccess: () => invaliderCachesSeance(queryClient),
  });
};

/** Supprime une séance. */
export const useDeleteSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => deleteSeance(id),
    onSuccess: () => invaliderCachesSeance(queryClient),
  });
};

/** Reporte une séance vers un nouveau créneau. */
export const useReporterSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => reporterSeance(id, data),
    onSuccess: () => invaliderCachesSeance(queryClient),
  });
};

export const usePublierSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => publierSeance(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};

export const useDepublierSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => depublierSeance(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};

export const usePublierMasseSeances = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (seanceIds) => publierMasseSeances(seanceIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};