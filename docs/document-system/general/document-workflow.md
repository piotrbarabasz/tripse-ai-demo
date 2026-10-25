# Przepływ tworzenia dokumentu

## 1. Główna ścieżka

1. **Wybierz wycieczkę** z bazy lub utwórz ją z formularza. [ETAP PÓŹNIEJSZY] Zaimportuj dłuższy plan z istniejącego planera (przez adapter).
2. **Wybierz typ i wariant** dokumentu z katalogu; panel zna wymagane pola i poufność.
3. **Zbuduj draft**: system mapuje dane wycieczki do szablonu, pokazuje brakujące wymagane informacje.
4. **Uzupełnij i edytuj**: pola formularza, kolejność dopuszczonych sekcji, zdjęcia, opisy; opcjonalne podpowiedzi AI.
5. **Waliduj**: wymagane dane, zgodność dat i logistyki, licencje zdjęć, statusy potwierdzenia oraz brak wycieku danych prywatnych.
6. **Podgląd**: strony A4 lub karty marketingowe z widocznymi ostrzeżeniami; podgląd nie jest automatycznie publikacją.
7. **Zatwierdź**: uprawniony użytkownik sprawdza treść; przy istotnej zmianie danych dokument wraca do draftu.
8. **Eksportuj**: deterministyczna generacja PDF / obrazu z danego snapshotu; wynik otrzymuje metadane i historię.
9. **Pobierz lub udostępnij** według polityki danego dokumentu. Publiczny link nigdy nie odblokowuje materiałów pilota.

## 2. Statusy dokumentu

`draft` → `needs_review` → `approved` → `generated` → `archived`

Dodatkowe stany techniczne zadania renderowania: `queued`, `running`, `succeeded`, `failed`. Status dokumentu opisuje akceptację treści; status zadania opisuje wykonanie operacji. Nie należy ich mieszać.

Zmiany po `approved`: utwórz nową rewizję `draft` i zachowaj wcześniejszą. Błąd renderowania nie powoduje automatycznej utraty zatwierdzenia, lecz blokuje wydanie nowego pliku.

## 3. Zachowanie przy brakach

| Brak / niepewność | Zachowanie panelu | Zachowanie eksportu |
|---|---|---|
| Brak terminu | Pokazuje `Termin do ustalenia` | Możliwy tylko dla ofert konceptowych, jeśli zatwierdzono taki tryb |
| Brak ceny | Ostrzeżenie i pole do uzupełnienia | Oferta handlowa blokowana, chyba że zatwierdzono wersję bez ceny |
| Hotel proponowany, nie potwierdzony | Etykieta `Proponowany obiekt` | Nie wolno użyć `Zarezerwowano` |
| Niezweryfikowana atrakcja/trasa | Jawny status źródła | Opcjonalna sugestia, nie fakt |
| Brak prawa do zdjęcia | Ostrzeżenie krytyczne | Blokada publicznego eksportu z tym zdjęciem |
| Dane kontaktowe/rezerwacyjne w marketingu | Ostrzeżenie bezpieczeństwa | Blokada eksportu |
| Brak planu B w `pilot.advanced` | Ostrzeżenie lub blokada zależna od oznaczonego ryzyka | Nie ukrywaj ryzyka |

## 4. Edycja i AI

- AI może zaproponować opis, skrót, ciekawostkę lub hasło; edytor pokazuje, co powstało automatycznie.
- AI nie może samodzielnie zmieniać danych źródłowych o cenie, statusie rezerwacji, locie, noclegu, wymaganiach zdrowotnych lub bezpieczeństwie.
- Każde pole posiada `value`, `source`, `verification_status` i opcjonalne `last_verified_at`; ograniczenia szczegółowo opisano w [content-validation.md](../system-data/content-validation.md).
- Podgląd dokumentów poufnych wymaga uwierzytelnienia tak samo jak pobranie.

## 5. Obsługa wyjątków

- Niepowodzenie AI: pozostaje ręczny formularz i zapis draftu.
- Brak zdjęć: użyj bezpiecznego wariantu bez zdjęcia; brak obrazu nie może rozwalać layoutu.
- Zbyt długi tekst: dziel treść na kolejne strony, nie zmniejszaj globalnie fontu.
- Błąd renderowania: komunikat z identyfikatorem zadania i możliwością ponowienia; żadnego fałszywego sukcesu.
- Równoczesne edycje: MVP może używać blokady optymistycznej `revision`; nie nadpisuj po cichu cudzej pracy.

## 6. Role w procesie

Autor edytuje → recenzent zatwierdza → uprawniony użytkownik eksportuje/udostępnia. W małym zespole jedna osoba może pełnić kilka ról, ale log operacji powinien zachować informacje, kto i kiedy to zrobił. Model uprawnień: [security.md](../architecture/security.md).

## 7. Kryteria akceptacji przepływu

Dla jednej wycieczki utworzenie dwóch dokumentów nie duplikuje danych wycieczki; usunięcie lub podmiana zdjęcia w draftcie nie zmienia starego zatwierdzonego eksportu; brak krytycznego pola jest widoczny przed publikacją; zapis nie zależy od działającego WhatsApp.
