"""CI-004 uses synthetic metadata only, never a live GCP resource."""
import json
import subprocess
import sys

import pytest

from scripts.gcp import registry_audit as a


def image(letter='a', package='tripse-ai', tags=None):
    return {'uri': a.PREFIX + package + '@sha256:' + letter*64,
            'tags': [] if tags is None else tags, 'imageSizeBytes': '100',
            'uploadTime': '2026-01-01T00:00:00Z', 'updateTime': '2026-01-01T00:00:00Z'}


def snapshot(images=None):
    return {'synthetic': True, 'observed_at': '2026-10-29T00:00:00Z',
            'repository': {'name': a.REPOSITORY, 'format': 'DOCKER',
                           'dockerConfig': {'immutableTags': True}, 'sizeBytes': '100'},
            'coverage': dict.fromkeys(a.COVERAGE, True),
            'image_pages': [{'request_page_token': '', 'response': {'dockerImages': images or []}}],
            'references': [], 'reviews': {}}


def test_empty_repository_has_no_candidates_and_no_fabricated_rows():
    result = a.analyze(snapshot())
    assert result['complete'] and result['counts']['images'] == 0
    assert result['images'] == []
    assert result['size_distribution_bytes']['median'] is None


def test_multiple_tags_merge_same_uri_but_shared_digest_across_packages_stays_separate():
    result = a.analyze(snapshot([image(tags=['a'*40]), image(tags=['b'*40]), image(package='other')]))
    assert result['counts'] == {'images': 2, 'packages': 2, 'distinct_digest_values': 1, 'tags': 2}
    assert result['summed_image_bytes_not_billable_storage'] == 200
    assert result['repository']['storage_bytes_observed'] == 100
    assert all(not row['safe_to_delete'] for row in result['images'])


@pytest.mark.parametrize('kind', ['deployed_dev', 'deployed_prod', 'rollback'])
@pytest.mark.parametrize('status', ['valid', 'expired', 'missing', 'unknown'])
def test_active_and_rollback_references_always_protected(kind, status):
    s = snapshot([image()])
    s['references'] = [{'kind': kind, 'image': image()['uri'], 'evidence_status': status}]
    row = a.analyze(s)['images'][0]
    assert row['classification'] == 'protected'
    assert not row['safe_to_delete']
    if status != 'valid':
        assert row['rollback_evidence_status'] == 'not_verified'


@pytest.mark.parametrize('status', ['valid', 'expired', 'missing'])
def test_historical_evidence_is_retained_even_when_rollback_cannot_be_verified(status):
    s = snapshot([image()])
    s['references'] = [{'kind': 'accepted_evidence', 'image': image()['uri'], 'evidence_status': status}]
    assert a.analyze(s)['images'][0]['classification'] == 'historically_retained'


def reviewed_snapshot():
    s = snapshot([image()])
    s['reviews'][image()['uri']] = {'provenance_reviewed': True, 'references_reviewed': True}
    return s


def test_candidate_is_only_review_proposal_never_safe_delete_or_release_proof():
    row = a.analyze(reviewed_snapshot())['images'][0]
    assert row['classification'] == 'potential_cleanup_candidate'
    assert row['requires_operator_review'] and not row['safe_to_delete']
    assert row['rollback_evidence_status'] == 'not_verified'
    unknown = a.analyze(snapshot([image()]))['images'][0]
    assert unknown['classification'] == 'unclassified'


@pytest.mark.parametrize('gap', list(a.COVERAGE))
def test_missing_coverage_blocks_all_candidates(gap):
    s = reviewed_snapshot()
    s['coverage'].pop(gap)
    result = a.analyze(s)
    assert not result['complete']
    assert result['images'][0]['classification'] == 'unclassified'


def test_immutable_tags_block_candidate_even_with_reviewed_provenance():
    s = reviewed_snapshot()
    s['image_pages'][0]['response']['dockerImages'][0]['tags'] = ['a'*40]
    row = a.analyze(s)['images'][0]
    assert row['classification'] == 'unclassified'
    assert any('Immutable' in reason for reason in row['reasons'])


def test_complete_pagination_and_truncated_failed_repeated_wrong_chains():
    pages = [{'request_page_token': '', 'response': {'dockerImages': [image()], 'nextPageToken': 'next'}},
             {'request_page_token': 'next', 'response': {'dockerImages': [image('b')]}}]
    s = snapshot();s['image_pages'] = pages
    assert a.analyze(s)['counts']['images'] == 2
    for bad in [pages[:1], [pages[0], {'request_page_token': 'next', 'error': 'Bearer SECRET'}],
                [pages[0], pages[0]], [pages[1]], pages + [pages[1]]]:
        s['image_pages'] = bad
        result = a.analyze(s)
        assert not result['complete']
        assert not any(row['classification'] == 'potential_cleanup_candidate' for row in result['images'])
        assert 'SECRET' not in json.dumps(result)


@pytest.mark.parametrize('field,value', [('uri', 'other-project/image@sha256:'+'a'*64),
    ('tags', 'not-a-list'), ('tags', ['bad tag']), ('imageSizeBytes', '-1'),
    ('imageSizeBytes', True), ('uploadTime', 'not-time'),
    ('updateTime', '2099-01-01T00:00:00Z')])
def test_incorrect_image_metadata_fails_closed(field, value):
    bad = image('b');bad[field] = value
    s = reviewed_snapshot();s['image_pages'][0]['response']['dockerImages'].append(bad)
    result = a.analyze(s)
    assert not result['complete']
    assert result['images'][0]['classification'] == 'unclassified'


def test_missing_reference_partial_failure_and_bad_storage_prevent_candidates():
    for mutate in [lambda s:s.update(errors=['API failed token=SECRET']),
                   lambda s:s['repository'].update(sizeBytes='bad'),
                   lambda s:s['references'].append({'kind':'rollback','image':image('c')['uri'],'evidence_status':'missing'})]:
        s = reviewed_snapshot();mutate(s)
        result = a.analyze(s)
        assert not result['complete'] and 'SECRET' not in json.dumps(result)
        assert result['images'][0]['classification'] == 'unclassified'


def test_wrong_repository_and_conflicting_duplicate_metadata_fail_closed():
    s = reviewed_snapshot();s['repository']['name'] = 'projects/other'
    assert not a.analyze(s)['complete']
    s = reviewed_snapshot();bad=image();bad['imageSizeBytes']='200'
    s['image_pages'][0]['response']['dockerImages'].append(bad)
    assert not a.analyze(s)['complete']


def test_tag_collision_or_foreign_resource_name_blocks_other_candidates():
    for invalid in [dict(image('b', tags=['same'])), dict(image('b'), name='projects/foreign/dockerImages/x')]:
        s = reviewed_snapshot()
        s['image_pages'][0]['response']['dockerImages'] += [image('c', tags=['same']), invalid]
        result = a.analyze(s)
        assert not result['complete']
        assert not any(r['classification'] == 'potential_cleanup_candidate' for r in result['images'])


def test_cli_cannot_overwrite_snapshot_or_existing_output_or_apply(tmp_path):
    source=tmp_path/'input.json';source.write_text(json.dumps(snapshot()))
    output=tmp_path/'report.json'
    args=[sys.executable,'-m','scripts.gcp.registry_audit','--snapshot',str(source),'--output',str(output)]
    assert subprocess.run(args,capture_output=True).returncode == 0
    original=output.read_bytes()
    assert subprocess.run(args,capture_output=True).returncode != 0
    assert output.read_bytes() == original
    assert subprocess.run(args+['--apply'],capture_output=True).returncode != 0
