# Roadmapa wdrożenia Document System

**Status:** plan roboczy; poszczególne zadania wymagają estymacji po wyborze backendu danych i rendererów. Nie deklaruje, że którakolwiek faza jest zaimplementowana.

## Etap 0 — dokumentacja, akceptacja i przykłady

**Wynik:** jeden zaakceptowany słownik typów/pól, zatwierdzone podstawowe zasady wizualne i trzy szkice układu.

1. Uzgodnić nazwy typów, docelowego odbiorcę i część wspólnych pól.
2. Pozyskać oryginalne logo i informację o prawach do zdjęć, wybrać fonty/kolory.
3. Przygotować projekt marketing / oferta / operacje na prawdziwym, ale zanonimizowanym przykładzie.
4. Uzgodnić proces zatwierdzania cen, terminów i treści oraz administratorów dostępu.

**Done:** [katalog](../general/template-catalog.md) bez sprzeczności, trzy zaakceptowane przykładowe układy i lista nierozwiązanych decyzji, które nie blokują MVP.

## Etap 1 — MVP i trzy reprezentatywne szablony

**Kolejność:** `marketing.collection` (`new_trips`) → `pilot.basic` → `offer.private`.

1. `Trip`/`Days`/`Assets`/`DocumentDraft` oraz zapis rewizji.
2. Katalog szablonów i walidacja pól.
3. Biblioteka brandingu/zdjęć z informacją o licencji (minimum formularz + upload).
4. HTML/CSS renderer + PDF, prywatny podgląd, kontrola układu.
5. Formularz draftu, uzupełnianie danych i akceptacja.
6. Trzy pełne szablony i testy regresyjne.

**Done:** z jednej wycieczki powstają 3 poprawne, różne dokumenty; każdy podlega walidacji, ma numer rewizji i poprawne ograniczenia dostępu. PDF działa dla PL, długich nazw i brakujących zdjęć.

## Etap 2 — komplet katalogu

1. `offer.self_guide` (jasny zakres bez pilota).
2. `offer.school` (edukacja/środowisko/integracja).
3. `offer.incentive` (mocno widoczny nocleg i moduły firmowe).
4. `pilot.advanced` (harmonogram godzinowy, trasy i ryzyka).
5. `pilot.knowledge` (weryfikowalne źródła, narracje, ok. 3 strony/dzień).
6. `marketing.collection` z `theme_collection`, formatami social i paginacją.

**Done:** wszystkie identyfikatory katalogu renderują się z przewidywalnych danych, a różnice między typami są sprawdzane automatycznie.

## Etap 3 — GCP i operacyjność

1. Wybór bazy danych i migracja ze szkicu lokalnego, trwały storage.
2. Cloud Run API/panel i osobna ścieżka jobów do renderowania.
3. Uwierzytelnienie, uprawnienia, historia operacji, logi/audyt.
4. Deployment do prywatnego DEV, testy smoke i PDF po restarcie.
5. Kontrola kosztów oraz backup i retencja.

**Done:** dane i pliki przetrwały restart/nowy kontener, role uniemożliwiają publiczny dostęp do materiałów pilota, testowy panel jest stabilny.

## Etap 4 — integracje i usprawnienia [PÓŹNIEJSZY]

Adapter istniejącego planera do pełnego modelu wielodniowej wycieczki; import plików i programów; opcjonalne generowanie opisów AI ze źródłami; powiązanie z kanałem WhatsApp; rozmowa online dla Self-Guide przed wyjazdem; ewentualne formaty DOCX/Google Docs po potwierdzeniu potrzeb.

## Proponowane work packages dla agentów

| Paket | Zakres | Czytaj najpierw |
|---|---|---|
| `DS-01` | model danych i migracje | `data/*`, `architecture/system-architecture.md` |
| `DS-02` | rejestr szablonów + walidator | `general/template-catalog.md`, `data/template-fields.md` |
| `DS-03` | brand i renderer PDF | `design/*`, `architecture/system-architecture.md` |
| `DS-04` | marketing nowości | `templates/marketing/collections.md`, `design/*` |
| `DS-05` | pilot basic | `templates/pilots/basic.md`, `architecture/security.md` |
| `DS-06` | oferta private | `templates/offers/private.md`, `data/*` |
| `DS-07` | panel edycji i akceptacji | `general/document-workflow.md` |
| `DS-08` | zabezpieczenia i DEV GCP | `architecture/gcp-deployment.md`, `architecture/security.md` |

Każdy pakiet powinien mieć własne testy, granice zakresu i pliki wejściowe. Nie uruchamiać równocześnie migracji bazy i zmiany planera bez wspólnego kontraktu.

## Stop/go decyzje

**Przed implementacją PDF:** mamy zatwierdzone fonty i podstawowy wygląd? **Przed pilot.basic:** mamy zatwierdzone zasady poufności? **Przed publikacją marketingu:** mamy prawa do zdjęć? **Przed GCP:** wiadomo, kto utrzymuje domenę, bazę i koszty?

**Powiązania:** [kryteria](acceptance-criteria.md) · [przepływ](../general/document-workflow.md).
