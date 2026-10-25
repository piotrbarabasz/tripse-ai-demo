# Katalog szablonów

## Konwencja

`template_id` jest stabilnym identyfikatorem używanym w API i danych; nazwa dla użytkownika może się zmieniać. Każdy szablon ma `family`, `audience`, `confidentiality`, `template_version`, wariant układu i zestaw walidowanych pól. Szablon nie jest tożsamy z pojedynczym PDF-em.

## Oferty klientowskie

| `template_id` | Nazwa UI | Szczególna cecha | Specyfikacja |
|---|---|---|---|
| `offer.private` | Wyjazd indywidualny | Personalizacja, warianty, wycena | [private.md](../templates/offers/private.md) |
| `offer.self_guide` | Self-Guide | Brak pilota, precyzyjny zakres wsparcia | [self-guide.md](../templates/offers/self-guide.md) |
| `offer.school` | Wycieczka szkolna | Edukacja, środowisko, integracja, opieka | [school.md](../templates/offers/school.md) |
| `offer.incentive` | Wyjazd firmowy / incentive | Wyeksponowany nocleg, szkolenia i integracja | [incentive.md](../templates/offers/incentive.md) |

Domyślne formaty: PDF A4 pion, warianty ilości treści: `standard` i ewentualnie `short` [ETAP PÓŹNIEJSZY]. Oferta nie zawiera danych rezerwacyjnych ani indywidualnych danych uczestników.

## Marketing

| `template_id` | Nazwa UI | Wariant `layout_variant` | Specyfikacja |
|---|---|---|---|
| `marketing.collection` | Nowości / kolekcje | `new_trips`, `theme_collection` | [collections.md](../templates/marketing/collections.md) |

Jedna rodzina z dwoma układami zamiast dwóch silników. Możliwe wyjścia: PDF A4 do druku, obraz 1080×1350, ewentualnie seria stron/kart. **Nie upychaj wszystkich pozycji kosztem czytelności.**

## Materiały pilota

| `template_id` | Nazwa UI | Szczególna cecha | Specyfikacja |
|---|---|---|---|
| `pilot.basic` | Rozpiska podstawowa | Kontakt, logistyka, rezerwacje, skrót dni | [basic.md](../templates/pilots/basic.md) |
| `pilot.advanced` | Rozpiska zaawansowana | Harmonogram minutowy, trasy, ryzyka, plan B | [advanced.md](../templates/pilots/advanced.md) |
| `pilot.knowledge` | Materiały merytoryczne | Historia, przyroda, ciekawostki, narracje | [knowledge.md](../templates/pilots/knowledge.md) |

Dokumenty `pilot.basic` i `pilot.advanced` są **wewnętrzne i ograniczone dostępem**. `pilot.knowledge` nie powinien z zasady zawierać danych osób ani dostępowych; pozostaje wewnętrzny do czasu odrębnej decyzji publikacyjnej.

## Rejestr wariantów

Wersja startowa nie mnoży wariantów dla każdego szablonu. Wariant jest uzasadniony tylko przy rzeczywistej różnicy układu i pól (np. katalog wielu wyjazdów vs. kolekcja górska); język, zdjęcia, terminy i liczba dni są danymi, a nie osobnymi typami szablonów.

## Reguły wersjonowania

- `template_id` nie zmienia się po zmianie koloru czy odstępów.
- `template_version` (np. `1.0.0`) zmienia się przy zmianie zachowania/układu/obowiązkowych sekcji.
- `document_revision` rośnie przy edycji treści dokumentu.
- `data_snapshot_id` wskazuje dokładnie użyte dane, a zapisany wynik eksportu powiązany jest z tą rewizją.
- Nie nadpisuj zatwierdzonego dokumentu bez nowej rewizji.

## Wymagania wspólne

Logo (jeśli dostępne), tytuł, wyraźny typ/odbiorca, data i/lub termin wycieczki, wersja, spójne formatowanie, źródła gdy potrzebne, walidacja braków i bezpieczny eksport. Konkretny minimalny zestaw pól: [template-fields.md](../system-data/template-fields.md).

## Rejestr otwartych decyzji

[DO UZGODNIENIA] Dokładne nazwy widoczne klientom; wersje językowe; czy oferty sprzedażowe mogą być udostępniane bez ceny; czy publiczne marketingowe grafiki wymagają prawnych dopisków; czy materiały pilota mają mieć wariant bez danych osobowych.
