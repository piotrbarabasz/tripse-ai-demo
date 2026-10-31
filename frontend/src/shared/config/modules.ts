import {
  Bot,
  FileText,
  LayoutDashboard,
  Megaphone,
  Route,
  Workflow,
} from "lucide-react";

export const home = { path: "/", title: "Pulpit", icon: LayoutDashboard };
export const modules = [
  {
    path: "/planner",
    title: "Planer podróży",
    icon: Route,
    category: "Planowanie",
    description: "Od pomysłu na wyjazd do trasy, programu i mapy podróży.",
    legacy: "/planner",
    legacyLabel: "Otwórz obecny planer",
    detail:
      "Przygotuj plan, obserwuj postęp zadania i otwórz istniejący podgląd z mapą. Tryb i dostęp sprawdzane są przez usługę. Katalog wycieczek pozostaje planowany.",
  },
  {
    path: "/documents",
    title: "Document Studio",
    icon: FileText,
    category: "Dokumenty",
    description:
      "Oferty, programy dla pilotów i materiały podróżnicze w jednym miejscu.",
    legacy: "/documents/demo",
    legacyLabel: "Otwórz obecne studio",
    detail:
      "Katalog, tworzenie i edycja treści dokumentów. Zaawansowane pola i zdjęcia pozostają w dotychczasowym Studio.",
  },
  {
    path: "/marketing",
    title: "Marketing",
    icon: Megaphone,
    category: "Komunikacja",
    description:
      "Przestrzeń na kampanie i materiały inspirowane Twoimi wycieczkami.",
    detail:
      "Ten moduł jest planowany. Integracja danych kampanii i materiałów marketingowych pojawi się w kolejnych etapach.",
  },
  {
    path: "/automations",
    title: "Automatyzacje",
    icon: Workflow,
    category: "Organizacja",
    description:
      "Docelowo: zadania, przebieg działań i historia ich wykonania.",
    detail:
      "Ten moduł jest planowany. Wykonywanie automatyzacji, statusy, historia i zatwierdzenia nie są jeszcze dostępne w nowym panelu.",
  },
  {
    path: "/assistant",
    title: "Asystent AI",
    icon: Bot,
    category: "Wsparcie",
    description: "Docelowo: pomoc w codziennej pracy z planami i dokumentami.",
    detail:
      "Ten moduł jest planowany. Rozmowa i wykonywanie operacji przez asystenta nie są jeszcze dostępne. Ten widok nie łączy się z dostawcami AI.",
  },
] as const;

export type WorkspaceModule = (typeof modules)[number];
