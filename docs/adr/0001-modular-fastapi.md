---
id: ADR-0001
title: "Izolowany moduł Document Studio w istniejącym FastAPI"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Granice modułów i API"
related_tasks: [DEMO-01, DEMO-02, DEMO-03]
related_prs: []
supersedes: []
---

# ADR-0001: Izolowany moduł Document Studio w istniejącym FastAPI

Wdrożone; retrospektywny zapis bez potwierdzenia właściciela.

## 1. Kontekst i problem

Do działającego planera i adaptera WhatsApp dołączono studio dokumentów.
Fakt: `create_app` rejestruje oddzielny router studia w tym samym FastAPI.
Studio ma własne modele, zapis i frontend; nie korzysta z kolejki generowania planów.

## 2. Rozważane alternatywy

Osobna aplikacja/usługa, zmiana planera w system dokumentów albo osobny moduł
w istniejącej aplikacji. To porównanie retrospektywne; brak protokołu historycznej oceny opcji.

## 3. Decyzja

Zachować `app/document_studio/` i `/api/document-studio`, współdzieląc proces
FastAPI. Nie rozszerzać przy tym SQLite, workera ani WAHA o obsługę dokumentów.
Izolacja jest logiczna i magazynowa, nie procesowa ani wdrożeniowa.

## 4. Uzasadnienie

**Udokumentowane:** specyfikacja architektury zaleca modułowy rozwój bez przepisywania
planera; instrukcje demo wskazują niezależne uruchomienie studia bez workera.
**Wniosek:** wspólne uruchomienie ogranicza liczbę usług do obsługi w demo.
**Niepotwierdzone:** porównanie kosztów osobnej aplikacji i zamierzony czas utrzymania tej granicy.

## 5. Konsekwencje pozytywne i negatywne

Plus: istniejący serwer i Compose obsługują nowy panel. Minus: wspólny proces,
zależności i cykl wydania; awaria inicjalizacji studia może wpływać na start całej aplikacji.

## 6. Dług techniczny i ograniczenia

Brak adaptera `TripPlan` → `Trip`, osobnego healthchecku magazynu studia i izolacji
procesowej. [DEBT-07 i DEBT-10](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

Wyceniać adapter i regresje osobno od ewentualnego wydzielenia usługi,
konfiguracji wdrożenia i monitoringu: [COST-05 i COST-06](../tracking/estimates.md).
Nie znamy rzeczywistej oszczędności wynikającej ze wspólnego FastAPI.

## 8. Powiązane taski, PR, commity i dokumenty

- [app/main.py](../../app/main.py): `create_app`; [API studia](../../app/document_studio/api.py): `document_router`.
- [Serwis](../../app/document_studio/service.py): operacje niezależne od planera.
- [Architektura docelowa](../document-system/architecture/system-architecture.md), sekcje 1–3 i 7;
  [DEMO-01](../DOCUMENT_STUDIO.md), [DEMO-02](../MARKETING_COLLECTION.md), [DEMO-03](../TRIP_DOCUMENTS.md).
- Commit `f9035e5ff16c293b8fddbe33938a29b96eb6ca87` zawiera razem DEMO-01–03.
  Brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Niezależne wdrożenia, odrębne wymagania dostępności/bezpieczeństwa albo zlecona
integracja planera i studia. Wydzielenie usługi wymaga nowego ADR, nie automatycznego refaktoru.
