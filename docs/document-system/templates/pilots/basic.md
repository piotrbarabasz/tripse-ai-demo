# Szablon: podstawowa rozpiska pilota

Stan implementacji lokalnej 2026-10-28 (szablony 0.4.0): Wspólne PilotData/OperationalEntry oraz domyślne i własne sekcje. Rozpiska pozostaje internal_restricted, bez pola PIN; nie duplikuje modelu rezerwacji.

Instrukcja edycji i ograniczenia publikacji: [Document Studio](../../../DOCUMENT_STUDIO.md).
Poniżej zachowano wymagania docelowe i inspiracje; nie oznaczają automatycznej akceptacji treści.

**ID:** `pilot.basic`  
**Rodzina:** `pilot` · **Odbiorca:** pilot TRIPSE dobrze znający kierunek  
**Poufność:** `internal_restricted` — zawiera operacyjne dane osobowe i rezerwacyjne.  
**Format początkowy:** PDF A4, początkowe podsumowanie + skrót dnia po dniu.

Aktualizacja DOC-TEMPLATES-006: lokalny szablon 0.5.0, uzupełniony przykład GT v1
i kopia do edycji przez `#examples`. Pola, kolejność oraz granice weryfikacji:
[raport implementacji](../../../DOC_TEMPLATES_006.md). Specyfikacja poniżej
nie oznacza zatwierdzenia biznesowego Ground Truth.

## 1. Cel i odbiorca

Szybki dostęp do istotnych informacji operacyjnych, kiedy pilot zna region i nie potrzebuje opisu każdego kilometra. Ma ułatwiać prowadzenie grupy, koordynację przylotów, noclegów, wejść i kontaktu z usługodawcami.

## 2. Charakterystyka dokumentu / materiał źródłowy

Pięciostronicowy wzór Islandia Road Trip zawiera listę uczestników, podgrupy, loty, atrakcje z godzinami, noclegi, układy pokoi, kontakty i luźne pytania do wyjaśnienia. Zachowujemy tę użyteczność, ale wprowadzamy ustalone pola i osobne bloki „Do potwierdzenia”. **Nie przepisujemy do specyfikacji faktycznych danych uczestników, telefonów ani PIN-ów.**

## 3. Sekcje obowiązkowe

1. Okładka / metryka: kierunek, okres, pilot, numer rewizji i data aktualizacji.
2. Skrót organizacyjny: liczba uczestników, miejsce i godzina rozpoczęcia, kontakt do koordynatora w zakresie potrzebnym pilotowi.
3. **Transport przyjazdowy i powrotny:** potwierdzone loty/przesiadki, godziny w lokalnej strefie, transfery i punkty zbiórki.
4. **Rezerwacje i noclegi:** obiekt, data, rodzaj zakwaterowania, podział pokoi w zakresie koniecznym, kontakt, status rezerwacji (bez automatycznego ujawniania sekretów dostępowych).
5. **Dzień po dniu:** data, trasa, orientacyjny plan, godziny krytycznych aktywności i wejść, nocleg na koniec dnia.
6. **Sprawy otwarte:** co wymaga potwierdzenia, kto odpowiada, termin.
7. Kontakty organizacyjne i sytuacje awaryjne — według zatwierdzonej polityki TRIPSE.

## 4. Sekcje opcjonalne

Lista uczestników i podział grup (tylko minimalnie potrzebne pola); linki do map; zestawienie biletów; lista zakupów; rozkład pokoi; checklisty odbioru aut; plan posiłków; notatki pilota. Dane osobowe powinny być umieszczone w oddzielnym dostępowo załączniku, jeśli wymaga tego polityka firmy.

## 5. Wymagane dane wejściowe

`trip.title`, `trip.dates`, `operations.leader`, `operations.meetings[]`, `operations.flights[]`, `operations.accommodation_bookings[]`, `operations.activity_bookings[]`, `operations.critical_contacts[]`, `trip.days[]`, `operations.open_items[]`. Dla rezerwacji: `status`, `source`, `date`, `provider`, `check_in_out` zależnie od typu.

## 6. Zasady prezentacji treści

- Noclegi, przeloty i rezerwacje nie mogą mieszać się z komentarzami do programu.
- Każda godzina ma miejscową strefę czasu lub jest w kontekście wyraźnie oznaczonej strefy dnia.
- Potwierdzone rezerwacje odróżniać od propozycji i spraw otwartych.
- Najważniejsze zdarzenia i numery kontaktowe dostępne bez przewijania kilkunastu stron.
- Nigdy nie wstrzykiwać PIN-ów i kodów dostępu do standardowego PDF-a z danych ogólnych; użyć osobnego kanału/sejfiku lub załącznika tylko dla uprawnionych, jeśli uzgodniono.

## 7. Wymagania wizualne

Motyw `operations`: mocna hierarchia godzin, jednolita tabela lotów i noclegów, numery dni, krótkie checkboksy, priorytet czytelności w druku. Brak dużych zdjęć poza ewentualną mini-mapą. Numer wersji i oznaczenie „WEWNĘTRZNE” na każdej stronie.

## 8. Obsługa brakujących informacji

Brak godziny lotu/biletu oznacza `do potwierdzenia`, a nie 00:00. Brak noclegu → widoczne ostrzeżenie krytyczne. Kod rezerwacji nie jest równoważny kodowi dostępu/PIN. Brak pełnej listy uczestników nie blokuje roboczego szkicu, ale jest sygnalizowany przed wyjazdem zgodnie z procedurą.

## 9. Przykładowa struktura dokumentu

Metryka wyjazdu → kluczowe telefony i zbiórki → loty → uczestnicy (opcjonalny bezpieczny załącznik) → noclegi/rezerwacje → skrócone dni → lista spraw otwartych.

## 10. Kryteria akceptacji

Pilot potrafi znaleźć kontakt, następny nocleg i godziny kluczowych biletów w kilkanaście sekund; brak niepotwierdzonych wartości prezentowanych jako pewne; PDF nie może być dostępny przez publiczny link planera.

**Powiązania:** [security](../../architecture/security.md) · [advanced](advanced.md) · [pola](../../system-data/template-fields.md).
