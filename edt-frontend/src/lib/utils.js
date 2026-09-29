import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatHeure(timeString) {
  if (!timeString) return '';
  const [heures, minutes] = timeString.split(':');
  return `${heures}h${minutes}`;
}

/** "09:00" → "9h", "11:15" → "11h15" (écriture courte des créneaux du planning). */
export function formatHeureCourte(timeString) {
  if (!timeString) return '';
  const [heures, minutes = '00'] = timeString.split(':');
  const h = Number(heures);
  return minutes.slice(0, 2) === '00' ? `${h}h` : `${h}h${minutes.slice(0, 2)}`;
}

/** "09:00", "11:00" → "9h – 11h". */
export function formatCreneau(heureDebut, heureFin) {
  if (!heureDebut) return '';
  return heureFin
    ? `${formatHeureCourte(heureDebut)} – ${formatHeureCourte(heureFin)}`
    : formatHeureCourte(heureDebut);
}

/** 292.0 → "292 h", 18.5 → "18,5 h" (virgule française, pas de ".0"). */
export function formatNombreHeures(valeur) {
  const n = Number(valeur) || 0;
  return `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(n)} h`;
}

export function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString + 'T00:00:00');
  if (isNaN(date.getTime())) return '';
  const options = { weekday: 'short', day: 'numeric', month: 'short' };
  let formatted = new Intl.DateTimeFormat('fr-FR', options).format(date);
  formatted = formatted.replace(/\./g, '');
  const parts = formatted.split(' ');
  if (parts.length >= 3) {
    const jourSemaine = parts[0].charAt(0).toUpperCase() + parts[0].slice(1) + '.';
    const jourMois = parts[1];
    const mois = parts[2].toLowerCase() + '.';
    return `${jourSemaine} ${jourMois} ${mois}`;
  }
  return formatted;
}

export function getDureeLabel(heureDebut, heureFin) {
  if (!heureDebut || !heureFin) return '';
  const toMinutes = (t) => {
    const [h, m] = t.split(':').map(Number);
    return h * 60 + m;
  };
  const debutMin = toMinutes(heureDebut);
  const finMin = toMinutes(heureFin);
  if (finMin <= debutMin) return '0h00';
  const pauseDebut = 11 * 60;
  const pauseFin = 11 * 60 + 15;
  const overlapStart = Math.max(debutMin, pauseDebut);
  const overlapEnd = Math.min(finMin, pauseFin);
  const chevauchementPause = Math.max(0, overlapEnd - overlapStart);
  const dureeEffective = (finMin - debutMin) - chevauchementPause;
  const hours = Math.floor(dureeEffective / 60);
  const minutes = dureeEffective % 60;
  return `${hours}h${minutes.toString().padStart(2, '0')}`;
}
