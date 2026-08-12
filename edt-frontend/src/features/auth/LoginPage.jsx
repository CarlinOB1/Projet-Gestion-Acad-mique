// src/features/auth/LoginPage.jsx
// Page de connexion — esthétique glassmorphism sombre, glow dégradé
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Navigate } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight, GraduationCap, Loader2 } from 'lucide-react';
import useAuthStore from '@/store/authStore';
import { loginSchema } from '@/lib/schemas';
import { useLogin, parseLoginError } from './useLogin';

export default function LoginPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);

  const { mutate, isPending, error, isError } = useLogin();
  const [showPassword, setShowPassword] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  });

  const onSubmit = (data) => {
    mutate({ username: data.username, password: data.password });
  };

  // Redirection automatique après login réussi
  // Redirection automatique après login réussi
  if (isAuthenticated && user) {
    switch (user.role) {
      case 'admin':
      case 'chef_departement':
      case 'referent_l1': return <Navigate to="/chef/planning" replace />;
      case 'enseignant': return <Navigate to="/enseignant/planning" replace />;
      case 'etudiant': return <Navigate to="/etudiant/planning" replace />;
      default: return <Navigate to="/unauthorized" replace />;
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(onSubmit)();
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#050506] p-4 relative overflow-hidden">

      {/* Ambiance de fond — vignette douce */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 50% at 50% 40%, rgba(45,212,191,0.06), transparent 70%)',
        }}
      />

      <div className="relative w-full max-w-sm">

        {/* Glow dégradé au coin, flouté derrière la carte */}
        <div
          className="absolute -top-10 -left-10 h-40 w-40 rounded-full blur-3xl opacity-50"
          style={{
            background:
              'conic-gradient(from 180deg, #34d399, #22d3ee, #a78bfa, #34d399)',
          }}
        />

        {/* Carte verre */}
        <div className="relative rounded-3xl border border-white/10 bg-white/[0.04] backdrop-blur-2xl shadow-[0_8px_40px_rgba(0,0,0,0.5)] p-8">

          {/* Badge / logo */}
          <div className="flex justify-center mb-5">
            <div className="h-11 w-11 flex items-center justify-center">
              <GraduationCap className="h-5 w-5 text-emerald-300" />
            </div>
          </div>

          <div className="text-center mb-7">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Bon retour
            </h1>
            <p className="text-sm text-white/40 mt-1">
              Connectez-vous à votre espace EDT UCCB
            </p>
          </div>

          <div className="space-y-3" onKeyDown={handleKeyDown}>

            {/* Identifiant */}
            <div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5 focus-within:border-emerald-400/40 transition-colors">
                <label htmlFor="username" className="block text-[11px] text-white/35">
                  Identifiant
                </label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  placeholder="Ex: mbemba"
                  className="w-full bg-transparent text-white placeholder-white/25 text-sm outline-none mt-0.5"
                  aria-invalid={!!errors.username}
                  {...register('username')}
                />
              </div>
              {errors.username && (
                <p className="text-xs font-medium text-rose-400 mt-1.5 px-1">{errors.username.message}</p>
              )}
            </div>

            {/* Mot de passe */}
            <div>
              <div className="relative rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5 focus-within:border-emerald-400/40 transition-colors">
                <label htmlFor="password" className="block text-[11px] text-white/35">
                  Mot de passe
                </label>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="w-full bg-transparent text-white placeholder-white/25 text-sm outline-none mt-0.5 pr-7"
                  aria-invalid={!!errors.password}
                  {...register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  tabIndex={-1}
                  className="absolute right-3.5 bottom-2.5 text-white/30 hover:text-white/70 transition-colors"
                  aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs font-medium text-rose-400 mt-1.5 px-1">{errors.password.message}</p>
              )}
            </div>

            {isError && (
              <div className="p-3 text-xs font-medium text-rose-300 bg-rose-500/10 rounded-xl border border-rose-500/20">
                {parseLoginError(error)}
              </div>
            )}

            {/* Bouton pilule dégradé */}
            <button
              type="button"
              onClick={handleSubmit(onSubmit)}
              disabled={isPending}
              className="w-full mt-2 rounded-2xl py-3 flex items-center justify-center gap-2 font-semibold text-sm text-black
                bg-gradient-to-r from-emerald-400 to-cyan-400 hover:brightness-110
                disabled:opacity-60 disabled:pointer-events-none transition-all"
            >
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Connexion...
                </>
              ) : (
                <>
                  Se connecter
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>

          <p className="text-center text-xs text-white/30 mt-6">
            Accès réservé au personnel et étudiants de l'UCCB.
          </p>
        </div>
      </div>
    </div>
  );
}