import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import { Outlet, useLocation } from "react-router-dom";
import { home, modules } from "../../shared/config/modules";
import { Button } from "../../shared/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from "../../shared/ui/sheet";
import { Navigation } from "./Navigation";

export function AppLayout() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const title =
    [home, ...modules].find((module) => module.path === pathname)?.title ??
    "Nie znaleziono strony";
  useEffect(() => {
    document.title = `${title} — TRIPSE`;
    // Wait until dialog focus restoration finishes before focusing the new page.
    const frame = requestAnimationFrame(() =>
      document.getElementById("page-title")?.focus(),
    );
    return () => cancelAnimationFrame(frame);
  }, [pathname, title]);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Przejdź do treści
      </a>
      <aside className="desktop-sidebar">
        <Navigation />
      </aside>
      <div className="workspace">
        <header className="app-header">
          <div className="header-start">
            <div className="mobile-toggle">
              <Sheet open={open} onOpenChange={setOpen}>
                <SheetTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Otwórz nawigację"
                  >
                    <Menu size={22} aria-hidden="true" />
                  </Button>
                </SheetTrigger>
                <SheetContent
                  onCloseAutoFocus={(event) => {
                    if (document.activeElement?.closest("nav")) {
                      event.preventDefault();
                      document.getElementById("page-title")?.focus();
                    }
                  }}
                >
                  <SheetTitle>Nawigacja TRIPSE</SheetTitle>
                  <SheetDescription>
                    Wybierz pulpit lub moduł przestrzeni pracy.
                  </SheetDescription>
                  <Navigation onNavigate={() => setOpen(false)} />
                </SheetContent>
              </Sheet>
            </div>
            <span className="header-workspace">
              Przestrzeń pracy<span>/</span>
            </span>
            <span className="header-title">{title}</span>
          </div>
          <span className="header-status">
            <span aria-hidden="true" />
            Nowy panel
          </span>
        </header>
        <main id="main" tabIndex={-1} className="main-content">
          <Outlet />
        </main>
        <footer className="workspace-footer">
          <span>TRIPSE · Przestrzeń dla Twoich pomysłów</span>
          <span>Panel w rozwoju</span>
        </footer>
      </div>
    </div>
  );
}
