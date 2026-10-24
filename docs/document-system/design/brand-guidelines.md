# Design system: identyfikacja wizualna TRIPSE

**Status:** roboczy zestaw tokenów i zasad; **nie zastępuje oficjalnego brand booka**. Grafika „Pilotażowe nowości 2027 / Wyprawy górskie” jest inspiracją, ale nie dowodzi rzeczywistych wartości HEX ani użytych rodzin fontów.

## 1. Wspólny język

TRIPSE łączy podróżniczą energię z czytelnością. Logo, kierunek, data, numer dnia, fotografie i CTA powinny wyglądać jak część jednej marki niezależnie od tego, czy dokument jest marketingowy, sprzedażowy czy operacyjny.

### Trzy tematy z jednej bazy

| Motyw | Wrażenie | Dominujące środki |
|---|---|---|
| `brand.marketing` | Dynamiczny, wyprawowy | Szerokie zdjęcia, wyraziste tytuły, ciepłe akcenty |
| `brand.offer` | Inspirujący i godny zaufania | Spokojna siatka, zdjęcia, wyraźny program i zakres świadczeń |
| `brand.operations` | Funkcjonalny i szybki w użyciu | Tabele, etykiety statusów, hierarchia godzin, minimum dekoracji |

## 2. Robocza paleta tokenów

| Token | Roboczy HEX | Zastosowanie |
|---|---|---|
| `color.ink` | `#172B41` | Nagłówki, tekst operacyjny |
| `color.accent` | `#E5A01D` | Wyróżniki, podkreślenia, badge marketingowe |
| `color.dark` | `#171717` | Hasła i tekst na jasnym tle |
| `color.paper` | `#FFFFFF` | Główne tło |
| `color.surface` | `#EDF3F2` | Tabele, neutralne panele |
| `color.error` | [DO UZGODNIENIA] | Błędy i statusy krytyczne |
| `color.success` | [DO UZGODNIENIA] | Weryfikacja zakończona |

**Nie traktuj proponowanych wartości jako zmierzonych ze wzorca.** Po pozyskaniu materiałów źródłowych potwierdź tokeny z właścicielem marki i uruchom test kontrastu.

## 3. Robocza typografia

- **Tekst główny:** Inter, proponowany zamiennik systemowy sans-serif; sprawdzić licencję i polskie znaki w silniku PDF.
- **Nagłówki:** Montserrat albo Barlow Condensed; ostatecznie wybierz jedną rodzinę dla ofert i dokumentów wewnętrznych.
- **Akcent marketingowy:** Kalam Bold lub inna zatwierdzona ekspresyjna rodzina — wyłącznie krótkie hasła, nie daty, adresy i warunki sprzedaży.
- **Fallback:** zatwierdzony zestaw fontów osadzanych w PDF; nigdy poleganie wyłącznie na fontach systemowych użytkownika.

Orientacyjne skale **A4**: tytuł strony 25–32 pt, nagłówek sekcji 16–21 pt, podtytuł 12–14 pt, tekst 10–11 pt, przypis 8–9 pt. Minimum zależy od próby wydruku i czytelności. Dla materiałów marketingowych stosować osobne skale wg rozdzielczości.

## 4. Logo i komponenty

- Logo powinno pochodzić z oryginalnego źródła (SVG lub wysokiej jakości PNG). Nie wycinać go z przykładowej grafiki, jeśli dostępny jest oryginał.
- Zachować proporcje, kontrast i pole ochronne [DO UZGODNIENIA].
- Komponenty wspólne: `DocumentHeader`, `SectionTitle`, `DayLabel`, `DateRange`, `StatusTag`, `PhotoTile`, `InfoStrip`, `TableHeader`, `Footer`, `SourceFootnote`.
- Etykiety statusu mają mieć zarówno kolor, jak i tekst; statusu nie koduje sam kolor.
- Ikonografia ma być prosta i konsekwentna; nie mieszać emoji z ikonami wektorowymi w generowanym PDF bez decyzji projektowej.

## 5. Spójność nazewnictwa

Daty w PL: `DD.MM.RRRR`; zakres dat z pełnym kontekstem roku, jeżeli dokument mógłby być czytany oddzielnie. Godziny: `HH:mm` oraz strefa tam, gdzie ma znaczenie. Jednostki: `km`, `min`, `h`, waluta zgodna z wyceną. Preferowane formy: „Dzień 3”, „Nocleg”, „W programie”, „W cenie”, „Poza ceną”, „Do potwierdzenia”.

## 6. Czego unikać

Brak małego tekstu na zdjęciu bez gradientu/tła; brak nieczytelnych kontrastów; brak wyszarzonych statusów krytycznych; brak tytułów pociętych w połowie strony; brak niezliczonych fontów; brak generowanych wizualizacji przedstawianych jako rzeczywiste krajobrazy.

## 7. Proces zatwierdzenia brandingu

1. Pozyskać logo, oficjalne kolory i ewentualny zestaw fontów.
2. Przygotować po jednej stronie marketingowej, ofertowej i operacyjnej.
3. Sprawdzić druk A4, eksport obrazowy i czytelność na telefonie.
4. Zatwierdzić tokeny i zapisać dokładny numer wersji identyfikacji.

**Powiązania:** [layout-rules.md](layout-rules.md) · [asset-guidelines.md](asset-guidelines.md).
