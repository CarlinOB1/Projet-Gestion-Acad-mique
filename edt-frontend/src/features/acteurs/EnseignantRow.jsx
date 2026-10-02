import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from '@/components/ui/icons';
import { getAffectations } from "@/api/affectations";
import { getAnnees } from "@/api/academique";
import { Badge } from "@/components/ui/badge";
import { STATUT_COLORS, STATUT_LABELS } from "@/lib/constants";
import { cn, formatNombreHeures } from "@/lib/utils";

/** Une information de la fiche, en texte simple (ce n'est pas un champ modifiable). */
function Info({ label, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-foreground truncate">{children || "—"}</dd>
    </div>
  );
}

/**
 * horsDepartement : l'enseignant appartient à un département que le chef ne
 * dirige pas. Ses coordonnées restent consultables, mais la liste des modules
 * se limite à ceux qu'il assure chez ce chef (le serveur ne renvoie que ceux-là).
 */
export default function EnseignantRow({ enseignant, horsDepartement = false }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Les affectations sont historisees par annee academique : sans ce filtre,
  // la fiche cumule toutes les annees et affiche les memes modules en double.
  const { data: annees = [] } = useQuery({
    queryKey: ["annees", "active"],
    queryFn: () => getAnnees({ statut: "active" }),
    enabled: isExpanded,
    staleTime: 5 * 60 * 1000,
  });
  const anneeActiveId = annees[0]?.id;

  const { data: affectations = [], isLoading: loadingAffectations } = useQuery({
    queryKey: ["affectations", "enseignant", enseignant.profil_id, anneeActiveId],
    queryFn: () => getAffectations({
      enseignant_id: enseignant.profil_id,
      annee_id: anneeActiveId,
    }),
    enabled: isExpanded && !!anneeActiveId,
  });

  // Calculs statistiques
  const totalHeuresPrevues = affectations.reduce(
    (acc, curr) => acc + parseFloat(curr.heures_prevues || 0),
    0
  );
  // heures_consommees = volume planifie sur le semestre ;
  // heures_effectuees = heures reellement dispensees a ce jour.
  const totalHeuresEffectuees = affectations.reduce(
    (acc, curr) => acc + parseFloat(curr.heures_effectuees ?? curr.heures_consommees ?? 0),
    0
  );
  const totalCredits = affectations.reduce(
    (acc, curr) => acc + parseFloat(curr.module?.credits || 0),
    0
  );

  // Badge affiché seulement quand le compte n'est pas actif : un « actif »
  // répété sur chaque ligne n'apprenait rien.
  const statut = enseignant.profil?.statut;
  const c = STATUT_COLORS[statut] || {};
  const user = enseignant.profil?.user;
  const panneauId = `enseignant-${enseignant.profil_id}`;

  return (
    // Pas de cadre propre : la ligne s'inscrit dans le bloc de son département.
    <div className="bg-card">
      {/* Ligne résumé : un vrai bouton, avec une flèche qui montre qu'il s'ouvre */}
      <button
        type="button"
        aria-expanded={isExpanded}
        aria-controls={panneauId}
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left hover:bg-muted/30 transition-colors"
      >
        <div className="flex flex-col min-w-0">
          <span className="font-semibold text-base text-card-foreground truncate">
            {enseignant.nom_complet}
          </span>
          {/* Le département est dans l'intitulé du groupe, au-dessus. */}
          <span className="text-sm text-muted-foreground truncate">
            {enseignant.grade || "Aucun grade"}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {statut && statut !== "actif" && (
            <Badge className={`px-2.5 py-0.5 text-xs ${c.bg} ${c.text} ${c.border}`}>
              {STATUT_LABELS[statut] ?? statut}
            </Badge>
          )}
          <ChevronDown
            className={cn("size-4 text-muted-foreground", isExpanded && "rotate-180")}
            aria-hidden
          />
        </div>
      </button>

      {/* Contenu déroulant */}
      {isExpanded && (
        <div
          id={panneauId}
          className="border-t border-border p-5 grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]"
        >
          {/* Colonne gauche : coordonnées, visibles pour tous les départements */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Coordonnées</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div className="col-span-2">
                <Info label="E-mail">{user?.email}</Info>
              </div>
              <Info label="Téléphone">{enseignant.profil?.telephone}</Info>
              <Info label="Genre">
                {enseignant.profil?.genre === "M" ? "Masculin" : enseignant.profil?.genre === "F" ? "Féminin" : null}
              </Info>
              <Info label="Grade">{enseignant.grade}</Info>
              <Info label="Contrat">{enseignant.contrat}</Info>
            </dl>
          </section>

          {/* Colonne droite : charge et avancement */}
          <section className="space-y-4 min-w-0">
            <h3 className="text-sm font-semibold text-foreground">
              {horsDepartement ? "Modules dans votre département" : "Modules de l'année"}
            </h3>

            {loadingAffectations ? (
              <div className="animate-pulse space-y-2">
                <div className="h-14 bg-muted rounded-lg w-full" />
                <div className="h-8 bg-muted rounded w-full" />
                <div className="h-8 bg-muted rounded w-full" />
              </div>
            ) : (
              <>
                {/* Trois compteurs à zéro n'apprennent rien de plus que le message ci-dessous. */}
                {affectations.length > 0 && (
                  <dl className="grid grid-cols-3 gap-3">
                    <div className="p-3 border border-border rounded-lg">
                      <dt className="text-xs text-muted-foreground">Heures prévues</dt>
                      <dd className="text-xl font-bold text-foreground tabular-nums">{formatNombreHeures(totalHeuresPrevues)}</dd>
                    </div>
                    <div className="p-3 border border-border rounded-lg">
                      <dt className="text-xs text-muted-foreground">Heures faites</dt>
                      <dd className="text-xl font-bold text-foreground tabular-nums">{formatNombreHeures(totalHeuresEffectuees)}</dd>
                    </div>
                    <div className="p-3 border border-border rounded-lg">
                      <dt className="text-xs text-muted-foreground">Crédits · modules</dt>
                      <dd className="text-xl font-bold text-foreground tabular-nums">
                        {totalCredits} <span className="text-sm font-medium text-muted-foreground">· {affectations.length}</span>
                      </dd>
                    </div>
                  </dl>
                )}

                {affectations.length === 0 ? (
                  <p className="text-sm text-muted-foreground p-4 text-center border border-dashed rounded-lg text-pretty">
                    {horsDepartement
                      ? "Aucun module dans votre département cette année. Pour lui en confier un, passez par « Contenu Pédagogique » en cochant « Intervention inter-départements »."
                      : "Aucun module affecté cette année. Les affectations se font depuis « Contenu Pédagogique »."}
                  </p>
                ) : (
                  // Tableau compact : 13 modules en grandes cartes obligeaient
                  // à faire défiler plusieurs écrans.
                  <div className="overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50 text-xs text-muted-foreground">
                        <tr>
                          <th scope="col" className="text-left font-semibold px-3 py-2">Module</th>
                          <th scope="col" className="text-left font-semibold px-3 py-2">Type</th>
                          <th scope="col" className="text-left font-semibold px-3 py-2 w-44">Faites / prévues</th>
                        </tr>
                      </thead>
                      <tbody>
                        {affectations.map((aff) => {
                          const prevues = parseFloat(aff.heures_prevues || 0);
                          const faites = parseFloat(aff.heures_effectuees ?? aff.heures_consommees ?? 0);
                          const pourcentage = prevues > 0 ? Math.min(100, Math.round((faites / prevues) * 100)) : 0;
                          return (
                            <tr key={aff.id} className="border-t border-border">
                              <td className="px-3 py-2 align-top">
                                <p className="font-medium text-foreground text-pretty">
                                  {aff.module?.libelle}
                                  {aff.hors_departement && (
                                    <Badge variant="outline" className="ml-2 text-[10px] align-middle">
                                      {aff.module?.matiere?.departement?.libelle ?? "Autre département"}
                                    </Badge>
                                  )}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {aff.module?.classe?.libelle}
                                  {aff.module?.credits ? ` · ${aff.module.credits} ECTS` : ""}
                                </p>
                              </td>
                              <td className="px-3 py-2 align-top text-xs font-semibold text-muted-foreground">
                                {aff.type_seance ?? "Tous"}
                              </td>
                              <td className="px-3 py-2 align-top">
                                <div className="flex justify-between text-xs text-muted-foreground tabular-nums mb-1">
                                  <span>{formatNombreHeures(faites)} / {formatNombreHeures(prevues)}</span>
                                  <span>{pourcentage} %</span>
                                </div>
                                <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                                  <div className="bg-primary h-full rounded-full" style={{ width: `${pourcentage}%` }} />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
