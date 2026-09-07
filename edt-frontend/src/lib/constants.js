export const ROLES = Object.freeze({
   CHEF_DEPARTEMENT: 'chef_departement',
   REFERENT_L1: 'referent_l1',
   ENSEIGNANT: 'enseignant',
   ETUDIANT: 'etudiant',
   ADMIN: 'admin',
});

export const TYPE_SEANCE = Object.freeze({
  CM: 'CM',
  TD: 'TD',
  TP: 'TP',
});

export const STATUT_SEANCE = Object.freeze({
  BROUILLON: 'brouillon',
  CONFIRMEE: 'Confirmée',
  ANNULEE: 'Annulée',
  REPORTEE: 'Reportée',
});

export const SEANCE_COLORS = Object.freeze({
  [TYPE_SEANCE.CM]: {
    bg: 'bg-blue-100 dark:bg-blue-950/40',
    text: 'text-blue-800 dark:text-blue-300',
    border: 'border-blue-300 dark:border-blue-800',
  },
  [TYPE_SEANCE.TD]: {
    bg: 'bg-green-100 dark:bg-green-950/40',
    text: 'text-green-800 dark:text-green-300',
    border: 'border-green-300 dark:border-green-800',
  },
  [TYPE_SEANCE.TP]: {
    bg: 'bg-purple-100 dark:bg-purple-950/40',
    text: 'text-purple-800 dark:text-purple-300',
    border: 'border-purple-300 dark:border-purple-800',
  },
});

export const STATUT_COLORS = Object.freeze({
  [STATUT_SEANCE.BROUILLON]: {
    bg: 'bg-slate-100 dark:bg-slate-800',
    text: 'text-slate-600 dark:text-slate-300',
    border: 'border-slate-200',
  },
  [STATUT_SEANCE.CONFIRMEE]: {
    bg: 'bg-emerald-100 dark:bg-emerald-950/40',
    text: 'text-emerald-800 dark:text-emerald-300',
    border: 'border-emerald-300 dark:border-emerald-800',
  },
  [STATUT_SEANCE.ANNULEE]: {
    bg: 'bg-rose-100 dark:bg-rose-950/40',
    text: 'text-rose-800 dark:text-rose-300',
    border: 'border-rose-300 dark:border-rose-800',
  },
  [STATUT_SEANCE.REPORTEE]: {
    bg: 'bg-amber-100 dark:bg-amber-950/40',
    text: 'text-amber-800 dark:text-amber-300',
    border: 'border-amber-300 dark:border-amber-800',
  },
  actif: {
    bg: 'bg-green-100 dark:bg-green-950/40',
    text: 'text-green-800 dark:text-green-300',
    border: 'border-green-300 dark:border-green-800 rounded-full',
  },
  suspendu: {
    bg: 'bg-destructive/10 dark:bg-destructive/20',
    text: 'text-destructive dark:text-destructive',
    border: 'border-destructive/20 rounded-full',
  }
});

export const RESPONSABLE_ROLES = Object.freeze([ROLES.ADMIN]);
export const GESTIONNAIRE_ROLES = Object.freeze([
  ROLES.ADMIN, 
  ROLES.CHEF_DEPARTEMENT, 
  ROLES.REFERENT_L1
]);

// Bornes de la journee, alignees sur le backend
// (EDT_app/validation_seance.py : MIN_HEURE_DEBUT / HEURE_FIN_MAX).
// Elles etaient auparavant a 07h30-18h30 : les formulaires validaient donc
// des creneaux que l'API rejetait ensuite en 400.
export const HEURE_MIN = '09:00';
export const HEURE_MAX = '16:20';

// Pause meridienne non enseignable (validation_seance.PAUSE_MERIDIENNE_*).
export const PAUSE_MERIDIENNE_DEBUT = '13:15';
export const PAUSE_MERIDIENNE_FIN   = '14:15';
