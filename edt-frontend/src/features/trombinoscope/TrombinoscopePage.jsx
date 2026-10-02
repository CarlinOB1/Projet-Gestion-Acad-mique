/**
 * @file TrombinoscopePage.jsx
 * @description Page listant les enseignants intervenant dans le planning de
 * l'étudiant connecté, avec leurs modules et le prochain cours avec chacun.
 */
import { useState } from 'react';
import { Search, Users } from '@/components/ui/icons';
import { Input } from '@/components/ui/input';
import PageHeader from '@/components/shared/PageHeader';
import { useTrombinoscope } from '@/hooks/useTrombinoscope';
import EnseignantCard from './EnseignantCard';

/** Au-delà, une recherche aide à retrouver quelqu'un (même seuil que la page du chef). */
const SEUIL_RECHERCHE = 8;

/** Minuscules sans accents : « Géologie » se trouve en tapant « geologie ». */
const normaliser = (texte = '') =>
  texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

function description(nombre) {
  if (nombre === 0) return 'Les enseignants qui interviennent dans votre classe ce semestre.';
  if (nombre === 1) return "L'enseignant qui intervient dans votre classe ce semestre.";
  return `Les ${nombre} enseignants qui interviennent dans votre classe ce semestre.`;
}

export default function TrombinoscopePage() {
  const { enseignants, isLoading, isError } = useTrombinoscope();
  const [recherche, setRecherche] = useState('');

  // Par nom ou par module : l'étudiant cherche souvent « qui fait l'anglais ? ».
  const terme = normaliser(recherche.trim());
  const enseignantsAffiches = terme
    ? enseignants.filter((e) =>
        [e.nom_complet, ...e.modules.map((m) => m.libelle)].some((texte) => normaliser(texte).includes(terme))
      )
    : enseignants;

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <PageHeader titre="Mes enseignants" description={description(isLoading ? 0 : enseignants.length)} />

      {!isLoading && !isError && enseignants.length > SEUIL_RECHERCHE && (
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" aria-hidden />
          <Input
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher un enseignant ou un module…"
            aria-label="Rechercher un enseignant ou un module"
            className="pl-8"
          />
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="h-44 rounded-xl bg-muted/60 animate-pulse"
            />
          ))}
        </div>
      )}

      {!isLoading && isError && (
        <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-destructive/20 bg-destructive/5 rounded-lg p-6 text-center">
          <Users className="w-10 h-10 text-destructive" aria-hidden="true" />
          <h2 className="font-semibold text-lg text-foreground">
            Impossible de charger vos enseignants
          </h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Une erreur est survenue. Veuillez rafraîchir la page ou réessayer plus tard.
          </p>
        </div>
      )}

      {!isLoading && !isError && enseignants.length === 0 && (
        <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-border/60 bg-muted/20 rounded-lg p-6 text-center">
          <Users className="w-10 h-10 text-muted-foreground" aria-hidden="true" />
          <h2 className="font-semibold text-lg text-foreground">
            Aucun enseignant trouvé
          </h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Vos enseignants apparaîtront ici dès que des séances seront planifiées
            pour votre classe.
          </p>
        </div>
      )}

      {!isLoading && !isError && enseignants.length > 0 && (
        enseignantsAffiches.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {enseignantsAffiches.map((enseignant) => (
              <EnseignantCard key={enseignant.id} enseignant={enseignant} />
            ))}
          </div>
        ) : (
          <p className="p-10 text-center text-sm text-muted-foreground border border-dashed rounded-lg">
            Aucun enseignant ne correspond à « {recherche.trim()} ».
          </p>
        )
      )}
    </div>
  );
}
