# Szablon: zaawansowana rozpiska pilota

Stan implementacji lokalnej 2026-10-28 (szablony 0.4.0): Wspólne PilotData/OperationalEntry plus DayLogistics per dzień: data, odcinki, metryki null przy braku danych, IANA, referencja noclegu, notatki i plan B. Podgląd ma tabelę trasy i harmonogramy; działa dla 10–15 dni. internal_restricted.

Instrukcja edycji i ograniczenia publikacji: [Document Studio](../../../DOCUMENT_STUDIO.md).
Poniżej zachowano wymagania docelowe i inspiracje; nie oznaczają automatycznej akceptacji treści.

**ID:** `pilot.advanced`  
**Rodzina:** `pilot` · **Odbiorca:** nowy pilot lub dobrze znany pilot na nowym kierunku  
**Poufność:** `internal_restricted`  
**Format początkowy:** PDF A4, strona zbiorcza + ok. 1–2 stron na dzień + aneksy.

## 1. Cel i odbiorca

Umożliwić bezpieczne i przewidywalne poprowadzenie trasy także przez osobę, która nie zna jeszcze jej operacyjnych szczegółów. Jest rozwinięciem `pilot.basic`, a nie drugim źródłem danych o lotach i hotelach.

## 2. Charakterystyka dokumentu / inspiracja

Przykład „Kanada — program / plan wyprawy” zawiera 16 stron z tabelą dni, trasą, kilometrami jazdy/pieszo, oknami godzinowymi, strefami czasu, wschodem i zachodem słońca, promami i noclegami. Ten poziom szczegółowości jest odpowiedni dla rozpiski zaawansowanej, **o ile dane są zweryfikowane i nie pomylimy planowanych czasów z faktycznymi**.

## 3. Sekcje obowiązkowe

1. Metryka wyjazdu + pilot, aktualizacja, status dokumentu.
2. **Tabela całej wyprawy**: dzień, data, kluczowa trasa, przybliżone kilometry autem/pieszo, przewidywany początek/koniec, nocleg.
3. Wszystkie sekcje wymagane w `pilot.basic` (transport, noclegi, rezerwacje i otwarte sprawy).
4. **Plan każdego dnia:** numer/data, lokalna strefa, start/mety, segmenty harmonogramu w kolejności, godziny i czas trwania, etapy przejazdów, czasy aktywności, punkty spotkań.
5. **Ruch i wysiłek:** dystans/czas jazdy (z podaniem źródła), trekking i przewyższenie jeśli ustalone, przerwy, strefy czasowe.
6. **Punkty krytyczne:** bilety na godzinę, promy, granice, ograniczenia sezonowe, zamknięcia tras, logistyka parkingów.
7. **Ryzyka i plan alternatywny:** pogoda, opóźnienia, rezerwy czasowe; określone przez organizatora i zweryfikowane.
8. Zestawienie rezerwacji i nierozstrzygniętych spraw.

## 4. Sekcje opcjonalne

Orientacyjne wschody/zachody słońca ze wskazaniem daty/źródła; linki do tras i map offline; numerowane punkty postoju; trasy alternatywne; checklista grupy; wariant dla opóźnionego lotu. Nie deklarować poprawności wschodów słońca bez danych lokalizacyjnych i daty.

## 5. Wymagane dane wejściowe

Wszystkie dane `pilot.basic` oraz `trip.days[].schedule_items[]`, `trip.days[].route`, `route.verification_status`, `route.source`, `trip.days[].walking_distance`, `trip.days[].risk_notes[]`, `trip.days[].fallbacks[]`, `trip.days[].time_zone`, `operations.booking_deadlines[]`. Rozróżniaj `planned_start`, `planned_end`, `actual` (jeśli zbierane) oraz `estimated`.

## 6. Zasady prezentacji treści

- Oś czasu ma format `HH:mm–HH:mm`, ze wskazaniem strefy dnia; zmiana strefy jest wyraźnie sygnalizowana.
- Dane Maps są oszacowaniem na konkretny moment i profil trasy, nie gwarancją przejazdu.
- Rozbieżności sumowania etapów i harmonogramu podlegają walidacji.
- Wyszczególnij punkty „MUST ON TIME” np. prom, lot, wejście z biletem — tylko na podstawie danych.
- Nie dodawaj do harmonogramu atrakcji, których nie ma w zatwierdzonym planie, bez zgody autora.
- Plan awaryjny jest propozycją logistyczną wymagającą oceny; AI nie „potwierdza” przejezdności drogi.

## 7. Wymagania wizualne

Tabela zbiorcza wycieczki, sekcje z numerami dni, naprzemienne tło wierszy, wyraźne odstępy między przejazdem a aktywnością. Na każdej stronie nagłówek dnia i status „WEWNĘTRZNE”. Zostaw miejsce na praktyczne adnotacje po wydruku.

## 8. Obsługa brakujących informacji

Brak czasu przejazdu → `niezweryfikowany`, nie zero minut. Brak planu B przy ryzyku krytycznym → ostrzeżenie; przed akceptacją wymaga świadomej decyzji pilota/koordynatora. Nieznany nocleg → widoczny brak krytyczny. Nieustalony czas pieszo → nie sumować go do całości.

## 9. Przykładowa struktura dokumentu

Metryka → 1-stronicowe podsumowanie całej wycieczki → loty/noclegi → dzień 1 (oś czasu + ryzyka) → ... → dzień N → checklisty i sprawy do weryfikacji.

## 10. Kryteria akceptacji

Co najmniej jeden pełny dzień z licznymi postojami renderuje się bez ucięcia; czasy i daty są spójne; pilot odróżnia propozycje od rezerwacji; dla 10–15 dni nie ma ograniczenia do dwóch dni wynikającego z obecnego demo planera; poufne dane pozostają pod kontrolą dostępu.

**Powiązania:** [basic](basic.md) · [model](../../system-data/trip-data-model.md) · [content-validation](../../system-data/content-validation.md).
