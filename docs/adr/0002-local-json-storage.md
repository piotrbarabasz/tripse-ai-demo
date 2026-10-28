---
id: ADR-0002
title: "Lokalny JSON i odrębne dane demonstracyjne"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Przechowywanie danych Document Studio"
related_tasks: [DEMO-01]
related_prs: []
supersedes: []
---

# ADR-0002: Lokalny JSON i odrębne dane demonstracyjne

Wdrożone; retrospektywny zapis bez potwierdzenia właściciela.

## 1. Kontekst i problem

Demo potrzebuje trwałych wycieczek, kampanii i draftów bez wdrażania centralnej bazy.
Fakt: `JsonRepository` waliduje dane Pydantic i zapisuje osobne pliki.

## 2. Rozważane alternatywy

Lokalny JSON, rozszerzenie SQLite lub centralny magazyn. PostgreSQL/Firestore
występują w dokumentacji docelowej jako opcje, nie dokonany wybór.
Pozostałe zestawienie jest retrospektywne, bez dowodu historycznej analizy kosztów.

## 3. Decyzja

Fixture'y w `demo-fixtures/` są bazą tylko do odczytu; zapis tworzy lokalną
nakładkę w `local-data/document-studio/`. Katalog jest ignorowany przez Git
i Docker build context. Compose montuje go z hosta, oddzielnie od SQLite planera.
Zapis: plik tymczasowy, flush/fsync, `os.replace`; kontrola rewizji i `RLock` w procesie.

## 4. Uzasadnienie

**Udokumentowane:** instrukcja DEMO-01 opisuje lokalne demo, atomowy zapis,
trwałość po restarcie i możliwość podstawienia innego repozytorium.
**Wniosek:** rozdzielenie fixture'ów chroni przykłady przed edycją użytkownika.
**Niepotwierdzone:** przewidywany wolumen, liczba użytkowników i finansowe porównanie baz.

## 5. Konsekwencje pozytywne i negatywne

Plus: dane pozostają po restarcie, pliki są łatwe do inspekcji. Minus: brak
transakcji między plikami, zapytań centralnej bazy i blokady między procesami.
Atomowa podmiana pojedynczego pliku nie zastępuje backupu ani pełnych gwarancji po awarii zasilania.

## 6. Dług techniczny i ograniczenia

Jeden proces API. Historyczna obserwacja z 2026-10-25, że sama rewizja nie
przechowuje historii, została rozszerzona w [ADR-0014](0014-document-library-history.md):
od DOCUMENT-LIBRARY-001 zachowywane są poprzednie pełne zapisy i metadane biblioteki.
Nie odtworzono brakujących wersji sprzed tej funkcji. Brak migratora, backup/restore
i retencji; API oraz `AssetStore` znają konkretny magazyn. Migracja nie jest
obietnicą bezkosztowej podmiany. [DEBT-01, DEBT-02, DEBT-05](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

[COST-01 i COST-04](../tracking/estimates.md): wybór magazynu, migracja,
transakcje, testy konfliktów, backup i magazyn obrazów. Bez danych o skali nie wpisujemy kwot.

## 8. Powiązane taski, PR, commity i dokumenty

- [Repozytorium](../../app/document_studio/repository.py): `Repository`, `JsonRepository.save`.
- [Compose](../../compose.yaml), [Dockerfile](../../Dockerfile), [.gitignore](../../.gitignore), [.dockerignore](../../.dockerignore).
- [DEMO-01](../DOCUMENT_STUDIO.md); [propozycja GCP i baz](../document-system/architecture/gcp-deployment.md).
- DEMO-01; commit `f9035e5ff16c293b8fddbe33938a29b96eb6ca87`. Brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Wielu autorów/procesów, współdzielone środowisko, większy wolumen lub wymagania
backupów i audytu. Centralna baza wymaga odrębnego wyboru, nie wynika automatycznie z tego ADR.

## Historia zmian

| Data | Autor | Zmiana | Podstawa |
|---|---|---|---|
| 2026-10-28 | Codex | Uzupełnienie historycznego ograniczenia o bibliotekę i zachowane rewizje; brak zmiany statusu ADR | DOCUMENT-LIBRARY-001; ADR-0014 |
