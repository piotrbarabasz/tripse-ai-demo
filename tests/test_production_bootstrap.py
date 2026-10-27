"""PROD bootstrap contracts: offline only, no IAM/GitHub/resource mutations."""
from pathlib import Path
import json

import pytest

from scripts.gcp import ci, deployment as d, production_readiness
from scripts.gcp.bootstrap import full_validate
from scripts.gcp.ci_config import identities
from scripts.gcp.deployment_contract import Config
from tests.test_github_cicd import values, proof, workflow, SHA


def test_production_wif_pins_immutable_subject_master_environment_and_workflow():
    text = Path('infra/gcp/github-actions/main.tf').read_text(encoding='utf-8')
    prod = text.split(']) : join(" && ", [',1)[1].split('])',1)[0]
    assert 'local.base_condition' in prod
    assert "repo:piotrbarabasz@${local.owner_id}/tripse-ai-demo@${local.repo_id}:environment:production" in prod
    assert "assertion.ref == 'refs/heads/master'" in prod
    assert "assertion.environment == '${local.gh_env[each.key]}'" in prod
    assert "assertion.workflow_ref == '${local.repository}/.github/workflows/delivery.yml@' + assertion.ref" in prod
    assert "startsWith" not in prod
    base = text.split('base_condition = ',1)[1].split('\n',1)[0]
    assert 'repository_id' in base and 'repository_owner_id' in base and "['push', 'workflow_dispatch']" in base


def test_reviewed_production_profile_has_real_values_and_no_dev_service_accounts():
    data=Path('infra/gcp/github-actions/production.cloud_demo.json').read_text(encoding='utf-8')
    profile=json.loads(data)
    config=full_validate('prod',identities('prod')|{'DEPLOY_CONFIG_JSON':data,'EXPECTED_CLOUD_FEATURE_MODE':'cloud_demo'})
    assert config['GCP_PUBLIC_ACCESS']=='false' and config['PLANNING_MODE']=='mock'
    assert 'REPLACE' not in data and 'tripse-ai-dev' not in data
    assert profile['DEMO_READERS']=='tripse-ai-prod-ci-probe@tripse-ai.iam.gserviceaccount.com'
    assert profile['IAP_OAUTH_CLIENT_ID'].endswith('.apps.googleusercontent.com')
    assert 'OPENAI_API_KEY' not in data and 'private_key' not in data


def test_prod_data_root_is_separate_and_does_not_manage_dev_shared_apis():
    root = Path('infra/gcp/cloud-demo-prod/main.tf').read_text(encoding='utf-8')
    assert 'environment         = "prod"' in root and 'manage_project_apis = false' in root
    assert 'live_secret_ids     = []' in root
    assert 'terraform.tfstate' not in root
    module = Path('infra/gcp/cloud-demo/main.tf').read_text(encoding='utf-8')
    assert 'var.manage_project_apis ?' in module and 'default     = true' in module
    assert 'force_destroy               = false' in module and 'prevent_destroy = true' in module


def test_builder_new_roles_are_scoped_and_never_delete_images_or_read_prod_data():
    text = Path('infra/gcp/github-actions/builder-isolation.tf').read_text(encoding='utf-8')
    assert 'default     = false' in text and 'var.retain_legacy_builder_grant ? 1 : 0' in text
    assert 'roles/storage.admin' not in text and 'roles/editor' not in text and 'roles/owner' not in text
    assert 'roles/storage.objectViewer' in text and 'roles/storage.objectUser' in text
    assert 'tripse-ai-prod-documents' not in text and 'roles/datastore.user' not in text
    assert 'artifactregistry.repositories.uploadArtifacts' in text
    assert '.delete' not in text
    assert 'role       = google_project_iam_custom_role.builder_registry.name' in text


@pytest.mark.parametrize('role',['roles/cloudbuild.builds.builder','roles/storage.objectAdmin','roles/storage.objectViewer','roles/editor','roles/datastore.user'])
def test_prod_preflight_rejects_shared_builder_project_data_authority(role):
    policy={'bindings':[{'role':role,'members':['serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com']}]}
    with pytest.raises(ValueError,match='PROD isolation blocked'):
        ci.check_production_builder_isolation(policy)
    ci.check_production_builder_isolation({'bindings':[{'role':'projects/tripse-ai/roles/tripseBuildMetadata', 'members':policy['bindings'][0]['members']}]})


@pytest.mark.parametrize('name',['tripse-ai-dev','tripse-ai-dev-ci-deploy','tripse-ai-dev-ci-probe','tripse-ai-dev-tasks'])
def test_prod_preflight_rejects_dev_project_data_grants(name):
    with pytest.raises(ValueError,match='PROD isolation blocked'):
        ci.check_production_builder_isolation({'bindings':[{'role':'roles/storage.objectViewer','members':['serviceAccount:'+name+'@tripse-ai.iam.gserviceaccount.com']}]})
    ci.check_production_builder_isolation({'bindings':[{'role':'roles/datastore.user','members':['serviceAccount:tripse-ai-dev@tripse-ai.iam.gserviceaccount.com'],
        'condition':{'expression':"resource.name == 'projects/tripse-ai/databases/tripse-ai-dev'"}}]})


def test_accepted_dev_branch_evidence_cannot_authorize_prod_even_when_digest_matches():
    record, run, artifact, jobs = proof()
    run['head_branch']='dev';record['source_ref']='refs/heads/dev'
    with pytest.raises(ValueError,match='production release'):
        ci.validate_proof(record,run,artifact,jobs,'dev',SHA,'cloud_demo',production=True)
    run['head_branch']='master';record['source_ref']='refs/heads/master'
    ci.validate_proof(record,run,artifact,jobs,'dev',SHA,'cloud_demo',production=True)
    prod=workflow('delivery.yml')['jobs']['prod']
    assert "needs.dev.result == 'success'" in prod['if'] and "refs/heads/master" in prod['if']
    assert prod['env']['CI_EVIDENCE_ARTIFACT_ID']=='${{ needs.dev.outputs.artifact_id || inputs.evidence_artifact_id }}'
    assert not any('gcp-build' in s.get('run','') for s in prod['steps'])


def github_metadata():
    return {
      'environment':{'can_admins_bypass':False,'protection_rules':[{'type':'required_reviewers','prevent_self_review':False,'reviewers':[{'type':'User','reviewer':{'id':72949549}}]}],
                     'deployment_branch_policy':{'custom_branch_policies':True,'protected_branches':False}},
      'policies':{'branch_policies':[{'name':'master','type':'branch'}]},
      'master':{'required_status_checks':{'strict':True,'contexts':[],'checks':[{'context':'Tests and offline contracts','app_id':15368}]},'enforce_admins':{'enabled':True},
                'required_pull_request_reviews':{'required_approving_review_count':0},'allow_force_pushes':{'enabled':False},'allow_deletions':{'enabled':False}}}


@pytest.mark.parametrize('fault',[None,'missing_environment','missing_review','self_review_block','wrong_reviewer','wildcard_branch','unprotected_master','missing_ci','admin_bypass','environment_bypass','unknown_environment_bypass'])
def test_operator_readiness_does_not_assume_github_protections(monkeypatch,fault):
    data=github_metadata()
    if fault=='missing_review':data['environment']['protection_rules']=[]
    if fault=='self_review_block':data['environment']['protection_rules'][0]['prevent_self_review']=True
    if fault=='wrong_reviewer':data['environment']['protection_rules'][0]['reviewers'][0]['reviewer']['id']=1
    if fault=='wildcard_branch':data['policies']['branch_policies'][0]['name']='*'
    if fault=='missing_ci':data['master']['required_status_checks']['checks']=[]
    if fault=='admin_bypass':data['master']['enforce_admins']['enabled']=False
    if fault=='environment_bypass':data['environment']['can_admins_bypass']=True
    if fault=='unknown_environment_bypass':data['environment'].pop('can_admins_bypass')
    def command(args):
        assert args[:2]==['gh','api'] and len(args)==3
        if args[-1].endswith('/protection'):
            if fault=='unprotected_master':raise ValueError('not protected')
            return data['master']
        if 'deployment-branch-policies' in args[-1]:return data['policies']
        if fault=='missing_environment':raise ValueError('missing')
        return data['environment']
    monkeypatch.setattr(production_readiness,'command',command)
    assert bool(production_readiness.check()) == (fault is not None)


@pytest.mark.parametrize('scoped_role',[False,True])
def test_legacy_setup_never_reintroduces_broad_builder_role(monkeypatch,scoped_role):
    config=Config(values());calls=[]
    def g(*args,**kwargs):
        calls.append(args)
        if args[:2]==('services','list'):return ' '.join(d.APIS)
        if args[:3]==('iam','service-accounts','list'):
            return [{'email':f'tripse-ai-{n}@tripse-ai.iam.gserviceaccount.com','displayName':'TRIPSE managed '+label} for n,label in [('build','build'),('dev','dev'),('prod','prod')]]
        if args[:2]==('projects','get-iam-policy'):
            return {'bindings':[{'role':'projects/tripse-ai/roles/tripseBuildMetadata','members':['serviceAccount:'+config.build_account]}] if scoped_role else []}
        pytest.fail('Unexpected mutation or command')
    g.config=config
    monkeypatch.setattr(d,'check_region',lambda *_:None);monkeypatch.setattr(d,'repository',lambda *_:True)
    monkeypatch.setattr(d,'service',lambda *_:None);monkeypatch.setattr(d,'load_pair',lambda *_:config);monkeypatch.setattr(d,'Gcloud',lambda *_:g)
    if scoped_role:d.setup(g)
    else:
        with pytest.raises(ValueError,match='never grants project-wide'):
            d.setup(g)
    assert not any('add-iam-policy-binding' in args for args in calls)


@pytest.mark.parametrize('change',[{'projectNumber':'123456789'}, {'location':'US'}, {'name':'foreign-logs'}])
def test_log_destination_fails_closed_on_wrong_metadata(change):
    def g(*args,**kwargs):
        if args[:2]==('projects','describe'):return {'projectNumber':'690165197462'}
        assert args[:3]==('storage','buckets','describe') and '--raw' in args
        return {'name':'690165197462-europe-central2-cloudbuild-logs','projectNumber':'690165197462','location':'EUROPE-CENTRAL2'} | change
    g.config=Config(values())
    with pytest.raises(ValueError,match='no build submitted'):
        d.build_log_destination(g)
