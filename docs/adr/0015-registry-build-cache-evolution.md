---
id: ADR-0015
title: "Rozwój istniejącego Artifact Registry i cache CI/CD TRIPSE"
status: proposed
date: 2026-10-28
author: "Codex — autor propozycji dokumentacyjnej"
area: "CI/CD, Artifact Registry, build cache, proweniencja"
related_tasks: [CI-001, CI-002, CI-003, CI-004, CI-005]
related_prs: []
supersedes: []
---

# ADR-0015: Rozwój rejestru obrazów i cache CI/CD

Stan implementacji: istniejący rejestr i delivery są opisane w ADR-0012;
CI-001 zaimplementowano lokalnie 2026-10-29, bez publikacji workflow i pomiaru
zysku hosted. CI-002–CI-005 pozostają propozycjami. Akceptacja ADR przez właściciela:
brak; status pozostaje proposed. [Raport CI-001](../CI_001_PYTHON_CACHE.md).
CI-001–CI-005 to lokalne identyfikatory propozycji planu, nie numery GitHub Issues.

## 1. Kontekst i problem

TRIPSE już buduje obrazy przez Cloud Build, publikuje je do Artifact Registry
z niezmiennymi tagami SHA i wdraża po digest. CI i chroniona promocja DEV → PROD
mają własne dowody i granice zaufania. Potrzebny jest plan optymalizacji,
a nie drugi rejestr i alternatywny deploy omijający istniejącą weryfikację.

## 2. Rozważane alternatywy

- Utrzymać Cloud Build i najpierw zmierzyć/cache'ować Python CI — rekomendowane.
- Buildx z GHA cache jako nieuprzywilejowany benchmark — opcja do porównania.
- Zastąpić Cloud Build przez Buildx — wymaga osobnej decyzji i równoważnej
  weryfikacji źródła/proweniencji, obecnie niezatwierdzone.
- Nowy rejestr lub Nexus — brak wykazanego uzasadnienia.
- Mutable registry cache w obecnym rejestrze wydań — niezgodne z immutable tags.

## 3. Decyzja

Proponujemy zachować istniejący Artifact Registry, niezmienność tagów, pełny SHA,
digest i ścieżkę promocji. Rozpocząć od pomiarów/cache pip; Buildx ocenić osobno
bez dostępu do chmury. Nie zmieniać ADR-0012, IAP, środowisk ani reguł dowodu
wydania jako efektu ubocznego optymalizacji.

## 4. Uzasadnienie

**Udokumentowane:** `source_files()`, `build()`, `digest()` w koordynatorze oraz
[zapis wydania](../RELEASE_2026_10_28.md). **Wniosek:** optymalizacja istniejącej
ścieżki ma mniejsze ryzyko niż budowa równoległej. **Niepotwierdzone:** obecny
profil czasów/kosztów live i korzyść z Buildx — potrzebne pomiary.

## 5. Konsekwencje pozytywne i negatywne

Zachowujemy izolację DEV/PROD, rollback i proweniencję. Nie powstaje nowa usługa
do utrzymania. Ceną jest konieczność porównania builderów i jawnego rozwiązania
retencji niezmiennie otagowanych obrazów; nie deklarujemy oszczędności bez danych.

## 6. Dług techniczny i ograniczenia

Cache pip dodany lokalnie; hosted cold/warm pozostaje niezweryfikowany.
Niezmierzony profil buildu i storage,
nieprzypięty digest bazowego obrazu oraz ewentualny hardening UID wymagają
oddzielnych checkpointów. Nie wolno wyłączyć weryfikacji Cloud Build, aby przyjąć
obraz z innego buildera. Historia wydania nie jest nową inspekcją live.

## 7. Wpływ na kosztorys

Pakiety prac: pomiar/cache, kontener, benchmark, audyt rejestru/retencji i odbiór
koordynatora. Koszty obejmują CI, Cloud Build i storage; brak zmierzonych kwot/godzin.
Zasady: [estymacje](../tracking/estimates.md).

## 8. Powiązane taski, PR, commity i dokumenty

[Plan CI-001–CI-005](../ARTIFACT_REGISTRY_CICD_PLAN.md),
[ADR-0012](0012-github-actions-delivery.md), [CI/CD](../GITHUB_CICD.md).
Baza audytu: `ae8c051513f0300d19a16d7ce7b96499b6f388cd` na `dev`.
Nie ma nowego PR ani dowodu akceptacji właściciela. Nie wykonano wdrożenia.

## 9. Warunki ponownego rozważenia decyzji

Wykazana przewaga buildera przy tej samej proweniencji/bezpieczeństwie,
nowe wymaganie retencji lub istotny koszt storage, wymagane attestations albo
zmiana środowisk — wyłącznie po pomiarach i osobnej decyzji.

## Historia zmian

| Data | Autor | Zmiana i uzasadnienie | Powiązanie |
|---|---|---|---|
| 2026-10-28 | Codex | Propozycja rozwoju istniejącego rejestru, bez zmian operacyjnych | CI-001–CI-005 |
| 2026-10-29 | Codex | Lokalna implementacja CI-001 i baseline; hosted i zysk niezweryfikowane, status proposed zachowany | CI-001 |
