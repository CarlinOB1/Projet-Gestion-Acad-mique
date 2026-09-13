import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAffectations } from "@/api/affectations";
import { getAnnees } from "@/api/academique";
import { Badge } from "@/components/ui/badge";
import { STATUT_COLORS } from "@/lib/constants";

export default function EnseignantRow({ enseignant }) {
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

  const c = STATUT_COLORS[enseignant.profil?.statut] || {};

  return (
    <div className="border border-border rounded-lg mb-3 bg-card shadow-sm overflow-hidden">
      {/* Ligne Résumé (Cliquable) */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex flex-col">
          <span className="font-semibold text-base text-card-foreground">
            {enseignant.nom_complet}
          </span>
          <span className="text-sm text-muted-foreground">
            {enseignant.grade || "Aucun grade"} • {enseignant.departement?.libelle || "Aucun département"}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Badge className={`px-2.5 py-0.5 text-xs ${c.bg} ${c.text} ${c.border}`}>
            {enseignant.profil?.statut}
          </Badge>
        </div>
      </div>

      {/* Contenu Déroulant */}
      {isExpanded && (
        <div className="border-t border-border p-5 bg-muted/10 grid grid-cols-1 xl:grid-cols-2 gap-8">
          
          {/* Colonne Gauche : Informations */}
          <div className="space-y-5">
            <div>
              <h3 className="text-base font-semibold text-foreground mb-1">
                Informations Personnelles
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Détails personnels et académiques de cet enseignant.
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Prénom</p>
                  <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                    {enseignant.profil?.user?.first_name || "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Nom</p>
                  <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                    {enseignant.profil?.user?.last_name || "-"}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Email</p>
                <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                  {enseignant.profil?.user?.email || "-"}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Genre</p>
                  <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                    {enseignant.profil?.genre === "M" ? "Masculin" : enseignant.profil?.genre === "F" ? "Féminin" : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Téléphone</p>
                  <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                    {enseignant.profil?.telephone || "-"}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Grade</p>
                  <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                    {enseignant.grade || "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Contrat</p>
                  <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                    {enseignant.contrat || "-"}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Département</p>
                <p className="text-sm font-semibold bg-background p-2 rounded border border-border">
                  {enseignant.departement?.libelle || "-"}
                </p>
              </div>
            </div>


          </div>

          {/* Colonne Droite : Modules, Heures, Crédits et Avancement */}
          <div className="space-y-5">
            <div>
              <h3 className="text-base font-semibold text-foreground mb-1">
                Avancement et Modules Affectés
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Suivi pédagogique et charge horaire.
              </p>
            </div>

            {loadingAffectations ? (
              <div className="animate-pulse space-y-3">
                <div className="h-20 bg-muted/40 rounded-lg w-full"></div>
                <div className="h-20 bg-muted/40 rounded-lg w-full"></div>
              </div>
            ) : (
              <div className="space-y-5">
                
                {/* Cartes Statistiques */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-4 border border-border rounded-lg bg-background">
                    <p className="text-xs text-muted-foreground mb-1">Heures Prévues</p>
                    <p className="text-2xl font-bold text-foreground">
                      {totalHeuresPrevues.toFixed(1)} h
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Réalisées : {totalHeuresEffectuees.toFixed(1)} h
                    </p>
                  </div>
                  <div className="p-4 border border-border rounded-lg bg-background">
                    <p className="text-xs text-muted-foreground mb-1">Total Crédits</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {totalCredits}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {affectations.length} module(s)
                    </p>
                  </div>
                </div>

                {/* Liste des modules */}
                <div className="space-y-3">
                  <h4 className="font-medium text-foreground text-sm border-b border-border pb-1">
                    Détail des modules
                  </h4>
                  {affectations.length === 0 ? (
                    <p className="text-xs text-muted-foreground italic p-3 text-center border border-dashed rounded-lg">
                      Aucun module affecté.
                    </p>
                  ) : (
                    affectations.map((aff) => {
                      const prevues = parseFloat(aff.heures_prevues || 0);
                      const consommees = parseFloat(
                        aff.heures_effectuees ?? aff.heures_consommees ?? 0
                      );
                      const pourcentage = prevues > 0 ? Math.min(100, Math.round((consommees / prevues) * 100)) : 0;
                      
                      return (
                        <div key={aff.id} className="p-4 border border-border rounded-lg bg-background space-y-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <h5 className="font-semibold text-foreground text-sm">
                                  {aff.module?.libelle}
                                  {aff.hors_departement && aff.module?.matiere?.departement?.libelle
                                    ? ` — ${aff.module.matiere.departement.libelle}`
                                    : ''}
                                </h5>
                                {aff.hors_departement && (
                                  <Badge variant="outline" className="text-xs">Inter-département</Badge>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {aff.type_seance} • {aff.module?.credits} crédits
                                {aff.module?.classe?.libelle
                                  ? ` • ${aff.module.classe.libelle}`
                                  : ''}
                              </p>
                            </div>
                            <span className="font-medium text-xs px-2 py-0.5 bg-muted rounded-full">
                              {pourcentage}%
                            </span>
                          </div>
                          
                          {/* Barre de progression */}
                          <div className="space-y-1.5">
                            <div className="flex justify-between text-[11px] text-muted-foreground">
                              <span>{consommees.toFixed(1)} h réalisées</span>
                              <span>{prevues.toFixed(1)} h prévues</span>
                            </div>
                            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                              <div 
                                className="bg-blue-600 h-full transition-all duration-500 ease-in-out rounded-full"
                                style={{ width: `${pourcentage}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

              </div>
            )}
          </div>
          
        </div>
      )}
    </div>
  );
}
