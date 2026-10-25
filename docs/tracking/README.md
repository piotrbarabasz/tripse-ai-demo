# Rejestr prac i podstawy kosztorysu

[Worklog CSV](worklog.csv) zapisuje fakty o pracach, [ADR](../adr/README.md)
uzasadnienia decyzji, a [estimates.md](estimates.md) zakres i zasady przyszłej wyceny.
Punkt odniesienia: [audyt master z 25.10.2026](repository-audit.md).

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
- `HUB-01` to lokalne ID zlecenia Hubu z 25.10.2026. Jego commit/PR pozostaje
  pusty do czasu faktycznego utworzenia; zakres i kontrole opisuje [HUB.md](../HUB.md).
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

`CLOUD-01` to lokalny identyfikator zlecenia z 2026-10-25: audyt wzorców,
przygotowanie Cloud Preview i ręcznych skryptów DEV/PROD. Ukończenie oznacza
przygotowanie i lokalną kontrolę, bez rzeczywistego wdrożenia do GCP.

Worklog nie jest fakturą ani zatwierdzonym kosztorysem klienta. Nie ma pomiaru
czasu, integracji billingowej ani automatycznego egzekwowania reguł w CI.
Puste kwoty i godziny w pierwszym wykazie są celowe, nie oznaczają prac bezpłatnych.
