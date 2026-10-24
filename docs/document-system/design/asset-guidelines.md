# Zasady zdjęć, logo i innych zasobów

## 1. Cel

Zachować spójne, legalnie wykorzystywane fotografie i inne zasoby we wszystkich szablonach. Przykładowa grafika z rozmowy nie jest automatycznym źródłem praw do reprodukcji wszystkich zamieszczonych zdjęć.

## 2. Typy zasobów

| Typ | Zalecany format źródłowy | Reguły |
|---|---|---|
| Logo | SVG, ewentualnie PNG transparentny | Oryginalny plik od TRIPSE, warianty ciemny/jasny |
| Zdjęcie kierunku | JPG / WebP / PNG | Potwierdzone prawa do marketingowego/handlowego użycia |
| Zdjęcie hotelu | JPG / WebP | Zweryfikowany obiekt + prawo do zdjęć obiektu |
| Ikony | SVG | Jedna rodzina i spójne grubości linii |
| Mapa | Obraz lub link pochodzący z dozwolonego źródła | Respektować warunki API, przypisania, licencję i atrybucję |
| Fonty | Obsługiwane przez renderer pliki fontów | Zgodne z licencją i polskimi znakami; nie commitować bez praw |

## 3. Metadane obowiązkowe fotografii

`asset_id`, `filename`, `media_type`, `source`, `author_or_owner`, `license_type`, `usage_scope[]` (marketing/oferta/wewnętrzne), `license_verified_at`, `license_expires_at` (jeśli dotyczy), `description`, `location_reference` (jeśli przedstawia miejsce), `focal_point`, `width`, `height`, `status` (`draft|approved|rejected`).

Użytkownik może ustawić kadr, ale nie może przez kadrowanie zmienić tożsamości miejsca na fałszywą. Wrażliwe zdjęcia osób lub uczniów wymagają osobnego rozpatrzenia zgód.

## 4. Proces biblioteki

Wgraj → odczytaj metadane i rozmiar → przypisz źródło/licencję → zatwierdź → wybierz miejsce użycia → kadruj dla formatu → zapisz identyfikator w dokumencie. Zatwierdzony eksport odwołuje się do konkretnej wersji assetu.

## 5. Ograniczenia AI

AI może wskazać frazę do wyszukania zdjęcia, zasugerować podpis lub ocenę kadru. **Nie może twierdzić, że zdjęcie jest prawdziwym widokiem lokalizacji, jeśli jest wygenerowaną ilustracją.** Generowane ilustracje wymagają oznaczenia i decyzji TRIPSE przed publicznym użyciem.

## 6. Brak materiałów

Brak zdjęcia albo brak potwierdzonej licencji → użyj zatwierdzonego wariantu bez zdjęcia lub wstrzymaj publikację. Dla marketingu fotografia jest zwykle kluczowa; brak autoryzowanego obrazu powinien być ostrzeżeniem wysokiego priorytetu.

## 7. Gdzie przechowywać

Docelowo prywatny bucket obiektowy (Cloud Storage), osobne ścieżki/polityki dostępu dla `public`, `client`, `internal`; metadata w bazie. Nie dodawaj plików produkcyjnych z prawami osób trzecich bezpośrednio do repozytorium. W repozytorium mogą znajdować się neutralne fixture'y testowe z jawnie dopuszczoną licencją.

## 8. Kryteria akceptacji

Każda publiczna fotografia ma potwierdzone prawa, przypisany właściwy kierunek i dobre kadrowanie; podmiana w bibliotece nie zmienia automatycznie wcześniej zatwierdzonego pliku; eksport bez obrazu nie tworzy pustego białego prostokąta i nie przesuwa CTA poza stronę.

**Powiązania:** [branding](brand-guidelines.md) · [security](../architecture/security.md).
