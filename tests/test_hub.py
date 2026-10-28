from html.parser import HTMLParser
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class HubLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == 'a' and attributes.get('id'):
            self.links[attributes['id']] = attributes.get('href')


def client_for(tmp_path, peer='127.0.0.1', host='http://localhost'):
    return TestClient(create_app(tmp_path/'planner.sqlite3',document_data_path=tmp_path/'documents'),base_url=host,client=(peer,50000))


def test_hub_links_modes_and_existing_entrypoints(tmp_path,monkeypatch):
    with client_for(tmp_path) as client:
        response=client.get('/hub')
        assert response.status_code==200
        assert response.headers['cache-control']=='no-store'
        assert "script-src 'none'" in response.headers['content-security-policy']
        assert 'name="viewport"' in response.text
        assert 'lang="pl"' in response.text
        assert '{{' not in response.text
        links=HubLinks();links.feed(response.text)
        assert links.links=={'planner-link':'/planner','documents-link':'/documents/demo','assistant-link':'/demo/chat'}
        assert 'Dokument Studio działa osobno' in response.text
        for path in links.links.values():
            page=client.get(path)
            assert page.status_code==200,path
            assert 'href="/hub"' in page.text,path
        for asset in ('/static/hub.css','/static/module-nav.js','/static/module-nav.css','/documents/assets/brand-tokens.css'):
            assert client.get(asset).status_code==200
        assert client.get('/static/hub.html').status_code==404
        monkeypatch.setenv('PLANNING_MODE','live')
        response=client.get('/hub')
        assert response.status_code==200
        links=HubLinks();links.feed(response.text)
        assert links.links['assistant-link']=='#demo-mode'
        assert 'PLANNING_MODE=mock' in response.text
        assert '<section class="demo-config" id="demo-mode"  aria-' in response.text
        assert client.get('/demo/chat').status_code==404
        # No arbitrary environment text or configured secret reaches the page.
        monkeypatch.setenv('PLANNING_MODE','<script>secret-marker</script>')
        assert 'secret-marker' not in client.get('/hub').text


@pytest.mark.parametrize('headers',[
    {'Host':'evil.example'},{'Origin':'https://evil.example'},
    {'X-Forwarded-For':'127.0.0.1'},{'Forwarded':'for=127.0.0.1'},
    {'Sec-Fetch-Site':'cross-site'},
])
def test_hub_does_not_bypass_studio_local_guard(tmp_path,headers):
    with client_for(tmp_path) as client:
        assert client.get('/hub',headers=headers).status_code==403
        assert client.get('/documents/demo',headers=headers).status_code==403


def test_remote_peer_cannot_open_hub_or_studio(tmp_path):
    with client_for(tmp_path,peer='203.0.113.7') as client:
        assert client.get('/hub').status_code==403
        assert client.get('/documents/demo').status_code==403
        assert client.get('/api/document-studio/trips').status_code==403


def test_hub_is_navigation_without_job_or_document_creation(tmp_path):
    with client_for(tmp_path) as client:
        for _ in range(2):
            assert client.get('/hub').status_code==200
        assert client.get('/api/document-studio/drafts').json()==[]
        assert not list((tmp_path/'documents').rglob('*.json'))
        from app.db import Database
        assert Database(tmp_path/'planner.sqlite3').claim_next() is None
        assert client.post('/hub').status_code==405
    # Public map templates do not receive local Hub navigation.
    for filename in ('viewer.html','viewer-error.html'):
        assert '/hub' not in (Path('app/static')/filename).read_text(encoding='utf-8')


def test_docker_local_mode_preserves_proxy_rejection(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCUMENT_STUDIO_DOCKER_LOCAL','1')
    with client_for(tmp_path,peer='172.18.0.1') as client:
        assert client.get('/hub').status_code==200
        assert client.get('/hub',headers={'X-Forwarded-For':'203.0.113.7'}).status_code==403


def test_homepage_redirect_and_direct_module_refresh(tmp_path):
    with client_for(tmp_path) as client:
        root = client.get('/', follow_redirects=False)
        assert root.status_code == 302
        assert root.headers['location'] == '/hub'
        assert root.headers['cache-control'] == 'no-store'
        followed = client.get('/')
        assert followed.status_code == 200 and followed.url.path == '/hub'
        assert len(followed.history) == 1
        for path, marker in (('/hub', 'id="planner-link"'),
                             ('/planner', 'id="trip-form"'),
                             ('/documents/demo', 'studio.js'),
                             ('/demo/chat', 'id="chat-form"')):
            for _ in range(2):
                response = client.get(path, follow_redirects=False)
                assert response.status_code == 200 and marker in response.text
                assert 'location' not in response.headers
        assert 'data-hub-navigation="enabled"' in client.get('/planner').text
        slash = client.get('/planner/', follow_redirects=False)
        assert slash.status_code == 307 and slash.headers['location'].endswith('/planner')
        assert len(client.get('/planner/').history) == 1


@pytest.mark.parametrize('headers', [
    {'Host': 'evil.example'}, {'Origin': 'https://evil.example'},
    {'X-Forwarded-For': '127.0.0.1'}, {'X-Forwarded-Proto': 'https'},
    {'Forwarded': 'for=127.0.0.1'}, {'Sec-Fetch-Site': 'cross-site'},
])
def test_public_planner_does_not_advertise_private_hub(tmp_path, headers):
    # The existing public planner is preserved, without a misleading private link.
    with client_for(tmp_path) as client:
        response = client.get('/planner', headers=headers)
        assert response.status_code == 200
        assert 'data-hub-navigation="disabled"' in response.text
        assert client.get('/hub', headers=headers).status_code == 403
    with client_for(tmp_path, peer='203.0.113.7') as client:
        assert 'data-hub-navigation="disabled"' in client.get('/planner').text
        assert 'data-hub-navigation="disabled"' in client.get('/demo/chat').text


def test_caddy_allowlist_preserves_public_contract_and_private_boundary():
    # Configuration contract only; live HTTPS requires a running Caddy/Docker.
    import fnmatch
    text = Path('Caddyfile').read_text(encoding='utf-8')
    blocks = dict(re.findall(r'^\s*@(read|create)\s*\{([^}]+)\}', text, re.M))
    def allowed(method, path):
        for block in blocks.values():
            lines = [line.strip().split() for line in block.splitlines()]
            methods = next(parts[1:] for parts in lines if parts and parts[0] == 'method')
            paths = next(parts[1:] for parts in lines if parts and parts[0] == 'path')
            if method in methods and any(fnmatch.fnmatchcase(path, pattern) for pattern in paths):
                return True
        return False
    for path in ('/', '/planner', '/health', '/trip/token', '/api/viewer/token', '/api/trips/id'):
        assert allowed('GET', path)
    assert allowed('POST', '/api/trips') and allowed('POST', '/api/webhooks/waha')
    for path in ('/hub', '/documents/demo', '/api/document-studio/trips', '/demo/chat',
                 '/api/demo/messages', '/internal/jobs/id', '/dashboard', '/planner/'):
        assert not allowed('GET', path) and not allowed('POST', path)
