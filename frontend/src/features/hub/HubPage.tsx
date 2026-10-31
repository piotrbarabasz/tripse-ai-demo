import { ArrowRight, ArrowUpRight, Compass, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../shared/components/PageHeader";
import { modules } from "../../shared/config/modules";
import { legacyHref } from "../../shared/config/legacy";
import { Badge } from "../../shared/ui/badge";
import { Button } from "../../shared/ui/button";
import { HealthStatus } from "./HealthStatus";

export function HubPage() {
  return (
    <>
      <PageHeader
        eyebrow="Twoja przestrzeń TRIPSE"
        title="Dobry początek każdej podróży."
      >
        Witaj w TRIPSE. Zaplanuj wyjazd, przygotuj materiały i uporządkuj pracę
        biura podróży.
      </PageHeader>
      <section className="welcome-panel" aria-labelledby="welcome-title">
        <div className="welcome-icon">
          <Compass size={32} strokeWidth={1.5} aria-hidden="true" />
        </div>
        <div className="grow">
          <p className="eyebrow">Wszystko zaczyna się tutaj</p>
          <h2 id="welcome-title">Twoje narzędzia. Wspólny kierunek.</h2>
          <p>
            Zaplanuj podróż w nowym planerze. Document Studio otworzysz
            w dotychczasowym interfejsie; kolejne moduły powstają krok po kroku.
          </p>
        </div>
        <Button asChild variant="outline">
          <a href={legacyHref("/hub")}>
            Otwórz obecny Hub <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </Button>
      </section>
      <section aria-labelledby="modules-title" className="module-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Wybierz obszar pracy</p>
            <h2 id="modules-title">Moduły TRIPSE</h2>
          </div>
          <span className="section-caption">
            Jedna przestrzeń, kolejne możliwości
          </span>
        </div>
        <div className="module-grid">
          {modules.map((module) => (
            <article className="module-card" key={module.path}>
              <div className="card-top">
                <span className="module-icon">
                  <module.icon size={23} strokeWidth={1.6} aria-hidden="true" />
                </span>
                <Badge>
                  {module.path === "/planner" ? "Dostępny planer" : "legacy" in module
                    ? "Migracja planowana"
                    : "Moduł planowany"}
                </Badge>
              </div>
              <p className="card-category">{module.category}</p>
              <h3>{module.title}</h3>
              <p className="card-description">{module.description}</p>
              <div className="card-actions">
                <Link className="text-link" to={module.path}>
                  {module.path === "/planner" ? "Zaplanuj podróż" : "Poznaj moduł"} <ArrowRight size={16} aria-hidden="true" />
                  <span className="sr-only">: {module.title}</span>
                </Link>
                {"legacy" in module && (
                  <a
                    className="legacy-card-link"
                    href={legacyHref(module.legacy)}
                  >
                    {module.legacyLabel}
                    <ExternalLink size={14} aria-hidden="true" />
                    <span className="availability">
                      Dostępny obecny interfejs
                    </span>
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
      <HealthStatus />
      <aside className="workspace-note">
        <span className="note-marker" aria-hidden="true" />
        <p>
          <strong>Przestrzeń w rozwoju.</strong> Planer obsługuje tworzenie i postęp
          zadań, a plan z mapą otwiera się w obecnym podglądzie. Tryb MOCK lub LIVE
          oraz uprawnienia sprawdzisz w planerze. Dokumenty pozostają w obecnym
          studio; Marketing, Automatyzacje i Asystent są planowane.
        </p>
      </aside>
    </>
  );
}
