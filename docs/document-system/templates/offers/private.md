# Szablon: oferta wyjazdu indywidualnego

Stan implementacji lokalnej 2026-10-28 (szablony 0.4.0): Wspólne OfferData, dziesięć domyślnych ról sekcji, własne sekcje i dotychczasowa cena/concept_only/CTA. Nadal blokowany eksport przy błędach biznesowych.

Instrukcja edycji i ograniczenia publikacji: [Document Studio](../../../DOCUMENT_STUDIO.md).
Poniżej zachowano wymagania docelowe i inspiracje; nie oznaczają automatycznej akceptacji treści.

**ID:** `offer.private`  
**Rodzina:** `offer` · **Odbiorca:** klient prywatny / rodzina / zamknięta grupa  
**Poufność:** dokument klientowski; może być wysłany odbiorcy, ale nie zawiera danych operacyjnych.  
**Format początkowy:** PDF A4, orientacyjnie 3–6 stron; liczba stron zależy od długości programu.

Aktualizacja DOC-TEMPLATES-006: lokalny szablon 0.5.0, uzupełniony przykład GT v1
i kopia do edycji przez `#examples`. Pola, kolejność oraz granice weryfikacji:
[raport implementacji](../../../DOC_TEMPLATES_006.md). Specyfikacja poniżej
nie oznacza zatwierdzenia biznesowego Ground Truth.

## 1. Cel i odbiorca

Przedstawić dopasowaną do potrzeb podróż, jej wartość, przebieg i koszt. Odbiorca powinien szybko ocenić, czy wyprawa odpowiada jego zainteresowaniom, oczekiwanej intensywności i budżetowi.

## 2. Charakterystyka dokumentu

Styl: inspiracyjny, ale konkretny; duże autentyczne zdjęcia kierunku, proste podsumowanie, łatwy do porównania program. Dokument nie przypomina instrukcji dla pilota.

## 3. Sekcje obowiązkowe

1. **Okładka** — logo TRIPSE, nazwa kierunku, nazwa oferty, termin lub „proponowany termin”, zdjęcie z prawami użycia.
2. **W skrócie** — liczba dni, kraje/regiony, grupa docelowa, szacowany poziom aktywności, krótka obietnica wyjazdu.
3. **Najważniejsze atrakcje** — 3–6 wyróżników, powiązanych z faktycznym programem.
4. **Program dzień po dniu** — nagłówek dnia, główne miejsca, planowane aktywności, orientacyjne przejazdy; godziny tylko, gdy potrzebne klientowi.
5. **Zakwaterowanie i transport** — standard, sposób przemieszczania; obiekty tylko ze statusem `confirmed` lub wyraźnym `proposed`.
6. **Co obejmuje / czego nie obejmuje cena** — osobne sekcje z jednoznacznymi listami.
7. **Wycena** — kwota, waluta, jednostka kalkulacji (osoba/grupa), liczba uczestników i warunki, albo jawnie uzgodniony wariant konceptowy bez ceny.
8. **Następny krok** — kontakt/CTA, data ważności wyceny jeśli istnieje.

## 4. Sekcje opcjonalne

Mapa poglądowa trasy; rekomendowane loty; warianty programu i noclegów; trudność tras; opcjonalne aktywności; FAQ; informacje przygotowawcze. Nie dodawać sekcji nieposiadających danych.

## 5. Wymagane dane wejściowe

`trip.title`, `trip.destination`, `trip.duration_days` lub `dates`, `trip.days[]`, `trip.highlights[]`, `trip.transport_summary`, `trip.accommodation_summary`, `offer.included[]`, `offer.excluded[]`, `offer.pricing`, `offer.cta`, `document.language`, `assets.cover` lub zaakceptowany wariant bez okładkowej fotografii. Dane dodatkowe: wielkość grupy i preferencje klienta (nie muszą być drukowane).

Weryfikować osobno: ceny, terminy, obiekty noclegowe, opcjonalne aktywności i listę świadczeń. Jeśli oferty nie wyceniono, użytkownik musi świadomie wybrać tryb `concept_only`.

## 6. Zasady prezentacji treści

- Najpierw korzyść i najważniejsze atrakcje, później logistyka i świadczenia.
- Unikać długich godzinowych rozpiskek, numerów rezerwacji, numerów telefonów usługodawców.
- Spójna terminologia: „w planie”, „proponujemy”, „potwierdzono” zależnie od statusu danych.
- Nie prezentować czasu dojazdu oszacowanego przez LLM jako pomiaru z Google Routes.
- Tekst musi zawierać jasno określone założenia wyceny; nie obiecywać dostępności.

## 7. Wymagania wizualne specyficzne dla typu

Wizerunkowa okładka + czytelne dzienne karty; 1 zdjęcie na rozdział/dzień tylko gdy służy treści; sekcja ceny bardziej kontrastowa niż zwykły tekst; CTA w ostatnim bloku. Wspólne zasady w [brand-guidelines](../../design/brand-guidelines.md) i [layout-rules](../../design/layout-rules.md).

## 8. Obsługa brakujących informacji

| Pole | Co zrobić |
|---|---|
| Cena lub warunki wyceny | Zablokować tryb finalnej oferty albo jawnie oznaczyć `concept_only` |
| Hotel nieustalony | „Standard noclegów do potwierdzenia”; nie wymieniać konkretnego hotelu jako pewnego |
| Termin elastyczny | „Termin proponowany”; bez udawania rezerwacji |
| Zdjęcie bez licencji | Nie publikować; dopuścić wariant graficzny bez zdjęcia |

## 9. Przykładowa struktura dokumentu

1. Okładka i hero image.
2. Dlaczego ten kierunek + parametry wyjazdu.
3. Program dni 1–N, automatycznie paginowany.
4. Noclegi, transport, zakres świadczeń.
5. Cena, warunki, kontakt.

## 10. Kryteria akceptacji

Klient rozumie, dokąd i na jak długo jedzie, co robi, za co płaci i co zostaje do potwierdzenia; opisy dni wynikają z danych wycieczki; oferta nie zawiera PII uczestników, PIN-ów ani wewnętrznych notatek. PDF jest czytelny po wydruku i na telefonie.

**Powiązania:** [model danych](../../system-data/trip-data-model.md) · [pola](../../system-data/template-fields.md) · [walidacja](../../system-data/content-validation.md).
