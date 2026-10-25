# Szablon: oferta firmowa / incentive

**ID:** `offer.incentive`  
**Rodzina:** `offer` · **Odbiorca:** firma, HR, zarząd, organizator wydarzenia  
**Poufność:** oferta dla klienta biznesowego, bez wewnętrznych danych operacyjnych  
**Format początkowy:** PDF A4, orientacyjnie 4–7 stron.

## 1. Cel i odbiorca

Sprzedać wartość wspólnego wyjazdu dla zespołu: integrację, doświadczenie, ewentualnie warsztaty/szkolenia. Wyróżnikiem względem innych ofert jest **istotnie bardziej rozbudowana prezentacja noclegu i infrastruktury hotelowej**.

## 2. Charakterystyka dokumentu

Ton profesjonalny, konkretny, premium tam, gdzie wynika to z programu. Unikać zbyt turystycznej listy atrakcji bez odniesienia do celu firmowego.

## 3. Sekcje obowiązkowe

1. Okładka — nazwa wydarzenia (jeśli znana), miejsce, termin, zdjęcie, logo TRIPSE; branding klienta wyłącznie za zgodą.
2. Cel wyjazdu i krótka propozycja wartości dla zespołu.
3. Najważniejsze moduły programu: integracja, wypoczynek, aktywności, szkolenia (jeśli oferowane).
4. Program dzienny — logiczne bloki: aktywności, przerwy, posiłki, wydarzenia wieczorne.
5. **Rozbudowana sekcja noclegu** — zdjęcia obiektu, lokalizacja, standard, typ pokoi, posiłki, przestrzenie wspólne, udogodnienia; tylko informacje potwierdzone lub opisane jako propozycja.
6. Warsztaty / elementy szkoleniowe — cel, formuła, sprzęt, prowadzący, jeśli potwierdzeni; jeśli nie dotyczy, jawny brak zamiast sztucznej sekcji.
7. Transport i obsługa logistyczna.
8. Warianty/pakiety, lista świadczeń i wyłączenia.
9. Cena, założona liczba uczestników, warunki i kontakt.

## 4. Sekcje opcjonalne

Sale konferencyjne, układ miejsc, sprzęt AV, branding wydarzenia, kolacja tematyczna, team building, alternatywny hotel, plan pogodowy, wariant jednodniowy/wyjazdowy, harmonogram płatności.

## 5. Wymagane dane wejściowe

`incentive.event_objectives[]`, `incentive.team_size`, `incentive.integration_activities[]`, `incentive.training_modules[]` (może być pusta), `incentive.hotel_highlight` lub opis standardu obiektu, `trip.days[]`, `trip.transport_summary`, `trip.meals`, `offer.pricing`, `offer.included[]`, `offer.excluded[]`, `offer.cta`.

Dla hotelu: `name`, `status`, `location`, `rooming`, `amenities[]`, `meeting_spaces[]`, `image_asset_ids[]`; w przypadku nieustalonego obiektu specyfikuj tylko wymagania i klasę propozycji.

## 6. Zasady prezentacji treści

- **Hotel ma mieć mocniejszy akcent wizualny niż w `offer.private`**; ważny jest nie tylko nocleg, ale przestrzeń integracyjna i szkoleniowa.
- Nie dopisywać dostępnej sali, internetu, parkingu, cateringu czy wyposażenia bez potwierdzenia.
- Nie sugerować gwarantowanych rezultatów integracyjnych/szkoleniowych.
- Wyraźnie rozdzielać „proponowany wariant A/B” i „potwierdzona usługa”.
- Nie dodawać prywatnych danych pracowników uczestniczącej firmy.

## 7. Wymagania wizualne specyficzne dla typu

Wydzielony pełnoszerokościowy moduł „Obiekt i zakwaterowanie”, mini-galeria 2–4 zweryfikowanych zdjęć, ikonografia usług, czytelna agenda. Sekcja wariantów i ceny w układzie porównawczym.

## 8. Obsługa brakujących informacji

Nieznana liczba uczestników → wycena oznaczona jako wstępna albo blokada finalnej oferty. Niepotwierdzony hotel → „przykładowy obiekt” lub sekcja „wymagany standard”, bez przyrzeczenia. Brak informacji o sali szkoleniowej → nie umieszczaj jej w świadczeniach.

## 9. Przykładowa struktura dokumentu

Okładka → cele zespołu → highlights → program → **hotel i przestrzenie wspólne** → warsztaty/integracja → logistyka → warianty i wycena → kontakt.

## 10. Kryteria akceptacji

Kierownik HR umie odpowiedzieć: co zespół robi, gdzie śpi, jak wygląda standard obiektu, jak są zorganizowane posiłki/transport, co wynika z integracji/szkoleń i jakie są koszty oraz warianty. Żaden obiekt ani usługa nie są podawane jako potwierdzone bez weryfikacji.

**Powiązania:** [styl](../../design/brand-guidelines.md) · [pola](../../system-data/template-fields.md).
