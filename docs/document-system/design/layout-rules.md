# Reguły układów i eksportu

## 1. Zasady wspólne

Dokument jest składany z bloków semantycznych (`cover`, `summary`, `day`, `accommodation`, `price`, `booking`, `knowledge`, `cta`), a nie ręcznie pozycjonowanych pól dla każdego wyjazdu. Blok może mieć inną reprezentację w motywie marketingowym, ofertowym lub operacyjnym.

## 2. Formaty docelowe

| Format | Zastosowanie | Zasady |
|---|---|---|
| A4 pion (210×297 mm) | Oferta, pilot, materiały merytoryczne | Marginesy roboczo 14–18 mm, numery stron, kontrola łamania |
| A4 poziom [opcjonalny] | Szeroka tabela/katalog | Tylko jeśli treść rzeczywiście tego wymaga |
| 1080×1350 px [propozycja] | Social post 4:5 | Bez drobnej typografii, bezpieczne marginesy, QA na telefonie |
| Karuzela [ETAP PÓŹNIEJSZY] | Większa liczba ofert | Każda plansza czytelna osobno |

Rozdzielczości innych kanałów (Stories, banner WWW) zatwierdzić osobno; nie skalować automatycznie całej A4 do posta.

## 3. Reguły paginacji

- Unikaj samotnych nagłówków na końcu strony.
- Dzienny nagłówek i pierwsza aktywność muszą zostać razem.
- Dopuszczaj podział długiego harmonogramu na kolejne strony z powtórzonym nagłówkiem tabeli.
- Nie przecinaj pojedynczego zdjęcia/karty w połowie, chyba że format jest explicite wielostronicowym spreadem.
- Unikaj nakładania długich nazw i znaczników statusu; zapewnij przewidywalny overflow.
- Nie zmniejszaj fontu globalnie, aby zmieścić nienaturalnie dużo treści na jednej stronie.
- Sekcja rezerwacji i kontaktów w materiale pilota musi być łatwa do odszukania z poziomu spisu/zakładki.

## 4. Zdjęcia i kadry

Stosuj kadrowanie `cover` dla pełnoszerokościowych fotografii, ale pozwól użytkownikowi ustawić punkt ważny (focal point). Nie rozciągaj zdjęcia w jednym wymiarze. Logo zawsze `contain`. Nie umieszczaj drobnego tekstu bezpośrednio na ruchliwych tłach zdjęć.

## 5. Siatka i odstępy (propozycja startowa)

- Moduł bazowy odstępów: 4 px (dla web preview); konsekwentna skala 4/8/12/16/24/32.
- Oferta: zwykle pojedyncza kolumna opisowa, dwukolumnowe bloki tylko przy sensownej szerokości.
- Operacje: zawartość tabelaryczna, prawa kolumna na status/uwagę; w razie braku miejsca wróć do jednej kolumny.
- Długie ciągi URL i nazw obiektów muszą się łamać lub mieć skrócony podpis z pełnym linkiem.

## 6. Dostępność i stabilność

Tekst nie może zależeć wyłącznie od koloru statusu. Wyraźny kontrast i właściwe rozmiary fontu. Dokument drukowany w skali szarości nadal odróżnia sekcje. Na ekranie telefonu nie powinno być potrzeby odczytywania mikrotekstu w publikowanych grafikach.

## 7. Sprawdzenie przed eksportem

1. Brak overflow, nachodzenia, uciętych słów i pustych stron.
2. Polskie znaki i nazwy obce poprawnie osadzone w PDF.
3. Liczba i kolejność dni zgodne z danymi.
4. Zdjęcia mają właściwe proporcje, licencje i wystarczającą rozdzielczość.
5. Stopka, logo, tytuł i status poprawne dla typu dokumentu.
6. Wariant mobilny marketingu został obejrzany w skali docelowej.
7. Linki oraz kody QR działają na rzeczywistym eksporcie.

## 8. Testowe scenariusze

Krótki wyjazd 2-dniowy; wyjazd 15-dniowy; jedna nazwa atrakcji o bardzo dużej długości; dzień z 14 pozycjami; dzień bez zdjęcia; dwie strefy czasowe; cena z wieloma pozycjami; marketing 8 kierunków; polskie i islandzkie znaki specjalne.

**Powiązania:** [brand](brand-guidelines.md) · [akceptacja](../development/acceptance-criteria.md).
