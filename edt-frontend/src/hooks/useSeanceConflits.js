/**
 * @file useSeanceConflits.js
 * @description Hook TanStack Query — récupère les séances en conflit pour un
 * semestre donné et expose leurs ids sous forme de Set pour un lookup O(1).
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getConflitsSeances } from '@/api/seances';

/**
 * @param {string|number|null} semestreId
 * @returns {{ conflitsIds: Set<number>, isLoading: boolean }}
 */
export const useSeanceConflits = (semestreId) => {
    const { data, isLoading } = useQuery({
        queryKey: ['conflits', semestreId],
        queryFn: () => getConflitsSeances(semestreId),
        enabled: !!semestreId,
        staleTime: 1000 * 60 * 2,
    });

    const conflitsIds = useMemo(() => {
        if (!data?.results) return new Set();
        return new Set(data.results.map((s) => s.id));
    }, [data]);

    return { conflitsIds, isLoading };
};