# Architektura modułu dokumentów

DOCUMENT-LIBRARY-001 (implementacja lokalna 2026-10-28): istniejący Repository
ma listowanie lekkich metadanych i historię pełnych zapisów. JSON/GCS pozostają
magazynami; metadane GCS są częścią obiektu, lokalny metadata/ to cache. Historia
poprzedniej głowy jest zapisywana create-only przed CAS/replace głowy; brak
transakcji wielu obiektów. [Szczegóły i API](../../DOCUMENT_STUDIO.md),
[ADR-0014](../../adr/0014-document-library-history.md). DocumentExport i indeks
Firestore pozostają planem, nie działającą funkcją.

Stan implementacji lokalnej 2026-10-28: Implementacja korzysta z istniejących Trip/Campaign, DocumentDraft, JSON/GCS i przeglądarkowego eksportu. Sekcje Pydantic → definicje templates.py → instancje snapshotów są trzema poziomami. Nie wdrożono równoległych endpointów `/api/document-drafts`, kolejki renderowania ani modelu zatwierdzeń opisanego dalej jako docelowa propozycja.

Szczegóły operacyjne: [Document Studio](../../DOCUMENT_STUDIO.md).

**Status:** propozycja nowego modułu; nie jest to opis kodu, który już istnieje w repozytorium.  
**Zasada:** rozwijać `tripse-ai-demo` **modułowo**, nie przepisywać działającego planera.

## 1. Stan istniejący (przegląd `master`, 2026-10-24)

- `app/main.py`: FastAPI, endpointy tworzenia i statusów planów, włączenie routerów WAHA i widoku planu.
- `app/db.py`: lokalne SQLite z jobami planowania, wiadomościami i tokenami viewerów.
- `app/worker.py`: osobny proces wykonujący zadania.
- `app/planning_models.py`: model krótkiego demo, `Candidate.day` w przedziale 1–2 i do 8 kandydatów w planie.
- `app/viewer.py` + `app/static`: przeglądarkowy widok planu i mapy.
- Docker Compose + Caddy + opcjonalny WAHA; lokalna weryfikacja MOCK opisana w README. Publicznego DEV na GCP **nie uznajemy za potwierdzony**.

Modułu szablonów dokumentowych, biblioteki assetów i eksportu PDF **nie ma** w aktualnie sprawdzonych plikach.

## 2. Proponowany podział logiczny

```text
Panel / Admin Web (authenticated)
            |
         FastAPI
            |
    +-------+---------+--------------+
    |                 |              |
 Trips & Data     Templates       Assets
    |                 |              |
    +--------- Document Service -----+
                      |
                Validation
                      |
             Render Job Queue
                      |
              HTML/CSS -> PDF
                      |
               Object Storage
                      |
          Authorized download

Existing Trip Planner -> Adapter -> Trip model
Existing WhatsApp     -> separate optional integration
```

**Ważne:** wejście przez WhatsApp jest opcjonalnym adapterem, nie warunkiem działania panelu. Generowanie dokumentów nie powinno zależeć od działającej sesji WAHA.

## 3. Proponowane moduły kodu

```text
app/
  documents/
    api.py                # drafty, podgląd, aprobata, eksport, pobranie
    models.py             # Pydantic kontrakty API
    service.py            # budowa snapshotów dokumentów
    template_registry.py  # template_id, wersje, walidator, motyw
    validation.py         # reguły per szablon + cross-field
    rendering.py          # HTML/CSS -> PDF/image
  trip_catalog/
    models.py             # uniwersalny Trip, Days, Stops, Logistics
    adapter.py            # z obecnego planera do Trip
  assets/
    api.py                # upload, metadane, licencje
    service.py            # zapis, wersje, walidacja
  templates/
    shared/               # typography, blocks, CSS
    offers/               # 4 oferty
    marketing/            # collections (2 warianty)
    pilots/               # basic, advanced, knowledge
```

Struktura jest **propozycją**, nie ścisłym wymaganiem. Możliwy prostszy podział dla MVP. Unikać nadmiernej liczby klas/serwisów, jeśli logika jest niewielka.

## 4. Kontrakty API (propozycje, niezaimplementowane)

| Metoda i ścieżka | Operacja | Autoryzacja |
|---|---|---|
| `GET /api/document-templates` | Katalog template_id / wariantów | zalogowany |
| `GET /api/trip-catalog` | Lista wycieczek | zalogowany |
| `POST /api/document-drafts` | Nowy draft ze snapshotem | edytor |
| `GET /api/document-drafts/{id}` | Draft | zgodnie z dostępem |
| `PATCH /api/document-drafts/{id}` | Edycja z `revision` | edytor |
| `POST /api/document-drafts/{id}/validate` | Lista błędów/warningów | uprawniony |
| `POST /api/document-drafts/{id}/approve` | Zatwierdzenie rewizji | recenzent |
| `POST /api/document-drafts/{id}/exports` | Zadanie renderowania | uprawniony |
| `GET /api/document-exports/{id}` | Status i wynik | uprawniony |
| `GET /api/document-exports/{id}/download` | Plik | zgodnie z poufnością |
| `POST /api/assets` | Nowy zasób i metadane | edytor assetów |

W MVP można połączyć niektóre endpointy; identyfikatory i autoryzacja są ważniejsze niż dokładne URI. Nie wystawiaj surowych plików wewnętrznych pod publicznym StaticFiles.

## 5. Model generowania

1. Pobierz zatwierdzony/draft `DocumentSnapshot` z wersją danych, assetów i szablonu.
2. Zweryfikuj pola i ujawniane dane na poziomie backendu.
3. Renderuj deterministyczne HTML/CSS (np. Jinja2 z escaped content, jawnie kontrolowanym HTML) i wykonaj eksport do PDF w izolowanym procesie (np. headless Chromium/Playwright). Silnik renderowania wymaga weryfikacji wydajności i obsługi fontów.
4. Nadaj hash i zapisz wynik do trwałego storage.
5. Powiąż wynik z `document_revision`, `template_version`, `data_snapshot_id`, wersjami zdjęć.
6. Udostępnij tylko osobie mającej dostęp do typu dokumentu.

**Nie przekazuj swobodnego kodu HTML/CSS z LLM do renderera**. AI zwraca dane/tekst zgodnie ze schematem; renderowanie wykonuje system szablonów.

## 6. Renderowanie i podgląd

Ta sama reprezentacja HTML/CSS służy do podglądu i PDF, z wariantami `screen`/`print`. Podgląd roboczy jest chroniony autoryzacją; przy poufnych PDF-ach nie stosować publicznych linków. Można początkowo stosować render synchroniczny tylko do lekkiego preview, finalny eksport powinien być zadaniem z trwałym statusem.

## 7. Integracja z planerem

Adapter importuje miejsca/Google Places ID, oszacowania Routes i ostrzeżenia, ale pozostawia nieznane: daty, ceny, noclegi, rezerwacje, opisy i listę uczestników. Nie rozszerzać ograniczeń `Candidate.day` samym promptem. Przy projektowaniu docelowych wielodniowych tras używać niezależnego modelu `Trip`.

## 8. Testy architektury

- CRUD draftów i konflikt równoczesnej rewizji.
- Render tego samego snapshotu wielokrotnie bez zmiany treści.
- Niepoprawny `template_id`, brakujące pola i brak zdjęcia.
- 15 dni po imporcie nie zostają obcięte do 2.
- Próba pobrania `pilot.basic` przez nieuprawnionego użytkownika kończy się odmową.
- Awaria eksportu nie gubi danych i nie zwraca fałszywego `succeeded`.

**Powiązania:** [GCP](gcp-deployment.md) · [security](security.md) · [model danych](../system-data/trip-data-model.md).
