// Hook TanStack Query — séances filtrées et transformées pour FullCalendar
import { useQuery } from '@tanstack/react-query';
import {
  getSeances,
  getMonPlanningEnseignant,
  getMonPlanningEtudiant,
} from '@/api/seances';

/**
 * Transforme une séance API en événement FullCalendar.
 * Les couleurs sont gérées dans SeanceCard via extendedProps.
 * @param {Object} seance
 * @returns {Object|null}
 */
export const transformSeanceToEvent = (seance) => {
  if (!seance) return null;

  return {
    id:              String(seance.id),
    title:           seance.module?.libelle || 'Séance sans titre',
    start:           `${seance.date_seance}T${seance.heure_debut}`,
    end:             `${seance.date_seance}T${seance.heure_fin}`,
    backgroundColor: 'transparent',
    borderColor:     'transparent',
    extendedProps:   { ...seance },
  };
};

/**
 * Hook de récupération des séances selon le rôle connecté.
 * @param {{ role: string, filters: Object }} options
 * @returns {{ events, isLoading, isError, error, refetch }}
 */
export const useSeances = ({ role, filters = {} }) => {
  const getQueryFn = () => {
    switch (role) {
      case 'admin':
      case 'chef_departement':
      case 'referent_l1': return () => getSeances(filters);
      case 'enseignant':  return () => getMonPlanningEnseignant(filters);
      case 'etudiant':    return () => getMonPlanningEtudiant(filters);
      default:            return () => Promise.resolve([]);
    }
  };

  const { data: events = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['seances', role, filters],
    queryFn:  getQueryFn(),
    enabled:  !!role,
    staleTime: 1000 * 60 * 2,
    select: (data) => {
      if (!Array.isArray(data)) return [];
      return data.map(transformSeanceToEvent).filter(Boolean);
    },
  });

  return { events, isLoading, isError, error, refetch };
};