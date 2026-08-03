/**
 * @file PlanningGrid.jsx
 * @description Grille FullCalendar — skeleton, erreur, calendrier thématisé
 * avec barre de navigation 100% custom (shadcn).
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { AlertCircle, ChevronLeft, ChevronRight, CalendarDays, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
  const calendarRef = useRef(null);
  const [totalHours, setTotalHours] = useState(0);
  const [currentViewRange, setCurrentViewRange] = useState({ start: null, end: null });
  const [viewTitle, setViewTitle] = useState('');

  const getCalendarApi = () => calendarRef.current?.getApi();

  const handlePrev = () => { getCalendarApi()?.prev(); };
  const handleNext = () => { getCalendarApi()?.next(); };
  const handleToday = () => { getCalendarApi()?.today(); };

  const handleDatesSet = useCallback((arg) => {
    setCurrentViewRange(prev => {
      if (prev.start?.getTime() === arg.start.getTime() && prev.end?.getTime() === arg.end.getTime()) {
        return prev;
      }
      return { start: arg.start, end: arg.end };
    });

    // Compute "3 – 8 Août 2026" style title using Intl
    const fmtDay = new Intl.DateTimeFormat('fr-FR', { day: 'numeric' });
    const fmtFull = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    const start = arg.start;
    // end is exclusive, so subtract 1 day for display
    const end = new Date(arg.end.getTime() - 24 * 60 * 60 * 1000);
    const sameMonth = start.getMonth() === end.getMonth();
    const title = sameMonth
      ? `${fmtDay.format(start)} – ${fmtFull.format(end)}`
      : `${new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' }).format(start)} – ${fmtFull.format(end)}`;
    setViewTitle(title.charAt(0).toUpperCase() + title.slice(1));
  }, []);

  // Recalculate total hours when events or view range change
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
      setTotalHours(hours % 1 === 0 ? hours : parseFloat(hours.toFixed(1)));
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
    <div className="fc-theme-custom w-full flex flex-col gap-3">

      {/* ── Barre de navigation custom ── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">

        {/* Navigation gauche */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={handlePrev} aria-label="Semaine précédente" className="h-9 w-9">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={handleToday} className="h-9 px-4 text-sm font-medium gap-2">
            <CalendarDays className="h-4 w-4" />
            Aujourd'hui
          </Button>
          <Button variant="outline" size="icon" onClick={handleNext} aria-label="Semaine suivante" className="h-9 w-9">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Titre de la semaine (centre) */}
        <h2 className="text-base font-semibold text-foreground tracking-tight capitalize order-first w-full sm:order-none sm:w-auto sm:flex-1 text-center">
          {viewTitle}
        </h2>

        {/* Badge Total heures */}
        <div className="flex items-center gap-1.5 bg-primary/10 text-primary border border-primary/20 px-3 py-1.5 rounded-lg text-sm font-semibold">
          <Clock className="h-4 w-4 shrink-0" />
          <span>{totalHours}h de cours</span>
        </div>
      </div>

      {/* ── FullCalendar (sans sa propre toolbar) ── */}
      <style>{`
        .fc-theme-custom { --fc-border-color: hsl(var(--border)); --fc-today-bg-color: hsl(var(--primary) / 0.04); --fc-page-bg-color: transparent; }
        .fc-theme-custom .fc-col-header-cell-cushion { color: hsl(var(--foreground)); font-size: 0.8rem; font-weight: 600; text-transform: capitalize; padding: 10px 4px; }
        .fc-theme-custom .fc-timegrid-slot-label-cushion { color: hsl(var(--muted-foreground)); font-size: 0.75rem; }
        .fc-theme-custom .fc-timegrid-now-indicator-line { border-color: hsl(var(--destructive)); }
        .fc-theme-custom .fc-timegrid-now-indicator-arrow { border-left-color: hsl(var(--destructive)); }
        .fc-theme-custom .fc-scrollgrid { border-radius: 0.5rem; overflow: hidden; }
        /* Creneaux hors cours (pause & hors horaires) */
        .fc-theme-custom .fc-non-business { background-color: hsl(var(--muted) / 0.45); }
        /* Slot de pause : on cible la ligne 13h15-14h15 via CSS d'heure */
        .fc-theme-custom .fc-timegrid-slot[data-time="13:15:00"] .fc-timegrid-slot-label { color: hsl(var(--amber-600, 217 91% 60%) / 0.8); }
      `}</style>

      <FullCalendar
        ref={calendarRef}
        plugins={[timeGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        locale="fr"
        headerToolbar={false}
        slotMinTime="09:00:00"
        slotMaxTime="16:30:00"
        slotDuration="00:15:00"
        slotLabelInterval="01:00:00"
        slotLabelFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
        allDaySlot={false}
        weekends={true}
        hiddenDays={[0]}
        nowIndicator={true}
        height="auto"
        businessHours={[
          { daysOfWeek: [1, 2, 3, 4, 5, 6], startTime: '09:00', endTime: '11:00' },
          { daysOfWeek: [1, 2, 3, 4, 5, 6], startTime: '11:15', endTime: '13:15' },
          { daysOfWeek: [1, 2, 3, 4, 5, 6], startTime: '14:15', endTime: '16:15' },
        ]}
        events={events}
        eventContent={(eventInfo) => <SeanceCard eventInfo={eventInfo} />}
        eventClick={onEventClick}
        dateClick={onDateClick}
        datesSet={handleDatesSet}
      />
    </div>
  );
}