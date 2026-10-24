# Walidacja treści i faktów

## 1. Dlaczego

Materiał marketingowy i oferta zawierają deklaracje dla klienta, a rozpiska pilota może wpływać na organizację prawdziwej podróży. Model językowy tworzy draft, ale nie może samodzielnie gwarantować dostępności, cen, bezpieczeństwa ani rzetelności faktów historycznych.

## 2. Trzy poziomy kontroli

1. **Strukturalny:** wymagane pola, typy, zakresy, maksymalna długość, unikatowe identyfikatory dni, poprawne daty i kolejność.
2. **Faktyczny/logistyczny:** źródła miejsc i tras, zgodność rezerwacji, lotów, hotelu, dat, cen i statusów, sezonowość.
3. **Publikacyjny:** odpowiedni odbiorca, zdjęcia na właściwej licencji, brak danych poufnych, zatwierdzenie człowieka.

## 3. Klasy danych

| Typ informacji | Kto / co może potwierdzić | Reguła |
|---|---|---|
| Miejsce na mapie | Google Places / organizator | Dopasowanie miejsca nie potwierdza godzin otwarcia |
| Czas/dystans trasy | Google Routes / sprawdzona trasa | Szacunek przypisany do konkretnego wariantu i daty sprawdzenia |
| Godziny lotów i promów | Przewoźnik / dokument rezerwacji | Wymaga lokalnej strefy, daty i potwierdzenia |
| Nocleg | Obiekt / operator / rezerwacja | `confirmed` tylko po potwierdzeniu |
| Cena i świadczenia | Uprawniony organizator TRIPSE | Model nie tworzy kwoty ani warunków |
| Warunki bezpieczeństwa | Organizatorka/organizator i aktualne źródła oficjalne | Nie publikować automatycznie |
| Historia / przyroda / kultura | Merytoryczne źródło i przegląd redakcyjny | Konkretne źródło + data dostępu |
| Opis marketingowy | Autor + recenzent | Dopuszcza interpretację, nie fikcyjne obietnice |

## 4. System statusów

`unverified`: brak potwierdzenia; `proposed`: hipoteza lub wersja robocza; `verified`: potwierdzone w ustalonym zakresie i momencie; `rejected`: odrzucone. W każdym przypadku przechowuj `source_type`, `source_ref` i `verified_at`, o ile istnieją. Dla zmiennych faktów `verified` może stracić aktualność — to nie jest dożywotnia gwarancja.

## 5. Co generuje AI

**Dozwolone:** propozycja atrakcyjnego nagłówka, streszczenie planu, redakcja opisu dnia, klasyfikacja treści pod sekcje, szkic ciekawej narracji podpartej źródłem.

**Niedozwolone bez potwierdzenia:** nadanie ceny, wskazanie dostępnego hotelu jako zarezerwowanego, wydłużenie programu o nieistniejące atrakcje, automatyczne ustalenie liczb miejsc, wymyślenie godzin lotów i rezerwacji, twierdzenie o bezpieczeństwie danej trasy, „źródło: Parks Canada” bez faktycznego odnośnika do materiału.

## 6. Materiały merytoryczne — proces

1. Weź wyłącznie atrakcje z `TripDay.stops`.
2. Zbierz niezależne źródła (preferuj urzędy parków, muzea, instytucje naukowe, oficjalne przewodniki).
3. Wpisz dla ważnych faktów konkretny URL, tytuł i datę sprawdzenia.
4. Ułóż tekst w bloki: atrakcje, najważniejsze fakty, kontekst, obserwacje, historie.
5. Oznacz bez źródła jako `unverified` i nie publikuj jako faktu.
6. Poproś pilota lub recenzenta merytorycznego o akceptację.

## 7. Sprawdzanie spójności harmonogramu

- `day_number` rośnie w wycieczce; daty odpowiadają zakresowi wyjazdu.
- Przejazd kończy się przed kolejną aktywnością, z uwzględnieniem przejścia przez północ i strefy.
- Czas dnia nie przekracza fizycznie dostępnych godzin bez jawnego oznaczenia nocnego przejazdu.
- Godziny biletów nie są zduplikowane pomiędzy dniami przez pomyłkę.
- `estimated_duration` nie staje się automatycznie `confirmed_duration`.
- Brak wartości nie zostaje zamieniony na `0`.

## 8. Kontrola poufności

Blokuj obecność `participant`, `reservation_pin`, `access_code`, `internal_notes`, prywatnych kontaktów i identyfikatorów rezerwacji w publicznych szablonach. Mechanizm nie może bazować tylko na wykrywaniu słów; dane muszą być izolowane strukturalnie i whitelistowane per szablon. Dodatkowy skan dokumentu jest zabezpieczeniem uzupełniającym.

## 9. Raport walidacji

Zwracaj tablicę `{rule_id, severity, field_path, message, suggested_action}`. `severity`: `error` blokuje, `warning` wymaga świadomej akceptacji, `info` informuje. Raport musi być widoczny w panelu i testowalny bez uruchamiania AI.

## 10. Warunki akceptacji

Testy negatywne na fikcyjne ceny, brak strefy czasowej, niezweryfikowaną trasę, złe zdjęcie, ukryte PII, brak źródeł ciekawostek i niepotwierdzoną rezerwację. Finalny eksport blokuje co najmniej każdy błąd `error`.

**Powiązania:** [workflow](../general/document-workflow.md) · [security](../architecture/security.md).
