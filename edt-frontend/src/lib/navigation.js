import {
  CalendarDays, Clock,
  Users, BookOpen, Building2,
  GraduationCap, UserCheck, BarChart3, UserCircle, FileText
} from 'lucide-react';

export const NAV_ITEMS = [
  // Admin & Chef & Référent (Hybride) - GESTION DU DÉPARTEMENT
  { key: 'chef-planning', label: 'Planning des classes', path: '/chef/planning', icon: CalendarDays, roles: ['admin', 'chef_departement', 'referent_l1'], section: 'GESTION DU DÉPARTEMENT' },
  { key: 'chef-classes', label: 'Classes & Étudiants', path: '/chef/classes', icon: Users, roles: ['admin', 'chef_departement', 'referent_l1'], section: 'GESTION DU DÉPARTEMENT' },
  { key: 'chef-enseignants', label: 'Enseignants', path: '/chef/enseignants', icon: GraduationCap, roles: ['admin', 'chef_departement', 'referent_l1'], section: 'GESTION DU DÉPARTEMENT' },
  { key: 'chef-organisation', label: 'Structure Académique', path: '/chef/organisation', icon: Building2, roles: ['admin', 'chef_departement'], section: 'GESTION DU DÉPARTEMENT' },

  // Enseignant & Chef / Référent (Double casquette) - MON COMPTE
  { key: 'enseignant-planning', label: 'Mon planning', path: '/enseignant/planning', icon: CalendarDays, roles: ['enseignant', 'chef_departement', 'referent_l1'], section: 'MON COMPTE' },
  { key: 'enseignant-modules', label: 'Mes modules', path: '/enseignant/modules', icon: BookOpen, roles: ['enseignant', 'chef_departement', 'referent_l1'], section: 'MON COMPTE' },
  { key: 'enseignant-classes', label: 'Classes & Étudiants', path: '/enseignant/classes', icon: Users, roles: ['enseignant'], section: 'MON COMPTE' },
  { key: 'enseignant-documents', label: 'Mes documents', path: '/enseignant/documents', icon: FileText, roles: ['enseignant', 'chef_departement', 'referent_l1'], section: 'MON COMPTE' },
  { key: 'chef-profil', label: 'Mon profil', path: '/chef/profil', icon: UserCircle, roles: ['admin', 'chef_departement', 'referent_l1'], section: 'MON COMPTE' },
  { key: 'enseignant-profil', label: 'Mon profil', path: '/enseignant/profil', icon: UserCircle, roles: ['enseignant'], section: 'MON COMPTE' },

  // Etudiant - MON COMPTE
  { key: 'etudiant-planning', label: 'Mon planning', path: '/etudiant/planning', icon: CalendarDays, roles: ['etudiant'], section: 'MON COMPTE' },
  { key: 'etudiant-enseignants', label: 'Mes enseignants', path: '/etudiant/enseignants', icon: Users, roles: ['etudiant'], section: 'MON COMPTE' },
  { key: 'etudiant-progression', label: 'Ma progression', path: '/etudiant/progression', icon: BarChart3, roles: ['etudiant'], section: 'MON COMPTE' },
  { key: 'etudiant-documents', label: 'Documents', path: '/etudiant/documents', icon: FileText, roles: ['etudiant'], section: 'MON COMPTE' },
  { key: 'etudiant-profil', label: 'Mon profil', path: '/etudiant/profil', icon: UserCircle, roles: ['etudiant'], section: 'MON COMPTE' },
];