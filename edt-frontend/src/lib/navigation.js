import {
  CalendarDays, Clock, AlertTriangle,
  Users, BookOpen, Building2,
  GraduationCap, UserCheck, BarChart3,
} from 'lucide-react';

export const NAV_ITEMS = [
  // Admin & Chef & Référent (Hybride)
  { key: 'chef-planning', label: 'Planning', path: '/chef/planning', icon: CalendarDays, roles: ['admin', 'chef_departement', 'referent_l1'] },
  { key: 'chef-seances', label: 'Séances', path: '/chef/seances', icon: Clock, roles: ['admin', 'chef_departement', 'referent_l1'] },
  { key: 'chef-classes', label: 'Classes', path: '/chef/classes', icon: Users, roles: ['admin', 'chef_departement', 'referent_l1'] },
  { key: 'chef-modules', label: 'Modules', path: '/chef/modules', icon: BookOpen, roles: ['admin', 'chef_departement'] },
  { key: 'chef-organisation', label: 'Organisation', path: '/chef/organisation', icon: Building2, roles: ['admin', 'chef_departement'] },
  { key: 'chef-enseignants', label: 'Enseignants', path: '/chef/enseignants', icon: GraduationCap, roles: ['admin', 'chef_departement', 'referent_l1'] },
  { key: 'chef-etudiants', label: 'Étudiants', path: '/chef/etudiants', icon: UserCheck, roles: ['admin', 'chef_departement', 'referent_l1'] },
  // Enseignant
  { key: 'enseignant-planning', label: 'Mon planning', path: '/enseignant/planning', icon: CalendarDays, roles: ['enseignant'] },
  { key: 'enseignant-seances', label: 'Mes séances', path: '/enseignant/seances', icon: Clock, roles: ['enseignant'] },
  // Etudiant
  { key: 'etudiant-planning', label: 'Mon planning', path: '/etudiant/planning', icon: CalendarDays, roles: ['etudiant'] },
  { key: 'etudiant-enseignants', label: 'Mes enseignants', path: '/etudiant/enseignants', icon: Users, roles: ['etudiant'] }, // ← nouvelle ligne
  { key: 'etudiant-progression', label: 'Ma progression', path: '/etudiant/progression', icon: BarChart3, roles: ['etudiant'] },
];