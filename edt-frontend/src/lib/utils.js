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
