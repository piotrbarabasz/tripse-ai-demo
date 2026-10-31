import { Component, type ReactNode } from "react";
import { TriangleAlert } from "lucide-react";
import { Button } from "../ui/button";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main className="error-page" role="alert">
          <TriangleAlert aria-hidden="true" />
          <h1>Nie udało się wyświetlić aplikacji</h1>
          <p>Odśwież stronę i spróbuj ponownie.</p>
          <Button asChild>
            <a href="/app/">Wróć do pulpitu</a>
          </Button>
        </main>
      );
    return this.props.children;
  }
}
