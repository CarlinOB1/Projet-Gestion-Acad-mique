/**
 * Topbar — titre dynamique, bouton menu mobile, profil et badge de rôle.
 */
import { useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';
import useAuthStore from '@/store/authStore';
import { NAV_ITEMS } from '@/lib/navigation';

export default function Topbar({ onMenuToggle }) {
  const location = useLocation();
  // CORRECTION : sélecteur ciblé
  const user = useAuthStore((state) => state.user);

  const currentItem = NAV_ITEMS.find((item) => item.path === location.pathname);
  const pageTitle   = currentItem ? currentItem.label : 'Tableau de bord';

  const roleStyles = {
    responsable: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-900',
    enseignant:  'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-400 dark:border-purple-900',
    etudiant:    'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900',
  };

  const roleLabels = {
    responsable: 'Responsable',
    enseignant:  'Enseignant',
    etudiant:    'Étudiant',
  };

  const currentRole = user?.role || 'etudiant';

  return (
    <header className="h-14 w-full bg-background border-b border-border flex items-center justify-between px-4 md:px-6 sticky top-0 z-40">

      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          type="button"
          className="p-2 -ml-2 rounded-md text-muted-foreground hover:bg-muted/80 focus:outline-none md:hidden"
          aria-label="Ouvrir le menu de navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h2 className="text-sm md:text-base font-semibold text-foreground tracking-tight">
          {pageTitle}
        </h2>
      </div>

      <div className="flex items-center gap-3 text-right">
        <div className="hidden sm:block">
          <p className="text-sm font-medium text-foreground leading-none">
            {user?.nom_complet}
          </p>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${roleStyles[currentRole] || roleStyles.etudiant}`}>
          {roleLabels[currentRole] || 'Étudiant'}
        </span>
      </div>

    </header>
  );
}