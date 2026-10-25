"""Only controlled components produce HTML. All content is escaped."""
from html import escape


def text(value):
    return escape(str(value), quote=True)


def photo(asset_id, position, caption):
    if not asset_id:
        return '<div class="photo placeholder"><div class="placeholder-shape"></div><span>TRIPSE / ilustracja zastępcza</span></div>'
    return (f'<figure class="photo"><img src="/api/document-studio/assets/{text(asset_id)}/content" '
            f'alt="{text(caption)}" style="object-position:{position.x}% {position.y}%;'
            f'transform:scale({position.zoom});transform-origin:{position.x}% {position.y}%"></figure>')


def trip_card(card, index, variant):
    return (f'<article class="block trip-card {variant}">'
            f'{photo(card.image_asset_id, card.image_position, card.title)}'
            f'<div class="card-copy"><div class="card-meta"><span class="trip-index">{index:02d}</span>'
            f'<span class="badge">{text(card.badge)}</span><span>{text(card.destination)}</span></div>'
            f'<h2>{text(card.title)}</h2><p class="date-label">{text(card.date_label)}</p>'
            f'<p class="card-description">{text(card.description)}</p>'
            f'<ul class="highlights">{"".join(f"<li>{text(h)}</li>" for h in card.highlights)}</ul></div></article>')
