"""DOC-FLOW-004/005: role-aware UI and bounded create retries without changing storage or saved schemas."""
from uuid import uuid4

import pytest

from app.document_studio.api import DraftRequest
from app.document_studio.service import DocumentService
from app.document_studio.repository import ConflictError, StorageError
from tests.test_document_library import store, CASES
from tests.test_source_categories import source_client, cloud_demo


@pytest.mark.parametrize('template,variant', CASES)
def test_stable_creation_id_and_selected_source_revision(store,template,variant):
    repo=store.repo;service=DocumentService(repo)
    kind='campaigns' if template=='marketing.collection' else 'trips'
    source=repo.get(kind,'demo-northern-journeys' if kind=='campaigns' else 'demo-canada')
    request=DraftRequest(document_id=uuid4().hex,source_revision=source.revision,
        template_id=template,layout_variant=variant,source_type='campaign' if kind=='campaigns' else 'trip',
        source_id=source.campaign_id if kind=='campaigns' else source.trip_id)
    created=service.create_draft(request)
    assert service.create_draft(request)==created
    assert len(repo.list_documents())==1 and [r.revision for r in repo.list_revisions(created.document_id)]==[1]
    source.title='Źródło zmienione później';changed=repo.save(kind,source)
    assert service.create_draft(request)==created  # read-back of the committed intent
    assert repo.get('drafts',created.document_id)==created
    with pytest.raises(ConflictError):service.create_draft(request.model_copy(update={'document_id':uuid4().hex}))
    newer=service.create_draft(request.model_copy(update={'document_id':uuid4().hex,'source_revision':changed.revision}))
    assert (newer.trip_snapshot or newer.campaign_snapshot).revision==2
    assert len(repo.list_documents())==2 and repo.get('drafts',created.document_id)==created


@pytest.mark.parametrize('after_commit',[False,True])
def test_creation_failure_retry_preserves_one_identity(store,monkeypatch,after_commit):
    repo=store.repo;service=DocumentService(repo)
    request=DraftRequest(document_id=uuid4().hex,source_revision=1,template_id='offer.private',source_type='trip',source_id='demo-canada')
    save=repo.save
    def fail(*args,**kwargs):
        if after_commit:save(*args,**kwargs)
        raise StorageError('isolated fault')
    monkeypatch.setattr(repo,'save',fail)
    with pytest.raises(StorageError):service.create_draft(request)
    monkeypatch.setattr(repo,'save',save)
    result=service.create_draft(request)
    assert result.document_id==request.document_id and result.revision==1
    assert len(repo.list_documents())==1



def test_same_id_with_different_creation_intent_conflicts(store):
    service=DocumentService(store.repo)
    request=DraftRequest(document_id=uuid4().hex,source_revision=1,template_id='offer.private',source_type='trip',source_id='demo-canada')
    original=service.create_draft(request)
    for change in ({'template_id':'pilot.basic'},{'source_id':'demo-iceland'},{'editorial_notes':'changed intent'},{'title':'different'}):
        with pytest.raises(ConflictError):service.create_draft(request.model_copy(update=change))
    assert store.repo.get('drafts',original.document_id)==original and len(store.repo.list_documents())==1


def test_create_race_returns_same_committed_result(store,monkeypatch):
    service=DocumentService(store.repo)
    request=DraftRequest(document_id=uuid4().hex,source_revision=1,template_id='offer.private',source_type='trip',source_id='demo-canada')
    save=store.repo.save;armed=True
    def race(*args,**kwargs):
        nonlocal armed
        if armed:
            armed=False;service.create_draft(request)
        return save(*args,**kwargs)
    monkeypatch.setattr(store.repo,'save',race)
    result=service.create_draft(request)
    assert result.revision==1 and len(store.repo.list_documents())==1


def test_api_guards_optional_fields_without_weakening_old_clients(source_client):
    with source_client as client:
        assert client.get('/api/document-studio/access').json()=={'can_edit':True}
        payload={'document_id':uuid4().hex,'source_revision':1,'template_id':'offer.private','source_type':'trip','source_id':'demo-canada'}
        first=client.post('/api/document-studio/drafts',json=payload)
        assert first.status_code==201
        assert client.post('/api/document-studio/drafts',json=payload).json()==first.json()
        for invalid in ({'document_id':'../escape'},{'source_revision':0},{'source_revision':-1},{'created_by':'fake'},{'confidentiality':'public'}):
            assert client.post('/api/document-studio/drafts',json=payload|invalid).status_code==422
        # Existing clients can still omit both additive guards.
        assert client.post('/api/document-studio/drafts',json={k:v for k,v in payload.items() if k not in {'document_id','source_revision'}}).status_code==201


@pytest.mark.parametrize("identity,expected", [("editor",True),("reader",False),(None,None)])
def test_creation_ui_capability_uses_authenticated_role(cloud_demo,identity,expected):
    with cloud_demo.client(identity) as client:
        result=client.get('/api/document-studio/access')
        if expected is None:
            assert result.status_code==401
        else:
            assert result.status_code==200 and result.json()=={'can_edit':expected}
            # The display hint does not grant write permission.
            result=client.post('/api/document-studio/trips',json={'title':'Role QA'})
            assert result.status_code==(201 if expected else 403)


# Explicit historical regression sources; active catalogue is tested in test_gt_templates.py.
import pytest as _pytest
pytestmark = _pytest.mark.usefixtures("legacy_document_sources")
