import { useQuery } from '@tanstack/react-query';
import { getMonProfil } from '@/api/acteurs';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User, Phone, Mail, GraduationCap, Briefcase, Hash } from '@/components/ui/icons';
import useAuthStore from '@/store/authStore';
import { ROLE_LABELS } from '@/lib/constants';
import PageHeader from '@/components/shared/PageHeader';

function Info({ icone: Icone, label, children }) {
  return (
    <div className="flex items-start gap-3 min-w-0">
      <div className="p-2 bg-primary/10 text-primary rounded-md shrink-0">
        <Icone className="size-4" aria-hidden />
      </div>
      <div className="min-w-0">
        <dt className="text-xs text-muted-foreground">{label}</dt>
        <dd className="text-sm font-medium text-foreground break-words">{children || 'Non renseigné'}</dd>
      </div>
    </div>
  );
}

export default function ProfilPage() {
  const userStore = useAuthStore((state) => state.user);

  const { data: profil, isLoading, isError } = useQuery({
    queryKey: ['mon-profil'],
    queryFn: getMonProfil,
  });

  if (isLoading) {
    return (
      <div className="space-y-6 w-full max-w-7xl mx-auto">
        <PageHeader titre="Mon profil" />
        <div className="h-64 rounded-xl border border-border bg-muted/40 animate-pulse" />
      </div>
    );
  }

  if (isError || !profil) {
    return (
      <div className="space-y-6 w-full max-w-7xl mx-auto">
        <PageHeader titre="Mon profil" />
        <p className="p-6 text-center text-sm text-destructive border border-destructive/20 bg-destructive/5 rounded-xl">
          Le profil n'a pas pu être chargé. Rechargez la page.
        </p>
      </div>
    );
  }

  const { user, enseignant, etudiant, telephone, photo } = profil;
  // Même ordre que la barre du haut (NOM Prénom), qui affichait
  // « ProfInformatique Chef » quand cette page affichait « Chef ProfInformatique ».
  const nomComplet = userStore?.nom_complet || [user?.last_name, user?.first_name].filter(Boolean).join(' ');
  const initiales = (user?.last_name?.[0] ?? '') + (user?.first_name?.[0] ?? '');

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <PageHeader titre="Mon profil" />

      <section className="rounded-xl border border-border bg-card">
        <div className="flex flex-col sm:flex-row items-center sm:items-center gap-4 p-6 border-b border-border text-center sm:text-left">
          <Avatar className="size-20 border-2 border-muted">
            {photo && <AvatarImage src={photo} alt={nomComplet} className="object-cover" />}
            <AvatarFallback className="text-2xl bg-primary/10 text-primary">
              {initiales || <User className="size-8" />}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <h2 className="text-xl font-semibold text-foreground text-balance">{nomComplet}</h2>
            <span className="mt-1 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold">
              {/* Le rôle de connexion, pas la présence d'une fiche enseignant :
                  un chef ou un référent a aussi une fiche enseignant, et
                  s'affichait donc « Enseignant ». */}
              {ROLE_LABELS[userStore?.role] ?? (enseignant ? 'Enseignant' : etudiant ? 'Étudiant' : 'Utilisateur')}
            </span>
          </div>
        </div>

        <dl className="grid gap-6 p-6 sm:grid-cols-2">
          <Info icone={Mail} label="E-mail">{user?.email}</Info>
          <Info icone={Phone} label="Téléphone">{telephone}</Info>

          {enseignant && (
            <>
              <Info icone={Briefcase} label="Grade et contrat">
                {[enseignant.grade, enseignant.contrat].filter(Boolean).join(' — ')}
              </Info>
              <Info icone={GraduationCap} label="Département">{enseignant.departement?.libelle}</Info>
            </>
          )}

          {etudiant && (
            <>
              <Info icone={Hash} label="Matricule">{etudiant.matricule}</Info>
              <Info icone={GraduationCap} label="Classe et parcours">
                {[etudiant.classe?.libelle || etudiant.classe?.code, etudiant.parcours?.libelle].filter(Boolean).join(' — ')}
              </Info>
            </>
          )}
        </dl>
      </section>
    </div>
  );
}
