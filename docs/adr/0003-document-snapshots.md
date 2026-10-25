---
id: ADR-0003
title: "Wspólne dane podróży i niezależne snapshoty dokumentów"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Model danych i poufność treści"
related_tasks: [DEMO-01, DEMO-02, DEMO-03]
related_prs: []
supersedes: []
---

# ADR-0003: Wspólne dane podróży i niezależne snapshoty dokumentów

Wdrożone; retrospektywny zapis bez potwierdzenia właściciela.

## 1. Kontekst i problem

Jeden program ma zasilać ofertę, materiały pilota i kampanie wielu kierunków.
Planer ma inny model `TripPlan` i ograniczenia 1–2 dni; nie jest źródłem studia przez adapter.

## 2. Rozważane alternatywy

Osobna kopia modelu wycieczki dla każdego szablonu, dokument odwołujący się
zawsze do aktualnego Trip lub snapshot z własnymi polami. Oprócz wzorca snapshotu
opisanego w specyfikacji brak potwierdzonego historycznego porównania alternatyw.

## 3. Decyzja

W studio wspólne `Trip`/`TripDay`/`Stop`; `Campaign.items` wskazują wiele Trip.
`DocumentDraft` zachowuje snapshot źródła, wersję szablonu i rewizję. Edycje
`day_overrides`, `offer_data`, `pilot_data` nie zapisują się do bazowego Trip.
Oferta używa jawnej listy dozwolonych pól, a dane operacyjne są od niej strukturalnie oddzielone.

## 4. Uzasadnienie

**Udokumentowane:** model docelowy opisuje jeden Trip i niezależne dokumenty;
DEMO-03 wyjaśnia izolację redakcji i poufności.
**Wniosek:** snapshot chroni dokument przed późniejszymi zmianami źródła.
**Niepotwierdzone:** wymagania biznesowe dla historii i przechowywania wszystkich rewizji.

## 5. Konsekwencje pozytywne i negatywne

Plus: wiele dokumentów korzysta z jednego programu, redakcja jest lokalna dla draftu.
Minus: snapshot świadomie kopiuje dane; nie aktualizuje się sam po zmianie Trip
i wymaga późniejszych reguł synchronizacji/retencji.

## 6. Dług techniczny i ograniczenia

Brak archiwum pełnych rewizji i workflow akceptacji. Lista dozwolonych pól nie
wykrywa sekretów wpisanych ręcznie w publiczny opis. [DEBT-02, DEBT-03, DEBT-06](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

[COST-01, COST-02 i COST-07](../tracking/estimates.md): migracje schematów,
historia/porównanie rewizji, kontrola dostępu i walidacja treści. Wolumen kopii
i wymagana retencja są danymi wejściowymi, nie oszacowanym dziś kosztem.

## 8. Powiązane taski, PR, commity i dokumenty

- [Modele](../../app/document_studio/models.py): `Campaign`, `DocumentDraft.valid_source`.
- [Serwis](../../app/document_studio/service.py): `create_draft`, `update_draft`;
  [projekcja oferty](../../app/document_studio/trip_documents.py): `OFFER_*_FIELDS`, `offer_trip_snapshot`.
- [Model docelowy](../document-system/system-data/trip-data-model.md), [DEMO-03](../TRIP_DOCUMENTS.md).
- DEMO-01–03; commit `f9035e5ff16c293b8fddbe33938a29b96eb6ca87`. Brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Wymóg pełnego audytu, aktualizacji dokumentów ze źródła, prawnego archiwum
lub integracji z planerem. Nie zastępować snapshotów odwołaniem do zmiennych danych bez nowej decyzji.
