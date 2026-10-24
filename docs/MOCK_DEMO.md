# Uruchomienie pełnego demo mock

Ustaw w istniejącym `.env`:

```dotenv
PLANNING_MODE=mock
PUBLIC_BASE_URL=http://localhost:8000
```

W PowerShell, w katalogu projektu:

```powershell
docker desktop start
docker compose up --build -d
```

Otwórz http://localhost:8000/demo/chat. Wybierz Karkonosze, Ojców lub Trójmiasto,
zostaw scenariusz „Pełny plan” i wyślij wiadomość. Worker zapisze potwierdzenie
oraz odpowiedź z linkiem. Pod linkiem zobaczysz dni, przystanki, przykładowe
kilometry i czas, ostrzeżenia oraz interaktywny schemat mapy.

Mapa nie wymaga internetu. Wybierz dzień, kliknij punkt, przeciągnij podkład lub
użyj przycisków powiększenia i dopasowania. Linie łączą punkty poglądowo:
nie przedstawiają przebiegu drogi ani trasy pieszej.

## Scenariusze testowe

- Pełny plan: komplet dni, przystanków i linii demonstracyjnych.
- Przekroczony limit jazdy: limit jest celowo ustawiony na godzinę; zobacz ostrzeżenia.
- Nieznalezione miejsce: brak jednego przystanku i linii pierwszego dnia; informacja
  o brakującym miejscu znajduje się w uwagach do planu.
- Błąd trasy: pierwszy dzień ma punkty, lecz nie pokazuje czasu, dystansu i linii.
- Awaria planowania: odpowiedź z błędem; kolejna wiadomość nadal może utworzyć plan.
- Ponowienie wysyłki: pierwsza próba wysłania wyniku zawodzi, następna następuje
  po około 30 sekundach. Gotowy plan nie jest generowany ponownie.
- Wygasły link: wynik powstaje, ale link od razu zwraca stronę niedostępnego planu.

„Powtórz to samo zdarzenie” wysyła ten sam identyfikator wiadomości i zwraca
to samo zadanie. „Wyślij wiadomość” tworzy nowe zdarzenie, nawet przy takim samym
tekście. „Nowa rozmowa” otwiera pustą rozmowę; nie usuwa historii z bazy.
Rozmowa jest przechowywana w bieżącej sesji karty przeglądarki. Jej losowy
identyfikator jest lokalnym kluczem dostępu, nie systemem kont użytkowników.

Formularz http://localhost:8000/ używa tej samej kolejki i generatora, ale nie
tworzy wiadomości czatu. W mock obsługujemy przygotowane wycieczki, a nie dowolne
prośby. Nieznany region lub niepasująca liczba dni daje czytelny błąd.

## Architektura i ograniczenia

- Dane: `app/demo_data.py`, walidowane przez wspólne modele planu.
- Demo ma źródło `demo_fixture`, stan miejsc/tras `demo` i `is_mock=true`.
  Przykładowe identyfikatory z prefiksem `demo:` nie są Google Place ID.
- Prawdziwa kolejka, worker, SQLite, trwałe wiadomości i tokeny podglądu.
- Kanał `demo` trafia do lokalnej skrzynki, a sesja WAHA do adaptera WAHA.
- `/api/demo/*` oraz `/demo/chat` są dostępne tylko przy `PLANNING_MODE=mock`.
- Etapy pokazują zapisany przez backend stan kolejki, przygotowania i dostarczenia;
  nie symulują oddzielnych wywołań AI ani Google.
- Brak wywołań OpenAI, Google i WAHA w przepływie symulatora. Mapę rysuje lokalny SVG.
- Brak wyszukiwania internetowego, rezerwacji, edycji rozmową i zapisanych map Google.
- Tryb live nadal używa bezpośrednich API OpenAI, Places, Routes i Google Maps JS;
  wymaga kluczy i osobnej weryfikacji z rzeczywistymi usługami.

Restart kontenerów zachowuje historię. Nie używaj `docker compose down -v` do
resetowania pojedynczego demo: usuwa również pozostałe plany i sesje WhatsApp.

## Weryfikacja

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python tests/browser_smoke.py
# Wymaga uruchomionego lokalnego API i workera w mock:
.\.venv\Scripts\python tests/browser_demo_smoke.py
```

Ostatni skrypt sprawdza trzy wycieczki, czat, mapę i jej interakcje, duplikaty,
błędy, wygasanie oraz ponowienie wysyłki. Zapisuje zrzuty komputera i telefonu
w ignorowanym katalogu `data/demo-screenshots/`.
