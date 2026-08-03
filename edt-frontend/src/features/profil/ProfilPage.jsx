import { useQuery } from '@tanstack/react-query';
import { getMonProfil } from '@/api/acteurs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { User, Phone, Mail, GraduationCap, Briefcase, Hash } from 'lucide-react';
import useAuthStore from '@/store/authStore';

export default function ProfilPage() {
  const userStore = useAuthStore((state) => state.user);

  const { data: profil, isLoading, isError } = useQuery({
    queryKey: ['mon-profil'],
    queryFn: getMonProfil,
  });

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Chargement du profil...</div>;
  }

  if (isError || !profil) {
    return <div className="p-8 text-center text-destructive">Erreur lors du chargement du profil.</div>;
  }

  const { user, enseignant, etudiant, telephone, genre } = profil;
  const initals = user?.first_name?.[0] + (user?.last_name?.[0] || '');

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h2 className="text-3xl font-bold tracking-tight">Mon Profil</h2>

      <div className="grid gap-8 lg:grid-cols-4">
        {/* Colonne Gauche : Avatar et infos de base */}
        <Card className="md:col-span-1 flex flex-col items-center justify-center p-6 text-center">
          <Avatar className="h-32 w-32 mb-4 border-4 border-muted shadow-sm">
            <AvatarFallback className="text-3xl bg-primary/10 text-primary">
              {initals || <User className="h-12 w-12" />}
            </AvatarFallback>
          </Avatar>
          <h3 className="text-xl font-semibold">{user?.first_name} {user?.last_name}</h3>
          <p className="text-sm text-muted-foreground">{user?.email}</p>
          
          <div className="mt-4 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
             {enseignant ? 'Enseignant' : etudiant ? 'Étudiant' : userStore?.role || 'Utilisateur'}
          </div>
        </Card>

        {/* Colonne Droite : Détails */}
        <Card className="lg:col-span-3 shadow-sm flex flex-col">
          <CardHeader className="pb-4 border-b text-center shrink-0">
            <CardTitle className="text-xl">Informations Personnelles</CardTitle>
          </CardHeader>
          <CardContent className="p-8 flex-1 flex items-center justify-center">
            <div className="grid sm:grid-cols-2 gap-8 w-full">
              
              <div className="flex items-center gap-5 p-5 rounded-xl bg-muted/20 border border-muted/50 hover:bg-muted/40 transition-colors">
                <div className="p-3 bg-primary/10 text-primary rounded-lg shrink-0">
                  <Mail className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">Email</p>
                  <p className="text-sm text-muted-foreground break-words mt-0.5">{user?.email || 'Non renseigné'}</p>
                </div>
              </div>

              <div className="flex items-center gap-5 p-5 rounded-xl bg-muted/20 border border-muted/50 hover:bg-muted/40 transition-colors">
                <div className="p-3 bg-primary/10 text-primary rounded-lg shrink-0">
                  <Phone className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">Téléphone</p>
                  <p className="text-sm text-muted-foreground break-words mt-0.5">{telephone || 'Non renseigné'}</p>
                </div>
              </div>

              {/* Infos spécifiques Enseignant */}
              {enseignant && (
                <>
                  <div className="flex items-center gap-5 p-5 rounded-xl bg-muted/20 border border-muted/50 hover:bg-muted/40 transition-colors">
                    <div className="p-3 bg-primary/10 text-primary rounded-lg shrink-0">
                      <Briefcase className="h-6 w-6" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">Grade & Contrat</p>
                      <p className="text-sm text-muted-foreground break-words mt-0.5">
                        {enseignant.grade} — {enseignant.contrat}
                      </p>
                    </div>
                  </div>
                  {enseignant.departement && (
                    <div className="flex items-center gap-5 p-5 rounded-xl bg-muted/20 border border-muted/50 hover:bg-muted/40 transition-colors">
                      <div className="p-3 bg-primary/10 text-primary rounded-lg shrink-0">
                        <GraduationCap className="h-6 w-6" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">Département</p>
                        <p className="text-sm text-muted-foreground break-words mt-0.5">{enseignant.departement.libelle}</p>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Infos spécifiques Étudiant */}
              {etudiant && (
                <>
                  <div className="flex items-center gap-5 p-5 rounded-xl bg-muted/20 border border-muted/50 hover:bg-muted/40 transition-colors">
                    <div className="p-3 bg-primary/10 text-primary rounded-lg shrink-0">
                      <Hash className="h-6 w-6" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">Matricule</p>
                      <p className="text-sm text-muted-foreground break-words mt-0.5">{etudiant.matricule}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-5 p-5 rounded-xl bg-muted/20 border border-muted/50 hover:bg-muted/40 transition-colors">
                    <div className="p-3 bg-primary/10 text-primary rounded-lg shrink-0">
                      <GraduationCap className="h-6 w-6" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">Classe & Parcours</p>
                      <p className="text-sm text-muted-foreground break-words mt-0.5">
                        {etudiant.classe?.libelle || etudiant.classe?.code} — {etudiant.parcours?.libelle}
                      </p>
                    </div>
                  </div>
                </>
              )}

            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
