/**
 * Topbar — titre dynamique, bouton menu mobile, profil et badge de rôle.
 */
import { Link, useLocation } from 'react-router-dom';
import { Menu, User } from 'lucide-react';
import useAuthStore from '@/store/authStore';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { NAV_ITEMS } from '@/lib/navigation';
import { ROLE_LABELS } from '@/lib/constants';

export default function Topbar({ onMenuToggle }) {
  const location = useLocation();
  // CORRECTION : sélecteur ciblé
  const user = useAuthStore((state) => state.user);

  // Correspondance exacte, puis par préfixe (sous-pages éventuelles). Pas de
  // titre par défaut : l'ancien repli « Tableau de bord » désignait une page
  // qui n'existe pas et s'affichait sur toute page absente du menu.
  const currentItem =
    NAV_ITEMS.find((item) => item.path === location.pathname) ??
    NAV_ITEMS.find((item) => location.pathname.startsWith(`${item.path}/`));
  const pageTitle = currentItem?.label ?? '';

  // Une seule couleur pour tous les rôles : chacun ne voit que le sien,
  // une couleur par rôle ajoutait seulement un accent de plus à l'écran.
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
        <Link to="profil" className="flex items-center gap-3 hover:bg-muted/50 px-3 py-2 rounded-lg transition-colors focus:outline-none">
          <div className="hidden sm:block text-right">
            <p className="text-base font-semibold text-foreground leading-tight">
              {user?.nom_complet}
            </p>
            <span className="mt-1.5 inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-primary/10 text-primary border-primary/20">
              {ROLE_LABELS[currentRole] || 'Étudiant'}
            </span>
          </div>
          <Avatar className="h-10 w-10">
            {user?.photo && <AvatarImage src={user.photo} alt={user?.nom_complet} className="object-cover" />}
            <AvatarFallback className="bg-primary/10 text-primary text-sm font-semibold">
              {user?.first_name?.[0]}{user?.last_name?.[0] || <User className="h-4 w-4" />}
            </AvatarFallback>
          </Avatar>
        </Link>
      </div>

    </header>
  );
}