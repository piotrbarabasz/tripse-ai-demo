import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../shared/components/PageHeader";
import { legacyHref } from "../shared/config/legacy";
import type { WorkspaceModule } from "../shared/config/modules";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";

export function ModulePage({ module }: { module: WorkspaceModule }) {
  return (
    <>
      <PageHeader eyebrow={module.category} title={module.title}>
        {module.description}
      </PageHeader>
      <section className="placeholder-panel" aria-labelledby="module-status">
        <span className="module-icon">
          <module.icon aria-hidden="true" size={30} />
        </span>
        <Badge>Widok planowany</Badge>
        <h2 id="module-status">Ten moduł jest przed nami</h2>
        <p>{module.detail}</p>
        <div className="placeholder-actions">
          {"legacy" in module && (
            <Button asChild>
              <a href={legacyHref(module.legacy)}>
                {module.legacyLabel}
                <ArrowUpRight size={16} aria-hidden="true" />
              </a>
            </Button>
          )}
          <Button variant="outline" asChild>
            <Link to="/">
              <ArrowLeft size={16} aria-hidden="true" />
              Wróć do pulpitu
            </Link>
          </Button>
        </div>
      </section>
    </>
  );
}
