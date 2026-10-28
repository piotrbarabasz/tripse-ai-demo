"""Read-only candidate report for legacy parity records; never writes the repository.

Operator must review exact IDs and current revisions before separately authorizing
any source update. Names alone are not used for filtering or classification.
"""
import argparse
import json
from pathlib import Path

from app.document_studio.repository import JsonRepository


def candidates(repository):
    trips = repository.list('trips')
    trip_ids = {t.trip_id for t in trips if t.data_origin == 'unknown'
        and t.title.startswith('CLOUD-PARITY synthetic DEV ')
        and t.duration_days == 15 and len(t.days) == 15
        and all(d.title == f'Synthetic day {i}' and d.internal_notes == 'PARITY_PRIVATE_OPS'
                for i, d in enumerate(t.days, 1))}
    campaigns = repository.list('campaigns')
    campaign_ids = {c.campaign_id for c in campaigns if c.data_origin == 'unknown'
        and c.title.startswith('CLOUD-PARITY synthetic DEV ')
        and all(i.trip_id in trip_ids for i in c.items)}
    rows = []
    for kind, objects, identifiers in (('trips', trips, trip_ids), ('campaigns', campaigns, campaign_ids)):
        rows.extend({'kind':kind, 'id':getattr(value, 'trip_id' if kind=='trips' else 'campaign_id'),
                     'revision':value.revision, 'current_origin':value.data_origin,
                     'suggested_origin':'synthetic_test', 'requires_operator_review':True}
                    for value in objects if getattr(value, 'trip_id' if kind=='trips' else 'campaign_id') in identifiers)
    # Saved documents must remain independent: this tool never proposes rewriting snapshots.
    return {'dry_run':True, 'candidates':rows, 'document_snapshots':'unchanged',
            'instruction':'Review IDs and provenance; explicitly authorize each source PUT with its current revision. No apply mode is provided.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Existing local JSON overlay or an isolated export')
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error('root must already exist; no initialization or migration is performed')
    print(json.dumps(candidates(JsonRepository(args.root)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
