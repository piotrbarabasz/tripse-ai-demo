# Bezpieczeństwo i prywatność dokumentów

**Kontekst:** wzór podstawowej rozpiski pilota zawiera dane uczestników i rezerwacji. Dokumenty marketingowe są publiczne, oferty klientowskie są przeznaczone dla konkretnych odbiorców, a materiały pilota mogą być poufne. W pierwszej implementacji dostęp musi być rozdzielony niezależnie od wizualnego wyglądu dokumentu.

## 1. Klasy dokumentów

| Klasa | Przykłady | Zasada dostępu |
|---|---|---|
| `public` | Zatwierdzone materiały marketingowe | Publiczne po osobnej akcji „Publikuj” |
| `client` | Oferty private, Self-Guide, school, incentive | Odbiorca oferty lub uprawniony pracownik, nie wyszukiwalne publicznie |
| `internal` | Materiały merytoryczne bez PII | Zalogowany pracownik/pilot z przyznanym zakresem |
| `internal_restricted` | Rozpiska basic i advanced, rezerwacje | Wyłącznie osoby obsługujące odpowiedni wyjazd lub administrator |

## 2. Role (propozycja minimalna)

`admin` zarządza użytkownikami; `editor` tworzy wycieczki i drafty; `reviewer` zatwierdza dokumenty; `pilot` czyta tylko przypisane dokumenty operacyjne; `viewer` ma prawo do wskazanych ofert. Dopuszczalne łączenie ról w małym zespole, ale nie domyślne przyznawanie pełnego dostępu.

## 3. Zasady niezbywalne

- Serwer **sprawdza autoryzację** dla odczytu draftu, preview, eksportu i downloadu; UI nie jest mechanizmem bezpieczeństwa.
- `public` nie pobiera w ogóle pól `Operations`, `Participant`, `internal_notes`, PIN-ów i sekretów.
- Link z istniejącego viewer planera z tokenem nie daje dostępu do danych operacyjnych.
- Kody dostępu, PIN-y i numery dokumentów to sekrety: przechowywać oddzielnie tylko jeśli naprawdę konieczne; **nie** w standardowym PDF.
- Wszystkie dane osobowe zbierać w zakresie niezbędnym do organizacji wyjazdu; politykę retencji i podstawy prawne uzgodnić z TRIPSE.
- Zdjęcia osób, w szczególności dzieci, wymagają właściwych zgód i weryfikacji celu publikacji.

## 4. Zagrożenia i kontrolki

| Zagrożenie | Kontrolka |
|---|---|
| Publiczny URL do pliku pilota | Bucket prywatny, autoryzowane pobranie, żadnych stałych publicznych linków |
| Zgadywanie ID dokumentu | Kontrola roli oraz przypisania do konkretnego wyjazdu dla każdego odczytu |
| Wycieki przez prompt/LLM | Minimalny kontekst, nie wysyłać sekretnych danych do modelu, filtrować pola wejściowe |
| Niebezpieczne uploady | Limit MIME/rozmiaru, kontrola typu pliku, skan, brak serwowania jako kod |
| Niewłaściwy asset | Zatwierdzenie źródła/licencji i zakresu wykorzystania |
| Błędy operatora | Wyróżnione statusy poufności i dodatkowy krok potwierdzenia publikacji |
| Zbyt szczegółowe logi | Redakcja PII/tokenów, retencja, ograniczone role odczytu |

## 5. Audyt

Zapisuj kto utworzył draft, kto zatwierdził, kto wygenerował i pobrał dokument poufny, wersję szablonu i wynik; nie loguj całej zawartości PDF-ów ani PIN-ów. Błędy klienta nie ujawniają istnienia cudzych dokumentów czy szczegółów rezerwacji.

## 6. Uprawnienia do wysyłki

Przygotowanie dokumentu ≠ publikacja. Wysyłka do klienta, link do pliku i post społecznościowy muszą być odrębnymi akcjami z własnym odbiorcą oraz logiem. [ETAP PÓŹNIEJSZY] Integracja WhatsApp/e-mail powinna korzystać z tej samej kontroli dostępu co panel.

## 7. Kryteria akceptacji

Testy negatywne: rola `viewer` nie pobierze `pilot.basic`; `pilot` nie otworzy wyjazdu innej grupy; marketing nie zawiera danych uczestników/rezerwacji w HTML ani PDF; ujawnienie ID nie umożliwia pobrania; stary token wygasły nie działa; logi i wyjątki nie ujawniają kodów dostępu.

**Powiązania:** [walidacja](../system-data/content-validation.md) · [workflow](../general/document-workflow.md).
