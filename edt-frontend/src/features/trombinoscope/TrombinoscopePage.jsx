/**
 * @file TrombinoscopePage.jsx
 * @description Page listant les enseignants intervenant dans le planning de
 * l'étudiant connecté, regroupés avec leurs matières respectives.
 */
import { Users } from 'lucide-react';
import { useTrombinoscope } from '@/hooks/useTrombinoscope';
import EnseignantCard from './EnseignantCard';

export default function TrombinoscopePage() {
  const { enseignants, isLoading, isError } = useTrombinoscope();

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <header className="border-b border-border pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Mes enseignants
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Retrouvez les enseignants qui interviennent dans votre planning ce semestre.
        </p>
      </header>

      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div
              key={index}
              className="h-40 rounded-xl border border-border/60 bg-muted/40 animate-pulse"
            />
          ))}
        </div>
      )}

      {!isLoading && isError && (
        <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-destructive/20 bg-destructive/5 rounded-lg p-6 text-center">
          <Users className="w-10 h-10 text-destructive" aria-hidden="true" />
          <h3 className="font-semibold text-lg text-foreground">
            Impossible de charger vos enseignants
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            Une erreur est survenue. Veuillez rafraîchir la page ou réessayer plus tard.
          </p>
        </div>
      )}

      {!isLoading && !isError && enseignants.length === 0 && (
        <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-border/60 bg-muted/20 rounded-lg p-6 text-center">
          <Users className="w-10 h-10 text-muted-foreground" aria-hidden="true" />
          <h3 className="font-semibold text-lg text-foreground">
            Aucun enseignant trouvé
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            Vos enseignants apparaîtront ici dès que des séances seront planifiées
            pour votre classe.
          </p>
        </div>
      )}

      {!isLoading && !isError && enseignants.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {enseignants.map((enseignant) => (
            <EnseignantCard key={enseignant.id} enseignant={enseignant} />
          ))}
        </div>
      )}
    </div>
  );
}