import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import DataTable from '@/components/shared/DataTable';
import apiClient from '@/api/client';

const getMesModules = async () => {
  const response = await apiClient.get('/modules/mes_modules/');
  return response.data?.results ?? response.data;
};

export default function MesModulesPage() {
  const { data: modules = [], isLoading, isError } = useQuery({
    queryKey: ['mes-modules'],
    queryFn: getMesModules,
  });

  const columns = [
    { key: 'libelle', label: 'Nom du module' },
    { 
      key: 'matiere', 
      label: 'Matière', 
      render: (row) => row.matiere?.libelle || <span className="text-muted-foreground">-</span>
    },
    { 
      key: 'semestre', 
      label: 'Semestre', 
      render: (row) => <Badge variant="outline">{row.semestre?.libelle || '-'}</Badge>
    },
    { 
      key: 'credits', 
      label: 'Crédits',
      render: (row) => <span className="font-semibold">{row.credits} ECTS</span>
    },
    {
      key: 'volume',
      label: 'Volume Horaire',
      render: (row) => {
        const consomme = row.heures_consommees || 0;
        const max = row.heures_max || 1; 
        const percentage = Math.min((consomme / max) * 100, 100);

        let progressBarColor = 'bg-green-500';
        if (percentage >= 80 && percentage < 100) {
          progressBarColor = 'bg-orange-500';
        } else if (percentage >= 100) {
          progressBarColor = 'bg-red-500';
        }

        return (
          <div className="flex flex-col gap-1.5 w-44">
            <div className="flex justify-between text-xs font-medium text-muted-foreground">
              <span>{consomme}h / {max}h</span>
              <span>{Math.round(percentage)}%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden border border-border/30">
              <div
                className={`h-full ${progressBarColor} transition-all duration-300 rounded-full`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      }
    }
  ];

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-lg hidden sm:block">
            <BookOpen className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Mes Modules</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              Consultez les modules que vous dispensez, vos crédits et le suivi du volume horaire.
            </p>
          </div>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={modules}
        isLoading={isLoading}
        isError={isError}
        emptyMessage="Vous n'avez aucun module attribué pour le moment."
        onEdit={undefined}
        onDelete={undefined}
      />
    </div>
  );
}
