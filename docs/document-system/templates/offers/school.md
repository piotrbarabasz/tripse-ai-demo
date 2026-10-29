# Szablon: oferta wycieczki szkolnej

Stan implementacji lokalnej 2026-10-28 (szablony 0.4.0): OfferData + OfferDetails: wiek, liczebność, opieka i cele trzech filarów z day_id/stop_id. Nie ma automatycznych efektów edukacyjnych ani gwarancji bezpieczeństwa.

Instrukcja edycji i ograniczenia publikacji: [Document Studio](../../../DOCUMENT_STUDIO.md).
Poniżej zachowano wymagania docelowe i inspiracje; nie oznaczają automatycznej akceptacji treści.

**ID:** `offer.school`  
**Rodzina:** `offer` · **Odbiorca:** szkoła, nauczyciel, osoba organizująca wyjazd  
**Poufność:** dokument klientowski (bez list imiennych uczniów)  
**Format początkowy:** PDF A4, orientacyjnie 3–6 stron.

Aktualizacja DOC-TEMPLATES-006: lokalny szablon 0.5.0, uzupełniony przykład GT v1
i kopia do edycji przez `#examples`. Pola, kolejność oraz granice weryfikacji:
[raport implementacji](../../../DOC_TEMPLATES_006.md). Specyfikacja poniżej
nie oznacza zatwierdzenia biznesowego Ground Truth.

## 1. Cel i odbiorca

Pokazać, że wycieczka wnosi korzyść **edukacyjną, środowiskową i integracyjną**, a jednocześnie jest zrozumiała organizacyjnie. Nauczyciel musi ocenić program, obciążenie grupy, rolę opiekunów i założenia ceny.

## 2. Charakterystyka dokumentu

Najpierw cele wychowawczo-edukacyjne i aktywności, potem harmonogram. Unikać pustych sloganów edukacyjnych. Każdy istotny cel powinien wskazywać rzeczywistą atrakcję lub zadanie w programie.

## 3. Sekcje obowiązkowe

1. Okładka — kierunek, termin, sugerowana grupa wiekowa/liczebność, logo.
2. **Cele wyjazdu** — edukacja, środowisko/przyroda, integracja; powiązanie z konkretnymi punktami planu.
3. Korzyści dla uczniów i organizatora — bez obiecywania certyfikacji, której nie potwierdzono.
4. Program dzień po dniu — atrakcje, aktywności, orientacyjne czasochłonności i przerwy.
5. Transport, posiłki, zakwaterowanie (jeśli obejmuje), organizacja zbiórek.
6. **Opieka i bezpieczeństwo organizacyjne** — obowiązki TRIPSE i szkoły, opieka, wymagania uczestnictwa, uzgodnione procedury; bez automatycznych gwarancji.
7. Zakres świadczeń i wyłączenia.
8. **Wycena** — na uczestnika lub grupę, z liczbą uczestników, zasadami dotyczącymi opiekunów, warunkami i terminem ważności, jeśli podano.
9. Kontakt i następne kroki.

## 4. Sekcje opcjonalne

Warsztaty, zadania terenowe, materiały dla nauczyciela, wariant pogody, informacje o dostępności, tematy interdyscyplinarne, program dla różnych roczników, wariant cenowy.

## 5. Wymagane dane wejściowe

`school.educational_goals[]`, `school.environmental_goals[]`, `school.integration_goals[]`, `school.age_range`, `school.group_size_assumption`, `school.supervision_responsibilities`, `trip.days[]`, `trip.meals`, `trip.transport_summary`, `trip.accommodations`, `offer.pricing`, `offer.included[]`, `offer.excluded[]`, `offer.cta`.

Dla każdej aktywności edukacyjnej: `activity_id`, `learning_outcome`, `location`, `duration_estimate`, `source`/status. [DO UZGODNIENIA] Standard wewnętrznej kwalifikacji ryzyka i szczegółowy podział odpowiedzialności szkoła/TRIPSE.

## 6. Zasady prezentacji treści

- Powiąż cel z programem: „obserwacja form polodowcowych” ⇄ konkretny punkt trasy, nie ogólna deklaracja.
- Jednoznacznie wskazuj, które zajęcia są prowadzone przez uprawnionych specjalistów, jeżeli taki fakt potwierdzono.
- Nie umieszczaj imion, telefonów, danych medycznych ani list obecności uczniów w ofercie.
- Dodatkowe regulacje i standardy opieki podlegają aktualnej weryfikacji prawnej/organizacyjnej; nie generuj ich jako pewników z modelu.

## 7. Wymagania wizualne specyficzne dla typu

Wyraźne trzy wyróżniki edukacja/przyroda/integracja, czytelna agenda, tabela założeń cenowych. Zdjęcia pokazują rzeczywiste miejsca lub uprawnione zdjęcia grupowe z odpowiednimi zgodami.

## 8. Obsługa brakujących informacji

Brak liczebności grupy → brak ceny „na osobę” w trybie finalnym. Brak uzgodnień opieki → blokada oferty finalnej. Brak weryfikacji zdjęć dzieci → użyj krajobrazu lub innej legalnej grafiki.

## 9. Przykładowa struktura dokumentu

Okładka → 3 filary wartości → ramowy program → szczegóły logistyczne i opieka → świadczenia, cena i kontakt.

## 10. Kryteria akceptacji

Co najmniej jeden sprawdzalny punkt programu na każdy deklarowany główny cel, jasne założenia grupy i ceny, zrozumiały zakres obowiązków, brak danych uczniów oraz brak niepotwierdzonych obietnic bezpieczeństwa.

**Powiązania:** [pola](../../system-data/template-fields.md) · [walidacja](../../system-data/content-validation.md).
