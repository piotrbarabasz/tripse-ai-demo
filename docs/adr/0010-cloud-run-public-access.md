---
id: ADR-0010
title: "Publiczny Cloud Run przez wyłączenie kontroli IAM invokera"
status: proposed
date: 2026-10-25
author: "Codex — zapis propozycji"
area: "deployment, security"
related_tasks: [GCP-ACCESS-001]
related_prs: []
supersedes: []
---

# ADR-0010: Publiczny Cloud Run przez wyłączenie kontroli IAM invokera

Stan implementacji: kod i testy offline; bez zmian GCP. Uzupełnia ADR-0009
w zakresie mechanizmu publikacji; zachowuje jego granice runtime i promocji.
Status `proposed` zgodnie z workflow rejestru; brak odrębnej akceptacji ADR.

## 1. Kontekst i problem

**Zgłoszenie użytkownika:** projekt `tripse-ai` odrzuca nadanie `allUsers`
z komunikatem o niedozwolonym customer. **Fakt z kodu przed zmianą:** prywatny
deploy i smoke poprzedzały dodanie bindingu `roles/run.invoker` dla `allUsers`.
Nie weryfikowano polityk ani stanu projektu online w tym zadaniu.

## 2. Rozważane alternatywy

Binding `allUsers` kończył zgłoszony deployment błędem. Zmiana polityki
organizacji lub fallback IAM nie należą do zakresu. Usługa wyłącznie prywatna
pozostaje opcją `GCP_PUBLIC_ACCESS=false`. Dla publicznej konfiguracji wybrano
udokumentowane wyłączenie kontroli invokera, o ile organizacja je dopuszcza.

## 3. Decyzja

Zachować prywatny deploy z `--invoker-iam-check`, usuwanie zastanego standardowego
bindingu `allUsers` i private smoke wymagający tokenu. Dopiero po sukcesie użyć
`run services update --no-invoker-iam-check` i wykonać anonimowy smoke.
Nie dodawać `allUsers`. Przy błędzie publikacji lub publicznego smoke przywrócić
kontrolę IAM, potwierdzić private smoke i zakończyć błędem. Niepotwierdzone
przywrócenie prywatności raportować jawnie. Nie zmieniać polityk organizacji.
DEV/PROD pozostają osobne; obraz jest promowany przez SHA/digest bez rebuild.
Kontrakt konfiguracji, adapter Make i runtime `readonly_demo` pozostają zgodne.

## 4. Uzasadnienie

**Udokumentowane:** zadanie GCP-ACCESS-001 wymaga tej sekwencji.
[Google Cloud Run](https://docs.cloud.google.com/run/docs/authenticating/public)
opisuje tę metodę oraz ograniczenie `run.managed.requireInvokerIam`.
**Wniosek:** prywatna walidacja przed publikacją zachowuje dotychczasową granicę QA.
**Niepotwierdzone:** efektywne polityki projektu i wynik deploymentu live.

## 5. Konsekwencje pozytywne i negatywne

Publikacja nie wymaga publicznego principal w IAM. Organizacja nadal może
zabronić wyłączenia kontroli. Deployment powoduje krótką niedostępność publiczną;
błąd po aktualizacji obrazu nie cofa obrazu. Próba zamknięcia dostępu również
może zawieść, dlatego komunikat odróżnia potwierdzoną prywatność od braku dowodu.

## 6. Dług techniczny i ograniczenia

GCP-ACCESS-001: brak testów live polityk, uprawnień i propagacji zmiany dostępu;
wymagany odbiór operatora dla obu środowisk. Testy symulują granicę IAM offline.
Pozostałe ograniczenia ADR-0009 nadal obowiązują. Nie dodano automatycznego
retry ani obchodzenia polityk; samodzielny smoke pozostaje operacją odczytu.

## 7. Wpływ na kosztorys

Istniejący COST-06: QA live i polityki organizacji, utrzymanie Cloud Run oraz
diagnostyka. Dodatkowe wywołania kontroli dostępu przy błędach. Brak pomiarów
czasu i kosztów; nie wprowadzamy kwot. [Zasady](../tracking/estimates.md).

## 8. Powiązane taski, PR, commity i dokumenty

Task GCP-ACCESS-001: zlecenie użytkownika 2026-10-25. Brak PR i commitu tej zmiany.
Dowody: [deployment](../../scripts/gcp/deployment.py),
[regresje](../../tests/test_gcp_deployment.py), [instrukcja](../DEPLOY_GCP.md),
[ADR-0009](0009-cloud-run-readonly-preview.md), [worklog](../tracking/worklog.csv).
Nie utożsamiamy autoryzacji przygotowania kodu z akceptacją ADR lub wdrożeniem GCP.

## 9. Warunki ponownego rozważenia decyzji

Zmiana wymagań na prywatne dane, autoryzację użytkowników, ograniczony ingress,
inne zasady organizacji lub mechanizm publicznego dostępu Cloud Run.

## Historia zmian

| Data | Autor | Zmiana i uzasadnienie | Powiązanie |
|---|---|---|---|
| 2026-10-25 | Codex | Mechanizm publikacji zgodny z zakresem zadania; bez zmian GCP | GCP-ACCESS-001 |
