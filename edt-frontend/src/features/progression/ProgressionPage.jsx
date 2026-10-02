/**
 * @file ProgressionPage.jsx
 * @description Avancement du semestre de l'étudiant : un bandeau de chiffres
 * (avancement global, modules, crédits, cours de la semaine) puis la liste
 * des modules, triable, dérivée du planning de sa classe.
 */
import { useMemo, useState } from 'react';
import { BarChart3 } from '@/components/ui/icons';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import PageHeader from '@/components/shared/PageHeader';
import { useProgression } from "@/hooks/useProgression";
import { TRIS_PROGRESSION } from '@/lib/progression';
import { cn, formatNombreHeures } from '@/lib/utils';
import BarreAvancement, { LegendeAvancement } from './BarreAvancement';
import ModuleProgressRow, { GRILLE_MODULES } from './ModuleProgressRow';

const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;

// Modules par état, dans l'ordre où l'étudiant les vit.
const ETATS_RESUME = [
    ['termine', (n) => pluriel(n, 'terminé')],
    ['en_cours', (n) => `${n} en cours`],
    ['a_venir', (n) => pluriel(n, 'pas commencé')],
];

function Chiffre({ valeur, label, detail, className }) {
    return (
        <Card className={cn('gap-1', className)}>
            <span className="text-2xl font-bold tabular-nums text-foreground">{valeur}</span>
            <span className="text-sm text-muted-foreground">{label}</span>
            {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
        </Card>
    );
}

function Resume({ resume }) {
    const { heuresFaites, heuresPrevues, pourcentage, parStatut } = resume;
    const etats = ETATS_RESUME
        .filter(([etat]) => parStatut[etat] > 0)
        .map(([etat, texte]) => texte(parStatut[etat]))
        .join(' · ');

    return (
        <section aria-label="Résumé du semestre" className="grid grid-cols-2 gap-3 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
            <Card className="col-span-2 gap-3 lg:col-span-1">
                <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm text-muted-foreground">Avancement du semestre</span>
                    <span className="text-2xl font-bold tabular-nums text-foreground">{pourcentage} %</span>
                </div>
                <BarreAvancement
                    faites={pourcentage}
                    label="Avancement du semestre"
                    valeur={`${formatNombreHeures(heuresFaites)} faites sur ${formatNombreHeures(heuresPrevues)} prévues`}
                />
                <span className="text-xs text-muted-foreground tabular-nums">
                    {formatNombreHeures(heuresFaites)} de cours faites sur {formatNombreHeures(heuresPrevues)} prévues
                </span>
            </Card>
            <Chiffre valeur={resume.nbModules} label={resume.nbModules > 1 ? 'modules' : 'module'} detail={etats} />
            <Chiffre valeur={resume.credits} label={resume.credits > 1 ? 'crédits ce semestre' : 'crédit ce semestre'} />
            {/* Pleine largeur tant que la grille n'a que deux colonnes : pas de case seule sur sa ligne. */}
            <Chiffre
                className="col-span-2 lg:col-span-1"
                valeur={formatNombreHeures(resume.heuresSemaine)}
                label="de cours cette semaine"
                detail={resume.seancesSemaine > 0 ? pluriel(resume.seancesSemaine, 'séance') : 'Aucune séance'}
            />
        </section>
    );
}

function ChoixTri({ tri, onChange }) {
    return (
        <div role="group" aria-label="Trier les modules par" className="inline-flex gap-0.5 rounded-lg bg-muted p-0.5">
            {TRIS_PROGRESSION.map(({ cle, label }) => (
                <button
                    key={cle}
                    type="button"
                    aria-pressed={tri === cle}
                    onClick={() => onChange(cle)}
                    className={cn(
                        'h-7 rounded-md px-3 text-xs font-semibold transition-colors',
                        tri === cle
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground',
                    )}
                >
                    {label}
                </button>
            ))}
        </div>
    );
}

function Chargement() {
    return (
        <div className="space-y-6" aria-hidden="true">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
                {Array.from({ length: 4 }).map((_, index) => (
                    <div
                        key={index}
                        className={cn('h-24 rounded-xl bg-muted/60 animate-pulse', index === 0 && 'col-span-2 lg:col-span-1')}
                    />
                ))}
            </div>
            <div className="rounded-xl ring-1 ring-foreground/10 divide-y divide-border">
                {Array.from({ length: 5 }).map((_, index) => (
                    <div key={index} className="h-20 animate-pulse bg-muted/30" />
                ))}
            </div>
        </div>
    );
}

function Message({ erreur = false, titre, children }) {
    return (
        <div
            className={cn(
                'w-full h-64 flex flex-col items-center justify-center gap-3 rounded-lg border p-6 text-center',
                erreur ? 'border-destructive/20 bg-destructive/5' : 'border-border/60 bg-muted/20',
            )}
        >
            <BarChart3
                className={cn('w-10 h-10', erreur ? 'text-destructive' : 'text-muted-foreground')}
                aria-hidden="true"
            />
            <h2 className="font-semibold text-lg text-foreground">{titre}</h2>
            <p className="text-sm text-muted-foreground max-w-sm">{children}</p>
        </div>
    );
}

export default function ProgressionPage() {
    const { modules, resume, isLoading, isError } = useProgression();
    const [tri, setTri] = useState(TRIS_PROGRESSION[0].cle);

    const modulesTries = useMemo(() => {
        const { comparer } = TRIS_PROGRESSION.find((t) => t.cle === tri);
        // Tri stable : à égalité, l'ordre alphabétique de départ est gardé.
        return [...modules].sort(comparer);
    }, [modules, tri]);

    return (
        <div className="space-y-6 w-full max-w-7xl mx-auto">
            <PageHeader
                titre="Ma progression"
                description="Les heures de cours déjà faites dans chaque module, comparées au volume prévu."
            >
                {resume.semestre && <Badge variant="outline" className="h-6 px-2.5">{resume.semestre}</Badge>}
            </PageHeader>

            {isLoading && <Chargement />}

            {!isLoading && isError && (
                <Message erreur titre="Impossible de charger votre progression">
                    Une erreur est survenue. Veuillez rafraîchir la page ou réessayer plus tard.
                </Message>
            )}

            {!isLoading && !isError && modules.length === 0 && (
                <Message titre="Aucun module trouvé">
                    Votre progression apparaîtra ici dès que des séances seront planifiées pour votre classe.
                </Message>
            )}

            {!isLoading && !isError && modules.length > 0 && (
                <>
                    <Resume resume={resume} />

                    <section aria-labelledby="titre-modules" className="overflow-hidden rounded-xl bg-card ring-1 ring-foreground/10">
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border px-4 py-3 sm:px-5">
                            <h2 id="titre-modules" className="text-base font-semibold text-foreground">Par module</h2>
                            <LegendeAvancement />
                            <div className="ml-auto">
                                <ChoixTri tri={tri} onChange={setTri} />
                            </div>
                        </div>

                        <div
                            aria-hidden="true"
                            className={cn(
                                'hidden gap-x-4 bg-muted/40 px-5 py-2 text-xs font-medium text-muted-foreground md:grid',
                                GRILLE_MODULES,
                            )}
                        >
                            <span>Module</span>
                            <span>Enseignants</span>
                            <span>Crédits</span>
                            <span>Heures</span>
                            <span>État</span>
                        </div>

                        <ul className="divide-y divide-border">
                            {modulesTries.map((module) => (
                                <ModuleProgressRow key={module.id} module={module} />
                            ))}
                        </ul>
                    </section>
                </>
            )}
        </div>
    );
}
