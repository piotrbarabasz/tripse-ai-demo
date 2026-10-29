# TRIPSE Document Studio — referencja treści szablonów (Ground Truth)

> **Plik docelowy w repozytorium:** `docs/document-system/general/template-content-ground-truth.md`  
> **Status:** `DRAFT / DO WALIDACJI Z TRIPSE`  
> **Data opracowania:** 2026-10-28  
> **Zakres:** treść i struktura 8 typów dokumentów (4 oferty, 3 materiały pilota, 1 marketing z 2 wariantami).  
> **Przeznaczenie:** stały punkt odniesienia do kolejnych promptów, przeglądów UX, implementacji szablonów i testów akceptacyjnych.

## 0. Jak używać tego pliku

Ten dokument określa **jakie informacje i sekcje powinny występować** w poszczególnych rodzajach dokumentów TRIPSE. Nie jest projektem interfejsu, gotowym dokumentem dla klienta ani potwierdzeniem warunków handlowych.

### Źródło informacji a rekomendacja

Przy opisach stosujemy oznaczenia:

- **[MATERIAŁ]** — element bezpośrednio widoczny w przesłanych wzorach TRIPSE; dotyczy *struktury*, nie wiarygodności każdej konkretnej danej.
- **[SPECYFIKACJA]** — wymóg lub przyjęta zasada opisana już w `docs/document-system/` w repozytorium.
- **[PROPOZYCJA]** — rozszerzenie rekomendowane do przyszłego szablonu; **nie jest potwierdzonym wymaganiem biznesowym TRIPSE**.
- **[DO UZGODNIENIA]** — wymaga decyzji Adriana / TRIPSE, zanim stanie się obowiązkowym polem, regułą publikacji lub zachowaniem aplikacji.

Znaczenie priorytetów: **MUST** = konieczne w finalnym dokumencie danego typu, gdy ma zastosowanie; **SHOULD** = oczekiwany standard z możliwością świadomego odstępstwa; **MAY** = opcjonalne. **Wersja robocza może być zapisana z brakami**, które należy pokazać w walidacji. Nie wolno utożsamiać `MUST` z wymogiem wypełnienia pola przed zapisaniem draftu.

### Relacja do innych dokumentów repozytorium

- Ten plik jest **referencją zawartości i materiałowych przykładów**, czytaną przy każdym zadaniu dotyczącym schematów dokumentów.
- `general/template-catalog.md` definiuje stabilne identyfikatory i typy.
- `templates/offers/*.md`, `templates/pilots/*.md`, `templates/marketing/collections.md` zawierają specyfikacje poszczególnych szablonów.
- `system-data/template-fields.md` i `system-data/content-validation.md` pozostają źródłem wymogów walidacyjnych, poufności i kompletności. Bieżące modele/API należy potwierdzać w kodzie.
- `design/*` definiuje wygląd, assety i layout; nie należy wnioskować z przesłanych plakatów o zatwierdzonym brand booku.
- Jeśli referencja, specyfikacje per-szablon i bieżący kod są rozbieżne: **wypisz różnicę**, wskaż źródło i uzyskaj decyzję, zamiast po cichu nadpisywać kontrakt.

## 1. Baza źródłowa

| ID | Materiał dostarczony przez użytkownika | Co rzeczywiście wspiera | Granica interpretacji |
|---|---|---|---|
| SRC-01 | `WZÓR PODSTAWOWEJ ROZPISKI 04-13.08 Road Trip` (5 str.) | Metryka wyjazdu, uczestnicy/podgrupy, loty, noclegi, rezerwacje, kontakty, godziny atrakcji, dzienne notatki i sprawy otwarte | Jest to **wewnętrzny** materiał operacyjny; nie przenosić danych osobowych, numerów rezerwacji ani PIN-ów do publicznych wzorów |
| SRC-02 | `Kanada - program / plan wyprawy` (16 str.) | Zbiorcza tabela 15 dni; godziny, przejazdy, kilometry samochodem/pieszo, strefy czasowe, wschody/zachody słońca, trekkingi, promy, noclegi, opcje | To plan operacyjny, **nie gotowy wzór wyceny** ani potwierdzenie wykonalności wszystkich godzin |
| SRC-03 | `Kanada_USA_ciekawostki_atrakcje_Dzien_3-15` (39 str.) | Powtarzalne bloki merytoryczne dla dni 3–15: atrakcje, fakty, wspólny kontekst, historia/geologia/przyroda, obserwacje, historie, źródła | Konkretne twierdzenia wymagają osobnej weryfikacji; źródło inspiruje strukturę, nie automatyczną akceptację faktów |
| SRC-04 | Grafika marketingowa TRIPSE: „Pilotażowe Nowości 2027” i „Wyprawy Górskie” | Układ kart wyjazdów, terminy, piloci, zdjęcia, statusy, hasła; drugi wariant z motywem, prowadzącym i rozszerzeniami | Nie jest księgą identyfikacji wizualnej; nie dowodzi praw do fotografii ani zatwierdzenia terminów |

**Nie dołączać do tego pliku surowych danych wrażliwych** występujących w SRC-01: imion i nazwisk uczestników, numerów telefonów, identyfikatorów rezerwacji, kodów dostępu/PIN ani szczegółów pozwalających odtworzyć rezerwacje. Źródłowe PDF-y i grafika nie muszą być kopiowane do publicznego repozytorium. Przy ewentualnym dodawaniu materiałów demonstracyjnych stosować dane syntetyczne.

### Mapa pokrycia źródłowego

- `offer.private`, `offer.self_guide`: **pośrednio** oparte na trasach SRC-01/SRC-02; sekcje handlowe są propozycją / dotychczasową specyfikacją.
- `offer.school`, `offer.incentive`: **brak osobnych przykładów** w załącznikach; to proponowane struktury, wspierane istniejącymi specyfikacjami repozytorium.
- `pilot.basic`: **bezpośrednio** SRC-01.
- `pilot.advanced`: **bezpośrednio** SRC-02, rozszerzenie zawartości `pilot.basic` zgodnie ze specyfikacją.
- `pilot.knowledge`: **bezpośrednio** SRC-03.
- `marketing.collection`: **bezpośrednio** SRC-04, osobno dla `new_trips` i `theme_collection`.

## 2. Wspólna zasada domenowa

**Jedna wycieczka (`Trip`) może zasilać wiele dokumentów.** Program źródłowy obejmuje kierunki, dni, atrakcje i dane trasy. Dokument ma własny snapshot i własne uzupełnienia. Późniejsza zmiana wycieczki nie powinna bez ostrzeżenia zmieniać już zapisanego dokumentu. Kampania (`Campaign`) łączy kilka wycieczek i zasila `marketing.collection`.

Nie mieszać następujących pojęć:

1. **Rodzaj dokumentu** — np. `offer.self_guide`.
2. **Kategoria wycieczki** — np. `self_guide`; służy m.in. filtrowaniu, a wycieczka może mieć wiele kategorii.
3. **Wariant marketingowy** — `new_trips` lub `theme_collection`.
4. **Pochodzenie danych** — business/demo/synthetic_test/unknown; to nie jest dowód potwierdzenia.
5. **Status dokumentu i walidacja** — zapisany/gotowy/zaakceptowany/bez błędów to nie to samo.

### Macierz typów i poufności

| Typ | ID | Odbiorca | Zasadniczy cel | Poufność wg specyfikacji |
|---|---|---|---|---|
| Oferta indywidualna | `offer.private` | klient | sprzedaż dopasowanej podróży | `client` |
| Self-Guide | `offer.self_guide` | klient | program samodzielnej podróży | `client` |
| Szkolna | `offer.school` | szkoła / organizator | edukacja i organizacja | `client` |
| Incentive | `offer.incentive` | firma | doświadczenie grupowe i wydarzenie | `client` |
| Rozpiska podstawowa | `pilot.basic` | pilot / organizator | szybki dostęp do operacji | `internal_restricted` |
| Rozpiska zaawansowana | `pilot.advanced` | pilot / organizator | godzinowa i trasowa logistyka | `internal_restricted` |
| Materiały merytoryczne | `pilot.knowledge` | pilot | fakty i narracja do prowadzenia grupy | `internal` |
| Marketing | `marketing.collection` | publiczny odbiorca | promocja kolekcji wyjazdów | `public` |

Poufność jest regułą specyfikacji; aktualne mechanizmy egzekwowania w kodzie należy weryfikować dla każdej zmiany.

---

## 3. Oferty klientowskie — cztery typy

### 3.1. `offer.private` — oferta indywidualna / prywatna

**Przykład tytułu (syntetyczny):** „Islandia — prywatna wyprawa 10 dni”.

**Zalecana kolejność i zawartość:**

1. **Okładka — SHOULD** [SPECYFIKACJA]: logo TRIPSE, tytuł, kierunek, termin lub informacja „do ustalenia”, długość i legalnie użyta fotografia albo zaakceptowany wariant bez niej.
2. **Podsumowanie podróży — MUST dla finalnej oferty** [SPECYFIKACJA]: odwiedzane regiony, liczba dni, charakter wyjazdu, przewidywana liczebność grupy/założenia wyceny, sposób podróżowania, orientacyjna intensywność.
3. **Opis doświadczenia — SHOULD** [PROPOZYCJA]: krótka zapowiedź, najważniejsze atrakcje i powód, dla którego wybrano tę trasę.
4. **Program dzień po dniu — MUST** [MATERIAŁ: SRC-01/SRC-02 + SPECYFIKACJA]: numer/data dnia, region i trasa, atrakcje i krótkie opisy, główne aktywności, ewentualnie orientacyjne przejazdy, miejsce noclegu. Godziny wyłącznie, jeśli są przydatne odbiorcy.
5. **Transport — MUST** [MATERIAŁ: SRC-01/SRC-02 + SPECYFIKACJA]: sposób dojazdu i przemieszczania; loty tylko jeśli podane/ustalone, transfery, samochód itp.
6. **Zakwaterowanie — MUST, gdy wyjazd obejmuje noclegi** [MATERIAŁ: SRC-01 + SPECYFIKACJA]: lokalizacja, standard i wyżywienie; konkretny obiekt wyłącznie przy właściwym statusie „proponowany/potwierdzony”.
7. **Zakres świadczeń — MUST** [SPECYFIKACJA]: osobno „W cenie” i „Poza ceną”, bez dopowiadania nieuzgodnionych usług.
8. **Cena i założenia kalkulacji — MUST albo jawny tryb konceptowy** [SPECYFIKACJA]: kwota/waluta, za osobę czy grupę, liczba osób, termin ważności oferty (jeśli określony), status potwierdzenia.
9. **Warunki i kolejny krok — MUST** [SPECYFIKACJA]: wymagane zasady rezerwacji/płatności, CTA i kontakt.
10. **Opcjonalnie — MAY** [PROPOZYCJA]: mini-mapa trasy, FAQ, warianty noclegu/aktywności, poziom trudności.

**Nie umieszczać:** listy uczestników, numerów rezerwacji, PIN-ów, prywatnych kontaktów kontrahentów, wewnętrznych notatek pilota ani technicznych checklist.

**Czego nie potwierdzają źródła:** cen, zasad płatności, rzeczywistej dostępności hoteli i ostatecznego zakresu usług; te dane wymagają odrębnego wprowadzenia i weryfikacji.

### 3.2. `offer.self_guide` — oferta samodzielnej podróży

**Przykład tytułu (syntetyczny):** „Kanada + USA — 15-dniowy Self-Guide”.

1. **Okładka i oznaczenie Self-Guide — MUST** [SPECYFIKACJA]: kierunek, termin, liczba dni, zdjęcie/wariant bez zdjęcia, jednoznaczne „bez pilota na miejscu”.
2. **Formuła i zakres obsługi — MUST** [SPECYFIKACJA]: co przygotowuje TRIPSE, co organizuje uczestnik, czego nie obejmuje wsparcie.
3. **Podsumowanie trasy — SHOULD** [MATERIAŁ: SRC-02]: punkt startu/mety, kraje/regiony, dystans samochodowy i pieszy, intensywność; liczby tylko z wiarygodnego źródła.
4. **Program dnia — MUST** [MATERIAŁ: SRC-02]: numer/data, kolejność miejsc, orientacyjne czasy, atrakcje, przejazdy, szlaki, przerwy i miejsce noclegu.
5. **Instrukcje samodzielnego poruszania się — SHOULD** [PROPOZYCJA]: mapy/linki, parkingi, promy, shuttle busy, opłaty i rezerwacje atrakcji, wskazówki terenowe.
6. **Transport i noclegi — MUST, gdy występują** [MATERIAŁ: SRC-02 + SPECYFIKACJA]: loty, auto, przeprawy, propozycje/ustalenia noclegowe; status każdej kluczowej rezerwacji.
7. **Alternatywy i ograniczenia — SHOULD** [PROPOZYCJA]: warianty zależne od pogody, sezonowości i kondycji; bez automatycznego deklarowania dostępności dróg/szlaków.
8. **Wsparcie TRIPSE i odpowiedzialność podróżującego — MUST** [SPECYFIKACJA]: realny zakres kontaktu i pomocy, obowiązki klienta, ograniczenia; nie obiecywać całodobowej opieki bez potwierdzenia.
9. **Cena, świadczenia, warunki, CTA — MUST albo odpowiednio oznaczony koncept** [SPECYFIKACJA].

**Nie umieszczać:** sugestii, że obecny będzie pilot; wewnętrznych numerów rezerwacji, PIN-ów i danych innych klientów; fikcyjnie potwierdzonych transferów/usług.

**Do uzgodnienia:** dokładny pakiet Self-Guide (rezerwacje, concierge, materiały, kontakt w podróży, zakres odpowiedzialności).

### 3.3. `offer.school` — oferta wycieczki szkolnej

> **Uwaga o źródłach:** brak osobnego wzoru szkolnego. Poniżej **[SPECYFIKACJA]/[PROPOZYCJA]**, nie ekstrakcja z dostarczonego szkolnego PDF-a.

1. **Okładka — SHOULD**: szkoła/grupa, kierunek, daty/liczba dni, zdjęcie.
2. **Parametry grupy — MUST**: wiek/klasa, zakładana liczba uczniów, opiekunów i zasady kalkulacji.
3. **Cele edukacyjne — MUST**: edukacja/historia/kultura, przyroda i środowisko, integracja; dopasowane do wieku.
4. **Program dzień po dniu — MUST**: miejsca, aktywności, orientacyjne godziny, przerwy, posiłki, noclegi; przy atrakcjach warto wskazać walor edukacyjny.
5. **Organizacja — MUST, gdy stosowne**: transport, zakwaterowanie, wyżywienie, opiekunowie i pilot/przewodnik (tylko jeśli zapewniony).
6. **Bezpieczeństwo i wymagania — SHOULD**: ograniczenia aktywności, wymagania sprzętowe, podstawowe zasady organizacyjne; szczegółowa polityka zgodnie z decyzją firmy.
7. **Cena i zakres świadczeń — MUST**: cena na ucznia przy określonych założeniach, koszty opiekunów, w cenie/poza ceną, minimalna liczebność, rezerwacja.
8. **Kontakt i następny krok — MUST**.
9. **Opcjonalnie — MAY**: karta korzyści dydaktycznych, alternatywny program na złą pogodę, FAQ dla rodziców.

**Nie umieszczać:** danych konkretnych nieletnich, danych wrażliwych i rezerwacyjnych w standardowej ofercie; nie deklarować opieki lub zabezpieczeń, których nie zapewniono.

**Do uzgodnienia:** minimalny zakres opieki, zasady odpowiedzialności, docelowe grupy wiekowe, czy opiekunowie mają osobne zasady kosztowe.

### 3.4. `offer.incentive` — oferta firmowa / incentive

> **Uwaga o źródłach:** brak osobnego wzoru incentive. Poniżej **[SPECYFIKACJA]/[PROPOZYCJA]**.

1. **Okładka — SHOULD**: klient/organizacja, tytuł wydarzenia, kierunek, termin, liczba dni, zdjęcie.
2. **Koncepcja i cele — MUST**: integracja, nagroda, motywacja, spotkanie zespołu; wartość dla pracowników i firmy.
3. **Parametry grupy — MUST**: liczebność, standard, cele wydarzenia, potrzeby organizacyjne.
4. **Program — MUST**: harmonogram ramowy, doświadczenia, aktywności integracyjne, posiłki, czas wolny, opcjonalne szkolenia/warsztaty.
5. **Hotel i infrastruktura — MUST, jeśli istotne dla oferty**: położenie, standard, rodzaje pokoi, zdjęcia z prawami, restauracja, sale spotkań i części wspólne; rozróżniać obiekt proponowany/potwierdzony.
6. **Transport i obsługa — MUST**: dojazd, transfery, przemieszczanie grupy, przewidziana koordynacja.
7. **Warianty programu — SHOULD**: dodatkowe dni, warsztaty, atrakcje, alternatywne scenariusze.
8. **Wycena i założenia — MUST albo odpowiednio oznaczony koncept**: koszt łączny i/lub jednostkowy, zakres świadczeń, pozycje dodatkowe, warunki.
9. **Podsumowanie wartości i CTA — MUST**: możliwość dopasowania i kontakt.

**Nie umieszczać:** operacyjnych danych rezerwacyjnych, prywatnych kontaktów, niepotwierdzonych nazw usługodawców, gwarancji infrastruktury bez potwierdzenia.

**Do uzgodnienia:** minimalny zakres personalizacji firmy, priorytet hotelu vs. aktywności, dodatkowe pola konferencyjne i warianty cenowe.

---

## 4. Dokumenty pilotów — trzy typy

### 4.1. `pilot.basic` — podstawowa rozpiska operacyjna

**Wzór bezpośredni:** SRC-01 (Islandia, 5 stron).

1. **Metryka wyjazdu — MUST** [MATERIAŁ]: nazwa, termin, kierunek, osoba prowadząca, wersja/aktualizacja [SPECYFIKACJA].
2. **Informacja o grupie — SHOULD** [MATERIAŁ]: liczba uczestników, skład podgrup i przydziały organizacyjne w minimalnym niezbędnym zakresie; szczegółowe listy osób w bezpiecznej, oddzielnej części/załączniku.
3. **Loty i przyjazdy/powroty — MUST, jeśli dotyczą** [MATERIAŁ]: przewoźnik, numer lotu, trasa, lokalne daty/godziny, grupy przylotowe, transfery.
4. **Zbiórki i transport — MUST, jeśli dotyczą** [MATERIAŁ/SPECYFIKACJA]: punkt spotkania, godzina, przejazdy krytyczne i osoba odpowiedzialna.
5. **Noclegi — MUST, jeśli dotyczą** [MATERIAŁ]: data, obiekt, lokalizacja/mapa, rodzaje pokoi, kontakt organizacyjny, status rezerwacji. Oryginał zawiera także PIN-y; **nie są standardowym polem wydruku**.
6. **Atrakcje z rezerwacjami — MUST, jeśli dotyczą** [MATERIAŁ]: data i godzina, nazwa, status biletu/rezerwacji, uwagi.
7. **Skrócony program dzień po dniu — MUST** [MATERIAŁ]: dzień, data, główne punkty, istotne godziny/przejazdy, posiłki/zakupy w razie potrzeby, nocleg na koniec dnia.
8. **Otwarte kwestie — MUST** [MATERIAŁ]: godziny niepotwierdzone, pytania o wyżywienie, check-in, bilety, ryzyka i osoba do wyjaśnienia [PROPOZYCJA].
9. **Kontakty operacyjne i sytuacje awaryjne — MUST według polityki firmy** [SPECYFIKACJA].
10. **Opcjonalnie — MAY** [PROPOZYCJA]: lista rzeczy do odebrania, checklista samochodu, krótkie notatki pilota, mapa punktów krytycznych.

**Nie umieszczać:** długich wykładów historycznych, ciężkiej marketingowej galerii, danych operacyjnych w materiałach publicznych. Dostęp tylko dla uprawnionych.

**Zasada szczególna:** kod PIN/hasło do obiektu to sekret dostępowy, nie „zwykły numer rezerwacji”. Nie kopiować go automatycznie do standardowego PDF-a; ewentualny bezpieczny kanał/załącznik wymaga oddzielnej decyzji i zabezpieczeń.

### 4.2. `pilot.advanced` — szczegółowa rozpiska logistyczna

**Wzór bezpośredni:** SRC-02 (Kanada + USA, 16 stron). **Rozszerza** `pilot.basic`; nie tworzy osobnej, niespójnej bazy lotów/noclegów.

1. **Metryka wyjazdu — MUST**: jak w podstawowej, dodatkowo status dokumentu i aktualizacja.
2. **Tabela całego wyjazdu — MUST** [MATERIAŁ]: dzień, data, główny park/region/atrakcja, kilometry autem, kilometry pieszo, planowany zakres godzin, orientacyjne sumy.
3. **Podstawowe operacje — MUST stosownie do wyjazdu** [MATERIAŁ/SPECYFIKACJA]: loty, transfery, rezerwacje, noclegi, kontakty, sprawy otwarte.
4. **Nagłówek dnia — MUST** [MATERIAŁ]: numer/data/dzień tygodnia, trasa w kolejności, lokalna strefa czasowa; wschód/zachód słońca tylko przy wiarygodnych danych [SHOULD/MAY].
5. **Oś czasu — MUST** [MATERIAŁ]: godzina startu/końca segmentu, przejazd, atrakcja, czas pobytu, posiłek, postój, check-in/check-out.
6. **Parametry tras — MUST, gdy ustalone** [MATERIAŁ]: szacowane km i czas jazdy, dystans pieszy, długość trekkingu, przewyższenie (jeśli dostępne), źródło pomiaru/status weryfikacji [SPECYFIKACJA].
7. **Transport specjalny i punkty krytyczne — MUST, gdy dotyczą** [MATERIAŁ]: prom, shuttle, odprawa graniczna, wejście z biletem na godzinę, deadline rezerwacji.
8. **Nocleg dnia — MUST, jeśli jest przewidziany** [MATERIAŁ]: nazwa/lokalizacja lub jawnie „do ustalenia”, godzina dotarcia, status.
9. **Podsumowanie dnia — SHOULD** [MATERIAŁ]: dystans auta/pieszo, przewidywana długość pracy/trasy.
10. **Ryzyka i plan B — MUST przy krytycznych ograniczeniach** [SPECYFIKACJA]: opóźnienia, pogoda, przejezdność, zmiana czasu, rezerwa, alternatywa do świadomego zatwierdzenia.
11. **Opcjonalnie — MAY** [PROPOZYCJA]: mapa offline, checklista, wariant skrócony lub tabela alertów.

**Nie umieszczać:** niezweryfikowanych, zmyślonych czasów jako faktów; zer dla nieznanych dystansów; opisów miejsc niepowiązanych z rzeczywistym planem; nadmiernie rozbudowanych tekstów marketingowych.

**Reguła:** rozróżnić `planowany`, `szacowany`, `potwierdzony`, `rzeczywisty` — jeśli system zna tylko wartość orientacyjną, nie może prezentować jej jako gwarancji logistycznej.

### 4.3. `pilot.knowledge` — materiały merytoryczne / storytelling

**Wzór bezpośredni:** SRC-03 (Kanada + USA, dni 3–15, 39 stron).

**Powtarzalna struktura dla każdego dnia:**

1. **Tytuł dnia i rzeczywista trasa — MUST** [MATERIAŁ]: dzień, główny temat, odwiedzane miejsca wynikające z programu źródłowego.
2. **Atrakcje dnia — MUST, gdy są atrakcje** [MATERIAŁ]: osobny opis każdej miejscowości/parku/punktu, co zobaczyć, dlaczego ważne, powiązane fakty.
3. **Najważniejsze fakty — SHOULD/MUST przy publikacji faktów** [MATERIAŁ]: kluczowe informacje geograficzne, historyczne i przyrodnicze; przy istotnych twierdzeniach wymagane źródło [SPECYFIKACJA].
4. **Co łączy te miejsca? — SHOULD** [MATERIAŁ]: wspólny motyw, kontekst trasy, sens zestawienia atrakcji.
5. **Historia / geologia / przyroda / kultura — SHOULD** [MATERIAŁ]: sekcje dopasowane do rzeczywiście odwiedzanych lokalizacji.
6. **Na co zwrócić uwagę na miejscu — SHOULD** [MATERIAŁ]: obserwacje terenowe, elementy krajobrazu, szczegóły możliwe do pokazania grupie.
7. **Krótkie historie do opowiedzenia podczas jazdy — SHOULD** [MATERIAŁ]: krótkie narracje, anegdoty i przykłady; wyraźnie odróżnione od faktów.
8. **Źródła i uwagi redakcyjne — MUST przy twierdzeniach faktograficznych** [MATERIAŁ/SPECYFIKACJA]: dokładny tytuł/URL, data sprawdzenia, powiązanie z informacją, status weryfikacji; uwagi o sezonowości.
9. **Opcjonalnie — MAY** [PROPOZYCJA]: wymowa nazw, dodatkowe pytania do grupy, mini-słowniczek, zdjęcia poglądowe z prawami, krótsza wersja narracji.

**Nie umieszczać:** danych uczestników, kodów dostępu, szczegółowych rezerwacji, logistyki minutowej, fikcyjnych atrakcji spoza planu ani legend przedstawionych jako udowodnione fakty.

**Układ referencyjny:** w SRC-03 często występują trzy warstwy/strony na dzień: (A) opisy atrakcji, (B) fakty i kontekst, (C) obserwacje, narracje, źródła. **Nie wymuszać 3 pustych stron**, gdy materiał jest krótszy.

---

## 5. `marketing.collection` — oferta marketingowa

**Wzór bezpośredni:** SRC-04. Jedno `template_id`, dwa `layout_variant`: `new_trips`, `theme_collection`.

### 5.1. Elementy wspólne

1. **Brand i tytuł kampanii — MUST** [MATERIAŁ/SPECYFIKACJA]: logo TRIPSE, nazwa, sezon/rok lub motyw.
2. **Hasło przewodnie — SHOULD** [MATERIAŁ]: krótki przekaz o charakterze kolekcji.
3. **Karty wyjazdów — MUST (min. 1)** [MATERIAŁ/SPECYFIKACJA]: nazwa kierunku, kraj/region, termin lub jawne „do ustalenia”, zdjęcie z prawami lub świadomie zaakceptowany wariant bez niego, krótkie wyróżniki, status produktu.
4. **Prowadzący / pilot — MAY** [MATERIAŁ]: imię i nazwisko tylko po potwierdzeniu oraz uzgodnieniu wykorzystania w materiałach.
5. **CTA i sposób kontaktu — MUST w specyfikacji** [SPECYFIKACJA]: wezwanie do działania i poprawne dane kontaktowe/link/QR; **grafika źródłowa nie stanowi dowodu, że komplet tych elementów wystąpił w każdym wzorze**.
6. **Wyróżniki marki — SHOULD** [MATERIAŁ]: małe grupy, doświadczenia, sprawdzone trasy/piloci — tylko jeśli to zweryfikowane obietnice TRIPSE.
7. **Cena — MAY**: nie występuje na przesłanych grafikach i nie jest obowiązkowa dla tego typu plakatu.

**Nie umieszczać:** danych uczestników, rezerwacji, PIN-ów, niepotwierdzonych cen i terminów, fikcyjnej informacji o dostępności miejsc ani zdjęć bez praw użycia.

### 5.2. `new_trips` — nowości / pilotażowe kierunki

**Przykład z grafiki:** plakat „Pilotażowe Nowości 2027”.

- **Nagłówek — MUST:** tytuł kolekcji, sezon, krótkie hasło.
- **Każda pozycja — MUST:** wyraźna fotografia/karta, nazwa wyjazdu, region lub kraj, data/etykieta terminu, ewentualny pilot, status (np. „pilotażowy”), 1–2-zdaniowy wyróżnik.
- **Zestawienie różnorodnych kierunków — SHOULD:** niezależne oferty o wspólnym sezonie/komunikacie.
- **Dolna sekcja — SHOULD:** kilka wspólnych zalet TRIPSE i CTA.
- **Wiele pozycji — SHOULD:** podział na strony/slajdy przy nadmiarze informacji; nie upychać kosztem czytelności.

### 5.3. `theme_collection` — kolekcja tematyczna

**Przykład z grafiki:** plakat „Wyprawy Górskie”.

- **Hero — MUST:** silny motyw przewodni, tytuł, zdjęcie i hasło.
- **Prowadzący — MAY:** osoba związana z kolekcją i krótkie zaproszenie tylko, jeśli potwierdzone.
- **Wspólne cechy — SHOULD:** np. góry, małe grupy, aktywne podróże.
- **Każda wyprawa — MUST:** nazwa kierunku/szczytu, kraj, termin lub etykieta, fotografia, krótki opis.
- **Rozszerzenia — MAY, gdy rzeczywiście oferowane:** połączenie dwóch wyjazdów, przedłużenie, dodatkowy kierunek, wariant tygodniowy/dwutygodniowy.
- **CTA — MUST:** jasny sposób zapytania o szczegóły lub zgłoszenia.

**Wskazówka:** wariant tematyczny promuje **wspólną ideę i doświadczenie**, a `new_trips` promuje **zestaw nowych kierunków**. Nie tworzyć dwóch niezależnych silników ani odrębnych kategorii wycieczek dla tych kompozycji.

---

## 6. Macierz zawartości — szybki indeks dla implementacji

Legenda: `M` = podstawowy element finalnego dokumentu, `W` = warunkowy (gdy dotyczy), `O` = opcjonalny, `—` = nie umieszczać lub nie ma zastosowania. Szczegóły i wyjątki wynikają z powyższych sekcji oraz `system-data/template-fields.md`.

| Element | Private | Self-Guide | School | Incentive | Pilot basic | Pilot advanced | Pilot knowledge | Marketing |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Nazwa, kierunek, termin/etykieta | M | M | M | M | M | M | M | M |
| Program dzień po dniu | M | M | M | M | M | M | M (merytoryczny) | — |
| Tabela całej trasy / dystanse | O | W | O | O | O | M | — | — |
| Godzinowy harmonogram | O | W | O | O | W (krytyczne) | M | — | — |
| Noclegi / transport | W | W | W | W | W | W | — | — |
| Rezerwacje operacyjne | — | — | — | — | W | W | — | — |
| Dane uczestników | — | — | — | — | W (ograniczone) | W (ograniczone) | — | — |
| Historia, ciekawostki, narracje | O | O | O | O | O | O | M | — |
| Cele edukacyjne / integracyjne | — | — | M | M (cele wydarzenia) | — | — | — | — |
| Ceny, świadczenia, warunki | M/koncept | M/koncept | M/koncept | M/koncept | — | — | — | O |
| Zdjęcia marketingowe | W | W | W | W | O | O | O | M/zaakceptowany brak |
| CTA do klienta | M | M | M | M | — | — | — | M |
| Źródła i status weryfikacji faktów | W | W | W | W | W (operacje) | W (operacje) | M | W |
| Plan B / ryzyka logistyczne | O | W | W | W | W | M przy ryzykach | — | — |

**Interpretacja:** macierz służy do projektowania sekcji. Nie jest jedyną walidacją. Na przykład „M” w ofercie nie oznacza, że brak ceny blokuje zapis roboczy; może blokować publikację finalną lub wymagać jasno oznaczonego `concept_only`.

## 7. Reguły treści, walidacji i bezpieczeństwa

1. **Żadnego wymyślania danych.** Nie generować nieznanej ceny, rezerwacji, godzin lotów, noclegów, liczby miejsc, potwierdzeń, kontaktu prowadzącego ani konkretnego hotelu.
2. **Braki jawne.** `Do ustalenia`, `proponowane`, `niepotwierdzone`, `weryfikacja wymagana` — stosownie do kontekstu. Nie zastępować braku wartości zerem lub słowem „potwierdzone”.
3. **Dane wrażliwe oddzielnie.** Uczestnicy i kontakty operacyjne tylko przy uzasadnionej potrzebie i zgodnych uprawnieniach; PIN-y/hasła poza standardowymi eksportami.
4. **Dokumenty klientowskie i marketingowe** nie mogą otrzymywać pól z `PilotData`, list uczestników, sekretów, notatek wewnętrznych ani numerów rezerwacji przez automatyczne mapowanie.
5. **Fakty merytoryczne** w `pilot.knowledge` muszą mieć powiązanie z odwiedzaną atrakcją, szczegółowe źródło, datę sprawdzenia i status weryfikacji. Rozdzielać fakt, interpretację i propozycję narracji.
6. **Statusy ofert**: rozróżniać propozycję/koncept i potwierdzony produkt; `ready` w bibliotece nie jest automatyczną zgodą na publikację.
7. **Prawa do zdjęć**: źródłowy plakat nie jest dowodem licencji. Nie publikować fotografii bez odpowiednich praw; dopuszczalny kontrolowany wariant bez zdjęcia.
8. **Rewizje/snapshoty**: zmiana programu źródłowego nie nadpisuje starszej zapisanej oferty. Dokumenty i materiały pilota mogą korzystać z tego samego Trip, ale muszą zachować własne zasady poufności.
9. **Układ a dane**: przy dłuższych wyjazdach rozbijać dokument na strony; nie obcinać tekstu ani tabel. Nie wymuszać trzech stron na dzień materiału merytorycznego.
10. **Środowiska i testy**: dane demonstracyjne wyraźnie oznaczyć, nie używać prawdziwych klientów w snapshotach QA, nie uruchamiać destrukcyjnych migracji.

## 8. Schematy referencyjne — w kolejności sekcji

Do szybkiego użycia w promptach i testach:

```text
offer.private:
  Okładka → W skrócie → Główne doświadczenia → Program dni 1..N
  → Noclegi i transport → W cenie / Poza ceną → Cena i warunki → CTA

offer.self_guide:
  Okładka + Bez pilota → Jak działa Self-Guide → Mapa i parametry trasy
  → Program dni 1..N → Instrukcje samodzielnego podróżowania
  → Noclegi i transport → Zakres wsparcia/odpowiedzialności
  → Cena i świadczenia → CTA

offer.school:
  Okładka → Grupa i cele edukacyjne → Program dni 1..N
  → Organizacja i bezpieczeństwo → Świadczenia i wycena → CTA

offer.incentive:
  Okładka → Cele i koncepcja → Parametry grupy → Program
  → Hotel i infrastruktura → Logistyka → Warianty
  → Wycena i warunki → CTA

pilot.basic:
  Metryka → Grupa/zbiórki → Loty i transfery → Noclegi/rezerwacje
  → Program dni 1..N (skrót) → Sprawy otwarte → Kontakty operacyjne

pilot.advanced:
  Metryka → Tabela całej wyprawy → Loty/noclegi/rezerwacje
  → [Dzień N: strefa + trasa + oś czasu + dystanse + nocleg + ryzyka/plan B]
  → Podsumowanie/checklista/sprawy otwarte

pilot.knowledge:
  [Dzień N: trasa i atrakcje → Najważniejsze fakty
  → Co łączy miejsca → Historia/geologia/przyroda/kultura
  → Na co zwrócić uwagę → Historie dla grupy → Źródła/uwagi]

marketing.collection / new_trips:
  Nagłówek kampanii → Hasło i wyróżniki
  → [Karta kierunku: foto + nazwa + kraj + termin + status + pilot? + krótki hook]
  → CTA

marketing.collection / theme_collection:
  Motyw przewodni + hero → Prowadzący? + zaproszenie? + cechy kolekcji
  → [Karta wyprawy: foto + nazwa + kraj + termin + krótki opis]
  → Możliwe rozszerzenia? → CTA
```

Znaki `?` oznaczają **warunkowo/opcjonalnie**, nie pola do automatycznego uzupełniania.

## 9. Pytania do zatwierdzenia z TRIPSE

Przed uznaniem pliku za zatwierdzony ground truth należy rozstrzygnąć:

1. Jakie dokładnie usługi obejmuje Self-Guide: rezerwacje, wsparcie, materiały, kontakt w trakcie podróży?
2. Czy oferta indywidualna może być wysyłana bez ceny i na jakich warunkach (`concept_only`)?
3. Jakie są wymagane pola dla wycieczek szkolnych: nadzór, grupy wiekowe, bezpieczeństwo, posiłki?
4. Jak TRIPSE standardowo wycenia incentive: grupa/osoba, warianty, hotel, warsztaty?
5. Jakie dane uczestników wolno przechowywać w rozpisce pilota i czy potrzebny jest osobny załącznik?
6. Jaki bezpieczny mechanizm stosować dla kodów dostępu do obiektów? Domyślnie **nie w PDF**.
7. Czy każdy materiał marketingowy musi zawierać kontakt/CTA, a także kto potwierdza terminy, pilotów i zdjęcia?
8. Czy sekcje pilotów mogą mieć wersję „na telefon” i „do druku”, bez zmiany źródła danych?
9. Kto zatwierdza fakty w materiałach merytorycznych, jak szczegółowe muszą być referencje źródłowe?
10. Czy są dodatkowe istniejące wzory ofert prywatnych, szkolnych i incentive do włączenia do referencji?

## 10. Kontrakt dla kolejnych promptów implementacyjnych

Każdy prompt dotyczący szablonów, edytora, walidacji, danych, podglądu lub PDF-ów powinien wymagać:

1. **Najpierw przeczytaj** ten plik, `general/template-catalog.md`, `system-data/template-fields.md`, `system-data/content-validation.md` oraz właściwy `templates/**/<typ>.md`.
2. **Wypisz różnice** między proponowaną zmianą a istniejącą specyfikacją i kodem; nie uznawaj elementów `[PROPOZYCJA]` za zaakceptowane pole obowiązkowe.
3. **Zachowaj wszystkie stabilne `template_id`** i rozdział Trip/Campaign/DocumentDraft.
4. **Mapuj sekcje do danych**: które pochodzą z Trip, które z Campaign, które są edycją konkretnego dokumentu, a które należą do chronionych danych operacyjnych.
5. **Nie przenoś danych wrażliwych** między dokumentami o różnej poufności.
6. **Dodaj testy treści, a nie tylko layoutu**: obecność właściwych sekcji, brak zakazanych pól, zachowanie kolejności, jawne braki i warianty marketingowe.
7. **Używaj danych syntetycznych**; nie kopiuj rzeczywistych przykładów z załączników do fixture'ów.
8. **Raportuj zmiany względem tej referencji** i aktualizuj ją tylko, jeśli nowa decyzja biznesowa jest uzgodniona i jawnie opisana.

### Minimalne testy akceptacyjne według rodzaju

| Rodzaj | Test pozytywny | Test negatywny |
|---|---|---|
| Private | program + świadczenia + wycena/koncept | brak wewnętrznych rezerwacji i uczestników |
| Self-Guide | „bez pilota”, zakres wsparcia, szczegóły trasy | brak obietnicy pilota/opieki bez potwierdzenia |
| School | cele, grupy, program, organizacja | brak danych dzieci i niepotwierdzonych zobowiązań |
| Incentive | cele firmy, hotel/program, wycena | brak fikcyjnych sal i potwierdzonych noclegów |
| Pilot basic | loty, noclegi, godziny atrakcji, otwarte sprawy | brak PIN-u w standardowym eksporcie |
| Pilot advanced | tabela i oś czasu, km/pieszo, ryzyka | brak nieznanych metryk = 0 i niespójnych stref |
| Pilot knowledge | miejsca programu, kontekst, historie, źródła | brak atrakcji spoza programu i faktów bez weryfikacji |
| Marketing | dwa warianty, daty/etykiety, statusy, CTA | brak PII, fikcyjnej dostępności i zdjęć bez praw |

## 11. Powiązane pliki repozytorium

- [Katalog szablonów](template-catalog.md)
- [Przepływ tworzenia dokumentu](document-workflow.md)
- [Mapa pól i walidacji](../system-data/template-fields.md)
- [Walidacja treści](../system-data/content-validation.md)
- [Oferta prywatna](../templates/offers/private.md)
- [Self-Guide](../templates/offers/self-guide.md)
- [Oferta szkolna](../templates/offers/school.md)
- [Incentive](../templates/offers/incentive.md)
- [Rozpiska podstawowa](../templates/pilots/basic.md)
- [Rozpiska zaawansowana](../templates/pilots/advanced.md)
- [Materiały merytoryczne](../templates/pilots/knowledge.md)
- [Marketing](../templates/marketing/collections.md)
- [Dokumentacja główna systemu](../README.md)

---

**Zasada nadrzędna:** dokument ma zawierać tylko informacje właściwe dla swojego odbiorcy, z poprawnym statusem potwierdzenia. Wzory pokazują, jak organizować treść; nie uprawniają do wymyślania danych, kopiowania tajnych szczegółów rezerwacji ani automatycznego uznawania propozycji za zaakceptowane wymagania.
