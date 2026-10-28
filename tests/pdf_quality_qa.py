"""DOC-PDF-003: synthetic PDFs, geometry, exact markers and raster contact sheets.

Run python tests/pdf_quality_qa.py; --compare-baseline additionally runs the same
matrix against an isolated git archive of HEAD. No real cloud or source data.
"""
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import pytest
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


GEOMETRY = """() => [...document.querySelectorAll('.sheet')].map(sheet=>{
  const box=el=>{const b=el.getBoundingClientRect();return {x:b.x,y:b.y,right:b.right,bottom:b.bottom,width:b.width,height:b.height};};
  const body=sheet.querySelector('.page-body'),b=box(body),header=box(sheet.querySelector('header')),footer=box(sheet.querySelector('footer'));
  const blocks=[...body.children].map(box),cells=[...body.querySelectorAll('td,th')].map(box);
  const textBoxes=[],walker=document.createTreeWalker(body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){if(!walker.currentNode.textContent.trim())continue;const range=document.createRange();range.selectNodeContents(walker.currentNode);
    for(const r of range.getClientRects())textBoxes.push({x:r.x,y:r.y,right:r.right,bottom:r.bottom});}
  const orphan=[...body.querySelectorAll('.block')].some(block=>block.querySelector('h1,h2')&&!block.querySelector('p,li,td,.photo'));
  return {body:b,header,footer,blocks,cells,textBoxes,orphan,number:sheet.querySelector('.page-number').textContent,
    text:body.innerText,scrollOK:body.scrollHeight<=body.clientHeight+1&&body.scrollWidth<=body.clientWidth+1};
})"""


def raster(pdf, folder, preview=None):
    # QA-only optional dependency. Never imported by the running application.
    import fitz
    folder.mkdir(parents=True,exist_ok=True)
    if not folder.resolve().is_relative_to(pdf.parent.resolve()):raise ValueError('QA raster folder escapes artifact directory')
    for previous in folder.glob('page-*.png'):previous.unlink()
    doc=fitz.open(pdf);thumbs=[];difference=None
    if preview:
        from PIL import ImageChops, ImageStat
        pix=doc[0].get_pixmap(matrix=fitz.Matrix(4/3,4/3),alpha=False)
        printed=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        screen=Image.open(preview).convert('RGB').resize(printed.size)
        difference=sum(ImageStat.Stat(ImageChops.difference(screen,printed)).mean)/(3*255)
        assert difference<.08,(pdf.name,'preview/PDF difference',difference)
    for i,page in enumerate(doc):
        pix=page.get_pixmap(matrix=fitz.Matrix(.65,.65),alpha=False)
        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        image.save(folder/f'page-{i+1:03d}.png')
        image.thumbnail((230,320))
        thumb=Image.new('RGB',(250,350),'#e4eae7');thumb.paste(image,((250-image.width)//2,15))
        ImageDraw.Draw(thumb).text((12,332),f'{pdf.stem} / {i+1}',fill='#172b41');thumbs.append(thumb)
    contact=Image.new('RGB',(1000,350*((len(thumbs)+3)//4)),'#e4eae7')
    for i,thumb in enumerate(thumbs):contact.paste(thumb,((i%4)*250,(i//4)*350))
    contact.save(folder/'contact.png')
    return difference


def run_pdf_quality():
    from test_cloud_demo import cloud_demo, ORIGIN
    baseline='--baseline' in sys.argv
    out=Path(os.getenv('PDF_QA_OUTPUT',str(ROOT/'local-data'/'pdf-quality-qa'/'current')))
    out.mkdir(parents=True,exist_ok=True);results=[]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('PLANNING_MODE','mock')
        for key in ('K_SERVICE','OPENAI_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_PLACES_API_KEY','GOOGLE_ROUTES_API_KEY'):
            patch.delenv(key,raising=False)
        demo=cloud_demo.__wrapped__(patch)
        with demo.client() as api,sync_playwright() as p:
            assets=[]
            for width,height in ((1200,700),(600,1000)):
                image=Image.new('RGB',(width,height),'#d3e4dd');draw=ImageDraw.Draw(image)
                draw.rectangle((0,0,width//3,height),fill='#172b41');draw.ellipse((width//3,height//4,width*9//10,height*3//4),fill='#e5a01d')
                data=io.BytesIO();image.save(data,'PNG')
                response=api.post('/api/document-studio/assets?filename=synthetic.png&rights_confirmed=true',content=data.getvalue(),headers={'content-type':'image/png'})
                response.raise_for_status();assets.append(response.json()['asset_id'])
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1300,'height':1000});page=context.new_page()
            context.add_init_script("""(() => {let ready=false;Object.defineProperty(window,'documentReady',{configurable:true,get:()=>ready,set:value=>{
              if(value===false&&!window.qaLeaves){
                const nodes=[...document.querySelectorAll('#source-blocks td,#source-blocks p,#source-blocks li')];
                window.qaLeaves=nodes.map((node,i)=>{node.dataset.qaLeaf=String(i);return node.textContent;});
              }ready=value;
            }});})();""")
            errors=[];external=[]
            def route_request(route):
                request=route.request
                if not request.url.startswith(ORIGIN+'/'):
                    external.append(request.url);route.abort();return
                response=api.request(request.method,request.url,headers=request.all_headers(),content=request.post_data_buffer,follow_redirects=False)
                route.fulfill(status=response.status_code,headers={k:v for k,v in response.headers.items() if k not in {'content-length','content-encoding'}},body=response.content)
            context.route('**/*',route_request);page.on('pageerror',lambda error:errors.append(str(error)))
            cases=[('offer.private',2,'standard','a4'),('offer.self_guide',5,'standard','a4'),('offer.school',5,'standard','a4'),
                ('offer.incentive',10,'standard','a4'),('pilot.basic',10,'standard','a4'),('pilot.advanced',15,'standard','a4'),('pilot.knowledge',15,'standard','a4'),('pilot.basic',2,'standard','a4')]
            cases += [('marketing.collection',count,variant,fmt) for variant in ('new_trips','theme_collection') for count,fmt in ((1,'a4'),(3,'a4'),(8,'a4'),(8,'social'))]
            for template,days,variant,fmt in cases:
                name=(template+'-'+variant+'-'+str(days)+'-'+fmt).replace('.','-')
                markers=[]
                def marker(value):markers.append(value);return value
                if template!='marketing.collection':
                    response=api.post('/api/document-studio/trips',json={'title':'Syntetyczna wyprawa — Żółć, Þingvellir i przestrzeń',
                        'data_origin':'synthetic_test','destinations':['Region testowy — długa nazwa kierunku'], 'duration_days':days,
                        'days':[{'day_number':i,'title':f'Dzień {i} — program testowy',
                            'public_description':marker(f'DAY{i:03d}')+' Opis syntetyczny. Odkrywamy strukturę programu bez potwierdzania faktów.',
                            'internal_notes':'PRIVATE_SENTINEL_FOR_PILOT',
                            'stops':[{'name':f'Punkt programu {i}','description':marker(f'STOP{i:03d}')+' Fikcyjny opis punktu.'}]} for i in range(1,days+1)]})
                    response.raise_for_status();trip=response.json();source_id=trip['trip_id']
                else:
                    trips=[]
                    for i in range(days):
                        response=api.post('/api/document-studio/trips',json={'title':('Bardzo długa nazwa kierunku — Żółć i Þingvellir. '*3)[:180] if i==0 else f'Kierunek testowy {i+1}',
                            'data_origin':'synthetic_test','destinations':['Region syntetyczny']})
                        response.raise_for_status();trips.append(response.json())
                    response=api.post('/api/document-studio/campaigns',json={'title':'Syntetyczne inspiracje TRIPSE','data_origin':'synthetic_test','layout_variant':variant,
                        'theme':'Przestrzeń i odkrywanie','description':'Wieloetapowa, fikcyjna kolekcja do kontroli składu.','cta':'Kontakt do uzgodnienia — scenariusz QA',
                        'hero_asset_id':assets[0],'items':[{'trip_id':t['trip_id'],'short_hook':marker(f'TRIP{i:03d}')+' Opis syntetyczny. '+('Więcej miejsca na odkrywanie. '*10),
                            'image_asset_id':assets[i%2] if i%3 else None,'image_position':{'x':25,'y':70,'zoom':1.4},'highlights':['Przestrzeń','Program do uzgodnienia']} for i,t in enumerate(trips)]})
                    response.raise_for_status();source_id=response.json()['campaign_id']
                response=api.post('/api/document-studio/drafts',json={'template_id':template,'source_type':'campaign' if template=='marketing.collection' else 'trip','source_id':source_id,'layout_variant':variant})
                response.raise_for_status();doc=response.json()
                update={'revision':1,'title':doc['title'],'sections':doc['sections']}
                if template.startswith('offer.'):
                    doc['offer_data'].update(concept_only=True,cta='Kontakt do uzgodnienia — dane syntetyczne',cover_asset_id=assets[0],photo_asset_ids=[assets[1]])
                    update['offer_data']=doc['offer_data']
                if template=='offer.incentive':
                    doc['offer_details']['hotel'].update(name_or_standard='Proponowany standard — obiekt syntetyczny',status='proposed',photo_asset_ids=assets)
                    update['offer_details']=doc['offer_details']
                if template=='pilot.knowledge':
                    # This template intentionally presents knowledge rather than the offer program.
                    markers=[]
                    for i,section in enumerate(doc['sections']):
                        if section['kind']=='knowledge':
                            section['knowledge']['facts']=marker(f'KNOW{i:03d}')+' '+('Syntetyczna narracja do kontroli składu, bez nowych faktów. '*22)
                if template=='pilot.advanced':
                    # Default logistics renders its own day description, not program() stop descriptions.
                    markers=[m for m in markers if m.startswith('DAY')]
                    for i,section in enumerate(doc['sections']):
                        if section['kind']=='logistics':section['logistics']['plan_b']=marker(f'PLAN{i:03d}')+' Plan alternatywny do uzgodnienia.'
                if template in ('offer.self_guide','pilot.advanced'):
                    long=' '.join(marker(f'TXT{i:04d}') for i in range(900))
                    lines='\n'.join(marker(f'LIN{i:03d}')+' Krótki wiersz — żółć.' for i in range(160))
                    update['sections'] += [{'kind':'text','title':'Wieloakapitowa narracja','order':100,'body':long+'\n\n'+lines},
                        {'kind':'table','title':'Długi harmonogram testowy','order':101,'columns':['Godzina / dzień','Opis / ustalenia','Status'],
                         'rows':[[marker(f'ROW{i:03d}')+' 09:15 Atlantic/Reykjavik',
                                  ' '.join(marker(f'CELL{j:04d}') for j in range(700)) if i==5 else 'Syntetyczne ustalenia, długa wartość do zawinięcia. '*3,
                                  'Do uzgodnienia'] for i in range(40)]}]
                if template=='offer.incentive':
                    update['sections'].append({'kind':'gallery','title':'Obrazy syntetyczne — poziom i pion','order':100,'images':[
                        {'asset_id':a,'position':{'x':25,'y':70,'zoom':1.4},'caption':marker(f'CAP{i:03d}')+' Neutralna ilustracja testowa, nie zdjęcie hotelu.'} for i,a in enumerate(assets)]})
                if template=='pilot.basic' and days==2:
                    update['sections'].append({'kind':'table','title':'Osiem kolumn — syntetyczne dane','order':100,
                        'columns':['Kolumna '+str(i) for i in range(8)],'rows':[
                            [marker(f'WID{r:03d}C{c}')+' '+('Wartość do zawinięcia. '*5) for c in range(8)] for r in range(30)]})
                response=api.put('/api/document-studio/drafts/'+doc['document_id'],json=update);response.raise_for_status()
                started=time.perf_counter();page.goto(ORIGIN+'/api/document-studio/drafts/'+doc['document_id']+'/preview?output_format='+fmt)
                page.wait_for_function('() => window.documentReady === true',timeout=60000)
                elapsed=(time.perf_counter()-started)*1000
                layout=page.evaluate('window.layoutErrors');geometry=page.evaluate(GEOMETRY)
                result={'name':name,'navigationReadyMs':round(elapsed,1),'layout':layout,'pages':len(geometry),'metrics':page.evaluate('window.layoutMetrics || null')}
                results.append(result)
                page.locator('.sheet').first.screenshot(path=str(out/(name+'.png')))
                if baseline and (layout or not page.locator('#print-document').is_enabled()):continue
                assert not layout,(name,layout)
                assert page.locator('#print-document').is_enabled(),name
                assert page.evaluate("""() => window.qaLeaves.every((text,i)=>[...document.querySelectorAll('#pages [data-qa-leaf="'+i+'"]')].map(n=>n.textContent).join('')===text)"""),(name,'DOM text integrity')
                for i,g in enumerate(geometry):
                    assert g['scrollOK'] and g['text'].strip() and not g['orphan'],(name,i,'overflow/empty/orphan')
                    assert g['number']==f'{i+1} / {len(geometry)}'
                    assert g['header']['bottom']<=g['body']['y']+1 and g['body']['bottom']<=g['footer']['y']+1
                    for b in g['blocks']+g['cells']+g['textBoxes']:
                        assert b['y']>=g['body']['y']-1 and b['bottom']<=g['body']['bottom']+1,(name,i,'vertical',b)
                        assert b['x']>=g['body']['x']-1 and b['right']<=g['body']['right']+1,(name,i,'horizontal',b)
                    for a,b in zip(g['blocks'],g['blocks'][1:]):assert a['bottom']<=b['y']+1,(name,i,'overlap')
                pdf=out/(name+'.pdf');page.pdf(path=str(pdf),prefer_css_page_size=True,print_background=True)
                reader=PdfReader(pdf);assert len(reader.pages)==len(geometry),(name,'PDF page count')
                (out/(name+'-dom.txt')).write_text(page.locator('#pages').inner_text(),encoding='utf-8')
                text='\n'.join(p.extract_text() for p in reader.pages)
                # Presentation headings/footers may repeat; data markers may not.
                marker_failures=[m for m in markers if len(re.findall(r'(?<![A-Z0-9])'+m+r'(?![A-Z0-9])',text))!=1]
                result['pdfMarkerFailures']=marker_failures
                if baseline:
                    normalized=re.sub(r'\s+','',text)
                    result['markersRecoveredIgnoringWhitespace']=sum(m in normalized for m in marker_failures)
                else:assert not marker_failures,(name,marker_failures[:5],'lost/duplicated/broken token')
                for prefix in ('TXT','LIN','ROW','CELL'):
                    actual=re.findall(prefix+r'\d+',text);expected=[m for m in markers if m.startswith(prefix)]
                    assert actual==expected,(name,prefix,'order')
                if not template.startswith('pilot.'):assert 'PRIVATE_SENTINEL_FOR_PILOT' not in text
                assert 'Żół' in text or 'żół' in text or template=='marketing.collection'
                width,height=(810,1012.5) if fmt=='social' else (595.276,841.89)
                for pdf_page in reader.pages:
                    assert abs(float(pdf_page.mediabox.width)-width)<1 and abs(float(pdf_page.mediabox.height)-height)<1
                for image in page.locator('#pages img').all():
                    assert image.evaluate('(img)=>getComputedStyle(img).objectFit')=='cover'
                    assert image.evaluate('(img)=>getComputedStyle(img.parentElement).overflow')=='hidden'
                    assert image.evaluate(r"""img=>{const requested=Number(img.style.transform.match(/scale\(([^)]+)\)/)[1]);
                        const actual=new DOMMatrix(getComputedStyle(img).transform);return Math.abs(actual.a-requested)<.001&&Math.abs(actual.d-requested)<.001&&getComputedStyle(img).objectPosition===img.style.objectPosition;}""")
                assert all('TEST' in p.extract_text() for p in reader.pages) if not baseline else True
                result['previewPdfMeanDifference']=raster(pdf,out/name,out/(name+'.png'))
                print(name+(': BASELINE / '+str(len(marker_failures))+' broken markers' if baseline else ': PASS')+' / '+str(len(geometry))+' pages / '+str(round(elapsed))+' ms',flush=True)
            # Unsplittable content and resource failures remain fail-closed, with context.
            if not baseline:
                from app.document_studio.rendering import render_shell
                from app.document_studio.marketing import Issue
                for key,block,kind in [('impossible','<section class="block"><h2>Niepodzielny test</h2><div class="photo" style="min-height:2500px!important"></div></section>','layout'),
                    ('missing','<section class="block offer-photo"><h2>Zdjęcie testowe</h2><figure class="photo"><img src="/api/document-studio/assets/missing/content"></figure></section>','resource')]:
                    html=render_shell('Synthetic failure',block,[])
                    page.route(ORIGIN+'/qa-render',lambda route:route.fulfill(content_type='text/html',body=html))
                    page.goto(ORIGIN+'/qa-render');page.wait_for_function('() => window.documentReady === true')
                    assert not page.locator('#print-document').is_enabled()
                    assert any(d['kind']==kind for d in page.evaluate('window.layoutDiagnostics'))
                    page.unroute(ORIGIN+'/qa-render')
                html=render_shell('Synthetic validation','<section class="block"><h2>Walidacja</h2><p>Poprawny układ, brak ceny.</p></section>',[
                    Issue(severity='error',field_path='offer_data.price',message='Brak ceny')])
                page.route(ORIGIN+'/qa-render',lambda route:route.fulfill(content_type='text/html',body=html))
                page.goto(ORIGIN+'/qa-render');page.wait_for_function('() => window.documentReady === true')
                assert page.evaluate('window.layoutErrors')==[]
                assert not page.locator('#print-document').is_enabled()
                assert 'walidacji danych' in page.locator('#layout-status').inner_text()
                page.unroute(ORIGIN+'/qa-render')
                token='A'*6000
                html=render_shell('Synthetic token','<section class="block document-section"><h2>Token testowy</h2><p>'+token+'</p></section>',[])
                page.route(ORIGIN+'/qa-render',lambda route:route.fulfill(content_type='text/html',body=html))
                page.goto(ORIGIN+'/qa-render');page.wait_for_function('() => window.documentReady === true')
                assert page.evaluate('window.layoutErrors')==[]
                assert page.locator('.sheet').count()>1
                assert ''.join(page.locator('#pages .page-body p').all_text_contents())==token
                page.unroute(ORIGIN+'/qa-render')
                assert not errors,errors
            assert not external,external
            browser.close()
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    overview=Image.new('RGB',(1000,350*((len(results)+3)//4)),'#e4eae7')
    links=[]
    for i,result in enumerate(results):
        name=result['name'];png=out/(name+'.png')
        image=Image.open(png).convert('RGB');image.thumbnail((230,320))
        x=(i%4)*250;y=(i//4)*350;overview.paste(image,(x+(250-image.width)//2,y+8))
        ImageDraw.Draw(overview).text((x+8,y+330),name[:38],fill='#172b41')
        links.append(f'<li>{name}: <a href="{name}.pdf">PDF</a> · <a href="{name}/contact.png">wszystkie strony</a></li>')
    overview.save(out/'overview.png')
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>TRIPSE PDF QA</title><h1>Syntetyczna macierz QA</h1><img width="1000" src="overview.png"><ul>'+''.join(links)+'</ul>',encoding='utf-8')
    print('PDF quality matrix '+('BASELINE recorded' if baseline else 'PASS')+': '+str(len(results))+' cases; '+str(out))


if __name__=='__main__':
    if '--compare-baseline' in sys.argv:
        with tempfile.TemporaryDirectory(prefix='tripse-pdf-baseline-') as tmp:
            archive=Path(tmp)/'head.zip';checkout=Path(tmp)/'repo';checkout.mkdir()
            reference=sys.argv[sys.argv.index('--baseline-ref')+1] if '--baseline-ref' in sys.argv else 'HEAD'
            subprocess.run(['git','archive',reference,'-o',str(archive)],cwd=ROOT,check=True)
            with zipfile.ZipFile(archive) as source:source.extractall(checkout)
            from app.document_studio.models import OperationalEntry
            from app.document_studio.rendering.trip_documents import operational_entry
            previous={}
            exec(compile((checkout/'app/document_studio/rendering/trip_documents.py').read_text(encoding='utf-8'),'baseline_component','exec'),previous)
            entry=OperationalEntry(title='UNIQUE_OPERATION_TITLE',details='Opis '*2000,start_local='2027-05-01T09:15:00',time_zone='Europe/Warsaw',status='planned')
            old=previous['operational_entry']('Test',entry);new=operational_entry('Test',entry)
            evidence={'baseline_ref':reference,'baseline_title_copies':old.count('UNIQUE_OPERATION_TITLE'),
                'current_title_copies':new.count('UNIQUE_OPERATION_TITLE'),'baseline_time_copies':old.count('09:15'),'current_time_copies':new.count('09:15')}
            evidence_path=ROOT/'local-data/pdf-quality-qa/component-comparison.json';evidence_path.parent.mkdir(parents=True,exist_ok=True)
            evidence_path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
            (checkout/'tests'/'pdf_quality_qa.py').write_bytes(Path(__file__).read_bytes())
            subprocess.run([sys.executable,str(checkout/'tests'/'pdf_quality_qa.py'),'--baseline'],cwd=checkout,
                env=dict(os.environ,PDF_QA_OUTPUT=str(ROOT/'local-data'/'pdf-quality-qa'/'baseline-matrix')),check=True)
    run_pdf_quality()
