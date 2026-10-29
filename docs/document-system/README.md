# TRIPSE AI — system dokumentów i szablonów

**Wersja dokumentacji:** 1.0-draft  
**Data bazowa:** 2026-10-24  
**Status:** dokumentacja łączy specyfikację docelową z implementacją. Stan lokalny
2026-10-28: wszystkie osiem typów, wspólne sekcje, snapshoty i roboczy PDF działają;
[aktualna instrukcja i granice](../DOCUMENT_STUDIO.md). Workflow zatwierdzania, AI
i eksport serwerowy opisane dalej pozostają propozycjami.
**Lokalizacja:** `docs/document-system/` w repozytorium `tripse-ai-demo`.

Bieżący etap [DOC-TEMPLATES-006](../DOC_TEMPLATES_006.md): dziewięć chronionych
przykładów GT v1, kopie do istniejących edytorów, szablony 0.5.0.
[Ground Truth](general/template-content-ground-truth.md) pozostaje **DRAFT / DO WALIDACJI Z TRIPSE**.

## Po co istnieje ten moduł

Jeden uporządkowany opis wycieczki ma zasilać wiele dokumentów: oferty dla klientów, materiały marketingowe i wewnętrzne materiały dla pilotów. Użytkownik wybiera rodzaj dokumentu, uzupełnia brakujące dane i zdjęcia, ogląda podgląd, zatwierdza treść i eksportuje PDF. Dane niepewne muszą być oznaczane; system nie może wymyślać cen, rezerwacji ani potwierdzać dostępności.

## Mapa dokumentacji

| Kategoria | Pliki | Kiedy czytać |
|---|---|---|
| [General](general/overview.md) | [overview](general/overview.md), [template-catalog](general/template-catalog.md), [document-workflow](general/document-workflow.md) | Zakres produktu, katalog i przebieg pracy |
| [Templates](templates/offers/private.md) | 4 oferty, marketing, 3 materiały pilota | Budowanie określonego szablonu |
| [Design](design/brand-guidelines.md) | [brand-guidelines](design/brand-guidelines.md), [layout-rules](design/layout-rules.md), [asset-guidelines](design/asset-guidelines.md) | Logo, fonty, układy, zdjęcia |
| [Data](system-data/trip-data-model.md) | [trip-data-model](system-data/trip-data-model.md), [template-fields](system-data/template-fields.md), [content-validation](system-data/content-validation.md) | Dane, mapowanie, statusy i kontrola faktów |
| [Architecture](architecture/system-architecture.md) | [system-architecture](architecture/system-architecture.md), [gcp-deployment](architecture/gcp-deployment.md), [security](architecture/security.md) | Backend, GCP, uprawnienia |
| [Development](development/roadmap.md) | [roadmap](development/roadmap.md), [acceptance-criteria](development/acceptance-criteria.md) | Realizacja i testowanie |

## Jak czytać wymagania

- **MUST** — warunek konieczny dla publikowalnego dokumentu danego typu.
- **SHOULD** — rekomendowany standard, możliwe świadome odstępstwo.
- **MAY** — opcjonalna funkcja lub sekcja.
- **[DO UZGODNIENIA]** — propozycja autora, niepotwierdzona decyzja TRIPSE.
- **[ETAP PÓŹNIEJSZY]** — poza pierwszym MVP.

**Źródło prawdy**: opis wspólny znajduje się w `design/` i `data/`, a konkretny wygląd/zawartość dokumentu — w `templates/`. Nie kopiuj globalnych zasad kolorów i modeli danych do każdego szablonu.

## Historyczna kolejność przygotowania (2026-10-24)

1. Zdefiniuj katalog i identyfikatory w [template-catalog.md](general/template-catalog.md).
2. Zatwierdź słownik pól w [trip-data-model.md](system-data/trip-data-model.md) i [template-fields.md](system-data/template-fields.md).
3. Zatwierdź identyfikację marki w [brand-guidelines.md](design/brand-guidelines.md).
4. Zrób MVP: `marketing.collection`, `pilot.basic`, `offer.private` — patrz [roadmap.md](development/roadmap.md).
5. Każdy eksport musi przejść [content-validation.md](system-data/content-validation.md) oraz [acceptance-criteria.md](development/acceptance-criteria.md).

## Powiązanie z istniejącym repozytorium

Przegląd `master` z 2026-10-24: aplikacja FastAPI, SQLite i osobny worker do planowania; opcjonalny adapter WhatsApp (WAHA), Google Places/Routes i prosty viewer HTML/JS. Brak potwierdzonej implementacji edytora dokumentów i PDF. Według README testy lokalne przechodziły w trybie MOCK; nie należy traktować tego jako potwierdzenia produkcyjnego wdrożenia na GCP.

Obecny model kandydata planera ogranicza `day` do 1–2, a liczbę kandydatów do 8. Generator dłuższych wycieczek wymaga **nowego uniwersalnego modelu wycieczki** i adaptera planera, nie samej zmiany promptu. Nie zmieniaj istniejącego planera przy wdrażaniu fundamentów dokumentów bez uzgodnionego tasku.

## Materiały źródłowe wykorzystane przy opracowaniu

- Przesłana grafika „Pilotażowe nowości 2027” / „Wyprawy górskie” — wzorzec rodzaju materiału marketingowego, **nie zatwierdzony brand book**.
- „WZÓR PODSTAWOWEJ ROZPISKI 04–13.08 Road Trip” (5 stron) — uczestnicy, loty, rezerwacje, noclegi i notatki pilota.
- „Kanada — program / plan wyprawy” (16 stron) — szczegółowy czasowy przebieg dni, przejazdy, dystanse, noclegi.
- „Kanada_USA_ciekawostki_atrakcje_Dzien_3-15” (39 stron) — powtarzalny układ wiedzy i storytellingu na dzień.
- Istniejące repozytorium `https://github.com/piotrbarabasz/tripse-ai-demo`.

Przykładowe PDF-y i grafika **nie są dołączone** do ZIP-a: mogą zawierać dane osobowe, dane rezerwacyjne oraz cudze fotografie. Specyfikacja nie zawiera ich kodów PIN ani numerów rezerwacji.

## Nierozstrzygnięte decyzje przed publikacją pierwszej oferty

Oryginalne logo i prawo używania zdjęć; oficjalna paleta i fonty; odpowiedzialny za zatwierdzanie ceny/terminów; dokładny zakres Self-Guide; minimalny zestaw danych pilota; sposób logowania i magazyn danych na GCP; czy docelowo poza PDF wymagane są edytowalne pliki.
