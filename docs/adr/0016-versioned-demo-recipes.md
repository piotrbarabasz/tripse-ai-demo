---
id: ADR-0016
title: "Wersjonowane receptury przykładów i niezależne kopie dokumentów"
status: proposed
date: 2026-10-28
author: "Codex — autor zapisu"
area: "document-studio"
related_tasks: [DOC-TEMPLATES-006]
related_prs: []
supersedes: []
---

# ADR-0016: Wersjonowane receptury przykładów

Stan: implementacja lokalna na dev. Akceptacja architektury przez właściciela
nieodnotowana; polecenie zadania upoważnia realizację lokalną, nie wdrożenie.

## 1. Kontekst i problem

Preset Islandii obejmował dwa typy i był związany z konkretnym ID. Dziewięć
konfiguracji GT wymaga powtarzalnych źródeł, sekcji i bezpiecznej inicjalizacji
magazynu posiadającego własne overlay oraz historię dokumentów.

## 2. Rozważane alternatywy

Surowe drafty JSON powielałyby model i sekcje; seed przy starcie zapisywałby dane
bez decyzji operatora; bezpośrednia edycja wzorców niszczyłaby wspólny punkt odniesienia.

## 3. Decyzja

Receptury `demo-fixtures/gt-v1/examples.json` są składane przez istniejącą usługę
i walidowane jako DocumentDraft. Kanoniczny katalog jest tylko do odczytu.
UUID operacji daje idempotentną kopię do zwykłej biblioteki i edytora. Opcjonalny
seed CLI jest create-only, wykrywa różnice i wznawia częściowy przebieg. Żaden
mechanizm nie kasuje overlay, zapisów historii ani assetów. Nie ma seeda przy starcie PROD.

## 4. Uzasadnienie

Udokumentowane: DOC-TEMPLATES-006 wymaga dziewięciu konfiguracji, niezależnych
snapshotów, bezpiecznego seedowania i zachowania danych. Wniosek projektowy:
katalog receptur oddziela stabilny materiał demonstracyjny od dokumentów użytkownika.
Nie twierdzimy, że TRIPSE zatwierdziło zawartość biznesową Ground Truth.

## 5. Konsekwencje pozytywne i negatywne

Przykłady działają przed inicjalizacją magazynu, kopiowanie używa dotychczasowego
CAS i rewizji. Koszt: utrzymanie wersji receptur i testów zgodności z modelami.
Aktualizacja receptury wymaga świadomej wersji; istniejące kopie pozostają snapshotami.

## 6. Dług techniczny i ograniczenia

Remote DEV nie był inicjalizowany ani inwentaryzowany. Rzeczywiste IAM/IAP, GCS
i odtworzenie backupu wymagają akceptacji operatora. System nie interpretuje
`demo`, zgodnego odcisku ani starego prefiksu jako upoważnienia do kasowania.

## 7. Wpływ na kosztorys

Utrzymanie receptur, przegląd treści i testy wizualne przy zmianach renderera.
Nie mierzono godzin ani kosztów; nie uruchamiano płatnych API.

## 8. Powiązane taski, PR, commity i dokumenty

Task DOC-TEMPLATES-006; [raport](../DOC_TEMPLATES_006.md),
[macierz](../audits/DOC_TEMPLATES_006_COVERAGE.md),
[ADR-0003](0003-document-snapshots.md), [ADR-0014](0014-document-library-history.md).
Baza: 53947b4; brak nowego commita i PR, brak dowodu akceptacji ADR.

## 9. Warunki ponownego rozważenia decyzji

Katalog zarządzany przez redaktorów, wiele wersji GT naraz lub zmiana zasad
przechowywania wzorców. Wtedy ponownie ocenić własność, migracje i uprawnienia.

## Historia zmian

| Data | Autor | Zmiana i uzasadnienie | Powiązanie |
|---|---|---|---|
| 2026-10-28 | Codex | Propozycja i implementacja lokalnego katalogu/receptur | DOC-TEMPLATES-006 |
