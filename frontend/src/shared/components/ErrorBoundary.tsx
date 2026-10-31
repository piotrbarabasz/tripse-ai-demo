import { Component, type ReactNode } from "react";
import { TriangleAlert } from "lucide-react";
import { Button } from "../ui/button";

export function ErrorPage() {
  return <main className="error-page" role="alert">
    <TriangleAlert aria-hidden="true" />
    <h1>Nie udało się wyświetlić aplikacji</h1>
    <p>Odśwież stronę i spróbuj ponownie.</p>
    <Button asChild><a href="/app/">Wróć do pulpitu</a></Button>
  </main>;
}

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed) return <ErrorPage />;
    return this.props.children;
  }
}
