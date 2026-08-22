import { useRouteError } from 'react-router-dom';

export default function RouteErrorPage() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : String(error ?? 'Erreur inconnue');

  return (
    <main className="min-h-screen flex items-center justify-center bg-background p-6">
      <section className="w-full max-w-lg rounded-xl border border-destructive/30 bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Erreur de route</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Le chargement de cette page a echoue. Rechargez la page pour reessayer.
        </p>
        <pre className="mt-5 max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs text-destructive">
          {message}
        </pre>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Recharger
        </button>
      </section>
    </main>
  );
}