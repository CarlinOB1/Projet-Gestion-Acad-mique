import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { getEnseignants } from "@/api/acteurs";
import useAuthStore, { selectIsChefDepartement } from "@/store/authStore";
import PageHeader from "@/components/shared/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import EnseignantRow from "./EnseignantRow";

const parNom = (a, b) => (a.nom_complet ?? "").localeCompare(b.nom_complet ?? "", "fr");

/** « Département Informatique » → « Informatique », pour les raccourcis. */
const nomCourt = (libelle) => libelle.replace(/^Département\s+/i, "");

/** Un groupe par département : ceux du chef d'abord, puis les autres par ordre alphabétique. */
function grouperParDepartement(enseignants, departementsDuChef) {
  const groupes = new Map();
  for (const enseignant of enseignants) {
    const id = enseignant.departement?.id ?? "aucun";
    if (!groupes.has(id)) {
      groupes.set(id, {
        id,
        libelle: enseignant.departement?.libelle ?? "Sans département",
        estLeSien: departementsDuChef.has(id),
        enseignants: [],
      });
    }
    groupes.get(id).enseignants.push(enseignant);
  }
  return [...groupes.values()]
    .map((groupe) => ({ ...groupe, enseignants: groupe.enseignants.sort(parNom) }))
    .sort((a, b) => (b.estLeSien - a.estLeSien) || a.libelle.localeCompare(b.libelle, "fr"));
}

export default function EnseignantsPage() {
  const estChef = useAuthStore(selectIsChefDepartement);
  const [vue, setVue] = useState("mien");
  const [recherche, setRecherche] = useState("");
  const [departementChoisi, setDepartementChoisi] = useState(null);
  const voirTous = estChef && vue === "tous";

  // Pour un chef, le serveur ne renvoie par défaut que son département : cette
  // liste sert aussi à reconnaître les siens quand il affiche tout le monde.
  const mesEnseignants = useQuery({
    queryKey: ["enseignants"],
    // Fonction fléchée : passée directement, getEnseignants recevait le
    // contexte de React Query comme filtres et l'envoyait au serveur
    // (?client=[object Object]&signal=…).
    queryFn: () => getEnseignants(),
  });
  const tousLesEnseignants = useQuery({
    queryKey: ["enseignants", "tous"],
    queryFn: () => getEnseignants({ tous_departements: 1 }),
    enabled: voirTous,
  });

  const requete = voirTous ? tousLesEnseignants : mesEnseignants;
  const enseignants = requete.data ?? [];
  const isLoading = requete.isLoading || (voirTous && mesEnseignants.isLoading);
  const isError = requete.isError;

  const idsDuChef = useMemo(
    () => new Set((mesEnseignants.data ?? []).map((e) => e.profil_id)),
    [mesEnseignants.data]
  );
  const departementsDuChef = useMemo(
    () => new Set(estChef ? (mesEnseignants.data ?? []).map((e) => e.departement?.id) : []),
    [estChef, mesEnseignants.data]
  );

  const terme = recherche.trim().toLowerCase();
  const enseignantsAffiches = terme
    ? enseignants.filter((e) => (e.nom_complet ?? "").toLowerCase().includes(terme))
    : enseignants;
  const groupes = grouperParDepartement(enseignantsAffiches, departementsDuChef);
  // Un seul département affiché à la fois ; par défaut le premier, c'est-à-dire
  // celui du chef. Si une recherche vide le département choisi, on passe au
  // premier qui a encore des résultats.
  const groupeAffiche = groupes.find((g) => g.id === departementChoisi) ?? groupes[0];

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <PageHeader
        titre="Enseignants"
        description="Cliquez sur un enseignant pour voir ses coordonnées, ses modules et l'avancement de ses heures."
      >
        {estChef && (
          <Tabs value={vue} onValueChange={(v) => { setVue(v); setRecherche(""); setDepartementChoisi(null); }}>
            <TabsList>
              <TabsTrigger value="mien" className="px-3">Mon département</TabsTrigger>
              <TabsTrigger value="tous" className="px-3">Tous les départements</TabsTrigger>
            </TabsList>
          </Tabs>
        )}
      </PageHeader>

      {voirTous && (
        <p className="text-sm text-muted-foreground text-pretty">
          Pour les enseignants des autres départements, la liste des modules se limite à ceux qu'ils assurent chez vous.
        </p>
      )}

      {!isLoading && (enseignants.length > 8 || groupes.length > 1) && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
          {enseignants.length > 8 && (
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" aria-hidden />
              <Input
                value={recherche}
                onChange={(e) => setRecherche(e.target.value)}
                placeholder="Rechercher un enseignant…"
                aria-label="Rechercher un enseignant"
                className="pl-8"
              />
            </div>
          )}
          {/* Choix du département affiché en dessous. */}
          {groupes.length > 1 && (
            <nav aria-label="Choisir un département" className="flex flex-wrap gap-2">
              {groupes.map((groupe) => {
                const actif = groupe.id === groupeAffiche?.id;
                return (
                  <button
                    key={groupe.id}
                    type="button"
                    aria-pressed={actif}
                    aria-controls="bloc-departement"
                    onClick={() => setDepartementChoisi(groupe.id)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                      actif
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-background text-foreground hover:bg-muted"
                    )}
                  >
                    {nomCourt(groupe.libelle)}
                    <span className={cn("tabular-nums", actif ? "text-primary-foreground/80" : "text-muted-foreground")}>
                      {groupe.enseignants.length}
                    </span>
                  </button>
                );
              })}
            </nav>
          )}
        </div>
      )}

      <div className="space-y-6">
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
        ) : enseignantsAffiches.length === 0 ? (
          <div className="p-10 text-center text-sm text-muted-foreground border border-dashed rounded-lg">
            Aucun enseignant ne correspond à « {recherche} ».{" "}
            <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => setRecherche("")}>
              Effacer la recherche
            </button>
          </div>
        ) : (
          // Le département choisi, dans un bloc encadré avec son propre bandeau.
          <section
            key={groupeAffiche.id}
            id="bloc-departement"
            aria-labelledby="titre-departement"
            className={cn(
              "rounded-xl border overflow-hidden bg-card",
              groupeAffiche.estLeSien ? "border-primary/40" : "border-border"
            )}
          >
            <header
              className={cn(
                "flex items-center gap-3 px-4 py-3 border-b",
                groupeAffiche.estLeSien ? "bg-primary/5 border-primary/20" : "bg-muted/50 border-border"
              )}
            >
              <div className="min-w-0 flex-1">
                <h2 id="titre-departement" className="text-base leading-snug font-semibold text-foreground text-balance">
                  {groupeAffiche.libelle}
                </h2>
                <p className="text-xs text-muted-foreground tabular-nums">
                  {groupeAffiche.enseignants.length} enseignant{groupeAffiche.enseignants.length > 1 ? "s" : ""}
                </p>
              </div>
              {voirTous && groupeAffiche.estLeSien && (
                <Badge className="shrink-0 bg-primary/10 text-primary border-transparent hover:bg-primary/10">
                  Votre département
                </Badge>
              )}
            </header>
            <div className="divide-y divide-border">
              {groupeAffiche.enseignants.map((enseignant) => (
                <EnseignantRow
                  key={enseignant.profil_id}
                  enseignant={enseignant}
                  horsDepartement={voirTous && !idsDuChef.has(enseignant.profil_id)}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
