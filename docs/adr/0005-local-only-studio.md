---
id: ADR-0005
title: "Lokalny dostęp do Document Studio bez logowania w demo"
status: proposed
date: 2026-10-25
author: "Codex — autor zapisu retrospektywnego"
area: "Bezpieczeństwo i wdrożenie demo"
related_tasks: [DEMO-01, DEMO-02, DEMO-03]
related_prs: []
supersedes: []
---

# ADR-0005: Lokalny dostęp do Document Studio bez logowania w demo

Wdrożone; retrospektywny zapis bez potwierdzenia właściciela.

## 1. Kontekst i problem

Studio zawiera materiały wewnętrzne, ale demo nie ma tożsamości i ról użytkowników.
Publiczny viewer planera nie jest kanałem udostępniania materiałów pilota.

## 2. Rozważane alternatywy

Uwierzytelniony panel, panel dostępny publicznie lub panel wyłącznie lokalny.
Logowanie i role są planem docelowym. Brak dowodu historycznego porównania dostawców tożsamości.

## 3. Decyzja

Router studia stosuje `local_only`: adres klienta, lokalny Host, Origin oraz
odrzucenie nagłówków proxy i żądań cross-site. W Compose port jest przypięty
do `127.0.0.1`; jawna opcja Docker dopuszcza prywatny adres mostu, nadal z lokalnym Host.
Caddy nie udostępnia ścieżek studia. JSON i uploady nie są publicznym StaticFiles.

## 4. Uzasadnienie

**Udokumentowane:** instrukcje DEMO-01/03 definiują lokalny zakres i zakaz
publicznych materiałów pilota bez logowania. Specyfikacja docelowa wymaga ról.
**Wniosek:** ograniczenie sieciowe jest tymczasową granicą dostępu demo.
**Niepotwierdzone:** akceptacja tego modelu dla realnych danych i polityka dostępu organizacji.

## 5. Konsekwencje pozytywne i negatywne

Plus: studia nie wystawia dostarczona konfiguracja publicznego proxy.
Minus: brak identyfikacji użytkownika, uprawnień per dokument, audytu i ochrony
przed innym lokalnym procesem. Kontrola lokalnego ruchu nie zastępuje logowania.

## 6. Dług techniczny i ograniczenia

Granica zależy od konfiguracji sieci/Host/proxy. Klasa poufności jest metadaną,
nie systemem ról. Nie rozszerzać opcji Docker na dowolne publiczne wdrożenie.
[DEBT-03 i DEBT-05](../tracking/repository-audit.md).

## 7. Wpływ na kosztorys

[COST-02 i COST-06](../tracking/estimates.md): tożsamość, autoryzacja, audyt,
dystrybucja materiałów, testy dostępu i bezpieczne wdrożenie. Wybór produktu
do logowania i jego opłaty nie są jeszcze znane.

## 8. Powiązane taski, PR, commity i dokumenty

- [API](../../app/document_studio/api.py): `local_only`, `document_router`;
  [Compose](../../compose.yaml), [Caddyfile](../../Caddyfile).
- [DEMO-01](../DOCUMENT_STUDIO.md), [DEMO-03](../TRIP_DOCUMENTS.md),
  [bezpieczeństwo docelowe](../document-system/architecture/security.md).
- Commit `f9035e5ff16c293b8fddbe33938a29b96eb6ca87`; brak potwierdzonego PR i akceptacji właściciela.

## 9. Warunki ponownego rozważenia decyzji

Współdzielony/publiczny dostęp, rzeczywiste dane poufne, użytkownicy zdalni
lub inne proxy. Wymaga to zaprojektowania dostępu przed zmianą ekspozycji sieciowej.
