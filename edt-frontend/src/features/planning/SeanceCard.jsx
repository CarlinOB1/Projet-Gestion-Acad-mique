/**
 * @file SeanceCard.jsx
 * @description Rendu custom d'un événement FullCalendar — adapté au type et statut de la séance.
 */
import { CalendarClock } from 'lucide-react';
import { SEANCE_COLORS, STATUT_COLORS } from '@/lib/constants';
import { formatHeure } from '@/lib/utils';

/**
 * @param {{ eventInfo: Object }} props - Payload eventContent de FullCalendar
 */
export default function SeanceCard({ eventInfo }) {
  const { event } = eventInfo;
  const { type_seance, statut, heure_debut, heure_fin, module, enseignant } =
    event.extendedProps;

  const typeStyle = SEANCE_COLORS[type_seance] || {
    bg:     'bg-slate-50',
    border: 'border-slate-400',
    text:   'text-slate-900',
  };

  const statutStyle = STATUT_COLORS[statut] || {
    bg:   'bg-slate-100',
    text: 'text-slate-700',
  };

  const isAnnulee  = statut === 'Annulée';
  const isReportee = statut === 'Reportée';

  return (
    <div
      className={`flex flex-col h-full w-full p-1.5 rounded-sm overflow-hidden border-l-4 select-none
        ${typeStyle.bg} ${typeStyle.border}
        ${isAnnulee ? 'opacity-60' : ''}`}
    >
      {/* Ligne 1 : badge type + horaire */}
      <div className="flex items-center gap-1.5 text-[10px] leading-none font-semibold mb-1 shrink-0">
        {/* CORRECTION : typeStyle.badge inexistant — on utilise bg + text du type */}
        <span className={`px-1 py-0.5 rounded-sm uppercase tracking-wide ${typeStyle.bg} ${typeStyle.text}`}>
          {type_seance}
        </span>
        <span className="text-muted-foreground font-medium">
          {formatHeure(heure_debut)} → {formatHeure(heure_fin)}
        </span>
      </div>

      {/* Ligne 2 : module */}
      <h4 className={`text-xs font-medium truncate leading-snug ${typeStyle.text}`}>
        {module?.libelle || 'Sans module'}
      </h4>

      {/* Ligne 3 : enseignant */}
      <p className="text-[11px] text-muted-foreground truncate leading-normal">
        {enseignant?.nom_complet || 'Enseignant non assigné'}
      </p>

      {/* Ligne 4 : badge statut — masqué si Confirmée */}
      {statut !== 'Confirmée' && (
        <div className="mt-auto pt-1 flex items-center shrink-0">
          <span className={`inline-flex items-center gap-0.5 px-1 py-0.5 rounded-sm text-[10px] font-medium
            ${statutStyle.bg} ${statutStyle.text}`}>
            {isReportee && (
              <CalendarClock className="w-2.5 h-2.5 shrink-0" aria-hidden="true" />
            )}
            <span>{statut}</span>
          </span>
        </div>
      )}
    </div>
  );
}