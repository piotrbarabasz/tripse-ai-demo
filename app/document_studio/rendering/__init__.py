"""Deterministic HTML renderer. Print/export lives in frontend/print-export.js."""
from app.document_studio.rendering.components import photo, text, trip_card


def render_marketing(document, output_format="a4"):
    if output_format not in {"a4", "social"}:
        raise ValueError("Unknown output format")
    title = text(document.title)
    intro = (f'<section class="block campaign-intro"><p class="eyebrow">{text(document.season or "Kolekcja podróży")}</p>'
             f'<h1>{title}</h1><p class="intro-description">{text(document.description)}</p></section>')
    if document.variant == "theme_collection":
        intro = (f'<section class="block theme-intro">{photo(document.hero_asset_id, document.hero_position, document.theme)}'
                 f'<div class="theme-copy"><p class="eyebrow">{text(document.season or "Kolekcja podróży")}</p>'
                 f'<h1>{text(document.theme)}</h1><h2>{title}</h2><p>{text(document.description)}</p></div></section>')
    blocks = intro + ''.join(trip_card(card, i, document.variant) for i, card in enumerate(document.cards, 1))
    blocks += f'<section class="block cta"><span class="eyebrow">TWOJA KOLEJNA PODRÓŻ</span><p>{text(document.cta or "CTA / kontakt do uzupełnienia")}</p></section>'
    return render_shell(document.title, blocks, document.issues, output_format, document.variant, document.revision_label)


def render_shell(document_title, blocks, issues, output_format="a4", variant="standard", revision_label="Podgląd roboczy", classification="KOLEKCJA PODRÓŻY"):
    """Shared page header/footer, CSP, branding and print entry point for all templates."""
    title = text(document_title)
    report = ''.join(f'<li class="{i.severity}">{text(i.message)}</li>' for i in issues)
    errors = any(i.severity == "error" for i in issues)
    page_size = "A4" if output_format == "a4" else "285.75mm 357.1875mm"
    return f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'">
<title>{title} — TRIPSE</title>
<link rel="stylesheet" href="/documents/assets/brand-tokens.css">
<link rel="stylesheet" href="/documents/assets/marketing.css">
<link rel="stylesheet" href="/documents/assets/trip-documents.css">
<style>@page{{size:{page_size};margin:0}}</style>
<script src="/documents/assets/print-export.js" defer></script></head>
<body class="format-{output_format} variant-{variant}" data-valid="{str(not errors).lower()}">
<div class="preview-toolbar"><div><strong>TRIPSE / podgląd</strong><small>Branding roboczy · {"A4" if output_format == "a4" else "1080 × 1350"} · {text(revision_label)}</small></div>
<button id="print-document" disabled>Zapisz jako PDF</button>
<details><summary>Uwagi do dokumentu ({len(issues)})</summary><ul>{report or '<li>Brak brakujących pól.</li>'}</ul></details>
<p id="layout-status" role="status">Przygotowanie stron…</p></div>
<div id="print-failure">Nie można wyeksportować: uzupełnij pola oznaczone błędem lub skróć zawartość zbyt dużej karty.</div>
<main id="pages" aria-label="Strony dokumentu"></main>
<template id="page-template"><div class="sheet-wrap"><section class="sheet"><header class="document-header"><span class="wordmark" aria-label="TRIPSE, zastępczy znak tekstowy">TRIPSE<span>ODKRYWAJ WIĘCEJ</span></span><span class="header-label">{text(classification)}</span></header><div class="page-body"></div><footer class="document-footer"><span>TRIPSE · <strong>{text(classification)}</strong> · {text(revision_label)}<br>Układ i identyfikacja wizualna: propozycja robocza</span><span class="page-number"></span></footer></section></div></template>
<div id="source-blocks" hidden>{blocks}</div>
</body></html>'''
