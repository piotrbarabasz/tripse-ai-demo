# Szablon: materiały merytoryczne dla pilota

Stan implementacji lokalnej 2026-10-28 (szablony 0.4.0): Trzy sekcje każdego dnia: atrakcje, kontekst, narracja. KnowledgeContent ma ręczne pola i KnowledgeSource z dokładnym odniesieniem oraz datą. Tylko stop_id programu; verified wymaga źródeł z datami. internal, bez PilotData. Około 3 stron to inspiracja, a nie wymuszona liczba pustych stron.

Instrukcja edycji i ograniczenia publikacji: [Document Studio](../../../DOCUMENT_STUDIO.md).
Poniżej zachowano wymagania docelowe i inspiracje; nie oznaczają automatycznej akceptacji treści.

**ID:** `pilot.knowledge`  
**Rodzina:** `pilot` · **Odbiorca:** pilot przygotowujący prowadzenie grupy  
**Poufność:** `internal`; domyślnie bez danych uczestników i rezerwacji  
**Format początkowy:** PDF A4, orientacyjnie **3 strony na dzień**, jeśli materiał uzasadnia taką objętość.

## 1. Cel i odbiorca

Przekazać pilotowi informacje, które może wykorzystać podczas przejazdów i na miejscu: kontekst historyczny, przyrodę, kulturę, ciekawostki, krótkie historie do opowiadania. Dokument nie powtarza godzinowego harmonogramu.

## 2. Charakterystyka dokumentu / inspiracja

Przesłany 39-stronicowy dokument Kanada/USA (dni 3–15) stosuje logiczny podział:
- Strona A: **atrakcje dnia** — fakty o miejscach objętych planem.
- Strona B: **najważniejsze fakty**, **co łączy te miejsca**, **historia / geologia / przyroda**.
- Strona C: **na co zwrócić uwagę na miejscu**, **krótkie historie do opowiedzenia podczas jazdy**, **źródła i uwagi redakcyjne**.

Ten trójdzielny rytm przyjmujemy jako bazę; puste strony nie są generowane. Na przykład w dniu obejmującym Banff Gondola, Takakkaw Falls, Emerald Lake i Wapta Falls materiał można uporządkować według miejsc, kontekstu Rockies oraz wskazówek obserwacyjnych — z osobno zweryfikowanymi źródłami.

## 3. Sekcje obowiązkowe

1. Tytuł dnia, lokalizacje faktycznie obecne w programie, wersja materiału.
2. **Atrakcje dnia** — osobne karty opisowe, zrozumiałe w 30–90 sekund.
3. **Najważniejsze fakty** — 3–6 konkretnych twierdzeń z poziomem pewności i źródłami.
4. **Kontekst** — historia, przyroda, geologia, kultura lub społeczeństwo stosownie do miejsca.
5. **Na co zwrócić uwagę** — obserwacje terenowe możliwe podczas danego etapu.
6. **Krótkie historie dla grupy** — propozycje narracji, nie fikcyjne anegdoty przedstawione jako fakty.
7. **Źródła** — dokładne tytuły/URL-e, data sprawdzenia, związek ze stwierdzeniem.

## 4. Sekcje opcjonalne

„Co łączy miejsca”, słowniczek nazw lokalnych, wymowa, pomysł na pytanie do grupy, 15/30/60-sekundowa wersja opowieści, mapa i zdjęcie poglądowe do legalnego użytku, tabela zwierząt roślin/geologii.

## 5. Wymagane dane wejściowe

`trip.days[]`, `trip.days[].stops[]`, `knowledge_items[]` z: `place_id/day_id`, `category`, `text`, `sources[]`, `verification_status`, `last_verified_at`, `editor_approved`. Opcjonalne `narration_short`, `narration_long`, `observation_tips[]`, `image_asset_ids[]`.

## 6. Zasady prezentacji treści

- Wybieraj fakty **o miejscach występujących w programie**, nie losowe ciekawostki o kraju.
- Unikaj „ciekawostek” bez źródła, legend i anegdot podawanych jako udokumentowana prawda.
- Rozdziel **fakt**, **interpretację** i **proponowaną narrację**. Sformułowanie opowieści może być autorskie, ale jej twierdzenia faktograficzne muszą być weryfikowalne.
- Zamiast nazwy instytucji bez adresu stosuj precyzyjny URL do artykułu/strony, datę dostępu i tytuł.
- Dla informacji zależnych od sezonu lub lokalnych ograniczeń pokaż `sprawdzić przed wyjazdem`.
- AI przygotowuje draft; pilot albo osoba merytoryczna zatwierdza przed użyciem w terenie.

## 7. Wymagania wizualne

Czytelne, tekstowe strony z jednym kolorem akcentu; wyróżnione fakty i narracje; duże nagłówki dni; brak sztucznego wydłużania treści. Stały margines i stopka z numerem dnia, rewizją i datą weryfikacji. Zdjęcia tylko, gdy poprawiają rozpoznanie miejsca.

## 8. Obsługa brakujących informacji

Brak źródła do twierdzenia → oznacz `niezweryfikowane` i skieruj do przeglądu, a nie przedstawiaj jako potwierdzone. Brak treści na 3 strony → generuj 1–2 wartościowe strony. Brak atrakcji w danym dniu → czytelna informacja, nie twórz na siłę materiału.

## 9. Przykładowa struktura dokumentu

Dzień N / atrakcje → kontekst i fakty → historie, obserwacje i źródła. Powtórz dla wszystkich dni programu. Dodatkowe rozwinięcia mogą być aneksami.

## 10. Kryteria akceptacji

Każde istotne twierdzenie ma precyzyjne źródło; nie pojawiają się atrakcje spoza zatwierdzonego programu; każda historia nadaje się do wykorzystania z grupą; brak przypadkowej kopii danych operacyjnych i niepotwierdzonych ciekawostek.

**Powiązania:** [walidacja faktów](../../system-data/content-validation.md) · [model wiedzy](../../system-data/trip-data-model.md).
