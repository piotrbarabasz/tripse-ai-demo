# Product overview — TRIPSE Document System

## 1. Problem

Dokumenty o tej samej wycieczce są dziś przygotowywane dla różnych odbiorców w odmiennych formach. Przykłady obejmują grafikę promującą kierunki, podstawową rozpiskę organizacyjną, szczegółowy program godzinowy oraz kilkudziesięciostronicowy zestaw wiedzy dla pilota. Dane są częściowo powtarzalne, a styl i poziom szczegółowości nie są zunifikowane.

## 2. Cel produktu

Panel WWW dostępny dla uprawnionych pracowników TRIPSE, hostowany docelowo w GCP. Panel ma umożliwiać utworzenie lub wybranie wycieczki i wygenerowanie z niej wielu dokumentów w spójnym stylu, przy zachowaniu odrębnych zasad widoczności i wymagań treści.

### Mierzalny rezultat MVP

- Ta sama testowa wycieczka → co najmniej 3 różne dokumenty (marketing, pilot basic, oferta private).
- Każdy dokument ma jasny typ, wersję, adresata, status i przydzielone zdjęcia.
- System pokazuje braki danych przed eksportem i nie dopisuje potwierdzonych faktów z własnej inicjatywy.
- PDF renderuje poprawnie polskie znaki, pełne strony i materiały graficzne.
- Dokument wewnętrzny nie jest przypadkowo dostępny jako publiczny materiał marketingowy.

## 3. Grupy odbiorców

| Odbiorca | Chce uzyskać | Rodzina dokumentów |
|---|---|---|
| Klient prywatny | Wizję wyjazdu, program, zakres świadczeń, cenę | Oferty |
| Uczestnik samodzielny | Jasny zakres podróży bez pilota i wsparcia | Oferta Self-Guide |
| Szkoła / nauczyciel | Walory edukacyjne, opiekę, logistykę i koszt | Oferta szkolna |
| Firma / HR | Integrację, hotel, elementy szkoleniowe i warianty | Oferta incentive |
| Odbiorca marketingu | Powód do zainteresowania się kierunkiem | Marketing |
| Pilot TRIPSE | Sprawny przebieg dnia i kontakt do usługodawców | Rozpiski |
| Pilot TRIPSE | Rzetelną historię, przyrodę, fakty, anegdoty | Materiały merytoryczne |

## 4. Granice modułu

**W zakresie:** katalog typów, formularz/edytor treści, wybór obrazów, podgląd, wersjonowanie dokumentów, statusy zatwierdzenia, generacja PDF, możliwość wykorzystania danych z planera przez adapter.

**Poza pierwszym MVP:** pełny CMS, CRM, automatyczna wysyłka klientom, synchronizacja rezerwacji w czasie rzeczywistym, automatyczna wycena z dostępnością, samodzielne podejmowanie decyzji przez agenta, edycja PDF jak w edytorze DTP, wideorozmowa grupy Self-Guide (pomysł na kolejny etap), pełny agent WhatsApp do zarządzania dokumentami.

## 5. Zasady produktu

1. **Jedne dane → wiele widoków.** Treść wycieczki jest oddzielona od jej prezentacji.
2. **Bez fikcyjnych konkretów.** Ceny, miejsca, obiekty, rezerwacje i bezpieczeństwo podlegają walidacji.
3. **Różna prywatność.** Dane uczestników/rezerwacji mogą być używane tylko w dokumentach wewnętrznych z właściwym dostępem.
4. **Edycja przez człowieka.** AI pomaga formułować opisy i streszczenia; człowiek zatwierdza efekt.
5. **Szablony deterministyczne.** Styl, układ, jednostki i obowiązkowe sekcje wynikają z konfiguracji szablonu, nie ze swobodnego promptu.
6. **Przewidywalny eksport.** Ten sam snapshot danych i wersja szablonu generują odtwarzalny dokument.

## 6. Ustalony zakres kontra propozycje

**Wymagania z rozmowy:** 4 rodzaje ofert, marketing nowości, 2 poziomy rozpiskek dla pilota, materiał merytoryczny (orientacyjnie 3 strony na dzień), zdjęcia, logo, spójna typografia, mały panel na GCP.

**Propozycje do zatwierdzenia:** dokładne nazwy ID, zestaw pól, układy, fonty i paleta, rola recenzenta, PDF jako pierwszy format eksportu, techniczna architektura i kolejność MVP.

## 7. Powiązane dokumenty

[Typy szablonów](template-catalog.md) · [Przepływ](document-workflow.md) · [Model danych](../system-data/trip-data-model.md) · [Roadmapa](../development/roadmap.md)
