# Rejestr prac i podstawy kosztorysu

2026-10-31: [CI-007 DEV PR gate](../CI_007_DEV_PR_GATE.md) is a user-supplied task ID.
Local trigger/tests/docs work and real GitHub-hosted acceptance are tracked separately;
Definition of Done remains pending until a dev PR completes the existing CI pipeline
without deployment. No branch-protection setting or ADR approval is inferred.

2026-10-31: [ARCH-001](../architecture/README.md) records a documentation-only source
audit and proposed React migration. Stage IDs ARCH-001, FRONT-001, API-001, FRONT-002,
FRONT-003 and AI-001 are user-supplied task labels, not verified GitHub issue IDs.
Implementation/deployment and ADR acceptance remain separate gates.

ARCH-001 closure: the original 446-line blueprint is restored unchanged and its source
reconciliation is complete. See [crosswalk and open decisions](../architecture/reconciliation.md)
for blueprint DOCS-001/ADR-FE-001/FRONT-004/AUTO-001 labels versus commissioned stages.
The final closure row completes the earlier in_progress review; historical rows remain
dated observations. Future implementation and ADR approval are not marked complete.

2026-10-28 operational milestone: [DEV/PROD release](../RELEASE_2026_10_28.md)
is automatically accepted. Earlier worklog rows retain their dated observations.
The new row uses existing GITHUB-CICD-001 for the completed deployment milestone,
without adding an identifier, hours or costs. ADR approval, human login, restore
and real customer-data acceptance remain separate criteria.

[Worklog CSV](worklog.csv) zapisuje fakty o pracach, [ADR](../adr/README.md)
uzasadnienia decyzji, a [estimates.md](estimates.md) zakres i zasady przyszłej wyceny.
Punkt odniesienia: [audyt master z 25.10.2026](repository-audit.md).

2026-10-29: [CI-006 integration](../CI_006_INTEGRATION_ACCEPTANCE.md) reconciles
CI-001–CI-005 locally. Source patches/hashes and regression results are recorded;
hosted/cloud acceptance is a separate operator-gated phase, not completed here.

## Format worklogu

UTF-8, nagłówek obowiązkowy, separator przecinek, standardowe cytowanie CSV.
Wartości liczbowe: nieujemne liczby dziesiętne z kropką; brak danych to pusta
komórka, **nie zero**. Zera wolno wpisać wyłącznie, gdy ich wartość jest potwierdzona.
Daty w ISO `YYYY-MM-DD`, dla bieżących prac w strefie Europe/Warsaw.

| Kolumna | Zasada |
|---|---|
| date | Data aktywności/wpisu; dla historii tutaj data dowodowego commitu, co wyjaśniają notes |
| task_id | Istniejące ID zadania lub jawnie lokalna etykieta, bez udawania numeru issue |
| area | Moduł/obszar, np. document-studio, planner, documentation |
| activity | Konkretna wykonana czynność lub wyraźnie oznaczona przyszła praca |
| status | Jeden ze statusów poniżej |
| estimated_hours | Estymacja tej aktywności tylko z opisanym źródłem, zakresem i datą |
| actual_hours | Rzeczywisty czas wyłącznie z pomiaru/ewidencji; nie z dat commitów lub sesji AI |
| external_cost_pln | Potwierdzony rzeczywisty koszt zewnętrzny w PLN; identyfikator dowodu w notes |
| commit_or_pr | Rzeczywisty hash / numer i adres PR; puste, gdy nie istnieje lub brak potwierdzenia |
| adr_ids | ID rozdzielone średnikiem, np. ADR-0001;ADR-0002; muszą istnieć w rejestrze |
| notes | Pochodzenie danych, ograniczenia weryfikacji, brak czasu/kosztów i niepewności |

Statusy: `planned`, `in_progress`, `completed`, `blocked`, `cancelled`,
`documented_completed`. Ostatni oznacza wyłącznie retrospektywny wykaz oparty
na kodzie/dokumentacji, bez nowego testu odbiorowego. `completed` nie oznacza
akceptacji ADR, wdrożenia produkcyjnego ani rozliczenia finansowego.

## Retrospekcja i identyfikatory

- `DEMO-01`, `DEMO-02`, `DEMO-03` odnoszą się do etapów opisanych w instrukcjach
  studia; nie są numerami GitHub Issues. Wszystkie mają ten sam dowodowy commit
  `f9035e5`, więc nie wolno liczyć go trzy razy jako trzy osobne okresy pracy.
- `HIST-PLANNER-01`, `HIST-MOCK-01`, `HIST-SPEC-01`, `HIST-DATA-PATH-01` to
  lokalne etykiety utworzone w audycie do pogrupowania zakresu commitów.
- `ADR-SETUP-01` to lokalne ID zadania dokumentacyjnego z 25.10.2026.
  W HUB-01 uzupełniono jego dowodowy commit `c232670` na podstawie Git;
  nie rekonstruowano czasu pracy ani kosztów.
- `HUB-01` to lokalne ID zlecenia Hubu z 25.10.2026. Commit `4624760`
  uzupełniono w CLOUD-01 po sprawdzeniu Git; zakres opisuje [HUB.md](../HUB.md).
- `MAKE-001` to identyfikator zlecenia Unified Development Makefile z 25.10.2026.
  Interfejs do istniejących operacji nie wymagał nowego ADR. Zakres i kontrole:
  [MAKEFILE.md](../MAKEFILE.md). Commit CLOUD-01 `049f0cc` uzupełniono na podstawie
  dostępnej historii Git; nie odtwarzano godzin ani kosztów.
- Daty commitów dowodzą obecności artefaktów, nie dat ani długości wykonywania
  etapów. Dokumenty DEMO raportują weryfikację 24.10; commit jest z 25.10.
- Liczby z [BUILD_DAY.md](../BUILD_DAY.md) są historycznym orientacyjnym budżetem,
  nie rzeczywistymi godzinami i nie są przenoszone do actual_hours.

## Aktualizacja po zadaniu

1. Nadaj/odczytaj rzeczywiste ID. Gdy nie ma zewnętrznego trackera, ustanów jawne
   lokalne ID i opisz je tutaj lub w notes; nie zgaduj numerów PR.
2. Dodaj aktywność z jej datą, zakresem i statusem. Dla różnych aktywności można
   mieć kilka wierszy tego samego tasku; notes muszą pozwolić uniknąć podwójnego rozliczenia.
3. Dopisz istniejące ADR-y i dowód wykonania. Przed commitem pole commit_or_pr
   pozostaje puste; po jego utworzeniu uzupełnij je w następnej zmianie rejestru.
4. Uzupełnij liczby tylko ze źródła: pomiar czasu, zatwierdzona estymacja,
   rachunek/raport rozliczeń. Zapisz w notes identyfikator, datę i zakres dowodu,
   bez sekretów, danych osobowych i treści dokumentów klienta.
5. Braki zostaw puste i opisz. Nie odtwarzaj godzin z liczby commitów, rozmiaru
   diffu, czasu odpowiedzi agenta ani „jednego dnia” w tytule planu.
6. Zaktualizuj nowe decyzje i dług zgodnie z [workflow ADR](../adr/README.md).
   Nowe obszary kosztowe dopisz do estimates.md, bez nazywania planu wykonanym zakresem.
7. Sprawdź CSV, ID, linki i Git diff. Nie wprowadzaj prawdziwych danych operacyjnych
   ani rachunków z danymi wrażliwymi do publicznego repozytorium.

Nie nadpisuj po cichu udokumentowanego czasu/kosztu. Korektę i jej powód zapisz
w notes, zachowując Git diff i wskazanie nowego dowodu; nie dodawaj ponownie
tej samej płatności jako nowego wydatku.

## Granice

`GCP-ACCESS-001` to identyfikator zlecenia użytkownika z 2026-10-25:
zmiana publikacji DEV/PROD na `--no-invoker-iam-check`, obsługa błędów,
regresje offline i dokumentacja. Nie oznacza wykonania deploymentu GCP.
Decyzja i ograniczenia: [ADR-0010](../adr/0010-cloud-run-public-access.md).

`CLOUD-01` to lokalny identyfikator zlecenia z 2026-10-25: audyt wzorców,
przygotowanie Cloud Preview i ręcznych skryptów DEV/PROD. Ukończenie oznacza
przygotowanie i lokalną kontrolę, bez rzeczywistego wdrożenia do GCP.

Worklog nie jest fakturą ani zatwierdzonym kosztorysem klienta. Nie ma pomiaru
czasu, integracji billingowej ani automatycznego egzekwowania reguł w CI.
Puste kwoty i godziny w pierwszym wykazie są celowe, nie oznaczają prac bezpłatnych.

`TRIPSE-CICD-PLAN-001` jest lokalną etykietą zadania dokumentacyjnego
[planu Artifact Registry/CI-CD](../ARTIFACT_REGISTRY_CICD_PLAN.md). Nie oznacza
implementacji CI-001–CI-005 ani nowego wydania; godziny i koszty nie zostały zmierzone.
