"""CI-004 offline, read-only analysis of captured registry metadata. No cloud client.

python -m scripts.gcp.registry_audit --snapshot capture.json --output report.json
Input is an operator snapshot or explicitly synthetic fixture, never release proof.
There is deliberately no delete/apply mode and no credential handling.
"""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import statistics

REPOSITORY = 'projects/tripse-ai/locations/europe-central2/repositories/tripse-ai'
PREFIX = 'europe-central2-docker.pkg.dev/tripse-ai/tripse-ai/'
IMAGE = re.compile(re.escape(PREFIX) + r'[a-z0-9][a-z0-9._/-]*@sha256:[a-f0-9]{64}')
COVERAGE = ('registry', 'services', 'revisions', 'release_evidence', 'rollback', 'build_sources')
KINDS = ('deployed_dev', 'deployed_prod', 'rollback', 'historical', 'accepted_evidence')


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Missing timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp requires timezone')
    return result


def byte_count(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)):
        raise ValueError('Invalid size')
    return int(value)


def collect_pages(pages):
    """Validate a complete recorded REST pagination chain; never trust a partial list."""
    if not isinstance(pages, list) or not pages:
        raise ValueError('Missing image pages')
    expected, seen, images = '', set(), []
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or 'error' in page:
            raise ValueError('Image page retrieval failed')
        if page.get('request_page_token') != expected or expected in seen:
            raise ValueError('Invalid pagination chain')
        seen.add(expected)
        response = page.get('response')
        if not isinstance(response, dict) or 'error' in response:
            raise ValueError('Invalid image page response')
        batch = response.get('dockerImages', [])
        if not isinstance(batch, list):
            raise ValueError('Invalid image list')
        images.extend(batch)
        expected = response.get('nextPageToken', '')
        if not isinstance(expected, str) or (not expected and index != len(pages)-1):
            raise ValueError('Unexpected pagination termination')
    if expected:
        raise ValueError('Truncated image inventory')
    return images


def analyze(snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError('Snapshot must be an object')
    now = timestamp(snapshot.get('observed_at'))
    errors, inventory = [], {}
    repository = snapshot.get('repository', {})
    if not isinstance(repository, dict):
        repository = {}
    immutable = repository.get('dockerConfig', {}).get('immutableTags') if isinstance(repository.get('dockerConfig', {}), dict) else None
    if repository.get('name') != REPOSITORY or repository.get('format') != 'DOCKER' or immutable is not True:
        errors.append('Repository identity/format/immutability differs from reviewed configuration')
    if snapshot.get('errors'):
        errors.append('Snapshot reports partial API failure; raw error text suppressed')
    coverage = snapshot.get('coverage', {})
    if not isinstance(coverage, dict) or not all(coverage.get(key) is True for key in COVERAGE):
        errors.append('Incomplete operator-attested reference coverage')
    try:
        raw_images = collect_pages(snapshot.get('image_pages'))
    except ValueError as error:
        errors.append(str(error))
        # Partial rows are intentionally not reported as a complete inventory.
        raw_images = []
    for image in raw_images:
        try:
            if not isinstance(image, dict) or not IMAGE.fullmatch(image.get('uri', '')):
                raise ValueError('Unexpected image identity')
            if 'name' in image and (not isinstance(image['name'], str) or not image['name'].startswith(REPOSITORY + '/dockerImages/')):
                raise ValueError('Unexpected image resource name')
            uri = image['uri']
            tags = image.get('tags', [])
            if not isinstance(tags, list) or any(not isinstance(t, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', t) for t in tags):
                raise ValueError('Invalid image tags')
            uploaded = timestamp(image.get('uploadTime'))
            updated = timestamp(image.get('updateTime', image.get('uploadTime')))
            if uploaded > updated or updated > now:
                raise ValueError('Invalid image chronology')
            size = byte_count(image.get('imageSizeBytes'))
            row = {'image': uri, 'digest': uri.split('@')[1], 'package': uri.split('@')[0],
                   'tags': sorted(set(tags)), 'size_bytes': size,
                   'uploaded_at': image['uploadTime'], 'updated_at': image.get('updateTime', image['uploadTime'])}
            if uri in inventory:
                previous = inventory[uri]
                if any(previous[k] != row[k] for k in ('size_bytes', 'uploaded_at', 'updated_at')):
                    raise ValueError('Conflicting duplicate image metadata')
                previous['tags'] = sorted(set(previous['tags']) | set(tags))
            else:
                inventory[uri] = row
        except (ValueError, TypeError, AttributeError):
            errors.append('Invalid image metadata; inventory is incomplete')
    tag_owners = {}
    for uri, row in inventory.items():
        for tag in row['tags']:
            key = (row['package'], tag)
            if key in tag_owners and tag_owners[key] != uri:
                errors.append('One package tag refers to conflicting digests')
            tag_owners[key] = uri
    references = snapshot.get('references', [])
    by_image, missing = {}, []
    if not isinstance(references, list):
        errors.append('Invalid reference list')
        references = []
    for reference in references:
        if (not isinstance(reference, dict) or reference.get('kind') not in KINDS
            or not isinstance(reference.get('image'), str) or not IMAGE.fullmatch(reference['image'])
            or reference.get('evidence_status') not in ('valid', 'expired', 'missing', 'unknown')):
            errors.append('Invalid reference metadata')
            continue
        safe = {k: reference[k] for k in ('kind', 'image', 'evidence_status')}
        by_image.setdefault(safe['image'], []).append(safe)
        if safe['image'] not in inventory:
            missing.append(safe)
    if missing:
        errors.append('Referenced images missing from captured inventory')
    reviews = snapshot.get('reviews', {})
    if not isinstance(reviews, dict):
        reviews = {}
        errors.append('Invalid review annotations')
    for uri, row in sorted(inventory.items()):
        refs = by_image.get(uri, [])
        row.update(classification='unclassified', safe_to_delete=False,
                   requires_operator_review=True, references=refs,
                   rollback_evidence_status='not_verified', reasons=[])
        if any(ref['kind'] in ('deployed_dev', 'deployed_prod', 'rollback') for ref in refs):
            row['classification'] = 'protected'
            row['reasons'].append('Active or rollback reference: retain even if evidence is missing/expired')
        elif refs:
            row['classification'] = 'historically_retained'
            row['reasons'].append('Historical/accepted evidence reference: retain')
        if refs and all(ref['evidence_status'] == 'valid' for ref in refs):
            row['rollback_evidence_status'] = 'operator_asserted_valid_not_release_verification'
        review = reviews.get(uri, {})
        if not isinstance(review, dict):
            review = {}
        if not refs:
            row['reasons'].append('No reference found in supplied snapshot does not establish deletability')
            if (not errors and not row['tags'] and review.get('provenance_reviewed') is True
                and review.get('references_reviewed') is True
                and now - timestamp(row['uploaded_at']) >= timedelta(days=90)):
                row['classification'] = 'potential_cleanup_candidate'
                row['reasons'].append('Untagged >=90d with complete attested coverage; explicit operator review still required')
        if row['tags'] and immutable is True:
            row['reasons'].append('Immutable tagged artifact: cleanup cannot delete it')
    sizes = [r['size_bytes'] for r in inventory.values()]
    try:
        storage = byte_count(repository['sizeBytes']) if 'sizeBytes' in repository else None
    except ValueError:
        storage = None
        errors.append('Invalid repository storage counter')
        # Late repository metadata failure must also revoke candidate status.
        for row in inventory.values():
            if row['classification'] == 'potential_cleanup_candidate':
                row['classification'] = 'unclassified'
    return {'schema_version': 1, 'observed_at': snapshot['observed_at'],
            'data_origin': 'synthetic' if snapshot.get('synthetic') is True else 'operator_supplied_unverified_snapshot',
            'production_acceptance': False, 'destructive_actions_supported': False,
            'complete': not errors, 'errors': sorted(set(errors)),
            'repository': {'name': REPOSITORY, 'format_observed': repository.get('format') if repository.get('format') == 'DOCKER' else 'unexpected',
                           'immutable_tags_observed': immutable if isinstance(immutable, bool) else None,
                           'cleanup_policy_configuration': 'Review original captured repository metadata; not simulated by this tool',
                           'storage_bytes_observed': storage},
            'counts': {'images': len(inventory), 'packages': len({r['package'] for r in inventory.values()}),
                       'distinct_digest_values': len({r['digest'] for r in inventory.values()}),
                       'tags': sum(len(r['tags']) for r in inventory.values())},
            'size_distribution_bytes': {'min': min(sizes) if sizes else None,
                                        'median': statistics.median(sizes) if sizes else None,
                                        'max': max(sizes) if sizes else None},
            'summed_image_bytes_not_billable_storage': sum(sizes),
            'unresolved_references': missing, 'images': [inventory[k] for k in sorted(inventory)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.snapshot.resolve():
        parser.error('Output must differ from input')
    try:
        report = analyze(json.loads(args.snapshot.read_text(encoding='utf-8-sig')))
    except (ValueError, TypeError, OSError):
        parser.exit(2, 'Invalid or unreadable snapshot; no deletion recommendation produced\n')
    # Never overwrite a previous audit or application data.
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
