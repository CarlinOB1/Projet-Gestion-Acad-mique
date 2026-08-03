/**
 * @file ClasseGroupSection.jsx
 * @description Groupe "Classe" collapsible — en-tête avec libellé, compteur
 * et chevron, contenant les sous-groupes JourGroupSection.
 */
import { useState } from 'react';
import { ChevronDown, GraduationCap } from 'lucide-react';
import JourGroupSection from './JourGroupSection';

/**
 * @param {{
 *   classeId: number,
 *   libelle: string,
 *   totalSeances: number,
 *   jours: Array<{ date: string, seances: Array<Object> }>,
 *   isOpen: boolean,
 *   onToggle: (classeId: number) => void,
 *   onEdit: Function,
 *   onReport: Function,
 *   onDelete: Function,
 * }} props
 */
export default function ClasseGroupSection({
    classeId,
    libelle,
    totalSeances,
    jours,
    isOpen,
    onToggle,
    onEdit,
    onReport,
    onDelete,
}) {
    return (
        <div className="border border-border/60 rounded-xl bg-card overflow-hidden">
            <button
                type="button"
                onClick={() => onToggle(classeId)}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 hover:bg-muted/40 transition-colors text-left"
            >
                <div className="flex items-center gap-2.5 min-w-0">
                    <GraduationCap className="h-4 w-4 text-primary shrink-0" />
                    <span className="font-semibold text-sm text-foreground truncate">
                        {libelle}
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">
                        {totalSeances} séance{totalSeances > 1 ? 's' : ''}
                    </span>
                </div>
                <ChevronDown
                    className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''
                        }`}
                />
            </button>

            {isOpen && (
                <div className="px-4 pb-4 pt-1 space-y-4 border-t border-border/60">
                    {jours.map((jour) => (
                        <JourGroupSection
                            key={jour.date}
                            date={jour.date}
                            seances={jour.seances}
                            onEdit={onEdit}
                            onReport={onReport}
                            onDelete={onDelete}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}