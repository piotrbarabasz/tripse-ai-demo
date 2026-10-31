import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="page-heading">
      <p className="eyebrow">{eyebrow}</p>
      <h1 tabIndex={-1} id="page-title">
        {title}
      </h1>
      <p className="page-description">{children}</p>
    </div>
  );
}
