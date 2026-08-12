// Arbre de routage — routes publiques, routes protégées par rôle et aiguillage racine
import { createBrowserRouter, Navigate } from 'react-router-dom';
import useAuthStore from '@/store/authStore';
import ProtectedRoute from './ProtectedRoute';
import LoginPage from '@/features/auth/LoginPage';
import AppShell from '@/components/layout/AppShell';
import PlanningPage from '@/features/planning/PlanningPage';
import SeancesListePage from '@/features/seances/SeancesListePage';
import OrganisationPage from '@/features/academique/OrganisationPage';
import ModulesPage from '@/features/academique/ModulesPage';
import ClassesPage from '@/features/academique/ClassesPage';
import EnseignantsPage from '@/features/acteurs/EnseignantsPage';
import EtudiantsPage from '@/features/acteurs/EtudiantsPage';
import TrombinoscopePage from '@/features/trombinoscope/TrombinoscopePage';
import ProgressionPage from '@/features/progression/ProgressionPage';
import ProfilPage from '@/features/profil/ProfilPage';

const NotFoundPage = () => <div className="p-8 text-center text-muted-foreground"><h3>404 — Page introuvable</h3></div>;
const UnauthorizedPage = () => <div className="p-8 text-center text-destructive"><h3>403 — Accès non autorisé</h3></div>;

// Dans ton fichier index.jsx
function RootRedirect() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user            = useAuthStore((state) => state.user);

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  switch (user?.role) {
    case 'admin':
    case 'chef_departement':
    case 'referent_l1':      return <Navigate to="/chef/planning"        replace />;
    case 'enseignant':       return <Navigate to="/enseignant/planning"  replace />;
    case 'etudiant':    return <Navigate to="/etudiant/planning"    replace />;
    default:            return <Navigate to="/unauthorized"         replace />;
  }
}

export const router = createBrowserRouter([
  { path: '/', element: <RootRedirect /> },
  { path: '/login', element: <LoginPage /> },



  // ── Admin & Chef & Référent (Hybride) ─────────────────────────────────────────────
  {
    path: '/chef',
    element: <ProtectedRoute allowedRoles={['admin', 'chef_departement', 'referent_l1']} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="planning" replace /> },
          { path: 'planning', element: <PlanningPage /> },
          { path: 'seances', element: <SeancesListePage /> },
          { path: 'classes', element: <ClassesPage /> },
          { path: 'modules', element: <ModulesPage /> },
          { path: 'organisation', element: <OrganisationPage /> },
          { path: 'enseignants', element: <EnseignantsPage /> },
          { path: 'etudiants', element: <EtudiantsPage /> },
          { path: 'profil', element: <ProfilPage /> },
          { path: '*', element: <Navigate to="planning" replace /> },
        ],
      },
    ],
  },

  // ── Enseignant ────────────────────────────────────────────────────────────
  {
    path: '/enseignant',
    element: <ProtectedRoute allowedRoles={['enseignant', 'chef_departement', 'referent_l1']} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="planning" replace /> },
          { path: 'planning', element: <PlanningPage /> },
          { path: 'seances', element: <SeancesListePage /> },
          { path: 'profil', element: <ProfilPage /> },
          { path: '*', element: <Navigate to="planning" replace /> },
        ],
      },
    ],
  },

  // ── Étudiant ──────────────────────────────────────────────────────────────
  {
    path: '/etudiant',
    element: <ProtectedRoute allowedRoles={['etudiant']} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="planning" replace /> },
          { path: 'planning', element: <PlanningPage /> },
          { path: 'enseignants', element: <TrombinoscopePage /> },
          { path: 'progression', element: <ProgressionPage /> },
          { path: 'profil', element: <ProfilPage /> },
          { path: '*', element: <Navigate to="planning" replace /> },
        ],
      },
    ],
  },

  { path: '/unauthorized', element: <UnauthorizedPage /> },
  { path: '*', element: <NotFoundPage /> },
]);