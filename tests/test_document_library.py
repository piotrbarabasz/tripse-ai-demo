"""Library persistence, immutable history, CAS failures, metadata and access boundaries."""
import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from google.api_core.exceptions import ServiceUnavailable

from app.document_studio.api import DraftRequest, DraftUpdate
from app.document_studio.library import DocumentLibrary, LibraryMutation, StatusMutation
from app.document_studio.models import DocumentSection
from app.document_studio.repository import JsonRepository, StorageError, ConflictError
from app.document_studio.cloud_storage import GCSRepository
from app.document_studio.service import DocumentService
from app.document_studio.templates import TEMPLATES
from tests.test_cloud_demo import FakeBucket, cloud_demo
from tests.test_document_studio import client_for


@pytest.fixture(params=['json','gcs'])
def store(request,tmp_path):
    bucket=FakeBucket()
    factory=(lambda:JsonRepository(tmp_path/'documents')) if request.param=='json' else lambda:GCSRepository(bucket)
    repo=factory();repo.initialize()
    return SimpleNamespace(repo=repo,factory=factory,bucket=bucket,kind=request.param)


def create(repo,template='offer.private',variant='standard'):
    return DocumentService(repo).create_draft(DraftRequest(template_id=template,
        source_type='campaign' if template=='marketing.collection' else 'trip',
        source_id='demo-northern-journeys' if template=='marketing.collection' else 'demo-canada',layout_variant=variant))


def mutation(revision):return LibraryMutation(revision=revision,operation_id=uuid4())


CASES=[(t,'standard') for t in TEMPLATES if t!='marketing.collection']+[('marketing.collection','new_trips'),('marketing.collection','theme_collection')]


@pytest.mark.parametrize('template,variant',CASES)
def test_all_templates_copy_full_state_snapshot_and_history(store,template,variant):
    repo=store.repo; service=DocumentService(repo);library=DocumentLibrary(repo)
    original=create(repo,template,variant)
    sections=copy.deepcopy(original.sections)
    sections.append(DocumentSection(title='Żółć — własna tabela',kind='table',columns=['Nazwa','Opis'],rows=[['Góry','Treść']],order=99,visible=False))
    sections.append(DocumentSection(title='Galeria',kind='gallery',images=[{'caption':'Opis','position':{'x':22,'y':67,'zoom':1.4}}],order=98))
    edited=service.update_draft(original.document_id,DraftUpdate(revision=1,title='Zapisany dokument',sections=sections,editorial_notes='Notatka zachowana'),actor='editor-subject')
    assert edited.revision==2 and edited.created_by is None and edited.updated_by=='editor-subject'
    ready=library.transition(edited.document_id,StatusMutation(revision=2,operation_id=uuid4(),document_status='ready'),'status','reviewer-subject')
    op=mutation(ready.revision)
    duplicate=library.duplicate(ready.document_id,op,'copy-author')
    assert library.duplicate(ready.document_id,op).document_id==duplicate.document_id
    assert duplicate.document_id!=ready.document_id and duplicate.revision==1 and duplicate.document_status=='draft'
    assert duplicate.created_by=='copy-author' and duplicate.updated_by=='copy-author'
    assert duplicate.title.endswith('— kopia') and duplicate.duplicated_from_document_id==ready.document_id
    for field in ('trip_snapshot','campaign_snapshot','campaign_trip_snapshots','sections','offer_data','offer_details','pilot_data','day_overrides','editorial_notes','layout_variant','template_id','confidentiality'):
        assert getattr(duplicate,field)==getattr(ready,field),field
    restarted=store.factory()
    assert restarted.get('drafts',duplicate.document_id)==duplicate
    assert restarted.get_revision(ready.document_id,1)==original
    assert restarted.get_revision(ready.document_id,2)==edited
    assert [r.revision for r in restarted.list_revisions(ready.document_id)]==[3,2,1]
    # A later source edit does not synchronize either document snapshot.
    source=repo.get('trips','demo-canada');source.title='Zmiana źródła';repo.save('trips',source)
    assert restarted.get('drafts',ready.document_id)==ready
    changed=DocumentService(restarted).update_draft(duplicate.document_id,DraftUpdate(revision=1,title='Tylko kopia'))
    assert changed.sections==duplicate.sections and changed.editorial_notes==duplicate.editorial_notes
    assert repo.get('drafts',ready.document_id)==ready


def test_archive_restore_status_idempotence_and_conflicts(store):
    doc=create(store.repo);library=DocumentLibrary(store.repo)
    archive=mutation(1)
    archived=library.transition(doc.document_id,archive,'archive')
    assert archived.document_status=='archived' and archived.archived_at and archived.revision==2
    assert library.transition(doc.document_id,archive,'archive')==archived
    assert library.list().total==0 and library.list(archived='only').total==1
    with pytest.raises(ConflictError):library.transition(doc.document_id,mutation(1),'restore')
    with pytest.raises(ConflictError):DocumentService(store.repo).update_draft(doc.document_id,DraftUpdate(revision=2,title='Forbidden'))
    restore=mutation(2)
    restored=library.transition(doc.document_id,restore,'restore')
    assert restored.document_status=='draft' and restored.archived_at is None and restored.revision==3
    assert library.transition(doc.document_id,restore,'restore')==restored
    assert store.repo.get_revision(doc.document_id,2)==archived
    assert store.repo.get_revision(doc.document_id,1)==doc


def test_metadata_filters_sort_and_pagination_without_document_bodies(store,monkeypatch):
    docs=[create(store.repo,t,v) for t,v in CASES]
    library=DocumentLibrary(store.repo)
    # All freshly saved documents have lightweight metadata; do not read JSON bodies.
    def forbidden(*args,**kwargs):raise AssertionError('Listing downloaded a full document')
    if store.kind=='gcs':monkeypatch.setattr(store.repo,'get',forbidden)
    else:
        original=__import__('pathlib').Path.read_bytes
        def read(path):
            if path.parent==store.repo.root/'drafts':forbidden()
            return original(path)
        monkeypatch.setattr(__import__('pathlib').Path,'read_bytes',read)
    page=library.list(limit=3)
    assert page.total==9 and len(page.items)==3 and page.has_more
    assert not {'sections','trip_snapshot','campaign_snapshot','pilot_data','offer_data'} & page.items[0].model_dump().keys()
    assert library.list(family='pilot').total==3
    assert library.list(template_id='marketing.collection').total==2
    assert library.list(search='KANADA').total==7
    titles=[r.title for r in library.list(sort='title',direction='asc').items]
    assert titles==sorted(titles,key=str.casefold)
    assert library.list(offset=8,limit=3).has_more is False


def test_legacy_metadata_fallback_does_not_invent_authors(store):
    doc=create(store.repo)
    raw=doc.model_dump(mode='json')
    for key in ('document_status','archived_at','created_by','updated_by','last_library_operation','duplicated_from_document_id'):raw.pop(key)
    import json
    if store.kind=='gcs':
        name=f'documents/drafts/{doc.document_id}.json'
        store.bucket.objects[name]=(json.dumps(raw).encode(),22);store.bucket.metadata.pop(name,None)
    else:(store.repo.root/'drafts'/f'{doc.document_id}.json').write_text(json.dumps(raw),encoding='utf-8')
    row=store.repo.list_documents()[0]
    assert row.created_by is None and row.updated_by is None and row.document_status=='draft'
    assert row.source_id=='demo-canada' and row.source_type=='trip'
    updated=DocumentService(store.repo).update_draft(doc.document_id,DraftUpdate(revision=1,title='Legacy edit'))
    assert store.repo.get_revision(doc.document_id,1).created_by is None and updated.revision==2


@pytest.mark.parametrize('stage',['history','head','ambiguous'])
def test_gcs_failures_preserve_last_good_revision_and_safe_retry(stage,monkeypatch):
    bucket=FakeBucket();repo=GCSRepository(bucket);doc=create(repo)
    value=doc.model_copy(deep=True);value.title='Next version'
    original=bucket.blob
    def blob(name):
        b=original(name);upload=b.upload_from_string
        def write(*args,**kwargs):
            if stage=='history' and name.startswith('documents/revisions/'):raise ServiceUnavailable('failure')
            if stage in {'head','ambiguous'} and name==f'documents/drafts/{doc.document_id}.json':
                if stage=='ambiguous':upload(*args,**kwargs)
                raise ServiceUnavailable('failure')
            return upload(*args,**kwargs)
        b.upload_from_string=write;return b
    monkeypatch.setattr(bucket,'blob',blob)
    with pytest.raises(StorageError):repo.save('drafts',value)
    monkeypatch.setattr(bucket,'blob',original)
    assert repo.get_revision(doc.document_id,1)==doc
    if stage=='ambiguous':
        assert repo.get('drafts',doc.document_id).revision==2
        with pytest.raises(ConflictError):repo.save('drafts',value)
    else:
        assert repo.get('drafts',doc.document_id)==doc
        saved=repo.save('drafts',value);assert saved.revision==2
    assert repo.get_revision(doc.document_id,1)==doc


def test_gcs_concurrent_cas_never_archives_losing_candidate(monkeypatch):
    bucket=FakeBucket();repo=GCSRepository(bucket);doc=create(repo)
    candidate=doc.model_copy(deep=True);candidate.title='Losing candidate'
    original=bucket.blob;armed=True
    def blob(name):
        b=original(name);upload=b.upload_from_string
        def write(*args,**kwargs):
            nonlocal armed
            if armed and name==f'documents/drafts/{doc.document_id}.json':
                armed=False
                winner=doc.model_copy(deep=True);winner.title='Winner'
                GCSRepository(bucket).save('drafts',winner)
            return upload(*args,**kwargs)
        b.upload_from_string=write;return b
    monkeypatch.setattr(bucket,'blob',blob)
    with pytest.raises(ConflictError):repo.save('drafts',candidate)
    assert repo.get('drafts',doc.document_id).title=='Winner'
    assert repo.get_revision(doc.document_id,1)==doc
    assert [r.revision for r in repo.list_revisions(doc.document_id)]==[2,1]


def test_local_failed_replace_retry_and_immutable_history(tmp_path,monkeypatch):
    import os
    repo=JsonRepository(tmp_path/'documents');doc=create(repo)
    value=doc.model_copy(deep=True);value.title='Next'
    original=os.replace
    def fail(source,target):
        if str(target).endswith(f'drafts{os.sep}{doc.document_id}.json') and 'metadata' not in str(target):raise OSError('failure')
        return original(source,target)
    monkeypatch.setattr(os,'replace',fail)
    with pytest.raises(StorageError):repo.save('drafts',value)
    assert repo.get('drafts',doc.document_id)==doc
    assert repo.get_revision(doc.document_id,1)==doc
    history=repo._revision_path(doc.document_id,1);raw=history.read_bytes()
    monkeypatch.setattr(os,'replace',original)
    assert repo.save('drafts',value).revision==2 and history.read_bytes()==raw
    history.write_text('{}')
    next_value=repo.get('drafts',doc.document_id);next_value.title='Third'
    repo.save('drafts',next_value)
    with pytest.raises(StorageError):repo.get_revision(doc.document_id,1)


def test_api_security_status_does_not_bypass_price_and_identity_guards(cloud_demo):
    with cloud_demo.client() as client:
        created=client.post('/api/document-studio/drafts',json={'template_id':'offer.private','source_type':'trip','source_id':'demo-canada'}).json()
        assert created['created_by']=='editor'
        identifier=created['document_id'];prefix='/api/document-studio/library/'+identifier
        body={'revision':1,'operation_id':str(uuid4()),'document_status':'ready'}
        ready=client.post(prefix+'/status',json=body)
        assert ready.status_code==200 and ready.json()['document_status']=='ready'
        assert 'data-valid="false"' in client.get('/api/document-studio/drafts/'+identifier+'/preview').text
        for field in ('document_id','template_id','confidentiality','created_by','source_id'):
            payload={'revision':2,'operation_id':str(uuid4()),field:'forbidden'}
            assert client.post(prefix+'/duplicate',json=payload).status_code==422
    with cloud_demo.client('reader') as client:
        for path in ('/api/document-studio/library',prefix+'/revisions',prefix+'/revisions/1',prefix+'/revisions/1/preview'):
            assert client.get(path).status_code==200
        assert client.post(prefix+'/archive',json={'revision':2,'operation_id':str(uuid4())}).status_code==403
    with cloud_demo.client(None) as client:
        assert client.get(prefix+'/revisions/1').status_code==401
        assert client.get(prefix+'/revisions/1/preview').status_code==401
        assert client.get('/api/document-studio/library').status_code==401


def test_local_library_rejects_remote_and_proxy_access(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(tmp_path/'db.sqlite3',document_data_path=tmp_path/'documents'),base_url='http://localhost',client=('203.0.113.7',1234)) as client:
        assert client.get('/api/document-studio/library').status_code==403
    with client_for(tmp_path) as client:
        assert client.get('/api/document-studio/library',headers={'X-Forwarded-For':'127.0.0.1'}).status_code==403
        assert client.get('/api/document-studio/library').headers['cache-control']=='private, no-store'
        for query in ('limit=101','offset=-1','sort=unknown','template_id=unknown'):
            assert client.get('/api/document-studio/library?'+query).status_code==422


def test_readonly_preview_does_not_register_library(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv('CLOUD_FEATURE_MODE','readonly_demo');monkeypatch.setenv('APP_ENV','dev');monkeypatch.delenv('K_SERVICE',raising=False)
    with TestClient(create_app()) as client:
        for path in ('/api/document-studio/library','/api/document-studio/library/id/revisions/1'):
            assert client.get(path).status_code==404
        assert client.post('/api/document-studio/library/id/archive',json={}).status_code==403


def test_local_metadata_cache_failure_is_recoverable_not_a_failed_commit(tmp_path,monkeypatch):
    repo=JsonRepository(tmp_path/'documents')
    def fail(*args):raise OSError('cache unavailable')
    monkeypatch.setattr(repo,'_metadata_path',fail)
    doc=create(repo)
    assert repo.get('drafts',doc.document_id)==doc
    assert repo.list_documents()[0].document_id==doc.document_id
    value=doc.model_copy(deep=True);value.title='Committed without cache'
    assert repo.save('drafts',value).revision==2
    assert repo.get_revision(doc.document_id,1)==doc


def test_history_metadata_does_not_download_full_snapshots(store,monkeypatch):
    doc=create(store.repo)
    value=doc.model_copy(deep=True);value.title='Second';store.repo.save('drafts',value)
    if store.kind=='gcs':
        def fail(*args,**kwargs):raise AssertionError('Downloaded history JSON for metadata listing')
        monkeypatch.setattr(store.repo,'get',fail)
        monkeypatch.setattr(store.repo,'_historical',fail)
    assert [r.revision for r in store.repo.list_revisions(doc.document_id)]==[2,1]


# Explicit historical regression sources; active catalogue is tested in test_gt_templates.py.
import pytest as _pytest
pytestmark = _pytest.mark.usefixtures("legacy_document_sources")
