---
id: ADR-0006
title: "Wspólny rejestr szablonów i komponenty wizualne"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Szablony i design system"
related_tasks: [DEMO-01, DEMO-02, DEMO-03]
related_prs: []
supersedes: []
---

# ADR-0006: Wspólny rejestr szablonów i komponenty wizualne

2026-10-28: wszystkie osiem ID ma lokalnie zaimplementowany edytor sekcji i
podgląd roboczy 0.4.0, współdzielący dotychczasowy shell, zdjęcia i paginację.
Retrospektywny zapis pozostaje `proposed`, bez formalnej akceptacji właściciela.
Nowa iteracja nie została wdrożona na DEV/PROD.

## 1. Kontekst i problem

Wiele dokumentów ma zachować tożsamość typów i wspólne elementy wizualne.
Historyczny stan 2026-10-25: katalog miał osiem ID, lecz kompletne generatory
obejmowały tylko `marketing.collection` (dwa warianty), `offer.private` i
`pilot.basic`. Pozostałe typy uzupełniono wspólnym mechanizmem sekcji dokumentu.

## 2. Rozważane alternatywy

Niezależne szablony z kopiowanymi stylami, rozbudowany CMS/plugin engine lub
niewielki rejestr i współdzielone komponenty. Jest to porównanie retrospektywne,
bez udokumentowanego historycznego wyboru CMS.

## 3. Decyzja

`TEMPLATES` utrzymuje ID, wersję, rodzinę, odbiorcę, poufność i warianty.
Renderery współdzielą `render_shell`, escapowanie, komponent zdjęcia, paginację
i tokeny brandingu. Frontend jest w HTML/CSS/JS, bez nowego frameworka.

## 4. Uzasadnienie

**Udokumentowane:** katalog docelowy rozdziela ID i wersję; design system
definiuje wspólne komponenty. DEMO-02 wskazuje podmianę brandingu przez tokeny.
**Wniosek:** wspólne elementy ograniczają powielanie składu między generatorami.
**Niepotwierdzone:** zatwierdzony brand book oraz wymagania rozszerzalności przez użytkowników.

## 5. Konsekwencje pozytywne i negatywne

Plus: jeden styl i mechanizm stron służy wszystkim ośmiu typom.
Minus: zmiana wspólnego komponentu wymaga regresji wszystkich dokumentów;
rejestr nie uruchamia automatycznie nowego generatora ani walidatora.

## 6. Dług techniczny i ograniczenia

Pięć wcześniej katalogowych ID ma teraz edytor i renderowanie sekcyjne.
Branding i znak tekstowy są robocze;
brak wersjonowanego archiwum rendererów. Przełączanie typów i część UI są
implementowane jawnie w kodzie. [DEBT-04 i DEBT-08](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

[COST-03 i COST-07](../tracking/estimates.md): zatwierdzenie identyfikacji,
projekty i walidatory kolejnych typów, testy współdzielonych komponentów,
ewentualne języki/formaty. Wpis w rejestrze nie oznacza, że te prace już wykonano.

## 8. Powiązane taski, PR, commity i dokumenty

- [Rejestr](../../app/document_studio/templates.py), [modele](../../app/document_studio/models.py).
- [Komponenty](../../app/document_studio/rendering/components.py),
  [wspólny shell](../../app/document_studio/rendering/__init__.py),
  [tokeny](../../app/document_studio/frontend/brand-tokens.css), [frontend](../../app/document_studio/frontend/index.html).
- [Katalog docelowy](../document-system/general/template-catalog.md),
  [branding](../document-system/design/brand-guidelines.md), [DEMO-02](../MARKETING_COLLECTION.md).
- Commit `f9035e5ff16c293b8fddbe33938a29b96eb6ca87`; brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Zatwierdzony branding, wiele języków, formaty poza obecnym drukiem lub
konfigurowanie szablonów przez użytkownika. Ewentualny CMS/framework wymaga osobnego uzasadnienia.

## Historia zmian

| Data | Autor | Zmiana | Podstawa |
|---|---|---|---|
| 2026-10-28 | Codex | Uzupełnienie ośmiu typów przez walidowane sekcje instancji; zachowanie wspólnego silnika, snapshotów i statusu proposed | Zlecenie użytkownika; [instrukcja](../DOCUMENT_STUDIO.md); brak nowego tasku/PR |
