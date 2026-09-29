/**
 * PageHeader — en-tête commun à toutes les pages : titre, description courte
 * et actions alignées à droite (passées en enfants).
 * Avant lui, chaque page avait son style (titre seul, titre avec icône,
 * marges différentes), ce qui donnait l'impression de changer d'application.
 */
import { cn } from '@/lib/utils';

export default function PageHeader({ titre, description, children, className }) {
  return (
    <header
      className={cn(
        'flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0">
        <h1 className="text-2xl font-bold text-foreground text-balance">{titre}</h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground text-pretty">{description}</p>
        )}
      </div>
      {children && (
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0">{children}</div>
      )}
    </header>
  );
}
