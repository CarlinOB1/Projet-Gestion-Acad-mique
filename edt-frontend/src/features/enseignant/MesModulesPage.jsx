import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import apiClient from '@/api/client';
import { getAnnees } from '@/api/academique';
import { formatNombreHeures } from '@/lib/utils';

const getMesModules = async (anneeId) => {
  const response = await apiClient.get('/modules/mes_modules/', {
    params: anneeId ? { annee_id: anneeId } : {},
  });
  return response.data?.results ?? response.data;
};

// Colonne « Matière » retirée : même valeur sur toutes les lignes.
const columns = [
  {
    key: 'libelle',
    label: 'Module',
    render: (row) => <span className="font-medium text-pretty">{row.libelle}</span>,
  },
  {
    key: 'classe',
    label: 'Classe',
    render: (row) => row.classe?.libelle || <span className="text-muted-foreground">—</span>,
  },
  {
    key: 'credits',
    label: 'Crédit(s)',
    render: (row) => <span className="font-semibold tabular-nums">{row.credits}</span>,
  },
  {
    // Ce qui intéresse l'enseignant : les heures faites, pas seulement
    // les heures planifiées (qui étaient les seules affichées).
    key: 'avancement',
    label: 'Heures faites',
    render: (row) => {
      const faites = Number(row.heures_effectuees) || 0;
      const planifiees = Number(row.heures_consommees) || 0;
      const max = Number(row.heures_max) || 1;
      const pct = Math.min((faites / max) * 100, 100);
      return (
        <div className="flex flex-col gap-1 w-48">
          <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
            <span>
              <span className="font-semibold text-foreground">{formatNombreHeures(faites)}</span> sur {formatNombreHeures(max)}
            </span>
            <span>{Math.round(pct)} %</span>
          </div>
          <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
            <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-[11px] text-muted-foreground tabular-nums">
            {formatNombreHeures(planifiees)} planifiées
          </span>
        </div>
      );
    },
  },
];

export default function MesModulesPage() {
  // Un module est rattaché à une année académique via son semestre : sans ce
  // filtre, un enseignant qui a dispensé plusieurs années cumule les modules
  // de toutes ces années dans la même liste (même correctif que EnseignantRow.jsx).
  const { data: annees = [] } = useQuery({
    queryKey: ['annees', 'active'],
    queryFn: () => getAnnees({ statut: 'active' }),
    staleTime: 5 * 60 * 1000,
  });
  const anneeActiveId = annees[0]?.id;

  const { data: modules = [], isLoading, isError } = useQuery({
    queryKey: ['mes-modules', anneeActiveId],
    queryFn: () => getMesModules(anneeActiveId),
    enabled: !!anneeActiveId,
  });

  // Regroupés par semestre, puis triés par classe et par nom : la liste
  // arrivait dans le désordre (S2 Biologie, puis S1 Informatique, …).
  const groupes = useMemo(() => {
    const map = new Map();
    modules.forEach((m) => {
      const cle = m.semestre?.id ?? 'autre';
      if (!map.has(cle)) {
        const libelle = [m.semestre?.libelle, m.semestre?.annee?.libelle].filter(Boolean).join(' · ');
        map.set(cle, { cle, libelle: libelle || 'Sans semestre', debut: m.semestre?.date_debut ?? '', modules: [] });
      }
      map.get(cle).modules.push(m);
    });
    const tri = (a, b) =>
      (a.classe?.libelle ?? '').localeCompare(b.classe?.libelle ?? '') ||
      (a.libelle ?? '').localeCompare(b.libelle ?? '');
    return [...map.values()]
      .sort((a, b) => a.debut.localeCompare(b.debut))
      .map((g) => ({ ...g, modules: [...g.modules].sort(tri) }));
  }, [modules]);

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <PageHeader
        titre="Mes modules"
        description="Les modules que vous enseignez cette année et l'avancement de vos heures."
      />

      {isLoading || isError || groupes.length === 0 ? (
        <DataTable
          columns={columns}
          data={[]}
          isLoading={isLoading}
          isError={isError}
          emptyMessage="Aucun module ne vous est attribué pour le moment. Le chef de département fait les affectations."
        />
      ) : (
        groupes.map((g) => (
          <section key={g.cle} className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">
              {g.libelle}
              <span className="ml-2 text-xs font-normal text-muted-foreground tabular-nums">
                {g.modules.length} module{g.modules.length > 1 ? 's' : ''}
              </span>
            </h2>
            <DataTable columns={columns} data={g.modules} />
          </section>
        ))
      )}
    </div>
  );
}
