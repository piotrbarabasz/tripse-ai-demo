"""Isolated measurements of documented limits; not assertions of supported behavior."""
import json
import multiprocessing as mp
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.document_studio.repository import JsonRepository
from app.document_studio.cloud_storage import GCSRepository
from app.document_studio.library import DocumentLibrary
from tests.test_document_library import create
from tests.test_cloud_demo import FakeBucket


def process_writer(root, identifier, title, barrier, commit_lock, output):
    repo = JsonRepository(root)
    # Isolate the head CAS limitation from disposable cache races on Windows.
    repo._cache_summary = lambda *args: None
    value = repo.get('drafts', identifier)
    value.title = title
    replace = os.replace
    def synchronize(source, target):
        if Path(target).parent == Path(root)/'drafts':
            barrier.wait(timeout=15)
            with commit_lock:
                return replace(source, target)
        return replace(source, target)
    os.replace = synchronize
    try:
        saved = repo.save('drafts', value)
        output.put({'title':saved.title, 'revision':saved.revision})
    except Exception as error:
        output.put({'error':type(error).__name__})


def run():
    results = {}
    with tempfile.TemporaryDirectory(prefix='tripse-process-race-') as tmp:
        repo = JsonRepository(tmp)
        doc = create(repo)
        context = mp.get_context('spawn')
        barrier, commit_lock, output = context.Barrier(2), context.Lock(), context.Queue()
        processes = [context.Process(target=process_writer, args=(tmp, doc.document_id, title, barrier, commit_lock, output))
                     for title in ('process A','process B')]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=25)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                raise RuntimeError('Experiment timeout')
        results['unsupported_multiple_local_processes'] = {
            'responses':[output.get(timeout=3) for _ in processes],
            'head_title':repo.get('drafts', doc.document_id).title,
            'history_revisions':[r.revision for r in repo.list_revisions(doc.document_id)]}
    scans = []
    for count in (100, 1000):
        bucket = FakeBucket()
        repo = GCSRepository(bucket)
        doc = create(repo)
        original_name = repo._name('drafts', doc.document_id)
        summary = bucket.metadata[original_name]['tripse_document']
        bucket.objects.clear()
        bucket.metadata.clear()
        for i in range(count):
            identifier = f'synthetic-{i:05d}'
            name = repo._name('drafts', identifier)
            row = json.loads(summary)
            row['document_id'] = identifier
            bucket.objects[name] = (b'not downloaded', i+1)
            bucket.metadata[name] = {'tripse_document':json.dumps(row)}
        def forbidden(*args, **kwargs):
            raise AssertionError('Metadata query downloaded document')
        repo.get = forbidden
        durations = []
        for _ in range(5):
            start = time.perf_counter()
            page = DocumentLibrary(repo).list(limit=25)
            durations.append((time.perf_counter()-start)*1000)
            assert len(page.items) == 25 and page.total == count
        scans.append({'documents':count, 'returned':25, 'metadata_rows_scanned':count,
            'median_ms_fake_gcs':round(statistics.median(durations),2),
            'metadata_json_bytes':sum(len(m['tripse_document'].encode()) for m in bucket.metadata.values()),
            'full_document_reads':0})
    results['metadata_scans'] = scans
    # Count real adapter calls; timings above deliberately exclude GCP latency.
    import io
    from PIL import Image
    from app.document_studio.assets import AssetStore
    from app.document_studio.cloud_storage import GCSAssetBytes
    from app.document_studio.models import DocumentSection
    from app.document_studio.rendering.sections import document_issues
    bucket = FakeBucket()
    repo = GCSRepository(bucket)
    binary = GCSAssetBytes(bucket)
    assets = AssetStore(repo, binary)
    image = io.BytesIO()
    Image.new('RGB', (12,10), 'orange').save(image, 'PNG')
    asset = assets.upload(image.getvalue(), 'image/png', 'synthetic.png', True)
    doc = create(repo)
    doc.sections.extend(DocumentSection(title='Repeated image', kind='image', images=[{'asset_id':asset.asset_id}]) for _ in range(20))
    reads = []
    read = binary.read
    def counted(asset):
        reads.append(asset.asset_id)
        return read(asset)
    binary.read = counted
    document_issues(doc, assets)
    results['image_validation'] = {'section_references':20, 'unique_images':1, 'binary_downloads_per_validation':len(reads)}
    from pypdf import PdfReader
    pdf = ROOT/'local-data'/'reliability-audit'/'multiline-15-day.pdf'
    if pdf.exists():
        reader = PdfReader(pdf)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        import re
        results['multiline_pdf'] = {'pages':len(reader.pages), 'all_160_lines_present':set(map(int,re.findall(r'Line (\d+)',text))) == set(range(160))}
    target = ROOT/'local-data'/'reliability-audit'/'experiments.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    run()
