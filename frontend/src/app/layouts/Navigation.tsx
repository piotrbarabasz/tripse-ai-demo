import { ArrowUpRight, Compass } from "lucide-react";
import { NavLink } from "react-router-dom";
import { home, modules } from "../../shared/config/modules";
import { legacyHref } from "../../shared/config/legacy";

export function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <div className="brand">
        <span className="brand-symbol">
          <Compass aria-hidden="true" size={27} strokeWidth={1.6} />
        </span>
        <div>
          TRIPSE<span>PRZESTRZEŃ PRACY</span>
        </div>
      </div>
      <nav aria-label="Nawigacja główna" className="sidebar-nav">
        <p className="nav-label">Przestrzeń pracy</p>
        <NavLink end to={home.path} onClick={onNavigate}>
          <home.icon size={19} aria-hidden="true" />
          {home.title}
        </NavLink>
        <p className="nav-label modules-label">Moduły</p>
        {modules.map((module) => (
          <NavLink key={module.path} to={module.path} onClick={onNavigate}>
            <module.icon size={19} aria-hidden="true" />
            {module.title}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-info">
          <span className="sidebar-info-label">NOWY ROZDZIAŁ TRIPSE</span>
          <p>
            Znane narzędzia.
            <br />
            Nowa przestrzeń.
          </p>
          <a href={legacyHref("/hub")}>
            Przejdź do obecnego Hubu
            <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </div>
        <span className="sidebar-footer">
          TRIPSE <span>·</span> Razem w dobrym kierunku
        </span>
      </div>
    </>
  );
}
