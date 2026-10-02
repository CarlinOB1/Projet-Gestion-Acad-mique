// src/features/auth/LoginPage.jsx
// Page de connexion — écran partagé : éphéméride + carrousel photos du campus à
// gauche, formulaire à droite. Palette rouge/vert/jaune/noir de l'UCCB.
import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Navigate } from 'react-router-dom';
import { Eye, EyeOff, ChevronLeft, ChevronRight, Pause, Play, Loader2 } from '@/components/ui/icons';
import useAuthStore from '@/store/authStore';
import { loginSchema } from '@/lib/schemas';
import { useLogin, parseLoginError } from './useLogin';
import { effacerMessageConnexion, lireMessageConnexion } from '@/lib/messageConnexion';
import logoUccb from '@/assets/login/logo-uccb.svg';
import campusBatiment from '@/assets/login/campus-batiment.jpg';
import campusSport from '@/assets/login/campus-sport.jpg';
import campusVieEtudiante from '@/assets/login/campus-vie-etudiante.jpg';

const SLIDES = [
  { src: campusBatiment, alt: "Le bâtiment principal du campus de l'UCCB", caption: 'Le campus' },
  { src: campusSport, alt: 'Des étudiants sur le terrain de sport du campus', caption: 'Terrain de sport' },
  { src: campusVieEtudiante, alt: 'Des étudiantes assises devant un bâtiment du campus', caption: 'Vie étudiante' },
];

const SLIDE_INTERVAL_MS = 5000;
const WEEKDAY_SHORT = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];

// Lundi à samedi de la semaine en cours, calculés à partir d'aujourd'hui —
// jamais de semaine ou de semestre inventés.
function useWeekStrip() {
  return useMemo(() => {
    const today = new Date();
    const mondayOffset = today.getDay() === 0 ? -6 : 1 - today.getDay();
    const monday = new Date(today);
    monday.setDate(today.getDate() + mondayOffset);
    return Array.from({ length: 6 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      return d;
    });
  }, []);
}

function useToday() {
  return useMemo(() => {
    const now = new Date();
    return {
      dayNumber: now.getDate(),
      weekday: new Intl.DateTimeFormat('fr-FR', { weekday: 'long' }).format(now),
      month: new Intl.DateTimeFormat('fr-FR', { month: 'long' }).format(now),
      year: now.getFullYear(),
    };
  }, []);
}

function CampusCarousel() {
  const [slideIdx, setSlideIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const [resetKey, setResetKey] = useState(0);
  const weekStrip = useWeekStrip();
  const today = useToday();

  // Respecte la préférence système « moins d'animations ».
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPaused(mq.matches);
  }, []);

  useEffect(() => {
    if (paused) return undefined;
    const id = setInterval(() => {
      setSlideIdx((i) => (i + 1) % SLIDES.length);
    }, SLIDE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [paused, resetKey]);

  const goTo = useCallback((i) => {
    setSlideIdx(((i % SLIDES.length) + SLIDES.length) % SLIDES.length);
    setResetKey((k) => k + 1);
  }, []);

  return (
    <section
      aria-label="Photos du campus et date du jour"
      className="relative hidden lg:block lg:w-[46%] xl:w-[42%] overflow-hidden bg-uccb-ink"
    >
      {SLIDES.map((slide, i) => (
        <img
          key={slide.src}
          src={slide.src}
          alt={slide.alt}
          className="absolute inset-0 h-full w-full object-cover transition-opacity duration-[1200ms] ease-in-out"
          style={{ opacity: i === slideIdx ? 1 : 0 }}
        />
      ))}

      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(180deg, rgba(20,20,20,0.35) 0%, rgba(20,20,20,0) 20%, rgba(20,20,20,0.1) 42%, rgba(20,20,20,0.88) 100%)',
        }}
      />

      {/* En-tête : logo + établissement */}
      <div className="absolute top-7 left-10 right-10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={logoUccb} alt="Logo de l'Université Catholique du Congo-Brazzaville" className="h-11 w-11" />
          <span className="text-[13px] font-bold tracking-[0.08em] uppercase text-white">EDT UCCB</span>
        </div>
      </div>

      {/* Date du jour + semaine, superposées sur la photo */}
      <div className="absolute left-10 right-10 bottom-9 flex flex-col gap-6 text-white">
        <div className="flex items-end gap-5">
          <span
            className="leading-[0.8] font-extrabold tracking-tight"
            style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 'clamp(96px, 12vw, 168px)' }}
          >
            {today.dayNumber}
          </span>
          <div className="flex flex-col gap-1 pb-1">
            <span className="text-3xl font-semibold capitalize" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
              {today.weekday}
            </span>
            <span className="text-lg text-white/85 capitalize" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
              {today.month} {today.year}
            </span>
          </div>
        </div>

        <div aria-hidden="true" className="flex gap-2">
          {weekStrip.map((d) => {
            const isToday = d.toDateString() === new Date().toDateString();
            return (
              <div
                key={d.toISOString()}
                className={`flex flex-1 flex-col items-center justify-center gap-0.5 rounded-lg border h-14 text-[13px] font-bold ${
                  isToday
                    ? 'bg-uccb-green border-uccb-green text-white'
                    : 'border-white/35 bg-white/10 text-white/85'
                }`}
              >
                <span>{WEEKDAY_SHORT[d.getDay()]}</span>
                <b className="text-[19px] font-semibold" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
                  {d.getDate()}
                </b>
              </div>
            );
          })}
        </div>

        {/* Commandes du carrousel */}
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {SLIDES.map((slide, i) => (
              <button
                key={slide.src}
                type="button"
                onClick={() => goTo(i)}
                aria-label={`Afficher la photo ${i + 1} sur ${SLIDES.length} : ${slide.caption}`}
                aria-current={i === slideIdx}
                className="flex h-11 w-7 items-center justify-center"
              >
                <span
                  className={`block h-1 rounded-full transition-all duration-300 ${
                    i === slideIdx ? 'w-7 bg-uccb-yellow' : 'w-3 bg-white/50'
                  }`}
                />
              </button>
            ))}
          </div>
          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={() => goTo(slideIdx - 1)}
              aria-label="Photo précédente"
              className="flex h-11 w-11 items-center justify-center rounded-full border border-white/55 bg-black/30 text-white hover:bg-black/45 transition-colors"
            >
              <ChevronLeft className="h-4.5 w-4.5" />
            </button>
            <button
              type="button"
              onClick={() => setPaused((p) => !p)}
              aria-label={paused ? 'Reprendre le défilement automatique' : 'Mettre le défilement en pause'}
              className="flex h-11 w-11 items-center justify-center rounded-full border border-white/55 bg-black/30 text-white hover:bg-black/45 transition-colors"
            >
              {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={() => goTo(slideIdx + 1)}
              aria-label="Photo suivante"
              className="flex h-11 w-11 items-center justify-center rounded-full border border-white/55 bg-black/30 text-white hover:bg-black/45 transition-colors"
            >
              <ChevronRight className="h-4.5 w-4.5" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function LoginPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);

  const { mutate, isPending, error, isError } = useLogin();
  const [showPassword, setShowPassword] = useState(false);
  // Raison d'une déconnexion forcée (compte suspendu, session expirée),
  // notée par api/client.js juste avant de revenir ici. Effacée à la
  // tentative de connexion suivante, pas à l'affichage : la déconnexion
  // affiche cette page une première fois avant de la recharger.
  const [messageConnexion] = useState(lireMessageConnexion);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  });

  const onSubmit = (data) => {
    effacerMessageConnexion();
    mutate({ username: data.username, password: data.password });
  };

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
    <div className="min-h-screen w-full flex flex-col bg-uccb-paper">
      {/* Bandeau tricolore */}
      <div aria-hidden="true" className="h-2 flex-none flex">
        <span className="flex-1 bg-uccb-green" />
        <span className="flex-1 bg-uccb-yellow" />
        <span className="flex-1 bg-uccb-red" />
      </div>

      <div className="flex-1 flex">
        <CampusCarousel />

        <section aria-label="Connexion" className="flex-1 flex flex-col px-6 py-8 sm:px-12 sm:py-10">
          <div className="flex items-center justify-between gap-3 pb-3.5 border-b-2 border-uccb-ink lg:hidden">
            <div className="flex items-center gap-3">
              <img src={logoUccb} alt="Logo de l'Université Catholique du Congo-Brazzaville" className="h-11 w-11" />
              <span className="text-[13px] font-bold tracking-[0.08em] uppercase text-uccb-ink">EDT UCCB</span>
            </div>
          </div>

          <div className="flex-1 flex items-center justify-center">
            <div className="w-full max-w-[480px] box-border rounded-2xl border border-[#E2DDD3] bg-white px-8 py-9 sm:px-11 sm:py-10 flex flex-col gap-7 shadow-[0_12px_32px_rgba(20,20,20,0.08)]">
              <div className="flex flex-col gap-2">
                <h1
                  className="text-4xl font-semibold tracking-tight text-uccb-ink"
                  style={{ fontFamily: "'Fraunces', Georgia, serif" }}
                >
                  Bonjour.
                </h1>
                <p className="text-[16.5px] leading-relaxed text-[#4A4741]">
                  Identifiez-vous avec le compte fourni par l'université.
                </p>
              </div>

              <div className="flex flex-col gap-[18px]" onKeyDown={handleKeyDown}>
                {messageConnexion && !isError && (
                  <div role="status" className="p-3 text-sm font-medium text-uccb-ink bg-uccb-yellow/15 rounded-lg border border-uccb-yellow/50">
                    {messageConnexion}
                  </div>
                )}

                {/* Identifiant */}
                <div>
                  <label htmlFor="username" className="block text-sm font-semibold text-uccb-ink mb-2">
                    Identifiant
                  </label>
                  <input
                    id="username"
                    type="text"
                    autoComplete="username"
                    autoFocus
                    placeholder="prenom.nom"
                    className="w-full h-[50px] box-border rounded-lg border border-[#BDB8AE] px-3.5 font-inherit text-[17px] text-uccb-ink bg-white outline-none focus:border-2 focus:border-uccb-green focus:ring-4 focus:ring-uccb-green/20 transition"
                    aria-invalid={!!errors.username}
                    {...register('username')}
                  />
                  {errors.username && (
                    <p className="text-xs font-medium text-uccb-red mt-1.5">{errors.username.message}</p>
                  )}
                </div>

                {/* Mot de passe */}
                <div>
                  <label htmlFor="password" className="block text-sm font-semibold text-uccb-ink mb-2">
                    Mot de passe
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      className="w-full h-[50px] box-border rounded-lg border border-[#BDB8AE] pl-3.5 pr-24 font-inherit text-[17px] text-uccb-ink bg-white outline-none focus:border-2 focus:border-uccb-green focus:ring-4 focus:ring-uccb-green/20 transition"
                      aria-invalid={!!errors.password}
                      {...register('password')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      tabIndex={-1}
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-10 px-3 flex items-center gap-1.5 text-sm font-bold text-uccb-ink underline underline-offset-4 hover:text-uccb-green transition-colors"
                      aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      {showPassword ? 'Masquer' : 'Afficher'}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="text-xs font-medium text-uccb-red mt-1.5">{errors.password.message}</p>
                  )}
                </div>

                {isError && (
                  <div role="alert" className="p-3 text-xs font-medium text-uccb-red bg-uccb-red/10 rounded-lg border border-uccb-red/20">
                    {parseLoginError(error)}
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleSubmit(onSubmit)}
                  disabled={isPending}
                  className="w-full h-[52px] mt-1.5 rounded-lg bg-uccb-green text-white font-bold text-[17px] flex items-center justify-center gap-2 hover:brightness-95 disabled:opacity-60 disabled:pointer-events-none transition"
                >
                  {isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Connexion...
                    </>
                  ) : (
                    'Se connecter'
                  )}
                </button>

                <a href="#" className="self-center text-[15px] font-semibold text-uccb-ink underline underline-offset-4 hover:text-uccb-green transition-colors">
                  J'ai oublié mon mot de passe
                </a>
              </div>
            </div>
          </div>

          <p className="text-[15px] text-[#4A4741]">Emplois du temps de l'université</p>
        </section>
      </div>
    </div>
  );
}
