/**
 * src/components/shared/DataTable.jsx
 * * Composant de tableau générique et réutilisable.
 * Intègre la gestion native des états de chargement (skeletons), d'erreurs, 
 * de listes vides, ainsi que les actions de modification et de suppression.
 * * Propulsé par Tailwind CSS et les primitives de shadcn/ui.
 */

import React from 'react';
import { Pencil, Trash2, AlertCircle, MoreHorizontal } from '@/components/ui/icons';
import { Button, buttonVariants } from '@/components/ui/button';
import { confirmer } from '@/lib/confirmer';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
  emptyMessage = "Aucune donnée disponible",
  // Actions en plus de Modifier / Supprimer : [{ libelle, icone, onClick(row) }].
  actionsSupplementaires = [],
  // Regroupe toutes les actions dans un menu « ⋯ » : pour les tableaux
  // étroits, où trois boutons côte à côte finissaient hors de l'écran.
  actionsEnMenu = false,
  libelleLigne = () => 'cette ligne',
}) {
  // Calcul du nombre total de colonnes (colonnes de données + colonne Actions)
  const hasRowActions = Boolean(onEdit || onDelete || actionsSupplementaires.length);
  const totalColumns = columns.length + (hasRowActions ? 1 : 0);

  /**
   * Gère la confirmation de suppression avant d'exécuter le callback
   */
  const handleDeleteClick = async (row) => {
    const nom = libelleLigne(row);
    const ok = await confirmer({
      titre: nom === 'cette ligne' ? 'Supprimer cet élément ?' : `Supprimer « ${nom} » ?`,
      description: 'Cette action est définitive.',
      libelleConfirmer: 'Supprimer',
      destructif: true,
    });
    if (ok) onDelete?.(row);
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
              <TableHead className={cn('text-xs uppercase font-semibold text-muted-foreground text-right h-10', actionsEnMenu ? 'w-12' : 'w-[100px]')}>
                <span className="sr-only">Actions</span>
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
                  group border-b last:border-b-0 transition-colors
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
                
                
                {/* Cellule d'actions — toujours visibles : masqués jusqu'au
                    survol, ils n'apparaissaient jamais sur écran tactile. */}
                {hasRowActions && actionsEnMenu && (
                  <TableCell className="py-2 text-right">
                    <DropdownMenu>
                      {/* Déclencheur Radix stylé en bouton : notre <Button> ne
                          transmet pas de ref (React 18), le menu ne saurait
                          pas où s'ouvrir. */}
                      <DropdownMenuTrigger
                        aria-label={`Actions pour ${libelleLigne(row)}`}
                        className={cn(buttonVariants({ variant: 'ghost', size: 'icon-sm' }))}
                      >
                        <MoreHorizontal className="size-4" />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="min-w-44">
                        {actionsSupplementaires.map((action) => {
                          const Icone = action.icone;
                          return (
                            <DropdownMenuItem key={action.libelle} onSelect={() => action.onClick(row)}>
                              {Icone && <Icone className="text-muted-foreground" />}
                              {action.libelle}
                            </DropdownMenuItem>
                          );
                        })}
                        {onEdit && (
                          <DropdownMenuItem onSelect={() => onEdit(row)}>
                            <Pencil className="text-muted-foreground" />
                            Modifier
                          </DropdownMenuItem>
                        )}
                        {onDelete && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem variant="destructive" onSelect={() => handleDeleteClick(row)}>
                              <Trash2 />
                              Supprimer
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                )}

                {hasRowActions && !actionsEnMenu && (
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