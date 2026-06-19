/**
 * AppShell — layout global : sidebar responsive, topbar, zone de contenu et toaster.
 */
import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { Toaster } from '@/components/ui/toaster';

export default function AppShell() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toggleMobileMenu  = () => setIsMobileMenuOpen((prev) => !prev);
  const closeMobileMenu   = () => setIsMobileMenuOpen(false);

  return (
    <div className="min-h-screen w-full flex bg-muted/40 text-foreground overflow-hidden">

      {/* Sidebar desktop */}
      <div className="hidden md:flex md:shrink-0">
        <Sidebar />
      </div>

      {/* Sidebar mobile — overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden animate-in fade-in duration-200">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={closeMobileMenu}
          />
          <div className="relative flex w-auto max-w-xs h-full animate-in slide-in-from-left duration-200">
            <div onClick={closeMobileMenu} className="h-full">
              <Sidebar />
            </div>
          </div>
        </div>
      )}

      {/* Zone principale */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        <Topbar onMenuToggle={toggleMobileMenu} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-background">
          <Outlet />
        </main>
      </div>

      <Toaster />
    </div>
  );
}