"""CI-005: synthetic provenance/evidence/recovery only; no network or credentials."""
import copy
import io
import json
import tarfile
from types import SimpleNamespace
import zipfile

import pytest

from scripts.gcp import build_proof as b, ci, deployment as d, smoke_auth
from scripts.gcp.deployment_contract import Config
from scripts.gcp.parity_smoke import Acceptance
from tests.test_github_cicd import SHA, IMAGE_DIGEST, ORIGIN, values, proof, receiving_revision

BUILD = '9c54ce2d-d425-44cd-9328-a765affb8bad'
OTHER = '8c54ce2d-d425-44cd-9328-a765affb8bad'


def archive(files):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as stream:
        for name, content in files.items():
            member=tarfile.TarInfo(name);member.size=len(content)
            stream.addfile(member,io.BytesIO(content))
    return data.getvalue()


@pytest.fixture
def provenance(monkeypatch):
    config=Config(values())
    tag=config.image+':'+SHA
    build={'id':BUILD,'projectId':'tripse-ai','status':'SUCCESS','images':[tag],
        'serviceAccount':'projects/tripse-ai/serviceAccounts/'+config.build_account,
        'steps':[{'name':'gcr.io/cloud-builders/docker','args':['build','--network','cloudbuild','--no-cache','-t',tag,'.']}],
        'results':{'images':[{'name':tag,'digest':IMAGE_DIGEST}]},
        'sourceProvenance':{'resolvedStorageSource':{'bucket':'tripse-ai_europe-central2_cloudbuild','object':'source/test.tgz','generation':'123'}}}
    expected={'Dockerfile':b'FROM python:3.12-slim','app/main.py':b'trusted'}
    source=expected | {'app/_build_version.txt':SHA.encode()}
    calls=[]
    def g(*args,**kwargs):
        calls.append(args)
        assert args[:2]==('builds','describe'), 'Direct lookup must not scan newer builds'
        return copy.deepcopy(build)
    g.config=config;g.executable='gcloud'
    monkeypatch.setattr(d,'source_files',lambda _:expected.items())
    monkeypatch.setattr(d,'run',lambda *args,**kwargs:archive(source))
    return g,build,source,expected,calls


def test_direct_older_build_has_no_1000_build_dependency_and_reads_pinned_generation(provenance,monkeypatch):
    g,build,source,_,calls=provenance
    reads=[]
    def read(args,**kwargs):reads.append(args);return archive(source)
    monkeypatch.setattr(d,'run',read)
    assert b.verify(g,SHA,IMAGE_DIGEST,BUILD)==BUILD
    assert len(calls)==1 and calls[0][2]==BUILD
    assert '--region=europe-central2' in calls[0]
    assert reads[0][3]=='gs://tripse-ai_europe-central2_cloudbuild/source/test.tgz#123'


@pytest.mark.parametrize('hint',['HEAD','a'*36,'../id','',123,'9C54CE2D-d425-44cd-9328-a765affb8bad'])
def test_invalid_lookup_hint_never_calls_cloud(provenance,hint):
    g,_,_,_,calls=provenance
    with pytest.raises(b.ProvenanceError):b.verify(g,SHA,IMAGE_DIGEST,hint)
    assert calls==[]


@pytest.mark.parametrize('attack',['id','project','region','sha','digest','builder','status','recipe','generation'])
def test_build_id_is_only_hint_all_proof_checks_remain(provenance,attack):
    g,build,_,_,_=provenance
    if attack=='id':build['id']=OTHER
    if attack=='project':build['projectId']='foreign'
    if attack=='region':build['name']=f'projects/tripse-ai/locations/us-central1/builds/{BUILD}'
    if attack=='sha':build['images']=[g.config.image+':'+'c'*40]
    if attack=='digest':build['results']['images'][0]['digest']='sha256:'+'c'*64
    if attack=='builder':build['serviceAccount']='untrusted'
    if attack=='status':build['status']='FAILURE'
    if attack=='recipe':build['steps'][0]['args'].remove('--no-cache')
    if attack=='generation':build['sourceProvenance']['resolvedStorageSource'].pop('generation')
    with pytest.raises(b.ProvenanceError):b.verify(g,SHA,IMAGE_DIGEST,BUILD)


@pytest.mark.parametrize('attack',['archive_bytes','committed_bytes','extra_file','corrupt_archive'])
def test_direct_lookup_still_verifies_exact_committed_source(provenance,monkeypatch,attack):
    g,_,source,expected,_=provenance
    if attack=='archive_bytes':source['app/main.py']=b'changed'
    if attack=='committed_bytes':expected['app/main.py']=b'other commit'
    if attack=='extra_file':source['private.txt']=b'do not include'
    if attack=='corrupt_archive':monkeypatch.setattr(d,'run',lambda *a,**kw:b'not gzip')
    with pytest.raises(b.ProvenanceError,match='archive'):b.verify(g,SHA,IMAGE_DIGEST,BUILD)


@pytest.mark.parametrize('missing',['build','source','discovery_page'])
def test_missing_historical_proof_or_partial_api_failure_never_falls_back(provenance,monkeypatch,missing):
    g,_,_,_,calls=provenance
    def failure(*args,**kwargs):raise d.CommandError('gcloud',1,operation='gcloud builds describe' if missing=='build' else 'gcloud storage cat')
    if missing=='source':monkeypatch.setattr(d,'run',failure)
    else:
        failure.config=g.config;failure.executable='gcloud';g=failure
    with pytest.raises(d.CommandError):b.verify(g,SHA,IMAGE_DIGEST,None if missing=='discovery_page' else BUILD)


@pytest.mark.parametrize('result',[None,{'builds':[]},[None],[{'results':None}]])
def test_malformed_or_incomplete_discovery_fails_closed(provenance,result):
    original,*_=provenance
    g=lambda *a,**k:result;g.config=original.config;g.executable='gcloud'
    with pytest.raises(b.ProvenanceError):b.verify(g,SHA,IMAGE_DIGEST)


def test_bounded_legacy_discovery_does_not_silently_accept_older_missing_record(provenance):
    original,build,*_=provenance
    newer=copy.deepcopy(build);newer['results']['images'][0]['digest']='sha256:'+'f'*64
    g=lambda *a,**k:[newer]*1000;g.config=original.config;g.executable='gcloud'
    with pytest.raises(b.ProvenanceError,match='exact_build_id_required'):b.verify(g,SHA,IMAGE_DIGEST)


def test_discovery_filters_target_digest_and_image_before_bounded_pagination(provenance):
    original,build,*_=provenance
    calls=[]
    def g(*args,**kwargs):calls.append(args);return [build]
    g.config=original.config;g.executable='gcloud'
    assert b.verify(g,SHA,IMAGE_DIGEST)==BUILD
    assert '--limit=1000' in calls[0]
    assert '--page-size=100' in calls[0] and not any(arg.startswith('--sort-by') for arg in calls[0])
    query=next(a for a in calls[0] if a.startswith('--filter='))
    assert f'results.images.name="{g.config.image}:{SHA}"' in query
    assert f'results.images.digest="{IMAGE_DIGEST}"' in query


def coordinator(tmp_path,monkeypatch,environment='prod',operation='promote'):
    config=Config(values(environment))
    old={'sha':'c'*40,'mode':'readonly_demo','image_digest':IMAGE_DIGEST,
         'service':config['GCP_SERVICE_NAME'],'environment':environment,'sequence':10,
         'url':ORIGIN,'iap_enabled':False,'traffic':[{'revisionName':config['GCP_SERVICE_NAME']+'-00001-old','percent':100}]}
    settings=dict(GITHUB_REPOSITORY=ci.REPOSITORY,GITHUB_EVENT_NAME='push' if operation=='dev' else 'workflow_dispatch',
        GITHUB_REF='refs/heads/master',GITHUB_SHA=SHA,GITHUB_RUN_ID='123',GITHUB_RUN_NUMBER='10',GITHUB_RUN_ATTEMPT='1',
        RUNNER_TEMP=str(tmp_path),GITHUB_OUTPUT=str(tmp_path/'output'),GITHUB_STEP_SUMMARY=str(tmp_path/'summary'),
        CI_OPERATION=operation,CI_TARGET_ENV=environment,CI_RELEASE_SHA=SHA,GCP_CI='1',
        DEPLOY_SERVICE_ACCOUNT=f'tripse-ai-{environment}-ci-deploy@tripse-ai.iam.gserviceaccount.com')
    for key,value in settings.items():monkeypatch.setenv(key,value)
    monkeypatch.setattr(d,'CONFIG_DIR',tmp_path)
    monkeypatch.setattr(ci,'config_from_environment',lambda *a:config)
    monkeypatch.setattr(d,'run',lambda *a,**k:'')
    monkeypatch.setattr(d,'check_release_source',lambda *a:{})
    g=lambda *a,**k:'synthetic-access-token';g.config=config
    monkeypatch.setattr(d,'Gcloud',lambda *a:g)
    monkeypatch.setattr(d,'online_preflight',lambda *a:None)
    monkeypatch.setattr(ci,'prerequisites',lambda *a:{'metadata':{}})
    monkeypatch.setattr(ci,'GitHub',lambda:SimpleNamespace(request=lambda *a:{'object':{'sha':SHA}}))
    monkeypatch.setattr(ci,'release_proof',lambda *a,**k:{'image_digest':IMAGE_DIGEST,'source_build_id':BUILD})
    monkeypatch.setattr(ci,'snapshot',lambda *a:copy.deepcopy(old))
    monkeypatch.setattr(d,'digest',lambda *a:IMAGE_DIGEST)
    calls=[]
    monkeypatch.setattr(d,'build',lambda *a:calls.append('build') or BUILD)
    monkeypatch.setattr(b,'verify',lambda *a:calls.append(('verify',a[-1])) or BUILD)
    monkeypatch.setattr(d,'deploy',lambda *a:calls.append('deploy'))
    state={'image_sha':SHA,'image_digest':IMAGE_DIGEST,'url':ORIGIN,
           'revision':config['GCP_SERVICE_NAME']+'-00002-new','environment':environment,'feature_mode':'readonly_demo'}
    monkeypatch.setattr(d,'deployed_state',lambda *a:copy.deepcopy(state))
    monkeypatch.setattr(ci,'restore',lambda *a:calls.append('restore'))
    return calls,state


@pytest.mark.parametrize('environment,operation',[('dev','dev'),('dev','rollback'),('prod','promote'),('prod','rollback')])
def test_coordinator_routes_direct_hint_and_preserves_prod_no_build_no_new_iam(tmp_path,monkeypatch,environment,operation):
    calls,_=coordinator(tmp_path,monkeypatch,environment,operation)
    ci.execute()
    assert ('build' in calls)==(operation=='dev')
    assert (('verify',BUILD) in calls)==(environment=='dev')
    assert json.loads((tmp_path/'tripse-deployment/release.json').read_text())['source_build_id']==BUILD


def test_failed_restore_keeps_original_error_and_never_writes_accepted_evidence(tmp_path,monkeypatch):
    coordinator(tmp_path,monkeypatch)
    original=ValueError('synthetic deployment failure')
    def deploy(*a):raise original
    def restore(*a):raise RuntimeError('NEVER_LOG_TOKEN')
    monkeypatch.setattr(d,'deploy',deploy);monkeypatch.setattr(ci,'restore',restore)
    with pytest.raises(ValueError) as error:ci.execute()
    assert error.value is original
    assert not (tmp_path/'tripse-deployment/release.json').exists()
    report=(tmp_path/'summary').read_text()
    assert '"accepted": false' in report and 'Restoration NOT verified' in report and 'NEVER_LOG_TOKEN' not in report


def test_output_io_failure_after_runtime_acceptance_revokes_acceptance(tmp_path,monkeypatch):
    calls,_=coordinator(tmp_path,monkeypatch)
    monkeypatch.setenv('GITHUB_OUTPUT',str(tmp_path))
    with pytest.raises(OSError):ci.execute()
    assert 'restore' in calls
    assert not (tmp_path/'tripse-deployment/release.json').exists()
    assert '"accepted": false' in (tmp_path/'summary').read_text()


def test_final_digest_change_after_smoke_is_rejected(tmp_path,monkeypatch):
    calls,state=coordinator(tmp_path,monkeypatch)
    checks=0
    def deployed(*a):
        nonlocal checks
        checks+=1
        return state | ({'image_digest':'sha256:'+'f'*64} if checks==2 else {})
    monkeypatch.setattr(d,'deployed_state',deployed)
    with pytest.raises(ValueError,match='after acceptance'):ci.execute()
    assert 'restore' in calls and not (tmp_path/'tripse-deployment/release.json').exists()


def test_existing_evidence_is_preserved_and_blocks_new_mutation(tmp_path,monkeypatch):
    calls,_=coordinator(tmp_path,monkeypatch)
    directory=tmp_path/'tripse-deployment';directory.mkdir();path=directory/'release.json';path.write_text('previous evidence')
    with pytest.raises(ValueError,match='fresh'):ci.execute()
    assert calls==[] and path.read_text()=='previous evidence'


@pytest.mark.parametrize('operation,stage',[('storage','release.source_proof'),('registry','release.digest')])
def test_source_and_registry_errors_classify_missing_without_sensitive_stderr(monkeypatch,operation,stage):
    monkeypatch.setattr(d.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=1,stdout=b'',stderr=b'NOT_FOUND NEVER_LOG_TOKEN'))
    args=['gcloud','storage','cat','private-source'] if operation=='storage' else ['gcloud','artifacts','docker','images','describe','private-image']
    with d.command_stage(stage), pytest.raises(d.CommandError) as error:d.run(args)
    assert 'NOT_FOUND' in str(error.value) and stage in str(error.value)
    assert 'NEVER_LOG_TOKEN' not in str(error.value) and 'private-source' not in str(error.value)


@pytest.mark.parametrize('field,value',[('repository','foreign'),('policy_sha','f'*40),
    ('image_digest','sha256:wrong'),('source_build_id','a'*36),('source_verified',False),
    ('project','other'),('region','us-central1'),('service','tripse-ai-prod'),
    ('revision','tripse-ai-prod-00001-x'),('traffic',[]),('run_id',999),('run_attempt',2),
    ('environment','prod'),('feature_mode','readonly_demo'),('accepted',False)])
def test_release_proof_identity_tampering_rejected(field,value):
    record,run,artifact,jobs=proof();record[field]=value
    with pytest.raises(ValueError):ci.validate_proof(record,run,artifact,jobs,'dev',SHA,'cloud_demo',production=True)


@pytest.mark.parametrize('case',['expiry','missing_expiry','missing_flag','workflow_conflict','wrong_run','failed_job','feature','wrong_workflow','pr'])
def test_release_metadata_conflicts_rejected(case):
    record,run,artifact,jobs=proof()
    if case=='expiry':artifact['expires_at']='2000-01-01T00:00:00Z'
    if case=='missing_expiry':artifact.pop('expires_at')
    if case=='missing_flag':artifact.pop('expired')
    if case=='workflow_conflict':artifact['workflow_run']['head_sha']='c'*40
    if case=='wrong_run':artifact['workflow_run']['id']=999
    if case=='failed_job':jobs[0]['conclusion']='failure'
    if case=='feature':run['head_branch']='feature';record['source_ref']='refs/heads/feature'
    if case=='wrong_workflow':run['path']='benchmark.yml'
    if case=='pr':run['event']='pull_request'
    with pytest.raises(ValueError):ci.validate_proof(record,run,artifact,jobs,'dev',SHA,'cloud_demo',production=True)


def zip_record(content, extra=False):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        z.writestr('release.json',content)
        if extra:z.writestr('other','untrusted')
    return output.getvalue()


@pytest.mark.parametrize('payload',[b'bad zip',b'x'*2000001,zip_record('x'*64001),
    zip_record('[]'),zip_record('{"accepted":true,"accepted":false}'),
    zip_record('{bad PRIVATE_BODY}'),zip_record('{"x":NaN}'),zip_record('{}',True)],
    ids=['bad-zip','oversized-zip','oversized-json','array-json','duplicate-fields','malformed-json','nan-json','extra-member'])
def test_invalid_oversized_duplicate_or_nonstandard_archive_is_safely_rejected(payload):
    with pytest.raises(ValueError) as error:ci.decode_release_archive(payload)
    assert 'PRIVATE_BODY' not in str(error.value)


def test_github_pagination_is_bounded_and_never_accepts_partial_results():
    api=object.__new__(ci.GitHub)
    api.request=lambda _: {'jobs':[{}]*100,'total_count':101}
    with pytest.raises(ValueError,match='limit'):api.pages('/actions/runs/1/jobs','jobs')
    api.request=lambda _: {'jobs':[{}],'total_count':2}
    with pytest.raises(ValueError,match='Incomplete'):api.pages('/actions/runs/1/jobs','jobs')
    api.request=lambda _: {'jobs':[],'total_count':0}
    assert api.pages('/actions/runs/1/jobs','jobs')==[]


def recovery(monkeypatch,mode='cloud_demo'):
    config=Config(values(mode='cloud_demo'));name='tripse-ai-dev-00001-old'
    old={'sha':SHA,'mode':mode,'iap_enabled':True,'url':ORIGIN,'service':'tripse-ai-dev',
         'environment':'dev','image_digest':IMAGE_DIGEST,'sequence':10,
         'traffic':[{'revisionName':name,'percent':100}]}
    revision=receiving_revision(config,SHA,mode,name)
    service={'metadata':{'labels':d.LABELS|{'environment':'dev','github-workflow':'delivery-v1','github-run-number':'10'},
                         'annotations':{'run.googleapis.com/iap-enabled':'true'}},
             'status':{'traffic':copy.deepcopy(old['traffic']),'url':ORIGIN}}
    health={'image_version':SHA,'feature_mode':mode,'environment':'dev'}
    policy={'bindings':[]};calls=[]
    def g(*args,**kwargs):
        calls.append(args)
        if args[:3]==('run','revisions','describe'):return copy.deepcopy(revision)
        if args[:3]==('run','services','describe'):return copy.deepcopy(service)
        if args[:3]==('run','services','get-iam-policy'):return copy.deepcopy(policy)
        return {}
    g.config=config
    monkeypatch.setattr(smoke_auth,'probe_token',lambda *a,**kw:'NEVER_LOG_TOKEN')
    monkeypatch.setattr(Acceptance,'call',lambda *a,**kw:copy.deepcopy(health))
    return g,old,revision,service,health,policy,calls


def test_verified_recovery_preserves_iap_digest_revision_environment_and_private_policy(monkeypatch):
    g,old,_,_,_,_,calls=recovery(monkeypatch)
    ci.restore(g,old)
    assert sum(c[:3]==('run','revisions','describe') for c in calls)==2
    assert not any('--no-iap' in c or '--no-invoker-iam-check' in c for c in calls)


@pytest.mark.parametrize('attack',['snapshot','revision_missing','revision_name','revision_digest','not_ready',
    'traffic','health','health_sha','health_mode','health_env','auth','newer_run','public_policy','iap_off','invoker_disabled','traffic_command'])
def test_failed_recovery_never_returns_success(monkeypatch,attack):
    g,old,revision,service,health,policy,calls=recovery(monkeypatch)
    if attack=='snapshot':old['traffic'][0]['percent']=50
    if attack=='revision_missing':revision.clear()
    if attack=='revision_name':revision['metadata']['name']='tripse-ai-prod-00001-x'
    if attack=='revision_digest':revision['status']['imageDigest']=g.config.image+'@sha256:'+'c'*64
    if attack=='not_ready':revision['status']['conditions']=[]
    if attack=='traffic':service['status']['traffic'][0]['revisionName']='tripse-ai-dev-00002-wrong'
    if attack=='health':monkeypatch.setattr(Acceptance,'call',lambda *a,**k:(_ for _ in ()).throw(ValueError('Synthetic health failure')))
    if attack=='health_sha':health['image_version']='c'*40
    if attack=='health_mode':health['feature_mode']='readonly_demo'
    if attack=='health_env':health['environment']='prod'
    if attack=='auth':monkeypatch.setattr(smoke_auth,'probe_token',lambda *a,**k:(_ for _ in ()).throw(ValueError('Synthetic auth failure')))
    if attack=='newer_run':service['metadata']['labels']['github-run-number']='11'
    if attack=='public_policy':policy['bindings']=[{'role':'roles/run.invoker','members':['allUsers']}]
    if attack=='iap_off':service['metadata']['annotations']['run.googleapis.com/iap-enabled']='false'
    if attack=='invoker_disabled':service['metadata']['annotations']['run.googleapis.com/invoker-iam-disabled']='true'
    if attack=='traffic_command':
        original=g
        def g(*args,**kwargs):
            if args[:3]==('run','services','update-traffic'):raise d.CommandError('gcloud',1)
            return original(*args,**kwargs)
        g.config=original.config
    with pytest.raises((ValueError,d.CommandError)):ci.restore(g,old)
    if attack in ('snapshot','revision_missing','revision_name','revision_digest','not_ready','newer_run'):
        assert not any(c[:3] in (('run','services','update'),('run','services','update-traffic')) for c in calls)


def test_bad_freshness_metadata_and_summary_io_never_leak_or_mask_original(monkeypatch,tmp_path,capsys):
    with pytest.raises(ValueError) as error:ci.fresh({'metadata':{'labels':{'github-workflow':'delivery-v1','github-run-number':'PRIVATE'}}},10)
    assert 'PRIVATE' not in str(error.value)
    monkeypatch.setenv('GITHUB_STEP_SUMMARY',str(tmp_path))
    ci.summary({'accepted':False})
    assert 'original outcome retained' in capsys.readouterr().err


def test_concurrent_newer_release_blocks_post_restore_success(monkeypatch):
    original,old,_,service,_,_,calls=recovery(monkeypatch)
    reads=0
    def g(*args,**kwargs):
        nonlocal reads
        if args[:3]==('run','services','describe'):
            reads+=1
            if reads==2:service['metadata']['labels']['github-run-number']='11'
        return original(*args,**kwargs)
    g.config=original.config
    with pytest.raises(ValueError,match='Stale'):ci.restore(g,old)
    assert any(c[:3]==('run','services','update-traffic') for c in calls)


def test_readonly_recovery_does_not_disable_current_iap(monkeypatch):
    g,old,*_=recovery(monkeypatch,mode='readonly_demo')
    old['iap_enabled']=False
    ci.restore(g,old)


@pytest.mark.parametrize('field,value',[('service','tripse-ai-prod'),('environment','prod'),
    ('url','https://private.example'),('mode','unknown'),('sha','not-a-sha'),
    ('traffic',[{'revisionName':'tripse-ai-prod-00001-x','percent':100}])])
def test_invalid_snapshot_contract_blocks_even_metadata_reads(monkeypatch,field,value):
    g,old,_,_,_,_,calls=recovery(monkeypatch)
    old[field]=value
    with pytest.raises(ValueError):ci.restore(g,old)
    assert calls==[]


def test_original_deployment_error_survives_both_recovery_and_summary_io_failure(tmp_path,monkeypatch):
    coordinator(tmp_path,monkeypatch)
    monkeypatch.setenv('GITHUB_STEP_SUMMARY',str(tmp_path))
    original=ValueError('original synthetic failure')
    def fail(*a):raise original
    monkeypatch.setattr(d,'deploy',fail)
    monkeypatch.setattr(ci,'restore',lambda *a:(_ for _ in ()).throw(RuntimeError('SECRET')))
    with pytest.raises(ValueError) as error:ci.execute()
    assert error.value is original and not (tmp_path/'tripse-deployment/release.json').exists()


@pytest.mark.parametrize('case',['wrong_run_id','wrong_artifact_id','missing_artifact'])
def test_release_proof_rejects_requested_id_conflicts_before_archive_download(monkeypatch,case):
    _,run,artifact,_=proof()
    if case=='wrong_run_id':run['id']=999
    if case=='wrong_artifact_id':artifact['id']=999
    class API:
        def request(self,path,**kwargs):
            if case=='missing_artifact' and '/artifacts/' in path:raise ValueError('missing_or_expired_artifact')
            if path=='/actions/runs/123':return run
            if path=='/actions/artifacts/456':return artifact
            pytest.fail('Archive must not be downloaded for a conflicting identity')
    monkeypatch.setattr(ci,'GitHub',API)
    monkeypatch.setenv('CI_EVIDENCE_RUN_ID','123');monkeypatch.setenv('CI_EVIDENCE_ARTIFACT_ID','456')
    with pytest.raises(ValueError):ci.release_proof('dev',SHA,'cloud_demo',production=True)


def test_artifact_redirect_never_forwards_token_or_logs_signed_url(monkeypatch):
    from urllib.error import HTTPError,URLError
    api=object.__new__(ci.GitHub);api.token='SECRET_TOKEN'
    url='https://example.invalid/blob?signature=SECRET_SIGNATURE'
    def redirect(request,**kwargs):raise HTTPError(request.full_url,302,'redirect',{'Location':url},None)
    api.opener=SimpleNamespace(open=redirect)
    def download(request,**kwargs):
        assert not request.has_header('Authorization')
        raise URLError('SECRET_SIGNATURE')
    monkeypatch.setattr(ci,'urlopen',download)
    with pytest.raises(ValueError) as error:api.request('/actions/artifacts/456/zip',archive=True)
    assert 'SECRET' not in str(error.value)
