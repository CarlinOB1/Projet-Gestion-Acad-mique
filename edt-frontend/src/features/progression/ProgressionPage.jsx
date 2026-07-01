/**
 * @file ProgressionPage.jsx
 * @description Page listant l'avancement de chaque module du semestre en cours,
 * dérivé du planning de l'utilisateur connecté.
 */
import { BarChart3 } from "lucide-react";
import { useProgression } from "@/hooks/useProgression";
import ModuleProgressCard from "./ModuleProgressCard";

export default function ProgressionPage() {
    const { modules, isLoading, isError } = useProgression();

    return (
        <div className="space-y-6 w-full max-w-7xl mx-auto">
            <header className="border-b border-border pb-5">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">
                    Ma progression
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Suivez l'avancement de chaque module par rapport à son volume horaire
                    prévu.
                </p>
            </header>

            {isLoading && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 6 }).map((_, index) => (
                        <div
                            key={index}
                            className="h-32 rounded-xl border border-border/60 bg-muted/40 animate-pulse"
                        />
                    ))}
                </div>
            )}

            {!isLoading && isError && (
                <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-destructive/20 bg-destructive/5 rounded-lg p-6 text-center">
                    <BarChart3
                        className="w-10 h-10 text-destructive"
                        aria-hidden="true"
                    />
                    <h3 className="font-semibold text-lg text-foreground">
                        Impossible de charger votre progression
                    </h3>
                    <p className="text-sm text-muted-foreground max-w-sm">
                        Une erreur est survenue. Veuillez rafraîchir la page ou réessayer
                        plus tard.
                    </p>
                </div>
            )}

            {!isLoading && !isError && modules.length === 0 && (
                <div className="w-full h-64 flex flex-col items-center justify-center gap-3 border border-border/60 bg-muted/20 rounded-lg p-6 text-center">
                    <BarChart3
                        className="w-10 h-10 text-muted-foreground"
                        aria-hidden="true"
                    />
                    <h3 className="font-semibold text-lg text-foreground">
                        Aucun module trouvé
                    </h3>
                    <p className="text-sm text-muted-foreground max-w-sm">
                        Votre progression apparaîtra ici dès que des séances seront
                        planifiées pour votre classe.
                    </p>
                </div>
            )}

            {!isLoading && !isError && modules.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {modules.map((module) => (
                        <ModuleProgressCard key={module.id} module={module} />
                    ))}
                </div>
            )}
        </div>
    );
}
