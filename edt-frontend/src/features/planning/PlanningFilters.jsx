/**
 * @file PlanningFilters.jsx
 * @description Barre de filtres du planning — recherche texte, type de séance,
 * enseignant (masqué pour le rôle enseignant) et statut.
 */
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { TYPE_SEANCE, STATUT_SEANCE } from "@/lib/constants";
import {
    DEFAULT_CRITERIA,
    getEnseignantsFromEvents,
} from "@/lib/planningFilters";

/**
 * @param {{
 *   events: Array,
 *   criteria: Object,
 *   onCriteriaChange: Function,
 *   showEnseignantFilter?: boolean,
 * }} props
 */
export default function PlanningFilters({
    events = [],
    criteria = DEFAULT_CRITERIA,
    onCriteriaChange,
    showEnseignantFilter = true,
}) {
    const enseignants = getEnseignantsFromEvents(events);

    const hasActiveFilters =
        criteria.search.trim() !== "" ||
        criteria.typeSeance !== "all" ||
        criteria.enseignantId !== "all" ||
        criteria.statut !== "all";

    const update = (patch) => onCriteriaChange({ ...criteria, ...patch });
    const reset = () => onCriteriaChange(DEFAULT_CRITERIA);

    return (
        <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-3 bg-muted/30 border border-border/60 rounded-lg p-3">
            <Input
                placeholder="Rechercher un module..."
                value={criteria.search}
                onChange={(e) => update({ search: e.target.value })}
                className="w-full sm:w-[220px] bg-background"
            />

            <Select
                value={criteria.typeSeance}
                onValueChange={(v) => update({ typeSeance: v })}
            >
                <SelectTrigger className="w-full sm:w-[140px] bg-background">
                    <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">Tous les types</SelectItem>
                    {Object.values(TYPE_SEANCE).map((type) => (
                        <SelectItem key={type} value={type}>
                            {type}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>

            {showEnseignantFilter && (
                <Select
                    value={criteria.enseignantId}
                    onValueChange={(v) => update({ enseignantId: v })}
                >
                    <SelectTrigger className="w-full sm:w-[200px] bg-background">
                        <SelectValue placeholder="Enseignant" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Tous les enseignants</SelectItem>
                        {enseignants.map((e) => (
                            <SelectItem key={e.id} value={String(e.id)}>
                                {e.nom_complet}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            )}

            <Select
                value={criteria.statut}
                onValueChange={(v) => update({ statut: v })}
            >
                <SelectTrigger className="w-full sm:w-[160px] bg-background">
                    <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">Tous les statuts</SelectItem>
                    {Object.values(STATUT_SEANCE).map((statut) => (
                        <SelectItem key={statut} value={statut}>
                            {statut}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>

            {hasActiveFilters && (
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={reset}
                    className="text-muted-foreground"
                >
                    <X className="h-4 w-4 mr-1" />
                    Réinitialiser
                </Button>
            )}
        </div>
    );
}
