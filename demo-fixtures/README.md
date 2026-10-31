# Przykładowe dokumenty TRIPSE — GT v1

Aktywny zestaw to `gt-v1/`: pięć programów Trip, dwie kampanie oraz dziewięć
receptur w `examples.json`. Receptura zawiera uzupełnienia dokumentu, nie surowy
rekord DocumentDraft. `examples.build_example` korzysta z modeli, usługi tworzenia
draftu i aktualnych sekcji. `retired.json` zawiera wyłącznie odciski treści czterech
wycofanych źródeł; nie przywraca ich do katalogu.

Otwórz `/documents/demo#examples` → przykład → **Utwórz kopię do edycji**.
Podgląd wzorca niczego nie zapisuje. Kopia trafia do zwykłej biblioteki, istniejącego
edytora i mechanizmu rewizji. Edycja kopii nie zmienia źródeł ani wzorca. GET
katalogu działa również dla uprawnionego czytelnika; kopiowanie wymaga edytora.

Wszystkie źródła i dokumenty mają `data_origin=demo`. Oznaczenie:
**PRZYKŁAD DEMO — DANE FIKCYJNE**. Ceny są wyłącznie `example`; loty nie mają
zmyślonych przewoźników/numerów, rezerwacje nie są potwierdzone. Hotel incentive
jest wymaganym/proponowanym standardem, nie konkretną zarezerwowaną usługą.
Nieznane odległości są `null`; jeden dzień ma jawnie fikcyjne liczby dydaktyczne.
Wiedza pozostaje `unverified`, bez udawanych źródeł i dat sprawdzenia. Zdjęcia
zastępują neutralne placeholdery. Adresy `example.invalid` są niedziałające.

Seed nie uruchamia się przy starcie aplikacji. Opcjonalne polecenia lokalne:

```powershell
.venv/Scripts/python.exe -m scripts.document_examples manifest
.venv/Scripts/python.exe -m scripts.document_examples dry-run --data-root local-data/gt-demo-store
.venv/Scripts/python.exe -m scripts.document_examples init --data-root local-data/gt-demo-store
.venv/Scripts/python.exe -m scripts.document_examples verify --data-root local-data/gt-demo-store
.venv/Scripts/python.exe -m scripts.document_examples obsolete --data-root local-data/document-studio
```

`init` tworzy tylko brakujące rekordy. Zgodny rekord daje `verified`; różnica daje
`conflict_preserved` i kod wyjścia 2, bez nadpisania. Przerwany seed można powtórzyć.
Źródła mogą być dostępne jako fallback fixture bez materializacji overlay.
`obsolete` niczego nie usuwa: raportuje dokładne ID, zgodność z odciskiem starej
 treści oraz dokumenty wymagające zachowania snapshotów/historii.

Stare trzy programy, kampania i preset Islandii są wycofane z aplikacji. Ich
historyczne kopie znajdują się wyłącznie w `tests/fixtures/legacy-demo/`, jawnie
włączanych przez testy regresji. Nie są kopiowane do kontekstu obrazu Cloud Build.
Nie usuwaj zapisanych dokumentów, assetów ani danych użytkownika po prefiksie
lub samym `data_origin`.

[Manifest przykładów](gt-v1/examples.json) i [instrukcja Studio](../docs/DOCUMENT_STUDIO.md).
Historyczny raport `docs/DOC_TEMPLATES_006.md` jest niedostępny; powyższe źródła
nie zastępują jego wyników ani dowodów akceptacji.
