# Zasady przygotowania kosztorysu TRIPSE

To mapa przyszłych prac, nie oferta cenowa ani potwierdzony budżet.
Nie ma dowodów pozwalających wpisać rzeczywiste godziny lub koszty historyczne;
dlatego odpowiednie pola [worklogu](worklog.csv) pozostają puste.

## Co rozdzielamy

- **Historia wykonania:** kod, dokumentacja i commity potwierdzają zakres,
  lecz nie nakład czasu ani koszt usług.
- **Estymacja prac:** jawnie określony zakres przyszły, założenia, zależności,
  ryzyka i źródło szacunku; dopiero po ustaleniu tych danych można wpisać godziny.
- **Koszt zewnętrzny:** osobno planowane opłaty i rzeczywisty rachunek.
  `external_cost_pln` worklogu jest tylko rzeczywistym, potwierdzonym kosztem.
- **Cena dla klienta:** wymaga uzgodnionego zakresu i zasad rozliczenia; nie wynika
  automatycznie z worklogu, liczby commitów ani hipotetycznej stawki.

Orientacyjne okna w [BUILD_DAY.md](../BUILD_DAY.md) nie są nowym kosztorysem.
Nie interpretujemy braku centralnej bazy, chmury lub logowania jako zerowego
kosztu przyszłego wdrożenia ani nie deklarujemy kwot „zaoszczędzonych” w demo.

## Przyszłe obszary kosztowe

| ID | Zakres do rozpoznania/wyceny | Zależności i potrzebne dane | ADR / dług |
|---|---|---|---|
| COST-01 | Centralny zapis, migracje JSON, konflikty, historia, backup/restore i retencja | Liczba autorów, rekordów, wersji i assetów; wymagane odtwarzanie; wybór magazynu | [ADR-0002](../adr/0002-local-json-storage.md), [ADR-0003](../adr/0003-document-snapshots.md); DEBT-01/02 |
| COST-02 | Logowanie, role, uprawnienia do dokumentu, audyt, bezpieczne udostępnianie i przegląd poufności | Odbiorcy i klasy danych; dostawca tożsamości; polityka dostępu i retencji | [ADR-0005](../adr/0005-local-only-studio.md), [ADR-0003](../adr/0003-document-snapshots.md); DEBT-03/06 |
| COST-03 | Branding, logo/fonty, QA składu, serwerowy PDF, archiwum, formaty graficzne | Zatwierdzone materiały i licencje; formaty, języki, liczba eksportów, odtwarzalność | [ADR-0004](../adr/0004-controlled-html-browser-pdf.md), [ADR-0006](../adr/0006-template-registry-shared-components.md); DEBT-02/04 |
| COST-04 | Biblioteka obrazów, metadane praw, retencja, usuwanie, magazyn obiektowy i transfer | Rozmiary/ilość zdjęć, źródła praw, zakres użycia, polityka usuwania | [ADR-0002](../adr/0002-local-json-storage.md), [ADR-0005](../adr/0005-local-only-studio.md); DEBT-05 |
| COST-05 | Adapter planera, dłuższe trasy, integracje live, idempotencja, kolejka i limity płatnych wywołań | Zatwierdzony kontrakt danych, wolumen zadań, polityka retry, dostawcy i testowe konta | [ADR-0001](../adr/0001-modular-fastapi.md), [ADR-0007](../adr/0007-sqlite-single-worker.md); DEBT-07/10/11 |
| COST-06 | Docelowe wdrożenie, konfiguracja sieci i sekretów, monitoring, CI, utrzymanie | Środowiska, SLA, operator, backup, dostępność; decyzja o hostingu | [ADR-0001](../adr/0001-modular-fastapi.md), [ADR-0005](../adr/0005-local-only-studio.md), [ADR-0007](../adr/0007-sqlite-single-worker.md); DEBT-03/10 |
| COST-07 | Kolejne generatory, reguły biznesowe, akceptacja treści, dokumentacja i testy regresyjne | Priorytety pięciu ID katalogowych, pola minimalne, zakres workflow, właściciele treści | [ADR-0003](../adr/0003-document-snapshots.md), [ADR-0006](../adr/0006-template-registry-shared-components.md); DEBT-06/08/09 |

To pakiety rozpoznania, nie zatwierdzony backlog. Części zakresu się stykają:
np. archiwizacja wymaga magazynu i renderera. Przy wycenie przypisz każdą
czynność do jednego pakietu, a zależności wskaż odnośnikiem, zamiast podwójnego naliczenia.
Opis długu: [audyt](repository-audit.md).

## Dane wejściowe przed podaniem liczb

1. Uzgodniony zakres dostawy, kryteria akceptacji, wyłączenia i priorytety.
2. Liczba użytkowników równoczesnych, wycieczek, eksportów i rozmiar danych.
3. Poufność, retencja, wymagania backupów, historii i dystrybucji dokumentów.
4. Zatwierdzony branding, legalne zasoby i odpowiedzialność za ceny/treści.
5. Wybór infrastruktury i integracji; aktualne warunki/cenniki dostawców,
   sprawdzone dopiero w momencie estymacji z datą oraz źródłem.
6. Uzgodniona metoda/stawka rozliczenia, sposób opisu niepewności i zakres utrzymania.

W zleceniu estymacji zapisz dla pakietu: task_id, zakres, założenia, zależności,
ryzyka, estymującego, datę, metodę i dowód. Jeśli używasz przedziału, nie wpisuj
arbitralnej średniej do estimated_hours; zachowaj przedział i założenia w dokumencie
estymacji, a pole CSV pozostaw puste do uzgodnienia konkretnej podstawy.

Rzeczywiste godziny pochodzą z ewidencji. Rzeczywiste opłaty API/hostingu z rachunku
lub raportu rozliczeń, z zakresem okresu i uniknięciem podwójnego wpisu. Przy PLN
przeliczanym z waluty udokumentuj oryginalną kwotę/walutę, datę i podstawę kursu;
nie publikuj w repo wrażliwych rachunków. Prognoz nie wpisuj jako kosztów rzeczywistych.

## Czego nie potwierdzono

Brak wiarygodnego podziału historycznego czasu na DEMO-01–03, rachunków usług,
decyzji o centralnej bazie, wyboru hostingu pełnej produkcji, wymaganego SLA i zatwierdzonego brandingu.
README i instrukcje zawierają wyniki lokalnych testów; nie dowodzą opłacenia
infrastruktury, działania realnego WhatsApp ani produkcyjnej akceptacji rozwiązania.

## CLOUD-01 — przygotowanie infrastruktury demo

[ADR-0009](../adr/0009-cloud-run-readonly-preview.md) i [instrukcja](../DEPLOY_GCP.md)
przygotowują ręczny Cloud Run DEV/PROD bez uruchomienia zasobów. Nie ma kosztów
rzeczywistych ani pomiaru pracy. COST-06 obejmuje przyszły bootstrap/IAM, QA live,
utrzymanie Run/Build/Artifact Registry/Storage/Logging, alerty i retencję.
Migracja zapisu oraz kolejki, autoryzacja i sekrety należą do powiązanych pakietów
danych/bezpieczeństwa/integracji; nie są ukończonym zakresem tego zadania.
Do kalkulacji potrzebne są region, ruch, rozmiar/liczba obrazów i buildów,
retencja logów, polityki organizacji i aktualne cenniki. Nie zakładamy kosztu 0
na podstawie min-instances=0 ani nie wpisujemy prognozy jako rachunku.
