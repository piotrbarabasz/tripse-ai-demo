# Plan pracy — 1 dzień / demo DEV

Priorytet **P0** = wymagane do pokazu; **P1** = tylko jeśli wystarczy czasu.

| Czas orientacyjny | Task | P | Warunek ukończenia |
|---|---|---|---|
| 0:00–0:45 | Repo + FastAPI + Docker Compose + healthcheck | P0 | Start jednym poleceniem; `/health` działa |
| 0:45–1:30 | Webhook WAHA + mock wiadomości; QR połączenie | P0 | WhatsApp testowy trafia do FastAPI, jest deduplikacja |
| 1:30–2:30 | Brief parser + `trip.create` + zapis job | P0 | Tekst → poprawny JSON wymagań i ID zadania |
| 2:30–4:15 | Google Places + Routes + walidacja | P0 | Prawdziwe punkty i trasy; poprawne ostrzeżenia |
| 4:15–5:30 | Viewer HTML + Google Maps | P0 | Plan i polyline widoczne na telefonie i desktopie |
| 5:30–6:30 | Worker + WAHA outbound + pełny happy path | P0 | Wiadomość WA → odpowiedź z linkiem do planu |
| 6:30–8:00 | Deployment DEV + smoke test + nagranie zapasowe | P0 | Działający publiczny HTTPS do widoku; scenariusz przechodzi E2E |

Te godziny są **budżetem prac, a nie gwarancją realizacji**; integracje i provisioning mogą potrwać dłużej. Nie rozpoczynaj P1 przed pełnym P0.

## Kolejność cięć, gdy brakuje czasu

1. **Wytnij web search i opisy atrakcji** — zostają Places + Routes.
2. **Wytnij zaawansowane działanie intent routera** — prosta komenda `trip.create`.
3. **Wytnij dodatkowe reguły walidacji** — zostają limit jazdy + brak trasy.
4. **Wytnij rysowanie polyline we własnym viewerze** — pozostają lista i poprawne linki Google Maps.
5. **Jeśli WhatsApp nie działa:** formularz/API musi pokazać identyczny wynik i ten sam viewer. Demo nie jest blokowane przez QR.

## Testy odbiorowe (obowiązkowe)

- [ ] Jedno żądanie WA tworzy **jedno** zadanie, nawet po powtórzeniu webhooka.
- [ ] Zadanie kończy się sukcesem lub czytelnym błędem — nigdy nieskończonym `running`.
- [ ] Minimum 2 dni, 4 dopasowane miejsca, 1 link do mapy per dzień.
- [ ] Żadna niewyliczona trasa nie jest prezentowana jako zweryfikowana.
- [ ] Ograniczenie jazdy np. 30 min/dzień wywołuje ostrzeżenie, jeśli wynik Routes je przekracza.
- [ ] WA odsyła prawidłowy link i podsumowanie po zakończeniu zadania.
- [ ] Link działa na telefonie poza lokalną siecią.
- [ ] Zmiennie środowiskowe nie trafiają do repo; WAHA API nie jest publicznie dostępne.

## Scenariusz pokazu (ok. 3 min)

1. Wyślij wiadomość z przykładową 2-dniową wycieczką.
2. Pokaż potwierdzenie przyjęcia zadania na WhatsApp.
3. Po zakończeniu otwórz link do planu i kliknij dwa dni na mapie.
4. Pokaż rzeczywiste czasy jazdy z Routes i ostrzeżenie walidatora.
5. Otwórz jeden dzień w Google Maps.
6. Powiedz wprost: „To szkic planu z geograficznie zweryfikowanymi trasami; nie jest to gotowa, operacyjnie zatwierdzona oferta Tripse”.

## Deployment DEV — minimum

Preferowany dla 1 dnia: **jeden zawsze dostępny host** z Docker Compose (`api`, `worker`, `waha`, `caddy`) oraz trwałymi wolumenami dla SQLite i sesji WhatsApp. Caddy wystawia tylko stronę/viewer i dozwolone endpointy backendu przez HTTPS. WAHA pozostaje w sieci Docker; nie wystawiamy panelu ani klucza API na zewnątrz.

Jeśli nie ma hosta: uruchom lokalnie i udostępnij wyłącznie viewer / webhook przez tymczasowy tunel HTTPS; do demonstracji komputer musi pozostać włączony. Nie nazywaj takiego wariantu trwałym wdrożeniem DEV.

### Ryzyka i decyzja go/no-go

- **Największe ryzyko:** WhatsApp QR/sesja i konfiguracja Google Maps. Testujemy je na początku.
- **GO:** do końca dnia jest dostępny URL, działający plan i rzeczywista trasa, choćby przez formularz.
- **NO-GO dla pokazu przez WA:** WhatsApp nie odbiera lub nie wysyła stabilnie; pokazujemy ten sam flow przez WWW, nie udajemy integracji.
- **NO-GO dla deklaracji „real route”:** Google Routes nie działa. Wtedy pokazujemy tylko propozycję atrakcji, wyraźnie jako wynik ograniczony.
