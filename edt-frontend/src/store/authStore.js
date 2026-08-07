import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useAuthStore = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setAuth: ({ accessToken, refreshToken, user }) => set({
        accessToken,
        refreshToken,
        user,
        isAuthenticated: true,
      }),

      setAccessToken: (token) => set({ accessToken: token }),

      clearAuth: () => set({
        accessToken: null,
        refreshToken: null,
        user: null,
        isAuthenticated: false,
      }),
    }),
    {
      name: 'edt-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...persistedState,
        isAuthenticated: !!persistedState?.accessToken,
      }),
    }
  )
);

export const selectIsResponsable     = (state) => state.user?.role === 'responsable' || state.user?.role === 'admin';
export const selectIsChefDepartement = (state) => state.user?.role === 'chef_departement';
export const selectIsReferentL1      = (state) => state.user?.role === 'referent_l1';
export const selectIsEnseignant      = (state) => ['enseignant', 'chef_departement', 'referent_l1'].includes(state.user?.role);
export const selectIsEtudiant        = (state) => state.user?.role === 'etudiant';
export const selectIsGestionnaire    = (state) => ['admin', 'responsable', 'chef_departement', 'referent_l1'].includes(state.user?.role);

export default useAuthStore;