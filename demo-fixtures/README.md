# Fikcyjne dane Document Studio

Wycieczki do Islandii (10 dni), Kanady (15 dni) i Norwegii (5 dni) oraz kampania
obejmująca te trzy kierunki są wyłącznie materiałami demonstracyjnymi.
Nazwy miejsc służą pokazaniu struktury programu; atrakcje, przejazdy, terminy,
dostępność i usługi nie zostały zweryfikowane. Nie są to gotowe oferty.
Brak danych uczestników, rezerwacji, kodów dostępu, cen i cudzych zdjęć.

`document-presets/iceland.json` dodaje jawnie fikcyjne dane oferty i rozpiski:
przykładową kwotę oznaczoną DEMO, role organizacyjne, fikcyjne godziny oraz
kontakty `example.invalid`. Nie są ładowane do Trip; użytkownik wybiera je
świadomie przy tworzeniu dokumentu. Nie zawierają prawdziwych osób ani sekretów.

Pliki są walidowane przez te same modele Pydantic co lokalne dane użytkownika.
Edytor nigdy ich nie nadpisuje: zapisuje lokalną wersję pod tym samym ID
w `local-data/document-studio/`. Usunięcie lokalnej wersji przy zatrzymanej
aplikacji przywraca widoczność fixture'a.
