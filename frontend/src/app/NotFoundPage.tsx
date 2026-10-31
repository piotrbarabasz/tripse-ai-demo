import { Link } from "react-router-dom";
import { PageHeader } from "../shared/components/PageHeader";
import { Button } from "../shared/ui/button";

export function NotFoundPage() {
  return (
    <>
      <PageHeader eyebrow="Błąd 404" title="Nie znaleziono strony">
        Ten adres nie prowadzi do żadnego widoku w przestrzeni TRIPSE.
      </PageHeader>
      <Button asChild>
        <Link to="/">Wróć do pulpitu</Link>
      </Button>
    </>
  );
}
