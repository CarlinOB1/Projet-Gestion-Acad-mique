/**
 * @file PlanningGrid.jsx
 * @description Grille FullCalendar — skeleton, erreur, calendrier thématisé.
 */
import { useState, useEffect } from 'react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { AlertCircle } from 'lucide-react';
import SeanceCard from './SeanceCard';
import { HEURE_MIN, HEURE_MAX } from '@/lib/constants';

/**
 * @param {{ events: Array, isLoading: boolean, isError: boolean, onEventClick: Function, onDateClick: Function }} props
 */
export default function PlanningGrid({
  events = [],
  isLoading,
  isError,
  onEventClick = () => {},
  onDateClick = () => {},
}) {
  const [totalHours, setTotalHours] = useState(0);
  const [currentViewRange, setCurrentViewRange] = useState({ start: null, end: null });

  // Recalculer les heures si les events ou la vue changent
  useEffect(() => {
    if (currentViewRange.start && currentViewRange.end) {
      const visibleEvents = events.filter((e) => {
        const start = new Date(e.start);
        return start >= currentViewRange.start && start < currentViewRange.end;
      });
      
      let totalMs = 0;
      visibleEvents.forEach((e) => {
        totalMs += (new Date(e.end) - new Date(e.start));
      });
      
      const hours = totalMs / (1000 * 60 * 60);
      setTotalHours(hours % 1 === 0 ? hours : hours.toFixed(1));
    }
  }, [events, currentViewRange]);

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
    <div className="fc-theme-custom w-full relative">
      <div className="absolute top-2 right-2 z-10 bg-primary/10 text-primary px-3 py-1 rounded-md text-sm font-semibold pointer-events-none hidden sm:block">
        Total : {totalHours}h
      </div>
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
        eventClick={onEventClick}
        dateClick={onDateClick}
        datesSet={(arg) => {
          setCurrentViewRange(prev => {
            if (prev.start?.getTime() === arg.start.getTime() && prev.end?.getTime() === arg.end.getTime()) {
              return prev;
            }
            return { start: arg.start, end: arg.end };
          });
        }}
      />
    </div>
  );
}