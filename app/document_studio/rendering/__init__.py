"""Deterministic HTML renderer. Print/export lives in frontend/print-export.js."""
from app.document_studio.rendering.components import photo, text, trip_card


def marketing_blocks(document, output_format="a4"):
    title = text(document.title)
    intro = (f'<section class="block campaign-intro"><p class="eyebrow">{text(document.season or "Kolekcja podróży")}</p>'
             f'<h1>{title}</h1><p class="intro-description">{text(document.description)}</p></section>')
    if output_format == "social" and document.variant == "new_trips":
        intro = intro.replace('</section>', photo(document.hero_asset_id, document.hero_position, document.title) + '</section>')
    if document.variant == "theme_collection":
        intro = (f'<section class="block theme-intro">{photo(document.hero_asset_id, document.hero_position, document.theme)}'
                 f'<div class="theme-copy"><p class="eyebrow">{text(document.season or "Kolekcja podróży")}</p>'
                 f'<h1>{text(document.theme)}</h1><h2>{title}</h2><p>{text(document.description)}</p></div></section>')
    blocks = intro + ''.join(trip_card(card, i, document.variant) for i, card in enumerate(document.cards, 1))
    if document.leader:
        blocks += f'<section class="block"><p>Prowadzący kolekcję: {text(document.leader)}</p></section>'
    blocks += f'<section class="block cta"><span class="eyebrow">TWOJA KOLEJNA PODRÓŻ</span><p>{text(document.cta or "CTA / kontakt do uzupełnienia")}</p></section>'
    return blocks


def render_marketing(document, output_format="a4", data_origin=None):
    if output_format not in {"a4", "social"}:
        raise ValueError("Unknown output format")
    return render_shell(document.title, marketing_blocks(document, output_format), document.issues, output_format, document.variant, document.revision_label,
                        data_origin=document.data_origin if data_origin is None else data_origin)


def render_shell(document_title, blocks, issues, output_format="a4", variant="standard", revision_label="Podgląd roboczy", classification="KOLEKCJA PODRÓŻY", draft_export=False, data_origin="unknown"):
    """Shared page header/footer, CSP, branding and print entry point for all templates."""
    title = text(document_title)
    report = ''.join(f'<li class="{i.severity}">{text(i.message)}</li>' for i in issues)
    errors = any(i.severity == "error" for i in issues)
    page_size = "A4" if output_format == "a4" else "285.75mm 357.1875mm"
    if data_origin in {"demo", "synthetic_test"}:
        origin_label = "DEMO" if data_origin == "demo" else "TEST — DANE SYNTETYCZNE"
        classification += " · " + origin_label
        if "DOKUMENT ROBOCZY</h2>" in blocks:
            blocks = blocks.replace("DOKUMENT ROBOCZY</h2>", f"DOKUMENT ROBOCZY · {origin_label}</h2>", 1)
        elif "FIKCYJNY PRZYKŁAD DEMO" not in blocks:
            blocks = f'<section class="block provenance-banner"><strong>{origin_label}</strong><p>Materiał do oceny i testów. Nie jest potwierdzoną ofertą ani rezerwacją.</p></section>' + blocks
    return f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'">
<title>{title} — TRIPSE</title>
<link rel="stylesheet" href="/documents/assets/brand-tokens.css">
<link rel="stylesheet" href="/documents/assets/marketing.css">
<link rel="stylesheet" href="/documents/assets/trip-documents.css">
<style>@page{{size:{page_size};margin:0}}</style>
<script src="/documents/assets/print-export.js" defer></script></head>
<body class="format-{output_format} variant-{variant}" data-valid="{str(not errors or draft_export).lower()}" data-final-valid="{str(not errors).lower()}">
<div class="preview-toolbar"><div><strong>TRIPSE / podgląd</strong><small>Branding roboczy · {"A4" if output_format == "a4" else "1080 × 1350"} · {text(revision_label)}</small></div>
<button id="print-document" disabled>Zapisz jako PDF</button>
<details><summary>Uwagi do dokumentu ({len(issues)})</summary><ul>{report or '<li>Brak brakujących pól.</li>'}</ul></details>
<p id="layout-status" role="status">Przygotowanie stron…</p></div>
<div id="print-failure">Eksport zablokowany. Sprawdź komunikat podglądu: walidację danych, wskazaną sekcję układu lub dostępność zdjęcia.</div>
<main id="pages" aria-label="Strony dokumentu"></main>
<template id="page-template"><div class="sheet-wrap"><section class="sheet"><header class="document-header"><span class="wordmark" aria-label="TRIPSE, zastępczy znak tekstowy">TRIPSE<span>ODKRYWAJ WIĘCEJ</span></span><span class="header-label">{text(classification)}</span></header><div class="page-body"></div><footer class="document-footer"><span>TRIPSE · <strong>{text(classification)}</strong> · {text(revision_label)}<br>Układ i identyfikacja wizualna: propozycja robocza</span><span class="page-number"></span></footer></section></div></template>
<div id="source-blocks" hidden>{blocks}</div>
</body></html>'''
