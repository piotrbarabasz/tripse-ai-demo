# Kryteria akceptacji i plan testów

## 1. Definition of Done dla modułu

- Każdy z 8 typów (wraz z dwoma wariantami marketingu) ma specyfikację, identyfikator i walidator pól.
- Każdy wygenerowany dokument ma `template_id`, `template_version`, `document_revision`, wersję danych/assetów, datę i status odbiorcy.
- W finalnym dokumencie nie ma nieoznaczonych fikcyjnych cen, statusów rezerwacji, niezweryfikowanych tras i źródeł.
- Teksty, zdjęcia, numery stron, tabele, fonty i polskie znaki renderują się bez ucinania.
- Przed publikacją istnieje jawne zatwierdzenie użytkownika z odpowiednią rolą.
- Uprawnienia blokują dostęp do danych wewnętrznych innemu odbiorcy, również przez bezpośrednie URL.
- Render działa ponownie dla zatwierdzonego snapshotu, a awaria generacji jest możliwa do diagnozy.

## 2. Testy per rodzina

| Rodzina | Test obowiązkowy | Oczekiwany wynik |
|---|---|---|
| `offer.private` | Nie ma ceny | Blokada finalnego eksportu albo jawny zatwierdzony tryb `concept_only` |
| `offer.self_guide` | Brak definicji wsparcia | Blokada finalnej oferty |
| `offer.school` | Brak wieku/liczebności | Informacja krytyczna i brak końcowej ceny na osobę |
| `offer.incentive` | Nieznany hotel | Jasny opis proponowanego standardu; brak fikcyjnej nazwy/udogodnień |
| `marketing.collection` | 8 kierunków / długie tytuły | Paginacja/więcej kart; brak mikrotekstu i uciętych danych |
| `pilot.basic` | Rezerwacja pending, numer/pin w danych źródłowych | Status pending; brak PIN-u w standardowym eksporcie |
| `pilot.advanced` | 15 dni i zmiana strefy | Wszystkie dni zachowane, godziny i strefy wyraźnie opisane |
| `pilot.knowledge` | Fakt bez źródła | Ostrzeżenie i blokada przedstawienia jako zweryfikowany fakt |

## 3. Testy modelu danych

- 2 i 15 dni, pusta i długa lista przystanków.
- Dni bez daty vs. dni z pełną datą, przekraczanie północy i zmiana stref czasowych.
- Import miejsca z Google Places bez potwierdzonego hotelu i ceny: pola pozostają puste.
- `verification_status` jest zachowany w adapterze i nie zmienia znaczenia.
- Równoczesna edycja tego samego draftu wykrywa konflikt wersji, nie nadpisuje zmian.

## 4. Testy wizualne PDF

Przygotować fixture'y **fikcyjne i pozbawione danych uczestników**:

1. Marketing: 1, 3 i 8 kierunków; zdjęcie panoramiczne i pionowe; długi termin.
2. Oferta: długi opis dnia, 15 dni, brak zdjęcia, cena w kilku wariantach.
3. Rozpiska: dzień z 14 punktami, dwie strefy, tabela noclegów, kilka stron.
4. Merytoryczny: dzień z dużą liczbą źródeł oraz dzień z małą ilością materiału.
5. Edge case: polskie ąęłóśźż, islandzkie/obce znaki, długie URL, bardzo długie nazwy.

Sprawdzać automatycznie format, liczbę stron, brak wyjątków renderera, oraz wizualnie (snapshoty stron, porównanie regresji). Nie polegać tylko na tym, że plik PDF „się otwiera”.

## 5. Testy bezpieczeństwa

- Niezalogowany użytkownik nie pobierze `client`, `internal` ani `internal_restricted`.
- Użytkownik innej grupy nie pobierze rozpiski nieprzypisanego wyjazdu.
- Publiczny marketing i oferta nie zawierają numerów rezerwacji, PIN-ów, list uczestników i notatek pilota nawet w ukrytym HTML/metadata PDF.
- Sekrety nie pojawiają się w logach i komunikatach wyjątków.
- Ktoś ze znajomością ID dokumentu nie może ominąć kontroli dostępu.
- Zdjęcie bez prawa publikacji nie trafia do publicznego eksportu.

## 6. Testy procesu

- Draft → edycja → walidacja → review → approval → export; zawartość eksportu odpowiada zatwierdzonej rewizji.
- Zmiana zatwierdzonego dokumentu tworzy nową rewizję.
- Job eksportu przechodzi `queued → running → succeeded/failed` i obsługuje awarię bez fałszywego sukcesu.
- Stary PDF pozostaje powiązany ze starym snapshotem po zmianie treści podróży.

## 7. Etapowe akceptacje

**MVP:** pierwsze 3 typy, wszystkie punkty testów wspólnych i zabezpieczenia pilota.  
**Pełna V1:** wszystkie 8 typów, dwa warianty marketingowe, 15-dniowy przebieg, źródła dla wiedzy.  
**GCP:** prywatny dostęp, trwałość po restarcie, monitoring, budżety, testy smoke i retencja.

## 8. Artefakty akceptacyjne

Zarchiwizować przykładowe (fikcyjne) dane JSON, rendered PDF/obrazy, raporty walidacji, snapshoty wizualne, checklistę ręcznego przeglądu oraz podpisaną decyzję recenzenta. Nie dodawać do repo prawdziwych danych osobowych ani sekretów rezerwacyjnych.

**Powiązania:** [roadmap](roadmap.md) · [reguły układu](../design/layout-rules.md) · [walidacja treści](../data/content-validation.md).
