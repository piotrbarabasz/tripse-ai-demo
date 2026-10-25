---
id: ADR-0007
title: "Kolejka planera w SQLite i jeden osobny worker"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Planer, kolejka i kanały wiadomości"
related_tasks: [HIST-PLANNER-01, HIST-MOCK-01]
related_prs: []
supersedes: []
---

# ADR-0007: Kolejka planera w SQLite i jeden osobny worker

Wdrożone przed Document Studio; retrospektywny zapis bez potwierdzenia właściciela.

## 1. Kontekst i problem

Planowanie i wywołania dostawców nie powinny blokować webhooka ani żądania HTTP.
Wyniki i wiadomości muszą zachować stan po restarcie procesu.

## 2. Rozważane alternatywy

Planowanie synchroniczne w HTTP, dedykowany broker z pulą workerów lub SQLite
z jednym workerem. Specyfikacja opisuje ostatni wariant jako minimum demo;
brak dowodu historycznego benchmarku brokerów.

## 3. Decyzja

`POST /api/trips` zapisuje job i zwraca 202. Osobny worker pobiera zadania;
SQLite przechowuje stan planu, deduplikację, wiadomości i tokeny viewerów.
Compose współdzieli wolumen SQLite między API i workerem. WAHA jest adapterem;
retry wiadomości nie uruchamia ponownie zakończonego planowania. Jeden worker jest wspieranym trybem.

## 4. Uzasadnienie

**Udokumentowane:** specyfikacja demo wymaga pracy poza HTTP i niezależności
od kanału; README wskazuje SQLite i jeden worker jako minimalny stack pokazu.
**Wniosek:** brak dodatkowego brokera upraszcza lokalną topologię.
**Niepotwierdzone:** wymagane przepustowości i przewaga kosztowa nad brokerem.

## 5. Konsekwencje pozytywne i negatywne

Plus: trwały stan i odzyskiwanie przerwanych prac. Minus: przetwarzanie jest
szeregowe, a restart requeue może powtórzyć płatne wywołania. Wysyłka wiadomości
nie gwarantuje exactly-once po awarii na granicy potwierdzenia.

## 6. Dług techniczny i ograniczenia

`recover_interrupted` zakłada jeden worker. Brak gwarancji jednokrotnego
naliczenia płatnych zadań; `/health` nie mierzy żywotności workera.
Planer live ogranicza trasę do 1–2 dni/8 lokalizacji. [DEBT-07, DEBT-10, DEBT-11](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

[COST-05 i COST-06](../tracking/estimates.md): idempotencja, retry i limity,
skalowanie kolejki, monitoring, testy realnych usług oraz opłaty dostawców.
Nie znamy faktycznych rachunków; limity liczby wywołań nie są pomiarem kosztów.

## 8. Powiązane taski, PR, commity i dokumenty

- [API](../../app/main.py), [SQLite](../../app/db.py): `claim_next`, `recover_interrupted`;
  [worker](../../app/worker.py): `process_next`, `process_result`, `main`.
- [Compose](../../compose.yaml), [specyfikacja demo](../DEMO_SPEC.md),
  [pipeline](../PLANNING.md), [WAHA](../WAHA.md), [README](../../README.md).
- Commity: `2e291a90577d6281824ec798a7b20827bf6b4a6b` (fundament),
  `0899d333ebb19fb843ef37150b8c9b16bebdc04a` (symulator/mock).
  Taski `HIST-*` to lokalne etykiety retrospektywne worklogu, nie numery zgłoszeń.
  Brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Wymagane równoległe zadania, współdzielony deployment, SLA lub gwarancje płatnych
wywołań. Skalowanie liczby workerów bez zmiany protokołu odzyskiwania nie jest objęte tym wyborem.
