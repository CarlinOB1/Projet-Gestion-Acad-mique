/**
 * Sidebar — navigation filtrée par rôle, logo et bouton de déconnexion.
 */
import { NavLink } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import useAuthStore from '@/store/authStore';
import { logout } from '@/api/auth';
import { NAV_ITEMS } from '@/lib/navigation';

export default function Sidebar() {
  // CORRECTION : sélecteur ciblé — évite les re-renders sur tout changement du store
  const user = useAuthStore((state) => state.user);

  const allowedNavItems = NAV_ITEMS.filter(
    (item) => item.roles && item.roles.includes(user?.role)
  );

  // CORRECTION : logout() est synchrone — clearAuth() vide isAuthenticated
  // ProtectedRoute détecte le changement et redirige automatiquement vers /login
  const handleLogout = () => {
    logout();
  };

  const displayRole = user?.role
    ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
    : '';

  return (
    <aside className="w-[240px] h-full flex flex-col bg-background border-r border-border select-none">

      {/* En-tête */}
      <div className="h-14 px-6 flex flex-col justify-center border-b border-border">
        <h1 className="text-base font-bold tracking-tight text-foreground">
          EDT UCCB
        </h1>
        <p className="text-[11px] text-muted-foreground truncate">
          Gestion des emplois du temps
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {allowedNavItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.key}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Pied de page */}
      <div className="p-4 border-t border-border bg-muted/20 space-y-3">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-destructive rounded-md hover:bg-destructive/10 transition-colors duration-150 text-left"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span>Déconnexion</span>
        </button>
      </div>

    </aside>
  );
}