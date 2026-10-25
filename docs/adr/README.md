# Architecture Decision Records

Lekki rejestr decyzji istotnych dla granic modułów, danych, bezpieczeństwa,
integracji, wdrożenia i kosztów utrzymania. ADR opisuje wybór i jego skutki;
task opisuje pracę, a [worklog](../tracking/worklog.csv) jej udokumentowany przebieg.

## Rejestr

| ID | Decyzja | Status | Stan implementacji |
|---|---|---|---|
| [ADR-0001](0001-modular-fastapi.md) | Document Studio jako izolowany moduł istniejącego FastAPI | proposed | Wdrożone |
| [ADR-0002](0002-local-json-storage.md) | Lokalny JSON, fixture'y i trwały katalog danych | proposed | Wdrożone |
| [ADR-0003](0003-document-snapshots.md) | Wspólne dane podróży, osobne snapshoty i pola dokumentu | proposed | Wdrożone |
| [ADR-0004](0004-controlled-html-browser-pdf.md) | Kontrolowane HTML/CSS i druk do PDF w przeglądarce | proposed | Wdrożone |
| [ADR-0005](0005-local-only-studio.md) | Lokalny dostęp do studia bez logowania w demo | proposed | Wdrożone |
| [ADR-0006](0006-template-registry-shared-components.md) | Wspólny rejestr szablonów, komponenty i tokeny | proposed | Wdrożone częściowo: 3 generatory, 8 ID |
| [ADR-0007](0007-sqlite-single-worker.md) | Kolejka planera w SQLite i jeden osobny worker | proposed | Wdrożone |

Wszystkie powyższe ADR-y sporządzono retrospektywnie 25.10.2026. Kod potwierdza
implementację, ale dostępne repozytorium nie zawiera jednoznacznej akceptacji
tych ADR-ów przez właściciela. **`proposed` nie oznacza tu „jeszcze nie wdrożono”.**
Nie potwierdzamy za właściciela historycznej motywacji ani docelowego zastosowania
produkcyjnego. Zakres dowodów: [audyt bieżącej gałęzi](../tracking/repository-audit.md).

## Kiedy tworzyć ADR

Twórz ADR, gdy wybór zmienia granice modułów, kontrakt danych, magazyn, zasady
dostępu, sposób eksportu, istotną integrację albo profil kosztów/utrzymania.
Nie twórz osobnego ADR dla poprawki tekstu, stylu przycisku lub zwykłego naprawienia błędu.
Powiązane aspekty jednej decyzji można połączyć, jak FastAPI i izolację modułu w ADR-0001.

## Numeracja i metadane

- Następny wolny numer: **ADR-0008**. Sprawdź rejestr i pliki przed nadaniem numeru;
  po dodaniu wpisu zaktualizuj tę wskazówkę. Nie używaj ponownie opublikowanego numeru.
- Plik: `0008-short-decision-name.md`; nagłówek i YAML: `ADR-0008`.
- Skopiuj [szablon](template.md). Wypełnij wszystkie dziewięć sekcji.
- YAML: `id`, `title`, `status`, `date`, `author`, `area`, `related_tasks`,
  `related_prs`, `supersedes`. Data ISO `YYYY-MM-DD`; trzy ostatnie pola są listami.
- `date` to data sporządzenia propozycji, nie odtworzona data historycznej decyzji.
  `author` oznacza autora zapisu; decydenta i dowód akceptacji podaj w treści.
- Nieznane taski/PR zapisuj jako `[]`, z wyjaśnieniem braku danych. Nie przypisuj
  agentowi autorstwa historycznej decyzji ani nie twórz fikcyjnego numeru PR.

## Statusy i zmiany

| Status | Znaczenie |
|---|---|
| `proposed` | Propozycja; także retrospektywny opis wdrożenia bez potwierdzenia właściciela |
| `accepted` | Właściciel lub jawnie upoważniony decydent zaakceptował wybór; dowód w sekcji 8 |
| `deprecated` | Decyzja wycofana bez zastąpienia innym ADR; odnotowany powód i data |
| `superseded` | Decyzja zastąpiona wskazanym nowym ADR |

Typowy przebieg: `proposed` → `accepted` → `deprecated` lub `superseded`.
Nie wolno uznawać commitu, udanego testu lub samego wdrożenia za dowód akceptacji.
Przy potwierdzeniu retrospektywnym wpisz, czy akceptacja dotyczy tylko demo,
czy także przyszłej produkcji. Nie trzeba wstrzymywać autoryzowanego zadania
dokumentacyjnego, aby zebrać te potwierdzenia; zapis pozostaje `proposed`.

Zaakceptowanej decyzji nie nadpisuj po cichu. Korekty dowodów i literówek są
dopuszczalne z uzasadnieniem oraz wpisem w historii zmian. Zmiana samego wyboru
powinna zwykle dostać nowy numer: nowy ADR ma `supersedes: [ADR-xxxx]`, stary
otrzymuje `superseded` i link zwrotny. Zachowaj oba pliki oraz historię zmian
(data, autor, zakres, powód, task/PR/commit). Dotychczasowe fakty nie znikają.

## Dowody i niepewność

Oddzielaj w treści **fakt z kodu**, **uzasadnienie udokumentowane**, **wniosek**
i **uzasadnienie niepotwierdzone**. Linkuj istniejące pliki oraz nazwy symboli.
Przy historii Git podawaj prawdziwy hash i granice wnioskowania. Alternatywy
odtworzone dziś oznacz jako retrospektywne, bez twierdzenia, że autor je porównywał.
Wpływ na kosztorys opisuj jakościowo lub przez pakiety prac; nie zgaduj godzin,
oszczędności, cen API ani rachunków. Zasady liczb: [estimates.md](../tracking/estimates.md).

## Workflow agentów

### Przed implementacją

1. Przeczytaj odpowiednie ADR-y i [audyt](../tracking/repository-audit.md), następnie
   sprawdź aktualny kod; audit jest snapshotem, nie automatycznie aktualnym stanem.
2. Sprawdź, czy zadanie narusza zaakceptowane decyzje lub granice wdrożonego demo.
   Retrospektywne `proposed` informują o stanie zastanym i nie zezwalają na jego
   samowolną zmianę. Zakres zlecony przez użytkownika pozostaje wiążący.
3. Gdy potrzebna jest nowa istotna decyzja, przygotuj `proposed` z alternatywami,
   konsekwencjami, brakami danych i wpływem na wycenę. Nie zmieniaj sam statusu na `accepted`.

### Podczas implementacji

1. Przestrzegaj zaakceptowanych decyzji i uzgodnionego zakresu zadania.
2. Uzupełniaj rzeczywiste powiązania task/PR/commit; jawnie opisuj odstępstwa.
3. Nie przedstawiaj roadmapy ani wpisu katalogu szablonów jako działającej funkcji.

### Po implementacji

1. Sprawdź, czy pojawiła się nowa decyzja architektoniczna. Uzupełnij dowody ADR
   lub zaproponuj nowy; przy zastąpieniu decyzji zachowaj stary wpis.
2. Zaktualizuj [worklog](../tracking/README.md) wyłącznie faktami. Nieznane godziny
   i koszty pozostaw puste; zakończenie tasku nie oznacza czasu równego zero.
3. Zidentyfikuj nowy dług techniczny, ograniczenia walidacji i koszty dalszego rozwoju.
   Uzupełnij rejestr długu w audycie lub powiązany task oraz mapę obszarów kosztowych.
4. Sprawdź YAML, numerację, odnośniki i zgodność z bieżącą gałęzią; do raportu
   dopisz zakres wykonanych kontroli oraz testy, których nie uruchomiono.

Sam ten standard nie wdraża automatycznej walidacji CI ani wieloosobowego workflow.

## Historia zmian standardu

| Data | Autor | Zmiana | Podstawa |
|---|---|---|---|
| 2026-10-25 | Codex | Utworzenie standardu i rejestru retrospektywnego | ADR-SETUP-01, zlecenie użytkownika |
