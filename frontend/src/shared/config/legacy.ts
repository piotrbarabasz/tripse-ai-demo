export type LegacyPath = "/hub" | "/planner" | "/documents/demo";

// Build-time variables are public. This option affects links only in Vite dev.
export function resolveLegacyHref(
  path: LegacyPath,
  development: boolean,
  origin?: string,
): string {
  if (!development || !origin) return path;
  const url = new URL(origin);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      "VITE_DEV_BACKEND_ORIGIN musi być adresem origin HTTP(S), bez ścieżki i danych logowania.",
    );
  }
  return `${url.origin}${path}`;
}

export function legacyHref(path: LegacyPath): string {
  if (!import.meta.env.DEV) return path;
  return resolveLegacyHref(
    path,
    true,
    import.meta.env.VITE_DEV_BACKEND_ORIGIN as string | undefined,
  );
}
