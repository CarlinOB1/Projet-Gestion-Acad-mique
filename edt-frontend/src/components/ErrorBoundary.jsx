import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error(
      "Erreur React interceptee par ErrorBoundary:",
      error,
      errorInfo,
    );
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <main className="min-h-screen flex items-center justify-center bg-background p-6">
        <section className="w-full max-w-lg rounded-xl border border-destructive/30 bg-card p-6 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-foreground">
            Erreur inattendue
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            L'application a rencontre une erreur de rendu. Rechargez la page
            pour reessayer.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Recharger
          </button>
          {import.meta.env.DEV && this.state.error?.message && (
            <pre className="mt-5 overflow-auto rounded-md bg-muted p-3 text-left text-xs text-destructive">
              {this.state.error.message}
            </pre>
          )}
        </section>
      </main>
    );
  }
}
