import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App, AppRoutes } from "./App";
import { modules } from "../shared/config/modules";
import { ErrorBoundary } from "../shared/components/ErrorBoundary";

function renderPage(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

// Shell tests exercise navigation. Health behavior is tested with controlled
// responses separately; no live network requests or asynchronous status changes.
beforeEach(() =>
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>(() => undefined)),
  ),
);
afterEach(() => vi.unstubAllGlobals());

describe("przestrzeń TRIPSE", () => {
  it.each(["/app", "/app/"])("bootstraps the real browser router at %s", (path) => {
    window.history.replaceState(null, "", path);
    render(<App />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Dobry początek każdej podróży.",
      }),
    ).toBeVisible();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("renders an informative Hub with module cards and existing functionality", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: "Moduły TRIPSE" }),
    ).toBeVisible();
    expect(screen.getAllByRole("article")).toHaveLength(5);
    expect(screen.getAllByText("Migracja planowana")).toHaveLength(2);
    expect(screen.getAllByText("Moduł planowany")).toHaveLength(3);
    expect(
      screen.getByRole("link", { name: /Otwórz obecny planer/ }),
    ).toHaveAttribute("href", "/planner");
    expect(
      screen.getByRole("link", { name: /Otwórz obecne studio/ }),
    ).toHaveAttribute("href", "/documents/demo");
    expect(
      screen.getByRole("link", { name: "Otwórz obecny Hub" }),
    ).toHaveAttribute("href", "/hub");
  });

  it("navigates client-side and updates active navigation, title and keyboard focus", async () => {
    const user = userEvent.setup();
    renderPage();
    const navigation = screen.getByRole("navigation", {
      name: "Nawigacja główna",
    });
    expect(
      within(navigation).getByRole("link", { name: "Pulpit" }),
    ).toHaveAttribute("aria-current", "page");
    await user.click(
      within(navigation).getByRole("link", { name: "Planer podróży" }),
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Planer podróży" }),
    ).toBeVisible();
    expect(
      within(navigation).getByRole("link", { name: "Planer podróży" }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      within(navigation).getByRole("link", { name: "Pulpit" }),
    ).not.toHaveAttribute("aria-current");
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1 })).toHaveFocus(),
    );
    expect(document.title).toBe("Planer podróży — TRIPSE");
    await user.click(screen.getByRole("link", { name: "Wróć do pulpitu" }));
    expect(
      screen.getByRole("heading", { name: "Moduły TRIPSE" }),
    ).toBeVisible();
  });

  it.each(modules)("supports a direct nested route: $path", (module) => {
    renderPage(module.path);
    expect(
      screen.getByRole("heading", { level: 1, name: module.title }),
    ).toBeVisible();
    expect(screen.getByText("Widok planowany")).toBeVisible();
    if ("legacy" in module)
      expect(
        screen.getByRole("link", { name: module.legacyLabel }),
      ).toHaveAttribute("href", module.legacy);
  });

  it("offers recovery from unknown routes without marking a module active", async () => {
    const user = userEvent.setup();
    renderPage("/nieznana/strona");
    expect(
      screen.getByRole("heading", { name: "Nie znaleziono strony" }),
    ).toBeVisible();
    expect(
      screen.getByRole("navigation").querySelector("[aria-current]"),
    ).toBeNull();
    await user.click(screen.getByRole("link", { name: "Wróć do pulpitu" }));
    expect(
      screen.getByRole("heading", { name: "Moduły TRIPSE" }),
    ).toBeVisible();
  });

  it("opens a named drawer, traps keyboard focus, closes on Escape and restores trigger focus", async () => {
    const user = userEvent.setup();
    renderPage();
    const trigger = screen.getByRole("button", { name: "Otwórz nawigację" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Nawigacja TRIPSE" });
    expect(dialog).toBeVisible();
    expect(
      within(dialog).getByRole("navigation", { name: "Nawigacja główna" }),
    ).toBeInTheDocument();
    const close = within(dialog).getByRole("button", {
      name: "Zamknij nawigację",
    });
    close.focus();
    await user.tab();
    expect(dialog.contains(document.activeElement)).toBe(true);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("closes the mobile drawer when selecting a module", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: "Otwórz nawigację" }));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("link", {
        name: "Marketing",
      }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Marketing" }),
    ).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1 })).toHaveFocus(),
    );
  });

  it("provides a named skip link and a focusable main region", () => {
    renderPage();
    expect(
      screen.getByRole("link", { name: "Przejdź do treści" }),
    ).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
    expect(screen.getByRole("main")).toHaveAttribute("tabindex", "-1");
  });

  it("recovers from a render failure without displaying internal error details", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    function Broken(): never {
      throw new Error("private diagnostic detail");
    }
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Nie udało się wyświetlić aplikacji",
    );
    expect(
      screen.queryByText("private diagnostic detail"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Wróć do pulpitu" }),
    ).toHaveAttribute("href", "/app/");
  });
});
