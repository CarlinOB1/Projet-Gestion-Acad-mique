/**
 * @file JourGroupSection.jsx
 * @description Sous-groupe "Jour" à l'intérieur d'un groupe Classe —
 * en-tête de date + DataTable des séances de ce jour.
 */
import DataTable from '@/components/shared/DataTable';
import { getSeanceColumns } from './seanceTableColumns';
import { formatDate } from '@/lib/utils';

/**
 * @param {{
 *   date: string,
 *   seances: Array<Object>,
 *   onEdit: Function,
 *   onReport: Function,
 *   onDelete: Function,
 * }} props
 */
export default function JourGroupSection({
    date,
    seances,
    onEdit,
    onReport,
    onDelete,
}) {
    const columns = getSeanceColumns({ onEdit, onReport, onDelete });

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
                <h4 className="text-sm font-semibold text-foreground capitalize">
                    {formatDate(date)}
                </h4>
                <span className="text-xs text-muted-foreground">
                    {seances.length} séance{seances.length > 1 ? 's' : ''}
                </span>
            </div>

            <DataTable
                columns={columns}
                data={seances}
                isLoading={false}
                isError={false}
                emptyMessage="Aucune séance ce jour."
            />
        </div>
    );
}