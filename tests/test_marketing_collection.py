import io

import pytest
from PIL import Image

from app.document_studio.assets import AssetStore, MAX_UPLOAD_BYTES
from app.document_studio.marketing import build_marketing
from app.document_studio.models import Campaign, CampaignItem, ImagePosition, Trip
from app.document_studio.rendering import render_marketing
from app.document_studio.repository import JsonRepository
from tests.test_document_studio import client_for


def image_bytes(format="PNG"):
    output = io.BytesIO()
    image = Image.new("RGB", (600, 400), "#aac4b7")
    image.save(output, format=format)
    return output.getvalue()


@pytest.mark.parametrize("variant", ["new_trips", "theme_collection"])
@pytest.mark.parametrize("count", [1, 3, 8])
def test_structured_renderer_scenarios(tmp_path, variant, count):
    repository = JsonRepository(tmp_path)
    trips = [Trip(trip_id=f"trip-{i}",title="Żółte góry i jeziora — " + "długi tytuł " * 10, destinations=["Islandia"]) for i in range(count)]
    campaign = Campaign(title="Kolekcja podróży", theme="Góry i jeziora", cta="Napisz do nas", layout_variant=variant,
                        items=[CampaignItem(trip_id=trip.trip_id, short_hook="Opis kierunku", highlights=["Natura", "Przestrzeń"]) for trip in trips])
    document = build_marketing(campaign, trips, AssetStore(repository))
    assert not [i for i in document.issues if i.severity == "error"]
    for format in ("a4", "social"):
        html = render_marketing(document, format)
        assert html.count('class="block trip-card ') == count
        assert "ilustracja zastępcza" in html
        assert "Termin do ustalenia" in html
        assert "Napisz do nas" in html
        assert ('class="block theme-intro"' in html) == (variant == "theme_collection")


def test_validation_and_escape_whitelist(tmp_path):
    repository = JsonRepository(tmp_path)
    trip = Trip(title="<script>alert(1)</script>")
    campaign = Campaign(title="<img src=x onerror=alert(1)>", layout_variant="theme_collection", items=[CampaignItem(trip_id=trip.trip_id)])
    document = build_marketing(campaign, [trip], AssetStore(repository))
    assert {i.field_path for i in document.issues if i.severity == "error"} == {"cta", "theme"}
    assert any(i.field_path.endswith("date_range_or_label") for i in document.issues)
    assert any(i.field_path.endswith("image_asset_id") for i in document.issues)
    html = render_marketing(document)
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert '<img src=x' not in html
    assert 'data-valid="false"' in html
    assert 'internal_notes' not in html


@pytest.mark.parametrize("format,mime,extension", [("JPEG","image/jpeg","jpg"),("PNG","image/png","png"),("WEBP","image/webp","webp")])
def test_upload_reencoding_and_restart(tmp_path, format, mime, extension):
    with client_for(tmp_path) as client:
        response = client.post(f"/api/document-studio/assets?filename=legal.{extension}&rights_confirmed=true", content=image_bytes(format), headers={"Content-Type":mime})
        assert response.status_code == 201, response.text
        asset = response.json()
        assert asset["width"] == 600 and asset["height"] == 400
        assert asset["rights_confirmed"] is True
        path = f"/api/document-studio/assets/{asset['asset_id']}/content"
        content = client.get(path)
        assert content.status_code == 200
        assert content.headers["content-type"] == mime
        with Image.open(io.BytesIO(content.content)) as decoded:
            assert decoded.size == (600,400)
            assert not decoded.getexif()
        assert client.get(path,headers={"Origin":"https://evil.example"}).status_code == 403
        assert client.get('/documents/assets/'+asset['asset_id']+'.'+extension).status_code == 404
    with client_for(tmp_path) as client:
        assert client.get(path).status_code == 200
        assert len(client.get("/api/document-studio/assets").json()) == 1


@pytest.mark.parametrize("body,mime,filename,rights", [
    (b'<svg onload="alert(1)"></svg>',"image/svg+xml","image.svg",True),
    (b"not a png","image/png","image.png",True),
    (image_bytes(),"image/jpeg","wrong.jpg",True),
    (image_bytes(),"image/png","photo.html",True),
    (image_bytes(),"image/png","photo.png",False),
])
def test_reject_invalid_uploads(tmp_path, body, mime, filename, rights):
    with client_for(tmp_path) as client:
        response = client.post("/api/document-studio/assets", params={"filename":filename,"rights_confirmed":rights}, content=body, headers={"Content-Type":mime})
        assert response.status_code == 422
        assert client.get("/api/document-studio/assets").json() == []


def test_upload_limits_and_path_handling(tmp_path):
    with client_for(tmp_path) as client:
        response = client.post("/api/document-studio/assets?filename=huge.png&rights_confirmed=true", content=b"x"*(MAX_UPLOAD_BYTES+1),headers={"Content-Type":"image/png"})
        assert response.status_code == 413
        large = io.BytesIO()
        Image.new("1", (5000,5000)).save(large,format="PNG")
        response = client.post("/api/document-studio/assets?filename=pixels.png&rights_confirmed=true",content=large.getvalue(),headers={"Content-Type":"image/png"})
        assert response.status_code == 422
        # Filename is display-only. The generated ID determines the private path.
        response = client.post("/api/document-studio/assets?filename=../../outside.png&rights_confirmed=true",content=image_bytes(),headers={"Content-Type":"image/png"})
        assert response.status_code == 201
        assert not (tmp_path / "outside.png").exists()


def test_campaign_edits_images_crops_and_export_snapshot_persist(tmp_path):
    with client_for(tmp_path) as client:
        asset = client.post("/api/document-studio/assets?filename=own.png&rights_confirmed=true",content=image_bytes(),headers={"Content-Type":"image/png"}).json()
        campaign = client.get("/api/document-studio/campaigns/demo-northern-journeys").json()
        campaign.update(title="Nowa kolekcja", layout_variant="theme_collection", theme="Żółte góry", cta="Kontakt", hero_asset_id=asset["asset_id"],hero_position={"x":20,"y":80,"zoom":1.5})
        campaign["items"].reverse()
        campaign["items"][0].update(display_title="Tytuł w kampanii",short_hook="Opis redakcyjny",image_asset_id=asset["asset_id"],image_position={"x":10,"y":90,"zoom":2})
        updated = client.put("/api/document-studio/campaigns/demo-northern-journeys",json=campaign)
        assert updated.status_code == 200,updated.text
        assert client.get("/api/document-studio/trips/demo-norway").json()["title"] != "Tytuł w kampanii"
        preview = client.post("/api/document-studio/marketing/preview",json={"campaign":updated.json(),"output_format":"social"})
        assert preview.status_code == 200
        assert 'object-position:10.0% 90.0%' in preview.text
        assert 'transform:scale(2.0)' in preview.text
        draft = client.post("/api/document-studio/drafts",json={"template_id":"marketing.collection","source_type":"campaign","source_id":"demo-northern-journeys","layout_variant":"theme_collection"}).json()
        url = f"/api/document-studio/drafts/{draft['document_id']}/preview"
        frozen = client.get(url).text
        edit = updated.json()
        edit["title"]="Późniejsza zmiana"
        assert client.put("/api/document-studio/campaigns/demo-northern-journeys",json=edit).status_code == 200
        assert client.get(url).text == frozen
        assert client.get(url,headers={"X-Forwarded-For":"127.0.0.1"}).status_code == 403
        assert client.get(url+"?output_format=invalid").status_code == 422
    with client_for(tmp_path) as client:
        assert client.get(url).text == frozen
        restored = client.get("/api/document-studio/campaigns/demo-northern-journeys").json()
        assert restored["items"][0]["image_position"]["zoom"] == 2
        assert restored["hero_position"]["x"] == 20


def test_invalid_image_references_and_crop_values(tmp_path):
    with pytest.raises(ValueError):
        ImagePosition(x=101)
    with pytest.raises(ValueError):
        ImagePosition(zoom=float('nan'))
    with client_for(tmp_path) as client:
        campaign = client.get("/api/document-studio/campaigns/demo-northern-journeys").json()
        campaign["hero_asset_id"]="missing-image"
        assert client.put("/api/document-studio/campaigns/demo-northern-journeys",json=campaign).status_code == 404


def test_upload_removes_real_exif_and_applies_orientation(tmp_path):
    image = Image.new("RGB", (600,400), "#aac4b7")
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise.
    exif[270] = "Private metadata must not survive"
    data = io.BytesIO()
    image.save(data,format="JPEG",exif=exif)
    store = AssetStore(JsonRepository(tmp_path))
    asset = store.upload(data.getvalue(),"image/jpeg","own.jpg",True)
    assert (asset.width,asset.height) == (400,600)
    with Image.open(store.image_path(asset)) as decoded:
        assert not decoded.getexif()


def test_animated_upload_is_rejected(tmp_path):
    data = io.BytesIO()
    image = Image.new("RGB",(20,20),"red")
    image.save(data,format="WEBP",save_all=True,append_images=[Image.new("RGB",(20,20),"blue")],duration=100)
    with pytest.raises(ValueError,match="statyczne"):
        AssetStore(JsonRepository(tmp_path)).upload(data.getvalue(),"image/webp","animation.webp",True)
