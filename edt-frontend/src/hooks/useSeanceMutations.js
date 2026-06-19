/**
 * @file useSeanceMutations.js
 * @description Hooks de mutation TanStack Query v5 pour les séances.
 * Invalide automatiquement le cache ['seances'] après chaque opération.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createSeance, updateSeance, deleteSeance, reporterSeance } from '@/api/seances';

/** Crée une nouvelle séance. */
export const useCreateSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => createSeance(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};

/** Met à jour partiellement une séance. */
export const useUpdateSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => updateSeance(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};

/** Supprime une séance. */
export const useDeleteSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => deleteSeance(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};

/** Reporte une séance vers un nouveau créneau. */
export const useReporterSeance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => reporterSeance(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['seances'] }),
  });
};