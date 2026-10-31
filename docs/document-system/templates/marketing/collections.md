# Szablon: marketing — nowości i kolekcje wyjazdów

Stan implementacji lokalnej 2026-10-28 (szablony 0.4.0): Istniejący edytor i renderer zachowują oba warianty, A4/1080×1350, zdjęcia i kadry. Draft ma niezależny campaign_snapshot oraz wspólne sekcje promocyjne; zmiana draftu nie zmienia kampanii. Opcjonalny prowadzący jest wpisywany ręcznie.

Instrukcja edycji i ograniczenia publikacji: [Document Studio](../../../DOCUMENT_STUDIO.md).
Poniżej zachowano wymagania docelowe i inspiracje; nie oznaczają automatycznej akceptacji treści.

**ID:** `marketing.collection`  
**Warianty:** `new_trips`, `theme_collection`  
**Rodzina:** `marketing` · **Odbiorca:** publiczny, social media, mailing, strona WWW  
**Format początkowy:** A4 PDF i grafika 1080×1350 (warianty rozmiaru: [DO UZGODNIENIA]).

Aktualizacja DOC-TEMPLATES-006: lokalny szablon 0.5.0, uzupełniony przykład GT v1
i kopia do edycji przez `#examples`. Pola, kolejność oraz granice weryfikacji:
[current Studio guidance](../../../DOCUMENT_STUDIO.md).
Historical report `docs/DOC_TEMPLATES_006.md` is unavailable; the guidance does
not replace its acceptance evidence. Specyfikacja poniżej
nie oznacza zatwierdzenia biznesowego Ground Truth.

## 1. Cel i odbiorca

Szybko pokazać kilka nowych lub tematycznie powiązanych wypraw TRIPSE i zachęcić do kontaktu. Użytkownik powinien na pierwszy rzut oka zobaczyć **kierunek, termin i kluczową obietnicę każdego wyjazdu**.

## 2. Charakterystyka dokumentu i inspiracja

Przesłana grafika „Pilotażowe nowości 2027” / „Wyprawy górskie” wykorzystuje: zdjęcia w szerokich pasach, duże czarne ekspresyjne tytuły, ciepły żółto-pomarańczowy akcent, krótkie wyróżniki, podpisy pilotów, etykietę „PILOTAŻOWY” oraz kolaż kilku kierunków. Jest to **przykład layoutu**, nie kompletna księga znaku. Nowy szablon ma zachować energię i poprawić skalowalność dla małych ekranów.

## 3. Sekcje obowiązkowe

1. Logo TRIPSE i tytuł kampanii (np. sezon, temat kolekcji).
2. Jedno krótkie hasło / powód zainteresowania.
3. Lista wyjazdów; dla każdego: nazwa, kraj/region, data lub „do ustalenia”, jedna fotografia z prawami użycia, krótkie USP / charakter podróży.
4. Widoczna etykieta stanu produktu, jeśli używana: `pilotażowy`, `nowość` albo inny status potwierdzony przez TRIPSE.
5. CTA, nazwa / adres kontaktu, strona lub prawidłowy kod QR.
6. Ewentualne informacje wymagane przed publikacją, zatwierdzone przez TRIPSE.

## 4. Warianty

### `new_trips` — katalog nowości

- Kilka niezależnych kierunków w jednej kolekcji.
- Każda karta: zdjęcie, nazwa, termin, pilot (opcjonalnie), opis 5–12 słów i etykieta pilotażowa/statusu.
- Przy większej liczbie wyjazdów dzielić na kolejne strony/slajdy. Nie zagęszczać do niemożliwego do odczytania układu.

### `theme_collection` — kolekcja tematyczna

- Jeden motyw przewodni, np. „Wyprawy górskie”.
- Mocniejsza główna fotografia/hasło tematyczne, spójne ikony i wyróżniki programu.
- Może zawierać prowadzącego temat (tylko po potwierdzeniu) i krótkie porównanie długości, trudności, krajów.

## 5. Wymagane dane wejściowe

`campaign.title`, `campaign.season`, `campaign.layout_variant`, `campaign.cta`, `campaign.trips[]` (minimum 1), `asset_ids` i `asset.usage_rights`; wpis wyjazdu: `title`, `location`, `date_range_or_label`, `photo`, `short_hook`, `publication_status`. Opcjonalnie: `leader_display_name` i zweryfikowane uprawnienie do publikowania nazwiska/wizerunku.

## 6. Zasady prezentacji treści

- Terminy mają postać np. „21.01–09.02.2027” lub „Lato 2027 — termin w przygotowaniu”. Nie dopisywać nieznanych dat.
- Zachować poprawne znaki, diakrytykę i nazwy własne.
- Nie zakładać, że wyjazd ma wolne miejsca, pilota czy cenę, jeśli nie ma potwierdzenia.
- Odrębny przegląd grafiki na desktopie i ekranie telefonu.
- Długie nazwy: kontrolowane złamania, nie ucięte końcówki.
- W marketingu używać tylko zdjęć autentycznych lub jednoznacznie oznaczonych ilustracji; nie przedstawiać wygenerowanego widoku jako prawdziwej atrakcji.

## 7. Wymagania wizualne

Duże fotografie kierunków, ciemna typografia na dobrze kontrastującym tle, jednolity pasek danych każdej karty i zachowana przestrzeń na CTA. Ekspresyjny font jedynie dla krótkiego hasła, a nie dla godzin i dat. Szczegóły: [brand](../../design/brand-guidelines.md), [layout](../../design/layout-rules.md), [assets](../../design/asset-guidelines.md).

## 8. Obsługa brakujących informacji

Brak fotografii → materiał do uzupełnienia lub zaakceptowany placeholder markowy; brak terminu → „Termin w przygotowaniu”; brak potwierdzonego pilota → ukryj pole; brak prawa do zdjęcia → blokada publikacji. Nie publikować pustego CTA.

## 9. Przykładowa struktura dokumentu

**A4:** nagłówek kampanii → 3–5 kart wyjazdów (limit zależny od długości tekstu) → CTA/stopka. Następna strona tylko przy większej liczbie ofert. **Social:** seria pionowych kart: okładka kampanii → 1–2 wyjazdy na kartę → końcowe CTA. Limity kart są wstępną propozycją wymagającą prób wizualnych.

## 10. Kryteria akceptacji

Każdą nazwę i datę da się przeczytać na telefonie, każda fotografia ma potwierdzone prawa użycia, brak fikcyjnego statusu miejsc/ceny, logo i CTA są widoczne, a warianty `new_trips` / `theme_collection` generują różne układy z tego samego modułu.

**Powiązania:** [katalog](../../general/template-catalog.md) · [pola](../../system-data/template-fields.md).
