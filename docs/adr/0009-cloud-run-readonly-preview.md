---
id: ADR-0009
title: "Cloud Run DEV/PROD jako bezstanowy podgląd tylko do odczytu"
status: superseded
date: 2026-10-25
author: "Codex — zapis propozycji"
area: "deployment, security, storage"
related_tasks: [CLOUD-01]
related_prs: []
supersedes: []
---

# ADR-0009: Cloud Run DEV/PROD jako bezstanowy podgląd tylko do odczytu

2026-10-26: superseded by [ADR-0011](0011-authenticated-cloud-demo.md) for the
restriction to preview-only Cloud Run. The readonly_demo mode remains supported.
Historical reasoning and evidence below are preserved; no deployment is implied.

Stan implementacji: przygotowano kod/skrypty; nie wykonano wdrożenia GCP.
Akceptacja właściciela ADR: brak odrębnego potwierdzenia. `proposed` nie blokuje
zleconego przygotowania; nie oznacza akceptacji architektury pełnej produkcji.

## 1. Kontekst i problem

**Fakt:** lokalne demo używa JSON/uploadów i SQLite z osobnym workerem.
Cloud Run nie zapewnia trwałości lokalnego dysku ani współdzielenia kolejki.
**Wymaganie zlecenia CLOUD-01:** ręczny, tani w utrzymaniu model dwóch usług,
bez centralnej bazy, bez anonimowego zapisu i kosztownych wywołań.

## 2. Rozważane alternatywy

Pełny lokalny runtime na publicznym Cloud Run naraża kolejkę i dane bez trwałości.
VM z dyskiem zachowałaby lokalny model, ale wymaga innego utrzymania.
Docelowa baza/kolejka i auth przekraczają zakres. Wybrano ograniczony bezstanowy
podgląd Cloud Run; porównanie wykonano teraz, nie przypisuje historii autorom demo.

## 3. Decyzja

Jeden projekt/region/Artifact Registry/obraz SHA, osobne usługi DEV i PROD oraz
konta runtime, min 0 i ograniczony max. PROD promuje digest przetestowany w DEV
bez rebuild. PowerShell + testowalny kontrakt Python, dwa ignorowane pliki env,
jawna lista runtime vars. Brak sekretów w tym trybie; przyszłe integracje wymagają
referencji Secret Manager i osobnej analizy dostępu.

`readonly_demo` rejestruje wyłącznie fixture preview i kodowe assety. Nie tworzy
repozytoriów JSON/SQLite, zadań ani uploadów. Edycja, pilot i WhatsApp są wyłączone
na backendzie. Cloud Run z błędną konfiguracją odmawia startu. Lokalne ADR-0002,
0005, 0007 i 0008 zachowują zakres; nie są zastępowane tym wpisem.

## 4. Uzasadnienie

**Udokumentowane:** treść zlecenia CLOUD-01 oraz kontrakt i ograniczenia
w [DEPLOY_GCP](../DEPLOY_GCP.md). **Wniosek:** fixture-only pozwala zaprezentować
część produktu bez pozornego przeniesienia lokalnej trwałości do chmury.
**Niepotwierdzone:** docelowe SLA, skala, budżet i akceptacja granicy IAM jednego
projektu. Nie twierdzimy, że brak storage spełni wymagania pełnej produkcji.

## 5. Konsekwencje pozytywne i negatywne

Powtarzalna promocja obrazu, brak providerów i anonimowego zapisu, zachowanie
lokalnego demo. Kosztem jest ograniczony publiczny zakres oraz osobny zestaw
tras do utrzymania. Wspólny projekt nadal współdzieli billing i uprawnienia
administracyjne; oddzielne usługi nie zastępują pełnej izolacji organizacyjnej.

## 6. Dług techniczny i ograniczenia

Brak live GCP QA, auth użytkowników, trwałości i kolejki w chmurze, automatycznych
skanów obrazu/podpisów, rate limiting i monitoringu. Rola buildera jest projektowa;
przyszłe zawężenie wymaga analizy staging/logów. Kontrola wzorców sekretów nie
rozpoznaje wszystkich możliwych danych wrażliwych. Każdy fixture nadal wymaga review.
Rollback zmienia obraz z bieżącą konfiguracją, nie odtwarza historycznego IAM/env.

## 7. Wpływ na kosztorys

Pakiety: bootstrap/IAM i QA live; utrzymanie Cloud Run/Build/AR/logów;
storage/backup/migracja; autoryzacja; kolejka/worker; sekrety i limity providerów;
obserwowalność i ochrona przed nadużyciami. Min 0 ogranicza bezczynność, nie
gwarantuje kosztu 0. Brak danych do godzin lub rachunków. Zobacz
[estimates](../tracking/estimates.md).

## 8. Powiązane taski, PR, commity i dokumenty

Task lokalny `CLOUD-01`, zlecenie użytkownika 2026-10-25. Brak PR/commitu tej
zmiany w chwili zapisu. Zastany TRIPSE HEAD `462476001b6c3dac60ad15333631726729ad422c`.
Dowody: [audyt źródeł](../DEPLOY_GCP_AUDIT.md),
[runtime](../../app/cloud_preview.py), [wybór aplikacji](../../app/main.py),
[kontrakt](../../scripts/gcp/deployment_contract.py),
[skrypty](../../scripts/gcp/deployment.py), [testy](../../tests/test_cloud_preview.py).
Brak odrębnego dowodu akceptacji właściciela ADR i brak dowodu wdrożenia GCP.

## 9. Warunki ponownego rozważenia decyzji

Wymaganie zapisu, danych rzeczywistych, pilota, generowania live lub WhatsApp
w chmurze; rozdzielenie uprawnień/billingu klientów; SLA, wzrost ruchu albo
ograniczenia organizacji wobec anonimowego dostępu. Najpierw nowy ADR dla auth,
storage i kolejki; samo włączenie lokalnych routerów nie realizuje migracji.

## Historia zmian

| Data | Autor | Zmiana i uzasadnienie | Powiązanie |
|---|---|---|---|
| 2026-10-25 | Codex | Propozycja ograniczonego Cloud Preview i ręcznego deploymentu | CLOUD-01 |
| 2026-10-26 | Codex | Superseded preview-only restriction by ADR-0011; preserve historical body and public preview | CLOUD-PARITY-001 |
