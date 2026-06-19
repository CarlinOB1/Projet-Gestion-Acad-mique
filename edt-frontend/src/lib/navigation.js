/**
 * Configuration de la navigation principale.
 * Définit les routes accessibles dans la sidebar par rôle.
 */
import {
  CalendarDays, Clock, AlertTriangle,
  Users, BookOpen, Building2,
  GraduationCap, UserCheck,
} from 'lucide-react';

export const NAV_ITEMS = [
  // Responsable
  { key: 'responsable-planning',     label: 'Planning',     path: '/responsable/planning',     icon: CalendarDays,  roles: ['responsable'] },
  { key: 'responsable-seances',      label: 'Séances',      path: '/responsable/seances',      icon: Clock,         roles: ['responsable'] },
  { key: 'responsable-conflits',     label: 'Conflits',     path: '/responsable/conflits',     icon: AlertTriangle, roles: ['responsable'] },
  { key: 'responsable-classes',      label: 'Classes',      path: '/responsable/classes',      icon: Users,         roles: ['responsable'] },
  { key: 'responsable-modules',      label: 'Modules',      path: '/responsable/modules',      icon: BookOpen,      roles: ['responsable'] },
  { key: 'responsable-organisation', label: 'Organisation', path: '/responsable/organisation', icon: Building2,     roles: ['responsable'] },
  { key: 'responsable-enseignants',  label: 'Enseignants',  path: '/responsable/enseignants',  icon: GraduationCap, roles: ['responsable'] },
  { key: 'responsable-etudiants',    label: 'Étudiants',    path: '/responsable/etudiants',    icon: UserCheck,     roles: ['responsable'] },
  // Enseignant
  { key: 'enseignant-planning', label: 'Mon planning', path: '/enseignant/planning', icon: CalendarDays, roles: ['enseignant'] },
  { key: 'enseignant-seances',  label: 'Mes séances',  path: '/enseignant/seances',  icon: Clock,        roles: ['enseignant'] },
  // Etudiant
  { key: 'etudiant-planning', label: 'Mon planning', path: '/etudiant/planning', icon: CalendarDays, roles: ['etudiant'] },
];