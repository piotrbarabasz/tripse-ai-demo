import { useEffect, useRef } from "react";
import { useBeforeUnload, useBlocker } from "react-router-dom";
import { Button } from "../../shared/ui/button";

export function UnsavedWarning({ dirty, title = "Opuścić tworzenie dokumentu?", description = "Formularz i dane odzyskiwania są tylko w pamięci tej strony. Utracisz je po wyjściu. Jeśli zapis był wysłany, dokument może już istnieć — najpierw sprawdź wynik." }: { dirty: boolean; title?: string; description?: string }) {
  useBeforeUnload((event) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  const blocker = useBlocker(dirty);
  const stay = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (blocker.state === "blocked") stay.current?.focus(); }, [blocker.state]);
  return blocker.state === "blocked" ? <section role="alertdialog" aria-labelledby="leave-title" aria-describedby="leave-description" className="documents-notice unsaved-warning">
    <h3 id="leave-title">{title}</h3><p id="leave-description">{description}</p>
    <Button ref={stay} onClick={() => blocker.reset()}>Zostań w formularzu</Button>
    <Button variant="outline" onClick={() => blocker.proceed()}>Opuść formularz</Button>
  </section> : null;
}
