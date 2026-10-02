/**
 * @file EnseignantCard.jsx
 * @description Carte individuelle du trombinoscope — avatar (initiales), nom,
 * grade et département, modules enseignés à la classe avec le type de cours
 * (CM, TD, TP), et prochain cours avec cet enseignant.
 */
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { CalendarClock } from '@/components/ui/icons';
import { formatJourProche } from '@/lib/creneau';
import { getInitials } from '@/lib/trombinoscope';
import { formatCreneau } from '@/lib/utils';

/**
 * @param {{ enseignant: { nom_complet, grade, departement, modules: Array, prochaine: Object|null } }} props
 */
export default function EnseignantCard({ enseignant }) {
  const { nom_complet, grade, departement, modules, prochaine } = enseignant;
  const fonction = [grade, departement].filter(Boolean).join(' · ');

  return (
    <Card className="gap-4">
      <div className="flex items-center gap-3">
        <Avatar size="lg">
          <AvatarFallback className="bg-primary/10 text-primary font-semibold">
            {getInitials(nom_complet)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <h3 className="font-semibold text-foreground leading-snug text-pretty">{nom_complet}</h3>
          {fonction && <p className="mt-0.5 text-xs text-muted-foreground text-pretty">{fonction}</p>}
        </div>
      </div>

      {modules.length > 0 && (
        <ul aria-label="Modules enseignés à votre classe" className="flex flex-wrap gap-1.5">
          {modules.map((module) => (
            <li key={module.id} className="rounded-md bg-muted px-2 py-1 text-xs font-medium text-foreground">
              {module.libelle}
              {module.types.length > 0 && (
                <span className="font-normal text-muted-foreground"> · {module.types.join(', ')}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-auto flex items-start gap-2 border-t border-border pt-3 text-xs">
        <CalendarClock className="mt-px size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        {prochaine ? (
          <p className="min-w-0 text-muted-foreground">
            Prochain cours :{' '}
            <span className="font-medium text-foreground">
              {formatJourProche(prochaine.date)} · {formatCreneau(prochaine.debut, prochaine.fin)}
            </span>
            <span className="block truncate">
              {[
                prochaine.seance?.module?.libelle,
                prochaine.seance?.type_seance,
                prochaine.seance?.statut === 'Reportée' && 'cours reporté',
              ].filter(Boolean).join(' · ')}
            </span>
          </p>
        ) : (
          <p className="text-muted-foreground">Plus de cours prévu avec votre classe ce semestre</p>
        )}
      </div>
    </Card>
  );
}
