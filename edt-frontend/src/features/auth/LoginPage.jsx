// Page de connexion — formulaire login avec redirection automatique si déjà authentifié
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Navigate } from 'react-router-dom';
import useAuthStore from '@/store/authStore';
import { loginSchema } from '@/lib/schemas';
import { useLogin, parseLoginError } from './useLogin';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

export default function LoginPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user            = useAuthStore((state) => state.user);

  const { mutate, isPending, error, isError } = useLogin();

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  });

  const onSubmit = (data) => {
    mutate({ username: data.username, password: data.password });
  };

  // Redirection automatique après login réussi
  if (isAuthenticated && user) {
    switch (user.role) {
      case 'responsable': return <Navigate to="/responsable/planning" replace />;
      case 'enseignant':  return <Navigate to="/enseignant/planning"  replace />;
      case 'etudiant':    return <Navigate to="/etudiant/planning"    replace />;
      default:            return <Navigate to="/unauthorized"         replace />;
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
      <Card className="w-full max-w-md shadow-lg border border-border bg-card text-card-foreground">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold tracking-tight">EDT Université</CardTitle>
          <CardDescription>Saisissez vos identifiants pour accéder à votre emploi du temps</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">

            <div className="space-y-2">
              <Label htmlFor="username">Identifiant de connexion</Label>
              <Input
                id="username"
                type="text"
                placeholder="Ex: mbemba"
                className="w-full"
                {...register('username')}
              />
              {errors.username && (
                <p className="text-xs font-medium text-destructive">{errors.username.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                className="w-full"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-xs font-medium text-destructive">{errors.password.message}</p>
              )}
            </div>

            {isError && (
              <div className="p-3 text-sm font-medium text-destructive bg-destructive/10 rounded-md border border-destructive/20">
                {parseLoginError(error)}
              </div>
            )}

            <Button
              type="button"
              onClick={handleSubmit(onSubmit)}
              disabled={isPending}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium transition-colors flex items-center justify-center gap-2"
            >
              {isPending ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Connexion...
                </>
              ) : (
                'Se connecter'
              )}
            </Button>

          </div>
        </CardContent>
      </Card>
    </div>
  );
}