---
id: ADR-0008
title: "Lokalny Hub jako nawigacja istniejących modułów demo"
status: proposed
date: 2026-10-25
author: "Codex — autor propozycji i implementacji"
area: "Nawigacja i granice dostępu"
related_tasks: [HUB-01]
related_prs: []
supersedes: []
---

# ADR-0008: Lokalny Hub jako nawigacja istniejących modułów demo

Wdrożone w ramach HUB-01; ADR pozostaje propozycją bez osobnej akceptacji.
Nie zastępuje decyzji o modułowym FastAPI ani lokalnym studiu.
Brak osobnego potwierdzenia właściciela dla tego ADR; zlecenie użytkownika obejmuje wykonanie Hubu.

## 1. Kontekst i problem

Moduły mają oddzielne wejścia: formularz `/`, studio `/documents/demo` i symulator
`/demo/chat`. Potrzebny jest wspólny start demonstracji, bez integracji ich danych.
Symulator jest obecnie wyłączany przez istniejący backend w trybie innym niż `mock`.

## 2. Rozważane alternatywy

Zastąpienie `/`, publiczny portal lub dodatkowa lokalna strona nawigacyjna.
Zastąpienie formularza naruszałoby zachowanie starego adresu; portal publiczny
wymagałby innego zakresu dostępu. Nowy framework nie jest potrzebny dla trzech kart.

## 3. Decyzja

Dodać `/hub` w tym samym FastAPI, z istniejącą zależnością `local_only`.
Karty wskazują istniejące adresy. Dla wyłączonego symulatora pokazać instrukcję
włączenia mocka; nie zmieniać jego guardu. Powroty dodać do formularza, symulatora
i panelu studia, bez zmian publicznego viewera `/trip/{token}` i reguł Caddy.

## 4. Uzasadnienie

**Udokumentowane:** zlecenie HUB-01 wymaga nawigacji istniejących modułów,
utrzymania endpointów i zabezpieczeń oraz jawnego odróżnienia planu od integracji.
**Wniosek:** lokalna granica Hubu jest spójna z pokazem Document Studio.
**Niepotwierdzone:** potrzeba publicznego Hubu i docelowy zatwierdzony branding.

## 5. Konsekwencje pozytywne i negatywne

Plus: jeden start i czytelne powroty bez zmiany przepływów danych.
Minus: stan prezentuje konfigurację trybu, nie sprawność workera lub integracji.
Bez mocka symulator nadal wymaga zmiany konfiguracji i restartu przez operatora.

## 6. Dług techniczny i ograniczenia

Lista trzech wejść jest jawnie utrzymywana w stronie Hubu. Przepływ mapa → dokument
pozostaje ręczny. Hub i studio są przeznaczone do bezpośredniego lokalnego wejścia,
nie do publicznego reverse proxy. Wspólne tokeny są roboczą identyfikacją wizualną.

## 7. Wpływ na kosztorys

Utrzymanie nawigacji i regresji UI należy do [COST-07](../tracking/estimates.md).
Publiczny dostęp lub automatyzacja między modułami byłyby osobnym zakresem
COST-02/05/06, bez przypisywania im tutaj godzin ani kwot.

## 8. Powiązane taski, PR, commity i dokumenty

- HUB-01: zlecenie użytkownika z 25.10.2026; brak commitu/PR tej lokalnej zmiany.
- [Router Hubu](../../app/hub.py), [strona](../../app/hub_frontend/index.html),
  [instrukcja Hubu](../HUB.md), [istniejący symulator](../../app/demo.py).
- [ADR-0001](0001-modular-fastapi.md), [ADR-0005](0005-local-only-studio.md),
  [ADR-0006](0006-template-registry-shared-components.md).

## 9. Warunki ponownego rozważenia decyzji

Zlecenie publicznego portalu, zastąpienia `/`, automatyzacji między modułami
lub monitorowania rzeczywistej dostępności. Nie wynika to z dodania kart nawigacyjnych.
