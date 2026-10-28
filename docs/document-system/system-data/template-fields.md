# Matryca pól szablonów

Stan implementacji lokalnej 2026-10-28: Aktualne nazwy pól i kontrakty PUT/preview/initialize opisuje instrukcja Document Studio. Wymagane role sekcji wyznacza konfiguracja SectionSpec, więc usunięcie/ukrycie nie usuwa obowiązku. Nazwy operations/pricing i workflow approved poniżej są specyfikacją przyszłą, a nie bieżącym API.

Szczegóły operacyjne: [Document Studio](../../DOCUMENT_STUDIO.md).

**Cel:** wskazać minimum wymagane dla **finalnego** dokumentu. Zapis draftu może następować pomimo braków — o tym, co blokuje eksport, decydują zasady poniżej. Pełna semantyka obiektów: [trip-data-model.md](trip-data-model.md).

## 1. Pola wspólne

| Pole | Oferty | Marketing | Pilot basic | Pilot advanced | Pilot knowledge |
|---|---|---|---|---|---|
| `trip.title` | MUST | dla każdej pozycji | MUST | MUST | MUST |
| `trip.days[]` | MUST | nie | MUST | MUST | MUST |
| `trip.dates` lub jawne `date_label` | MUST | MUST | MUST | MUST | w ramach planu |
| `document.language` | MUST | MUST | MUST | MUST | MUST |
| `document.template_version` | MUST | MUST | MUST | MUST | MUST |
| `assets.logo` (lub zaakceptowany fallback) | SHOULD | MUST | SHOULD | SHOULD | SHOULD |
| `document.audience/confidentiality` | MUST | MUST | MUST | MUST | MUST |

## 2. Oferty — dane handlowe

| Pole | private | self_guide | school | incentive |
|---|---|---|---|---|
| `offer.included[]`, `offer.excluded[]` | MUST | MUST | MUST | MUST |
| `offer.pricing` lub jawne `concept_only` | MUST | MUST | MUST | MUST |
| `offer.cta` | MUST | MUST | MUST | MUST |
| `trip.accommodation_summary` | MUST* | MUST* | jeśli obejmuje | MUST* |
| `trip.transport_summary` | MUST | MUST | MUST | MUST |
| `self_guide.guide_included=false` | — | MUST | — | — |
| `self_guide.support_scope` | — | MUST | — | — |
| `self_guide.customer_responsibilities[]` | — | MUST | — | — |
| `school.educational_goals[]` | — | — | MUST | — |
| `school.environmental_goals[]` | — | — | MUST | — |
| `school.integration_goals[]` | — | — | MUST | — |
| `school.age_range`, `school.group_size_assumption` | — | — | MUST | — |
| `school.supervision_responsibilities` | — | — | MUST | — |
| `incentive.event_objectives[]` | — | — | — | MUST |
| `incentive.team_size` | — | — | — | MUST |
| `incentive.hotel_highlight` | — | — | — | MUST* |

\* Gdy konkretny obiekt jest nieznany, można użyć potwierdzonego opisu **wymaganego standardu / proponowanego rozwiązania**, a nie fikcyjnej rezerwacji.

## 3. Marketing

`campaign.title`, `campaign.layout_variant`, `campaign.cta`, `campaign.trips[]` (>=1) to MUST. Każdy wpis: nazwa, kraj/region, `date_range_or_label`, `short_hook`, `photo` lub wyraźnie zaakceptowany wariant bez zdjęcia, `publication_status`. Nazwa pilota jest opcjonalna i wymaga potwierdzenia. Wariant `theme_collection` powinien mieć `theme` i powiązane elementy tematyczne.

## 4. Pilot basic

`operations.leader`, `operations.meetings[]` lub jawny brak zbiórki, `operations.flights[]` jeśli dotyczą, `operations.accommodation_bookings[]` jeśli są noclegi, `operations.activity_bookings[]` dla godzinowych rezerwacji, `trip.days[]`, `operations.open_items[]`, `operations.critical_contacts[]`. `participants[]` tylko gdy naprawdę potrzebne i dopuszczone przez politykę dostępu.

## 5. Pilot advanced

Cały zestaw `pilot.basic`, a także `trip.days[].schedule_items[]`, lokalna strefa czasu, `route.source/verification_status`, `risk_notes[]` i informacje o wyjątkach/planach alternatywnych dla dni z krytycznymi ryzykami. Odległości i czasy, jeśli niewiadome, muszą być jawnie nieustalone (a nie liczbą zero).

## 6. Pilot knowledge

Każdy opis dnia opiera się na rzeczywistych `stops[]`. Dla każdej publikowanej istotnej informacji wymagane są `body`, przypisanie `day_id/stop_id`, `sources[]`, `verification_status=verified` i zatwierdzenie redakcyjne. Układ zakłada informacje o atrakcjach, najważniejsze fakty, kontekst, obserwacje, narracje — sekcje można pominąć, jeśli brak sensownego materiału, ale nie wolno dopisywać fikcji.

## 7. Pola sterujące i poufność

- `document.confidentiality=public`: marketing; tylko dane publicznie zatwierdzone.
- `client`: oferta; tylko zakres wycieczki i handlowe dane dla odbiorcy.
- `internal`: wiedza pilota bez PII.
- `internal_restricted`: rozpiska pilota; dostępy indywidualne i audyt.
- `document.status`, `document.revision`, `data_snapshot_id`, `approved_by/at`, `generated_at` w metadanych każdego dokumentu.

## 8. Co oznacza „pole obowiązkowe”

- Na poziomie **draft**: brak → wyraźny komunikat i zapis roboczy.
- Na poziomie **review**: lista braków podzielona na `blocking` i `warning`.
- Na poziomie **final/approved**: brak `blocking` wstrzymuje publikację. Tryb `concept_only` może być dopuszczony dla oferty tylko po jawnej decyzji biznesowej TRIPSE [DO UZGODNIENIA].

## 9. Przykładowe reguły walidacji

`pricing.amount >= 0` tylko, gdy `pricing.status=approved`; `booking.status=confirmed` wymaga źródła potwierdzenia; `marketing.collection` nie może pobierać `Operations`; `self_guide.guide_included` musi być `false`; jeśli `school.group_size_assumption` nie jest określone, nie wolno publikować ceny per uczestnik jako ostatecznej; `pilot.knowledge` nie może mieć nieudokumentowanego źródła dla faktu.

**Powiązania:** [katalog](../general/template-catalog.md) · [walidacja](content-validation.md).
