/**
 * @file PlanningGrid.jsx
 * @description Grille FullCalendar — skeleton, erreur, calendrier thématisé.
 */
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { AlertCircle } from 'lucide-react';
import SeanceCard from './SeanceCard';
import { HEURE_MIN, HEURE_MAX } from '@/lib/constants';

/**
 * @param {{ events: Array, isLoading: boolean, isError: boolean, onEventClick: Function }} props
 */
export default function PlanningGrid({
  events = [],
  isLoading,
  isError,
  onEventClick = () => {},   // CORRECTION : prop ajoutée avec valeur par défaut
}) {

  if (isLoading) {
    return (
      <div className="w-full h-96 bg-muted/40 animate-pulse rounded-lg border border-border/60 flex items-center justify-center"
        role="status" aria-label="Chargement du planning">
        <span className="text-sm text-muted-foreground font-medium">
          Chargement de l'emploi du temps...
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="w-full h-96 flex flex-col items-center justify-center gap-3 border border-destructive/20 bg-destructive/5 rounded-lg p-6 text-center">
        <AlertCircle className="w-10 h-10 text-destructive" aria-hidden="true" />
        <h3 className="font-semibold text-lg text-foreground">Impossible de charger le planning</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Une erreur est survenue. Veuillez rafraîchir la page ou réessayer plus tard.
        </p>
      </div>
    );
  }

  return (
    <div className="fc-theme-custom w-full">
      <style>{`
        .fc-theme-custom { --fc-border-color: hsl(var(--border)); --fc-today-bg-color: hsl(var(--primary) / 0.04); --fc-page-bg-color: transparent; }
        .fc-theme-custom .fc-toolbar-title { color: hsl(var(--foreground)); font-size: 1.125rem; font-weight: 600; text-transform: capitalize; }
        .fc-theme-custom .fc-button-primary { background-color: hsl(var(--background)); border-color: hsl(var(--border)); color: hsl(var(--foreground)); font-weight: 500; font-size: 0.875rem; transition: all 0.2s; }
        .fc-theme-custom .fc-button-primary:hover { background-color: hsl(var(--accent)); border-color: hsl(var(--border)); color: hsl(var(--accent-foreground)); }
        .fc-theme-custom .fc-button-primary:not(:disabled).fc-button-active,
        .fc-theme-custom .fc-button-primary:not(:disabled):active { background-color: hsl(var(--accent)); border-color: hsl(var(--border)); color: hsl(var(--accent-foreground)); }
        .fc-theme-custom .fc-button-primary:disabled { background-color: hsl(var(--muted)); border-color: hsl(var(--border)); color: hsl(var(--muted-foreground)); opacity: 0.5; }
        .fc-theme-custom .fc-timegrid-now-indicator-line { border-color: hsl(var(--destructive)); }
        .fc-theme-custom .fc-timegrid-now-indicator-arrow { border-left-color: hsl(var(--destructive)); }
      `}</style>

      <FullCalendar
        plugins={[timeGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        locale="fr"
        headerToolbar={{ left: 'prev,next today', center: 'title', right: '' }}
        slotMinTime={`${HEURE_MIN}:00`}
        slotMaxTime={`${HEURE_MAX}:00`}
        slotDuration="00:30:00"
        allDaySlot={false}
        weekends={true}
        hiddenDays={[0]}
        nowIndicator={true}
        height="auto"
        events={events}
        eventContent={(eventInfo) => <SeanceCard eventInfo={eventInfo} />}
        eventClick={onEventClick}   // CORRECTION : branché sur la prop
      />
    </div>
  );
}