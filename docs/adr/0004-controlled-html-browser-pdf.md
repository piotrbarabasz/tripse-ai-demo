---
id: ADR-0004
title: "Kontrolowane HTML/CSS i eksport PDF w przeglądarce"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Rendering i eksport dokumentów"
related_tasks: [DEMO-02, DEMO-03, DOC-PDF-003]
related_prs: []
supersedes: []
---

# ADR-0004: Kontrolowane HTML/CSS i eksport PDF w przeglądarce

Wdrożone; retrospektywny zapis bez potwierdzenia właściciela.

## 1. Kontekst i problem

Demo wymaga podglądu i PDF, ale nie pełnej serwerowej infrastruktury eksportów.
Fakt: kontrolowane komponenty tworzą HTML, tekst jest escapowany, a druk wywołuje `window.print()`.

## 2. Rozważane alternatywy

Druk w przeglądarce, serwerowy Chromium/Playwright, bezpośredni generator PDF.
Serwerowy renderer jest propozycją w architekturze docelowej; brak dowodu
historycznego benchmarku tych opcji. Swobodny HTML od LLM jest zabroniony w specyfikacji.

## 3. Decyzja

Dane strukturalne → kontrolowany HTML/CSS → wspólny podgląd i print CSS.
JavaScript mierzy i dzieli bloki na strony, a użytkownik zapisuje PDF z przeglądarki.
Serwer nie uruchamia Playwright i nie archiwizuje wygenerowanego pliku.

DOC-PDF-003, 2026-10-28: lokalnie rozszerzono ten sam kontrakt o semantyczny
podział tekstu, list i tabel po pomiarze DOM, kontekst kontynuacji, dekodowanie
obrazów przed składem i kontrolę rzeczywistych PDF/rastrów w QA. Nie zmieniono
schematów zapisu, usługi eksportu ani statusu proposed tego ADR. Wyniki, ograniczenia
i artefakty: [raport DOC-PDF-003](../audits/DOC_PDF_003.md). Brak wdrożenia tej iteracji.

## 4. Uzasadnienie

**Udokumentowane:** DEMO-02 oddziela projekcję danych, skład i eksport; opisuje
przeglądarkowy druk jako zakres tego etapu. Specyfikacja zabrania wykonywalnego HTML od AI.
**Wniosek:** aktualny eksport nie wymaga serwerowego procesu przeglądarki.
**Niepotwierdzone:** zmierzona różnica kosztów i docelowe SLA/formaty eksportu.

## 5. Konsekwencje pozytywne i negatywne

Plus: podgląd i wydruk korzystają ze wspólnego składu. Minus: wynik zależy od
przeglądarki, ustawień druku i fontów; nie ma serwerowego potwierdzenia zapisu PDF.
Blokada przycisku drukowania nie jest mechanizmem autoryzacji publikacji.

## 6. Dług techniczny i ograniczenia

Brak kolejki eksportów, hashy i archiwum PDF, historycznych rendererów i osadzanych
własnych fontów. Social 1080×1350 ma układ i druk, bez eksportu PNG.
[DEBT-02 i DEBT-04](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

[COST-03](../tracking/estimates.md): zatwierdzenie brandingu, QA druków,
serwerowy eksport/archiwizacja, zależności przeglądarki i utrzymanie renderera.
Przed wyceną potrzebne są formaty, wolumen i wymagania odtwarzalności.

## 8. Powiązane taski, PR, commity i dokumenty

- [Renderer](../../app/document_studio/rendering/__init__.py): `render_shell`;
  [komponenty](../../app/document_studio/rendering/components.py): `text`, `photo`.
- [Paginacja i druk](../../app/document_studio/frontend/print-export.js),
  [print CSS](../../app/document_studio/frontend/marketing.css).
- [DEMO-02](../MARKETING_COLLECTION.md), [DEMO-03](../TRIP_DOCUMENTS.md),
  [architektura docelowa](../document-system/architecture/system-architecture.md), sekcje 5–6.
- Commit `f9035e5ff16c293b8fddbe33938a29b96eb6ca87`; brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Automatyczny eksport, archiwum, powtarzalny wynik niezależny od stanowiska,
większy wolumen lub dodatkowe formaty. Taki zakres wymaga osobnej decyzji i estymacji.
