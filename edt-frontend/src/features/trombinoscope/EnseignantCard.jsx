/**
 * @file EnseignantCard.jsx
 * @description Carte individuelle du trombinoscope — avatar (initiales), nom,
 * grade, département et badges des matières enseignées.
 */
import { GraduationCap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { getInitials } from '@/lib/trombinoscope';

/**
 * @param {{ enseignant: { nom_complet, grade, departement, matieres: string[] } }} props
 */
export default function EnseignantCard({ enseignant }) {
  const { nom_complet, grade, departement, matieres } = enseignant;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4 flex flex-col items-center text-center gap-3">
        <Avatar size="lg">
          <AvatarFallback className="bg-primary/10 text-primary font-semibold">
            {getInitials(nom_complet)}
          </AvatarFallback>
        </Avatar>

        <div>
          <h3 className="font-semibold text-sm text-foreground leading-snug">
            {nom_complet}
          </h3>
          {grade && (
            <p className="text-xs text-muted-foreground mt-0.5 flex items-center justify-center gap-1">
              <GraduationCap className="h-3 w-3" aria-hidden="true" />
              {grade}
            </p>
          )}
          {departement && (
            <p className="text-[11px] text-muted-foreground mt-0.5">{departement}</p>
          )}
        </div>

        {matieres.length > 0 && (
          <div className="flex flex-wrap gap-1.5 justify-center">
            {matieres.map((matiere) => (
              <Badge key={matiere} variant="secondary" className="text-[10px]">
                {matiere}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}