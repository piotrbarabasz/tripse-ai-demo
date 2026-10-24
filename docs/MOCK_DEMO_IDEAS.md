# Pełne demo Tripse bez kluczy API i numeru WhatsApp

Aktualizacja: podstawowy zakres został wdrożony. Instrukcja aktualnej wersji,
scenariusze i ograniczenia znajdują się w [MOCK_DEMO.md](MOCK_DEMO.md).
Poniżej zachowano pierwotną propozycję; nie wszystkie szczegóły projektu
(np. osobne pliki JSON i pięć etapów postępu) odpowiadają finalnej implementacji.

Propozycja rozbudowy, 22.10.2026. Ten dokument opisuje pomysły i plan prac;
poniższe funkcje nie są jeszcze zaimplementowane.

## Cel

Po uruchomieniu lokalnym użytkownik przechodzi cały scenariusz: wpisuje wiadomość,
otrzymuje potwierdzenie, obserwuje przygotowanie planu, dostaje podsumowanie i link,
a następnie ogląda dni wycieczki, punkty, mapę i ostrzeżenia. Wszystko działa bez
konta WhatsApp, kluczy OpenAI i Google oraz płatnych wywołań.

Demo pokazuje zachowanie produktu na przygotowanych przykładach. Nie dowodzi
działania prawdziwego AI, dostarczania WhatsApp ani aktualności tras. Cały ekran
ma widoczne oznaczenie „DEMO — dane przykładowe”.

## Co jest obecnie

- `app/generator.py` zwraca stały wynik: dwa dni, puste przystanki, brak geometrii,
  czasu jazdy i odległości. Nie interpretuje wiadomości.
- Formularz tworzy prawdziwe zadanie w SQLite, a worker je przetwarza. Działają
  statusy zadania oraz link do podglądu z terminem ważności.
- `app/static/viewer.js` celowo blokuje mapę i linki Google dla mocka.
- Modele w `app/planning_models.py` opisują miejsca jako zweryfikowane przez
  Google, a `TripPlan` dopuszcza tylko wynik live. Obecny mock omija te modele.
- Integracje OpenAI, Google Places, Google Routes i mapa Google w przeglądarce
  są napisane, lecz wymagają konfiguracji i osobnego sprawdzenia na żywych usługach.
- WhatsApp wymaga WAHA, sparowanego konta i dozwolonego nadawcy. Brakuje
  przeglądarkowego symulatora tego kanału.

## Proponowany zakres

| Funkcja | Zachowanie w demo | Co pozostaje rzeczywiste |
|---|---|---|
| Wiadomość użytkownika | Czat „Symulator WhatsApp”, bez logowania i QR | Zapis wejścia i utworzenie zadania |
| Interpretacja prośby | Wybór przygotowanego scenariusza, ograniczone reguły | Walidacja obsługiwanych danych |
| Wyszukiwanie atrakcji | Lokalne dane miejsc i opisy | Wyświetlenie danych i ich źródła |
| Planowanie | Przygotowane dni, kolejność i preferencje | Przetwarzanie przez worker |
| Czas i odległość | Jawnie przykładowe wartości | Formatowanie i kontrola limitu jazdy |
| Mapa | Lokalna mapa demonstracyjna, punkty i geometria z plików | Zoom, przesuwanie, wybór dnia i punktów |
| Odpowiedzi bota | Lokalna skrzynka wiadomości zamiast wysyłki WAHA | Potwierdzenie, wynik, obsługa ponowień |
| Udostępnianie | Link do podglądu i kopiowanie linku | Token, odczyt planu i wygasanie |
| Błędy | Wybieralne scenariusze awarii | UI błędów i zachowanie kolejki |

## 1. Pełne przykładowe plany zamiast pustego wyniku

Dodać pliki scenariuszy, np. `app/demo/scenarios/*.json`. Każdy zawiera:

- identyfikator, nazwę, przykładową wiadomość oraz wymagania wycieczki;
- dni, uporządkowane przystanki, współrzędne, krótkie opisy i preferencje;
- przykładowe odległości, czasy jazdy i przygotowaną geometrię;
- ostrzeżenia, brakujące miejsca i oczekiwany wynik;
- pochodzenie danych i informację, że wartości są demonstracyjne.

Na początek wystarczą trzy pełne plany:

1. Dwa dni: Wrocław → Karpacz → Szklarska Poręba → Wrocław, natura.
2. Jeden dzień: Kraków → Ojców → Kraków, krótka wycieczka.
3. Dwa dni: Gdańsk → Sopot → Gdynia → Gdańsk, spokojny wyjazd rodzinny.

Formularz i czat powinny mieć przyciski z gotowymi prośbami. Nieobsługiwany tekst
otrzymuje odpowiedź „Demo obsługuje te trzy przykłady” zamiast dowolnego planu
niezwiązanego z prośbą. Opcjonalnie można rozpoznawać nazwę regionu i limit jazdy;
nie należy przedstawiać takiej reguły jako rozumienia języka przez AI.

## 2. Mapa demonstracyjna bez Google Maps MCP i klucza

Rekomendowany pierwszy wariant: lokalny SVG ze schematycznym podkładem regionu,
pinezkami, nazwami miejsc i osobnymi kolorami dni. Geometrię wczytać z plików
scenariusza. Dodać powiększanie, przesuwanie, dopasowanie widoku, wybór dnia
i kliknięcie punktu powiązane z listą przystanków.

Mapa musi być opisana jako „Mapa demonstracyjna — przebieg poglądowy”, a czasy
i dystanse jako dane przykładowe. Nie rysować poglądowej linii pod etykietą
„trasa obliczona przez Google”. Taki podkład działa również bez internetu.

Możliwy późniejszy wariant: Leaflet z podkładem mapowym od wybranego dostawcy.
Przed wdrożeniem trzeba sprawdzić jego aktualne warunki, atrybucję i limity.
Brak klucza nie oznacza automatycznie braku zależności sieciowej. Do demo offline
pozostawić lokalny podkład; nie pobierać masowo publicznych kafelków.

W trybie live zachować Google Maps JavaScript API. MCP nie jest potrzebne do
samego wyświetlania map ani korzystania z Places i Routes przez backend.
Demo nie tworzy zapisanej mapy na koncie Google użytkownika.

## 3. Symulator WhatsApp w przeglądarce

Dodać stronę `/demo/chat`, dostępną wyłącznie przy włączonym trybie demo:

1. Użytkownik wybiera przykład lub wysyła obsługiwaną prośbę.
2. Backend przepuszcza ją przez wspólną logikę komend i tworzenia zadania.
3. Czat pokazuje potwierdzenie z prawdziwym `trip_id`.
4. Worker generuje plan i zapisuje odpowiedź do lokalnej skrzynki.
5. Czat pobiera wiadomości i pokazuje podsumowanie z działającym linkiem.

Dodać lokalny adapter zgodny z `MessagingProvider`, np. `DemoMessagingProvider`.
Przy zapisie wiadomości zachować kanał docelowy, aby worker nie próbował wysłać
wiadomości demo przez WAHA ani prawdziwej wiadomości WhatsApp do symulatora.
Przeglądarka nie powinna znać kluczy WAHA ani podpisywać webhooków. Symulator
wywołuje osobny endpoint demo; prawdziwy webhook zachowuje sprawdzanie HMAC.

Symulowane kontakty i wiadomości należy rozdzielać identyfikatorem rozmowy,
aby różne okna demo nie otrzymywały cudzych odpowiedzi. Tryb live domyślnie
nie udostępnia endpointów demo.

## 4. Widoczny postęp przygotowania

Pokazać etapy: „Odczyt prośby”, „Dobór miejsc”, „Przygotowanie dni”,
„Przygotowanie mapy”, „Plan gotowy”. W demo etykiety mają informować o symulacji.

Etapy powinien zapisywać worker, a UI odczytywać z backendu. Same animowane
komunikaty w przeglądarce nie potwierdzają pracy ani zakończenia zadania.
Nie trzeba sztucznie wydłużać generowania; opcjonalny krótki czas prezentacji
może być konfigurowalny i wyłączony podczas testów.

## 5. Scenariusze do przełączania jednym kliknięciem

| Scenariusz | Co użytkownik powinien zobaczyć |
|---|---|
| Pełny sukces | Potwierdzenie, dwa dni, komplet punktów, mapa i podsumowanie |
| Limit jazdy przekroczony | Przykładowy czas przekracza limit, ostrzeżenie przy dniu |
| Nieznalezione miejsce | Miejsce na liście braków; brak wymyślonej pinezki |
| Błąd obliczania trasy | Plan i punkty pozostają; czas, odległość i linia tej trasy znikają |
| Brak wymaganych danych | Prośba o podanie startu, końca i liczby dni; bez fikcyjnego planu |
| Nieobsługiwana długość | Czytelna informacja o limicie 1–2 dni |
| Awaria planowania | Zadanie kończy się błędem, następne może działać poprawnie |
| Awaria wysyłki odpowiedzi | Wynik istnieje, wiadomość oczekuje na ponowienie; plan nie jest generowany drugi raz |
| Powtórzona wiadomość | Ten sam identyfikator wiadomości daje jedno zadanie |
| Wygasły link | Widok niedostępny, bez ujawnienia planu |

Przyciski wymuszające błędy dostępne tylko w demo. Powtórzona wiadomość oznacza
ten sam identyfikator zdarzenia; ponowne wysłanie identycznego tekstu jako nowej
wiadomości nie musi być duplikatem. Wygasanie testować osobnym krótkim TTL demo
lub przygotowanym wygasłym rekordem, bez zmiany zegara systemowego.

## 6. Spójny model danych i oznaczenia

Najpierw rozszerzyć schematy, a dopiero potem odblokować wizualizację mocka.
Nie ustawiać fikcyjnego `verification_status=verified` ani `source=google_places`,
żeby obejść obecne zabezpieczenia widoku.

Proponowany kierunek:

- jawne źródła `demo_fixture`, `google_places` i `google_routes` w odpowiednich danych;
- osobny stan demonstracyjny miejsc i tras, obok stanów rzeczywistej weryfikacji;
- jeden walidowany kształt planu dla mock i live;
- renderowanie geometrii demo tylko w jawnie oznaczonym wariancie widoku;
- osobne podsumowania: „Przykładowo: 120 km / 2 h” oraz wynik usług live;
- współrzędne demo bez wymyślonych Google Place ID; ewentualne linki Google
  generowane z nazw lub współrzędnych, opisane jako otwarcie zewnętrznej mapy.

Rozdzielić konfigurację planowania i komunikacji. Przykładowe przyszłe ustawienia
`MESSAGING_MODE=demo` i `DEMO_ENABLED=true` nie istnieją jeszcze w aplikacji.
`PLANNING_MODE=mock` może współpracować zarówno z symulatorem, jak i rzeczywistym
WAHA, a `PLANNING_MODE=live` z formularzem bez WhatsApp.

## Kolejność wdrażania

### P1 — pełny plan i mapa

1. Rozszerzyć modele o jawne dane demonstracyjne.
2. Dodać pierwszy scenariusz z punktami i geometrią oraz walidację fixture.
3. Podłączyć go do istniejącego workera i zachować obecne linki/tokeny.
4. Dodać lokalną mapę demonstracyjną i powiązanie z kartami dni.
5. Zaktualizować treści formularza, widoku i podsumowania wiadomości.

Efekt: już zwykły formularz pokazuje kompletny przebieg planowania i bogaty wynik.

### P2 — rozmowa bez telefonu

1. Dodać kanał demo i lokalną skrzynkę wiadomości.
2. Wydzielić wspólną logikę przyjmowania komend z adaptera WAHA.
3. Dodać `/demo/chat`, izolację rozmów, potwierdzenie i odpowiedź końcową.
4. Dodać odczytywany z backendu postęp.

Efekt: pokaz „wiadomość → plan → mapa” bez numeru bota.

### P3 — pełny zestaw prezentacyjny

1. Dodać pozostałe plany i kontrolowane scenariusze błędów.
2. Spolszczyć interfejs demo i dopracować widok telefonu.
3. Dodać instrukcję startu, reset wyłącznie danych demo i scenariusz prezentacji.
4. Osobno wykonać test usług live po skonfigurowaniu kluczy i WhatsApp.

## Kryteria gotowości

- Start bez kluczy i WAHA pozwala przejść formularz oraz symulator czatu.
- Z każdego obsługiwanego przykładu powstaje odpowiadający mu plan.
- Widać dni, przystanki, przykładowe czasy i dystanse, punkty oraz przebieg mapy.
- Wybór dnia zmienia podświetlenie i zakres mapy; wybór punktu pokazuje opis.
- Mock nie wykonuje wywołań do OpenAI, Google ani WAHA.
- Lokalna mapa działa bez internetu, a oznaczenie demo jest stale widoczne.
- Wynik i wiadomości korzystają z rzeczywistego workera, bazy i linków do podglądu.
- Brak miejsca lub awaria trasy nie powodują pokazania fikcyjnych danych jako zweryfikowanych.
- Duplikat zdarzenia nie tworzy drugiego zadania; ponowienie wysyłki nie powtarza planowania.
- Wygasły token nie ujawnia danych; endpointy demo są wyłączone domyślnie w live.
- Testy obejmują scenariusze, brak wywołań zewnętrznych, izolację rozmów,
  ponowienia oraz zachowanie dotychczasowego trybu live.
- Kontrola w przeglądarce obejmuje komputer, telefon, wybór dni i błędy mapy.

## Pomysły na później

Wyszukiwanie aktualnych informacji w internecie, MCP, edycja planu w rozmowie,
zapisywanie map na koncie użytkownika, hotele i rezerwacje to osobne rozszerzenia.
Można dodać ich makiety prezentacyjne, ale należy wyraźnie oddzielić je od
funkcji obecnego produktu. Pierwszy etap powinien pokazać w pełni obecny zakres:
prośbę, plan 1–2 dni, miejsca, jazdę, mapę, ostrzeżenia i odpowiedź z linkiem.
