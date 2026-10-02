/**
 * @file useProgression.js
 * @description Dérive la progression des modules du semestre en cours à partir
 * des séances déjà exposées par useSeances. Aucun appel réseau supplémentaire.
 */
import { useMemo } from 'react';
import useAuthStore from '@/store/authStore';
import { useSeances } from './useSeances';
import { buildProgression, resumerProgression } from '@/lib/progression';

/**
 * @returns {{ modules: Array, resume: Object, isLoading: boolean, isError: boolean }}
 */
export function useProgression() {
    const role = useAuthStore((state) => state.user?.role);

    const { events, isLoading, isError } = useSeances({ role, filters: {} });

    const { modules, resume } = useMemo(() => {
        const maintenant = new Date();
        const modules = buildProgression(events, maintenant);
        return { modules, resume: resumerProgression(modules, events, maintenant) };
    }, [events]);

    return { modules, resume, isLoading, isError };
}
