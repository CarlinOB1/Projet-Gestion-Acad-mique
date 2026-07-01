/**
 * @file useTrombinoscope.js
 * @description Dérive la liste des enseignants distincts intervenant auprès de
 * l'utilisateur connecté à partir des séances déjà exposées par useSeances.
 * Aucun appel réseau supplémentaire — réutilise le cache TanStack Query existant.
 */
import { useMemo } from 'react';
import useAuthStore from '@/store/authStore';
import { useSeances } from './useSeances';
import { buildTrombinoscope } from '@/lib/trombinoscope';

/**
 * @returns {{ enseignants: Array, isLoading: boolean, isError: boolean }}
 */
export function useTrombinoscope() {
  const role = useAuthStore((state) => state.user?.role);

  const { events, isLoading, isError } = useSeances({ role, filters: {} });

  const enseignants = useMemo(() => buildTrombinoscope(events), [events]);

  return { enseignants, isLoading, isError };
}