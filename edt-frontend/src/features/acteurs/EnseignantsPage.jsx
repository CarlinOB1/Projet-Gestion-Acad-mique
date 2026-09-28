import { useQuery } from "@tanstack/react-query";
import { getEnseignants } from "@/api/acteurs";
import PageHeader from "@/components/shared/PageHeader";
import EnseignantRow from "./EnseignantRow";

export default function EnseignantsPage() {
  const {
    data: enseignants = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["enseignants"],
    // Fonction fléchée : passée directement, getEnseignants recevait le
    // contexte de React Query comme filtres et l'envoyait au serveur
    // (?client=[object Object]&signal=…).
    queryFn: () => getEnseignants(),
  });

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <PageHeader
        titre="Enseignants"
        description="Cliquez sur un enseignant pour voir ses coordonnées, ses modules et l'avancement de ses heures."
      />

      <div className="space-y-3">
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            <div className="h-16 bg-muted rounded-lg w-full" />
            <div className="h-16 bg-muted rounded-lg w-full" />
            <div className="h-16 bg-muted rounded-lg w-full" />
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
          enseignants.map((enseignant) => (
            <EnseignantRow
              key={enseignant.profil_id}
              enseignant={enseignant}
            />
          ))
        )}
      </div>
    </div>
  );
}
