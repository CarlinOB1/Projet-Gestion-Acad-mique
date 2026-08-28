import { useQuery } from "@tanstack/react-query";
import { getEnseignants } from "@/api/acteurs";
import EnseignantRow from "./EnseignantRow";

export default function EnseignantsPage() {
  const {
    data: enseignants = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["enseignants"],
    queryFn: getEnseignants,
  });

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
