# Szablon: oferta Self-Guide (bez pilota)

**ID:** `offer.self_guide`  
**Rodzina:** `offer` · **Odbiorca:** klient podróżujący samodzielnie  
**Poufność:** dokument klientowski  
**Format początkowy:** PDF A4, orientacyjnie 4–7 stron.

## 1. Cel i odbiorca

Sprzedać i jasno wyjaśnić wyjazd, w którym **nie ma pilota prowadzącego na miejscu**. Klient musi zrozumieć, co jest gotowe i zorganizowane, co wykona samodzielnie oraz jaka pomoc rzeczywiście jest dostępna.

## 2. Charakterystyka dokumentu

Oferta łączy atrakcyjny opis kierunku z ponadprzeciętnie czytelną logistyką. Informacje o niezależności klienta nie mogą być ukryte w przypisach. Plan ma być wykonalny, ale status rezerwacji, tras i usług zawsze wynika z danych.

## 3. Sekcje obowiązkowe

1. Okładka z kierunkiem, terminem/status terminu i fotografią.
2. „Jak działa Self-Guide” — brak pilota, rola TRIPSE i podróżnika, poziom samodzielności.
3. Podsumowanie trasy i głównych atrakcji.
4. Plan dzień po dniu: start i koniec etapu, główne aktywności, przewidziany transport, orientacyjny czas/poziom trudności.
5. Zakwaterowanie i zasady przemieszczania się.
6. **Co klient otrzymuje** — tylko faktycznie oferowane mapy, materiały, bilety, rezerwacje lub wsparcie.
7. **Zakres wsparcia oraz wyłączenia** — kanał kontaktu, ramy dostępności, co dzieje się w razie zmian i awarii; do uzupełnienia przez TRIPSE.
8. Lista świadczeń objętych ceną i nieobjętych ceną.
9. Cena, warunki, wymagania uczestnictwa i CTA lub jawny tryb konceptowy.

## 4. Sekcje opcjonalne

Linki/QR do map, pobieranie offline, etapy alternatywne, checklista sprzętu, informacje o zasięgu/roamingu, FAQ, link do wirtualnego briefingu. **Rozmowa online z grupą przed wyjazdem to [ETAP PÓŹNIEJSZY]** — nie umieszczać jej jako gwarantowanego świadczenia, dopóki nie będzie uzgodniona i wdrożona.

## 5. Wymagane dane wejściowe

Pola oferty: `trip.days[]`, `trip.difficulty`, `trip.transport_summary`, `trip.accommodations`, `offer.included[]`, `offer.excluded[]`, `offer.pricing`, `offer.cta`; specyficzne: `self_guide.guide_included=false`, `self_guide.customer_responsibilities[]`, `self_guide.support_scope`, `self_guide.deliverables[]`, `self_guide.emergency_process` (informacja zweryfikowana przez TRIPSE), `trip.route_links[]` opcjonalnie.

## 6. Zasady prezentacji treści

- Oświadczenie „wyjazd bez pilota” pojawia się już w pierwszym widocznym bloku.
- Rozdziel „zaplanowaliśmy”, „rezerwujemy”, „zapewniamy”, „uczestnik organizuje sam” — słowa odpowiadają rzeczywistemu zakresowi usługi.
- Oddziel szacowany czas przejazdu od potwierdzonych danych dostawcy map.
- W sekcji bezpieczeństwa podawaj konkretne instrukcje tylko po weryfikacji, bez obietnic całodobowego wsparcia z automatu.

## 7. Wymagania wizualne specyficzne dla typu

Dzienny plan w formie czytelnych etapów, ikony transportu i oznaczenie poziomu trudności; na pierwszych stronach wyróżniony blok „Samodzielnie / Z pomocą TRIPSE”. QR/linki muszą pozostawać skanowalne po wydruku.

## 8. Obsługa brakujących informacji

Brak uzgodnionego `support_scope` blokuje finalną ofertę. Brak potwierdzonego biletu oznacza „bilet do organizacji”, a nie „zapewniony”. Brak zweryfikowanego linku do trasy powoduje ukrycie QR i ostrzeżenie w edytorze.

## 9. Przykładowa struktura dokumentu

Okładka → Self-Guide w praktyce → mapa i zalety → program dnia 1–N → logistyka → zakres organizacji i wsparcia → świadczenia, cena i kontakt.

## 10. Kryteria akceptacji

Czytelnik bez kontaktu z organizatorem potrafi wskazać: czy pilot jedzie, kto dokonuje rezerwacji, kto organizuje transport, co dostanie przed podróżą, kiedy i jak może liczyć na pomoc. Nieoparte na danych deklaracje są blokowane przed publikacją.

**Powiązania:** [model danych](../../data/trip-data-model.md) · [bezpieczeństwo](../../architecture/security.md).
