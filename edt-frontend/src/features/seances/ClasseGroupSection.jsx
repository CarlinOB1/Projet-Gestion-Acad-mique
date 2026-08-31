/**
 * @file ClasseGroupSection.jsx
 * @description Groupe "Classe" collapsible — en-tête avec libellé, compteur
 * et chevron, contenant les sous-groupes JourGroupSection.
 */
import { useState } from 'react';
import { ChevronDown, GraduationCap, Send } from 'lucide-react';
import JourGroupSection from './JourGroupSection';
import { Button } from '@/components/ui/button';

/**
 * @param {{
 *   classeId: number,
 *   libelle: string,
 *   totalSeances: number,
 *   jours: Array<{ date: string, seances: Array<Object> }>,
 *   isOpen: boolean,
 *   onToggle: (classeId: number) => void,
 *   onEdit: Function,
 *   onDelete: Function,
 *   onPublier?: Function,
 *   onDepublier?: Function,
 *   onPublierMasse?: Function,
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
    onDelete,
    onPublier,
    onDepublier,
    onPublierMasse,
}) {
    // Calculer le nombre de séances en brouillon dans cette classe
    const brouillons = jours.flatMap(jour => jour.seances).filter(s => s.statut === 'brouillon');
    const hasBrouillons = brouillons.length > 0;

    return (
        <div className="border border-border/60 rounded-xl bg-card overflow-hidden">
            <div
                role="button"
                tabIndex={0}
                onClick={() => onToggle(classeId)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(classeId); } }}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 hover:bg-muted/40 transition-colors text-left cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
                <div className="flex items-center gap-2.5 min-w-0">
                    <GraduationCap className="h-4 w-4 text-primary shrink-0" />
                    <span className="font-semibold text-sm text-foreground truncate">
                        {libelle}
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">
                        {totalSeances} séance{totalSeances > 1 ? 's' : ''}
                    </span>
                    {hasBrouillons && onPublierMasse && (
                        <span className="ml-2 bg-amber-100 text-amber-800 text-[10px] px-2 py-0.5 rounded-full font-medium">
                            {brouillons.length} brouillon{brouillons.length > 1 ? 's' : ''}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {hasBrouillons && onPublierMasse && (
                        <Button
                            size="sm"
                            variant="default"
                            className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                            onClick={(e) => {
                                e.stopPropagation();
                                onPublierMasse(classeId, brouillons.map(s => s.id));
                            }}
                        >
                            <Send className="h-3 w-3 mr-1.5" />
                            Publier l'emploi du temps
                        </Button>
                    )}
                    <ChevronDown
                        className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''
                            }`}
                    />
                </div>
            </div>

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
                            onPublier={onPublier}
                            onDepublier={onDepublier}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}