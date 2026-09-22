import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getEnseignants, getMonProfil } from "@/api/acteurs";
import useAuthStore from "@/store/authStore";
import { Badge } from "@/components/ui/badge";
import EnseignantRow from "./EnseignantRow";

export default function EnseignantsPage() {
  const role = useAuthStore((state) => state.user?.role);
  const estChef = role === "chef_departement";

  // Le chef consulte les enseignants de tous les départements ; l'API renvoie
  // déjà le sien en premier. Clé distincte de ["enseignants"], utilisée
  // ailleurs pour la liste restreinte au département.
  const {
    data: enseignants = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["enseignants", "tous-departements"],
    queryFn: () => getEnseignants({ tous_departements: 1 }),
  });

  const { data: profil } = useQuery({
    queryKey: ["mon-profil"],
    queryFn: getMonProfil,
    enabled: estChef,
  });
  const monDepartementId = estChef ? profil?.enseignant?.departement?.id : null;

  // Regroupe par département en conservant l'ordre reçu de l'API.
  const groupes = useMemo(() => {
    const parDepartement = new Map();
    enseignants.forEach((enseignant) => {
      const dept = enseignant.departement;
      const cle = dept?.id ?? "aucun";
      if (!parDepartement.has(cle)) {
        parDepartement.set(cle, {
          id: dept?.id ?? null,
          libelle: dept?.libelle || "Aucun département",
          enseignants: [],
        });
      }
      parDepartement.get(cle).enseignants.push(enseignant);
    });
    return [...parDepartement.values()];
  }, [enseignants]);

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Enseignants
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Consultation du corps enseignant et de leurs avancements.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {isLoading ? (
          <div className="animate-pulse space-y-4">
            <div className="h-16 bg-muted/40 rounded-lg w-full"></div>
            <div className="h-16 bg-muted/40 rounded-lg w-full"></div>
            <div className="h-16 bg-muted/40 rounded-lg w-full"></div>
          </div>
        ) : isError ? (
          <div className="p-5 text-center text-destructive bg-destructive/10 rounded-lg">
            Une erreur est survenue lors du chargement des enseignants.
          </div>
        ) : enseignants.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground border border-dashed rounded-lg">
            Aucun enseignant enregistré.
          </div>
        ) : (
          groupes.map((groupe) => {
            const estMonDepartement =
              monDepartementId != null && groupe.id === monDepartementId;
            return (
              <section key={groupe.id ?? "aucun"} className="space-y-3">
                <div className="flex items-center gap-2 pt-2">
                  <h2 className="text-lg font-semibold text-foreground">
                    {groupe.libelle}
                  </h2>
                  {estMonDepartement && <Badge>Votre département</Badge>}
                  <span className="text-sm text-muted-foreground">
                    ({groupe.enseignants.length})
                  </span>
                </div>
                {groupe.enseignants.map((enseignant) => (
                  <EnseignantRow
                    key={enseignant.profil_id}
                    enseignant={enseignant}
                    // L'API des affectations est limitée au périmètre du chef :
                    // hors de son département, la fiche serait vide ou fausse.
                    affectationsVisibles={!estChef || estMonDepartement}
                  />
                ))}
              </section>
            );
          })
        )}
      </div>
    </div>
  );
}
