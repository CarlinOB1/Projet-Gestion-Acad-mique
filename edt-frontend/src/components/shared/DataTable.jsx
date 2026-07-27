/**
 * src/components/shared/DataTable.jsx
 * * Composant de tableau générique et réutilisable.
 * Intègre la gestion native des états de chargement (skeletons), d'erreurs, 
 * de listes vides, ainsi que les actions de modification et de suppression.
 * * Propulsé par Tailwind CSS et les primitives de shadcn/ui.
 */

import React from 'react';
import { Pencil, Trash2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export default function DataTable({
  columns = [],
  data = [],
  isLoading = false,
  isError = false,
  onEdit,
  onDelete,
  emptyMessage = "Aucune donnée disponible"
}) {
  // Calcul du nombre total de colonnes (colonnes de données + colonne Actions)
  const hasRowActions = Boolean(onEdit || onDelete);
  const totalColumns = columns.length + (hasRowActions ? 1 : 0);

  /**
   * Gère la confirmation de suppression avant d'exécuter le callback
   */
  const handleDeleteClick = (row) => {
    if (window.confirm("Êtes-vous sûr de vouloir supprimer cet élément ?")) {
      onDelete?.(row);
    }
  };

  return (
    <div className="w-full rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow>
            {columns.map((col) => (
              <TableHead 
                key={col.key} 
                className="text-xs uppercase font-semibold text-muted-foreground h-10"
              >
                {col.label}
              </TableHead>
            ))}
            {hasRowActions && (
              <TableHead className="text-xs uppercase font-semibold text-muted-foreground text-right h-10 w-[100px]">
                Actions
              </TableHead>
            )}
          </TableRow>
        </TableHeader>
        
        <TableBody>
          {/* ÉTAT : CHARGEMENT (5 lignes de Skeletons) */}
          {isLoading && (
            Array.from({ length: 5 }).map((_, index) => (
              <TableRow key={`skeleton-${index}`} className="h-10 animate-pulse bg-muted/10">
                <TableCell colSpan={totalColumns} className="p-2">
                  <div className="h-4 bg-muted/40 rounded w-full" />
                </TableCell>
              </TableRow>
            ))
          )}

          {/* ÉTAT : ERREUR */}
          {!isLoading && isError && (
            <TableRow>
              <TableCell colSpan={totalColumns} className="h-32 text-center">
                <div className="flex flex-col items-center justify-center gap-2 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  <span className="text-sm font-medium">Une erreur est survenue lors du chargement des données.</span>
                </div>
              </TableCell>
            </TableRow>
          )}

          {/* ÉTAT : VIDE */}
          {!isLoading && !isError && data.length === 0 && (
            <TableRow>
              <TableCell colSpan={totalColumns} className="h-32 text-center text-sm text-muted-foreground font-medium">
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}

          {/* ÉTAT : RENDER DES DONNÉES */}
          {!isLoading && !isError && data.length > 0 && (
            data.map((row, rowIndex) => (
              <TableRow 
                key={row.id || rowIndex} 
                className={`
                  border-b last:border-b-0 transition-colors
                  hover:bg-muted/40
                  ${rowIndex % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
                `}
              >
                {/* Cellules de données */}
                {columns.map((col) => (
                  <TableCell key={`${rowIndex}-${col.key}`} className="py-3 text-sm">
                    {col.render ? col.render(row) : row[col.key]}
                  </TableCell>
                ))}
                
                
                {/* Cellule d'actions */}
                {hasRowActions && (
                  <TableCell className="py-2 text-right whitespace-nowrap space-x-1">
                    {onEdit && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(row)}
                      >
                        <Pencil className="h-4 w-4 mr-1.5" />
                        Modifier
                      </Button>
                    )}
                    
                    {onDelete && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => handleDeleteClick(row)}
                      >
                        <Trash2 className="h-4 w-4 mr-1.5" />
                        Supprimer
                      </Button>
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}