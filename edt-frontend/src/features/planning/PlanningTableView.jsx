/**
 * @file PlanningTableView.jsx
 * @description Vue tableau semaine — disposition structurée par créneaux horaires fixes,
 * inspirée du format officiel de l'emploi du temps UCCB.
 */
import { useState, useMemo, useEffect } from 'react';
import { ChevronLeft, ChevronRight, CalendarDays, Clock, AlertCircle, CalendarX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SEANCE_COLORS, STATUT_COLORS } from '@/lib/constants';

// ── Créneaux horaires du planning UCCB ─────────────────────────────────────────
const TIME_SLOTS = [
  { id: 'slot1', label: '9h – 11h',      sub: null,    startMin: 9*60,     endMin: 11*60,    isPause: false, rowH: '9rem'  },
  { id: 'slot2', label: '11h15 – 13h15', sub: null,    startMin: 11*60,    endMin: 13*60+15, isPause: false, rowH: '9rem'  },
  { id: 'pause', label: '13h15 – 14h15', sub: 'Pause', startMin: 13*60+15, endMin: 14*60+15, isPause: true,  rowH: '3.5rem'},
  { id: 'slot3', label: '14h15 – 16h15', sub: null,    startMin: 14*60+15, endMin: 16*60+30, isPause: false, rowH: '9rem'  },
];

const WEEK_DAYS = [
  { offset: 0, full: 'Lundi'    },
  { offset: 1, full: 'Mardi'    },
  { offset: 2, full: 'Mercredi' },
  { offset: 3, full: 'Jeudi'    },
  { offset: 4, full: 'Vendredi' },
  { offset: 5, full: 'Samedi'   },
];

// ── Helpers ─────────────────────────────────────────────────────────────────────
function getMondayOf(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function timeToMin(timeStr) {
  if (!timeStr) return 0;
  const [h, m] = timeStr.split(':').map(Number);
  return h * 60 + (m || 0);
}

function formatDayDate(date) {
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' }).format(date);
}

function toDateKey(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function getSlotId(heureDebut) {
  const mins = timeToMin(heureDebut);
  for (const slot of TIME_SLOTS) {
    if (mins >= slot.startMin && mins < slot.endMin) return slot.id;
  }
  return null;
}

// ── Carte de cours ──────────────────────────────────────────────────────────────
function CourseCard({ seance, onClick, isPrintMode }) {
  const { type_seance, statut, module, enseignant } = seance;
  const typeStyle = SEANCE_COLORS[type_seance] || {
    bg: 'bg-slate-100', text: 'text-slate-900', border: 'border-slate-400',
  };
  const estAnnulee  = statut === 'Annulée';
  const estReportee = statut === 'Reportée';

  return (
    <button
      type="button"
      onClick={() => onClick && onClick(seance)}
      className={`
        w-full text-left ${isPrintMode ? 'px-2 py-1.5' : 'px-3 py-3'} border-l-[5px] flex flex-col ${isPrintMode ? 'gap-1' : 'justify-between'}
        transition-all hover:brightness-95 active:scale-[0.98] cursor-pointer
        ${typeStyle.bg} ${typeStyle.border}
        ${estAnnulee ? 'opacity-55' : ''}
      `}
      style={{ flex: 1, minHeight: isPrintMode ? 'min-content' : 0, overflow: isPrintMode ? 'visible' : 'hidden' }}
    >
      {/* Top : badge type + statuts */}
      <div>
        <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
          <span className={`${isPrintMode ? 'text-[8px]' : 'text-[10px]'} font-extrabold uppercase tracking-widest px-2 py-0.5 rounded-md bg-white/60 shadow-sm ${typeStyle.text}`}>
            {type_seance}
          </span>
          {estAnnulee && (
            <span className={`${isPrintMode ? 'text-[8px]' : 'text-[10px]'} font-bold px-1.5 py-0.5 rounded-md bg-rose-100 text-rose-700`}>Annulée</span>
          )}
          {estReportee && (
            <span className={`${isPrintMode ? 'text-[8px]' : 'text-[10px]'} font-bold px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-700`}>Reportée</span>
          )}
          {seance.is_mutualise && (
            <span className={`${isPrintMode ? 'text-[8px]' : 'text-[10px]'} font-bold px-1.5 py-0.5 rounded-md bg-indigo-100 text-indigo-700`}>Mutualisée</span>
          )}
        </div>

        {/* Module */}
        <p className={`${isPrintMode ? 'text-xs' : 'text-sm'} font-bold leading-snug ${isPrintMode ? '' : 'line-clamp-2'} ${typeStyle.text} ${estAnnulee ? 'line-through' : ''}`}>
          {module?.libelle || '—'}
        </p>

        {/* Matière (si différent) */}
        {module?.matiere?.libelle && module.matiere.libelle !== module.libelle && (
          <p className={`${isPrintMode ? 'text-[10px]' : 'text-xs'} leading-tight mt-1 opacity-75 ${typeStyle.text} ${isPrintMode ? '' : 'truncate'}`}>
            {module.matiere.libelle}
          </p>
        )}
      </div>

      {/* Bottom : enseignant */}
      <p className={`${isPrintMode ? 'text-[10px] mt-1' : 'text-xs mt-2'} text-muted-foreground ${isPrintMode ? '' : 'truncate'} font-semibold`}>
        {enseignant?.nom_complet || 'Non assigné'}
      </p>
    </button>
  );
}

// ── Composant principal ─────────────────────────────────────────────────────────
export default function PlanningTableView({
  events = [],
  isLoading,
  isError,
  onSeanceClick = () => {},
  weekStart: externalWeekStart,
  onWeekChange,
  semestre,
  isPrintMode = false,
  title = "Emploi du temps",
}) {
  const [internalWeekStart, setInternalWeekStart] = useState(() => getMondayOf(new Date()));

  // Use external control if provided, else internal
  const weekStart  = externalWeekStart ?? internalWeekStart;
  const setWeekStart = (updater) => {
    const nextVal = typeof updater === 'function' ? updater(weekStart) : updater;
    if (onWeekChange) onWeekChange(nextVal);
    else setInternalWeekStart(nextVal);
  };

  const handlePrev  = () => setWeekStart(d => addDays(d, -7));
  const handleNext  = () => setWeekStart(d => addDays(d,  7));
  const handleToday = () => setWeekStart(getMondayOf(new Date()));

  const weekDays = WEEK_DAYS.map(d => ({
    ...d,
    date:    addDays(weekStart, d.offset),
    dateKey: toDateKey(addDays(weekStart, d.offset)),
  }));

  const weekEnd   = addDays(weekStart, 4);
  const fmt       = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' });
  const fmtYear   = new Intl.DateTimeFormat('fr-FR', { year: 'numeric' });
  
  const debutSemestre = useMemo(() => {
    if (!semestre?.date_debut) return null;
    const [y, m, d] = semestre.date_debut.split('-').map(Number);
    const date = new Date(y, m - 1, d); // Parse in local timezone
    return getMondayOf(date);
  }, [semestre?.date_debut]);

  const weekNumber = debutSemestre 
    ? Math.round((weekStart.getTime() - debutSemestre.getTime()) / (7 * 24 * 60 * 60 * 1000)) + 1 
    : null;

  const dateRangeStr = `${fmt.format(weekStart)} – ${fmt.format(weekEnd)} ${fmtYear.format(weekEnd)}`;
  const weekTitle = weekNumber && weekNumber > 0
    ? `Semaine ${weekNumber} (${dateRangeStr})`
    : dateRangeStr;

  const totalHours = useMemo(() => {
    const wsMs = weekStart.getTime();
    const weMs = addDays(weekStart, 7).getTime();
    let ms = 0;
    events.forEach(e => {
      const s = new Date(e.start);
      if (s >= wsMs && s < weMs) ms += new Date(e.end) - s;
    });
    const h = ms / 3_600_000;
    return h % 1 === 0 ? h : parseFloat(h.toFixed(1));
  }, [events, weekStart]);

  const todayKey = toDateKey(new Date());

  const eventMap = useMemo(() => {
    const map = {};
    events.forEach(e => {
      const rawDate = e.start?.split('T')[0] || e.start?.split(' ')[0];
      const slotId  = getSlotId(e.extendedProps?.heure_debut);
      if (!rawDate || !slotId) return;
      if (!map[rawDate]) map[rawDate] = {};
      if (!map[rawDate][slotId]) map[rawDate][slotId] = [];
      map[rawDate][slotId].push({ id: e.id, ...e.extendedProps });
    });
    return map;
  }, [events]);

  if (isLoading) {
    return (
      <div className="w-full h-64 bg-muted/40 animate-pulse rounded-xl border border-border/60 flex items-center justify-center">
        <span className="text-sm text-muted-foreground font-medium">Chargement de l'emploi du temps…</span>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-destructive/20 bg-destructive/5 rounded-xl p-6 text-center">
        <AlertCircle className="w-10 h-10 text-destructive" />
        <p className="text-sm text-muted-foreground">Une erreur est survenue. Veuillez rafraîchir la page.</p>
      </div>
    );
  }

  // ── État vide contextualisé (aucun cours sur tout le semestre)
  const hasNoEventsAtAll = !isLoading && !isError && events.length === 0;
  const semestreDateDebut = semestre?.date_debut ? new Date(semestre.date_debut) : null;
  const semestreDateFin   = semestre?.date_fin   ? new Date(semestre.date_fin)   : null;
  const now               = new Date();
  const isFuture          = semestreDateDebut && semestreDateDebut > now;
  const isPast            = semestreDateFin   && semestreDateFin   < now;
  const fmtDate = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
  const emptyLabel =
    isFuture ? `Le ${semestre?.libelle || 'semestre'} n'a pas encore commencé. Il débutera le ${fmtDate.format(semestreDateDebut)}.`
  : isPast   ? `Le ${semestre?.libelle || 'semestre'} est terminé (jusqu'au ${fmtDate.format(semestreDateFin)}).`
  :            `Aucun cours n'a été planifié pour ce semestre.`;

  return (
    <div className={`flex flex-col gap-5 ${isPrintMode ? 'w-[1050px] bg-background p-4' : ''}`}>

      {/* ── État vide contextualisé ── */}
      {hasNoEventsAtAll && !isPrintMode && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-muted/30 py-12 px-6 text-center">
          <CalendarX className="h-10 w-10 text-muted-foreground/60" />
          <div>
            <p className="text-sm font-semibold text-foreground mb-1">Aucun cours trouvé</p>
            <p className="text-xs text-muted-foreground max-w-sm">{emptyLabel}</p>
          </div>
        </div>
      )}

      {/* ── Barre de navigation ── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {!isPrintMode ? (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={handlePrev} aria-label="Semaine précédente" className="h-9 w-9">
              <ChevronLeft className="h-4 w-4 text-blue-500" />
            </Button>
            <Button variant="outline" onClick={handleToday} className="h-9 px-4 text-sm font-medium gap-2">
              <CalendarDays className="h-4 w-4 text-blue-500" />
              Aujourd'hui
            </Button>
            <Button variant="outline" size="icon" onClick={handleNext} aria-label="Semaine suivante" className="h-9 w-9">
              <ChevronRight className="h-4 w-4 text-blue-500" />
            </Button>
          </div>
        ) : (
          <div className="text-xl font-extrabold text-foreground tracking-tight text-left flex-1 border-l-4 border-blue-500 pl-3">
            {title}
          </div>
        )}

        <h2 className={`text-base font-semibold text-foreground tracking-tight order-first w-full sm:order-none sm:w-auto sm:flex-1 capitalize ${isPrintMode ? 'text-right pr-4' : 'text-center'}`}>
          {weekTitle}
        </h2>

        {!isPrintMode ? (
          <div className="flex items-center gap-1.5 bg-blue-50 text-blue-600 border border-blue-200 px-3 py-1.5 rounded-lg text-sm font-semibold">
            <Clock className="h-4 w-4 shrink-0 text-blue-500" />
            <span>{totalHours}h de cours</span>
          </div>
        ) : (
          <div className="w-[150px]"></div> // Spacer to keep title centered in print mode
        )}
      </div>

      {/* ── Tableau ── */}
      <div className={`${isPrintMode ? '' : 'overflow-x-auto shadow-sm'} rounded-xl border border-border bg-card`}>
        <table className="w-full border-collapse min-w-[800px] text-sm" style={{ tableLayout: 'fixed' }}>

          {/* Colgroup pour largeurs fixes */}
          <colgroup>
            <col style={{ width: '110px' }} />
            {WEEK_DAYS.map(d => <col key={d.offset} />)}
          </colgroup>

          {/* En-tête jours */}
          <thead>
            <tr>
              <th className="p-4 bg-muted/60 border-b border-r border-border text-xs font-semibold text-muted-foreground text-center">
                Heures
              </th>
              {weekDays.map(day => {
                const isToday = day.dateKey === todayKey;
                return (
                  <th
                    key={day.offset}
                    className={`p-4 border-b border-r border-border text-center last:border-r-0 ${isToday ? 'bg-blue-50/60 dark:bg-blue-950/20' : 'bg-muted/60'}`}
                  >
                    <p className={`text-xs font-bold uppercase tracking-wider ${isToday ? 'text-blue-600' : 'text-foreground'}`}>
                      {day.full}
                    </p>
                    <p className={`text-xs mt-1 ${isToday ? 'text-blue-500 font-semibold' : 'text-muted-foreground'}`}>
                      {formatDayDate(day.date)}
                    </p>
                    {isToday && (
                      <div className="mt-2 w-1.5 h-1.5 rounded-full bg-blue-500 mx-auto" />
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody>
            {TIME_SLOTS.map((slot, slotIdx) => {
              const isLast = slotIdx === TIME_SLOTS.length - 1;
              return (
                <tr
                  key={slot.id}
                  className={slot.isPause ? 'bg-amber-50/70 dark:bg-amber-950/20' : 'bg-card'}
                >
                  {/* Colonne horaire */}
                  <td
                    className={`
                      border-r border-b ${isLast ? 'border-b-0' : ''} border-border text-center align-middle
                      ${slot.isPause ? 'bg-amber-100/60 dark:bg-amber-950/30' : 'bg-muted/30'}
                    `}
                    style={{ height: slot.rowH }}
                  >
                    <div className="px-3 py-2">
                      <p className={`text-xs font-bold leading-snug whitespace-nowrap ${slot.isPause ? 'text-amber-700 dark:text-amber-400' : 'text-foreground'}`}>
                        {slot.label}
                      </p>
                      {slot.sub && (
                        <p className="text-[10px] text-amber-600/70 dark:text-amber-500/70 mt-1.5 font-semibold uppercase tracking-widest">
                          {slot.sub}
                        </p>
                      )}
                    </div>
                  </td>

                  {/* Cellules par jour */}
                  {weekDays.map(day => {
                    const isToday = day.dateKey === todayKey;
                    const cellSeances = eventMap[day.dateKey]?.[slot.id] || [];

                    return (
                      <td
                        key={day.offset}
                        className={`
                          border-r border-b ${isLast ? 'border-b-0' : ''} last:border-r-0 border-border
                          ${slot.isPause ? 'bg-amber-50/40 dark:bg-amber-950/10' : ''}
                          ${isToday && !slot.isPause ? 'bg-blue-50/30 dark:bg-blue-950/10' : ''}
                        `}
                        style={{
                          height: slot.rowH,
                          position: 'relative',
                          overflow: isPrintMode ? 'visible' : 'hidden',
                        }}
                      >
                        {cellSeances.length > 0 && (
                          <div
                            style={{
                              position: 'absolute',
                              top: 0, left: 0, right: 0, bottom: 0,
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 0,
                            }}
                          >
                            {cellSeances.map((seance, i) => (
                              <div
                                key={seance.id ?? i}
                                style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
                              >
                                <CourseCard seance={seance} onClick={onSeanceClick} isPrintMode={isPrintMode} />
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
