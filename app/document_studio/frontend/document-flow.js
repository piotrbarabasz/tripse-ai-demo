/* Shared workflow and view helpers. Business data remains in the existing API. */
window.DocumentFlow=(()=>{
  let state=null,transient=null;
  const folds=new Map();
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uid=()=>crypto.randomUUID().replaceAll('-','');
  const variantLabel=value=>value==='theme_collection'?'Kolekcja tematyczna':value==='new_trips'?'Nowe kierunki':'Standard';
  function path(s=state){
    const query=new URLSearchParams();
    if(s.mode==='new'&&!s.sourceId)query.set('mode','new');
    if(s.demo)query.set('demo','1');
    return `create-document/${s.template}/${s.variant}`+(s.sourceId?`/${s.kind}/${s.sourceId}`:'')+(query.size?'?'+query:'');
  }
  function configure(template,variant,kind,sourceId,options={}){
    const key=[template,variant,kind,sourceId||''].join('/');
    const previousKey=state?[state.template,state.variant,state.kind,state.sourceId||''].join('/'):null;
    if(previousKey!==key){state={key,template,variant,kind,sourceId,attempt:null,demo:false};transient=null;}
    state.key=key;
    state.mode=options.mode==='new'?'new':'existing';
    if(options.attempt)state.attempt=options.attempt;
    if(options.demo!==undefined)state.demo=options.demo;
    return state;
  }
  function steps(active,s={},documentId){
    const labels=['Rodzaj',s.kind==='campaign'?'Kampania':'Program','Edycja','Sprawdzenie'];
    const routes=['templates',s.template?path(s):null,documentId?'edit-draft/'+documentId:null,documentId?'review-draft/'+documentId:null];
    return '<nav class="flow-progress" aria-label="Etapy tworzenia dokumentu">'+labels.map((label,i)=>{
      const n=i+1,disabled=n===active||!routes[i]||documentId&&n<3;
      return `<button type="button" ${disabled?'disabled':`data-go="${escape(routes[i])}"`} ${n===active?'aria-current="step"':''} class="${n<active?'flow-done':''}"><span>${n}</span>${label}${n<active?'<small>'+(n===3?'Zapisano':'Wybrano')+'</small>':''}</button>`;
    }).join('')+'</nav>';
  }
  function subset(actual,expected){
    if(expected===null||typeof expected!=='object')return actual===expected;
    if(Array.isArray(expected))return Array.isArray(actual)&&actual.length===expected.length&&expected.every((value,i)=>subset(actual[i],value));
    return actual&&Object.entries(expected).every(([key,value])=>['revision','updated_at'].includes(key)||subset(actual[key],value));
  }
  function matchesCreated(kind,actual,expected){
    if(kind!=='drafts')return subset(actual,expected);
    const source=actual.trip_snapshot||actual.campaign_snapshot;
    return actual.document_id===expected.document_id&&actual.template_id===expected.template_id&&actual.layout_variant===expected.layout_variant
      &&source&&(source.trip_id||source.campaign_id)===expected.source_id&&source.revision===expected.source_revision
      &&actual.editorial_notes===(expected.editorial_notes||'')&&actual.demo_example===!!expected.demo_example;
  }
  async function persistCreate(kind,value,api){
    const payload=JSON.parse(JSON.stringify(value)),identifier=payload.document_id||payload.trip_id||payload.campaign_id;
    try{return await api(kind,{method:'POST',body:JSON.stringify(payload)});}
    catch(error){
      // Stable IDs + create-only writes also protect retry after a lost response.
      if(error.status&&error.status<500&&error.status!==409)throw error;
      try{
        const stored=await api(kind+'/'+encodeURIComponent(identifier));
        if(matchesCreated(kind,stored,payload))return stored;
        throw new Error('Zapis o tym numerze zawiera inne dane. Otwórz go i sprawdź przed dalszą pracą.');
      }catch(readError){
        if(readError.status===404)throw error;
        const result=new Error(readError.status||readError instanceof TypeError?'Nie można teraz potwierdzić zapisu. Sprawdź zapisany obiekt lub ponów próbę z tym samym formularzem.':readError.message);
        result.recovery={kind,identifier};throw result;
      }
    }
  }
  function recovery(error,host){
    host.querySelector('.flow-recovery')?.remove();if(!error.recovery)return;
    const {kind,identifier}=error.recovery;
    const route=(kind==='drafts'?'edit-draft':kind==='campaigns'?'marketing':'trips')+'/'+identifier;
    const panel=document.createElement('section');panel.className='panel flow-recovery';
    panel.innerHTML=`<p>Wynik zapisu wymaga sprawdzenia. Formularz zachowuje ten sam identyfikator próby.</p><button type="button" data-go="${escape(route)}">Sprawdź zapis</button>`;host.prepend(panel);
  }
  function summary(source,kind){
    const campaign=kind==='campaign';
    const lines=campaign?[`${source.items.length} kierunków`,variantLabel(source.layout_variant)]:[
      (source.destinations||[]).join(' · ')||'Kierunek do ustalenia',`${source.days.length} dni`,
      source.start_date?`${source.start_date} — ${source.end_date||'data końca do ustalenia'}`:'Termin do ustalenia',
      (source.categories||[]).map(c=>SourcePicker.categories[c]).join(' · ')||'Nieprzypisane',
      `Dni z opisem: ${source.days.filter(d=>d.public_description.trim()).length}/${source.days.length} · Atrakcje: ${source.days.reduce((sum,d)=>sum+d.stops.length,0)}`];
    return `<section class="panel flow-source-summary"><h2>${escape(source.title)}</h2><p>${lines.map(escape).join(' · ')}</p><span class="tag">${escape(SourcePicker.origins[source.data_origin||'unknown'])}</span><p class="muted">To podsumowanie programu, nie potwierdzenie kompletności ani warunków wyjazdu.</p></section>`;
  }
  function decorateEditor(draft,ui){
    const source=draft.trip_snapshot||draft.campaign_snapshot,kind=draft.trip_snapshot?'trip':'campaign';
    const s={template:draft.template_id,variant:draft.layout_variant,kind,sourceId:source.trip_id||source.campaign_id};
    const header=document.createElement('div');header.innerHTML=steps(3,s,draft.document_id);ui.main.prepend(header);
    const info=document.createElement('section');info.className='panel flow-source-info';
    info.innerHTML=`<strong>${kind==='trip'?'Wycieczka':'Kampania'}: ${escape(ui.sourceTitle||source.title)}${draft.trip_snapshot?' · '+source.days.length+' dni':''}</strong><p>${kind==='campaign'?'Kampania przechowuje wspólną kolekcję wycieczek. ':''}Ten dokument jest niezależną wersją do dalszej edycji. Zmiany tutaj nie zmieniają ${kind==='campaign'?'kampanii':'programu źródłowego'}.</p><p id="document-save-state" role="status">${ui.isDirty?.()?'Masz niezapisane zmiany.':'Otwarta zapisana wersja dokumentu.'}</p><button type="button" data-go="${kind==='trip'?'trips':'marketing'}/${escape(s.sourceId)}">Otwórz ${kind==='trip'?'wycieczkę':'kampanię'}</button>`;
    ui.main.querySelector('.heading').after(info);
    const eyebrow=ui.main.querySelector('.heading .eyebrow');
    if(eyebrow){const metadata=document.createElement('details');metadata.className='flow-metadata';metadata.innerHTML='<summary>Informacje o zapisie</summary>';eyebrow.before(metadata);metadata.append(eyebrow);}
    const section=ui.main.querySelector('.section-editor');
    if(section){
      const key=draft.document_id+'/sections',details=document.createElement('details');details.className='flow-options';
      details.open=folds.has(key)?folds.get(key):draft.template_id.startsWith('pilot.');
      details.innerHTML='<summary>Układ i sekcje — kolejność, widoczność, tabele i materiały</summary>';
      section.before(details);details.append(section);details.addEventListener('toggle',()=>folds.set(key,details.open));
    }
    const form=ui.main.querySelector('#d-form');
    if(form){
      const labels=[...form.querySelectorAll('[data-d-field="offer_data.cover_asset_id"],[data-d-field="offer_data.photo_asset_ids"],[data-d-field="offer_details.hotel.photo_asset_ids"]')].map(field=>field.closest('label'));
      if(labels.length){
        const photos=document.createElement('details'),key=draft.document_id+'/photos';photos.className='flow-options';photos.open=folds.has(key)?folds.get(key):true;
        photos.innerHTML='<summary>Zdjęcia i materiały</summary>';form.append(photos);labels.forEach(label=>photos.append(label));
        const upload=ui.main.querySelector('#d-upload')?.closest('section');if(upload)photos.append(upload);
        photos.addEventListener('toggle',()=>folds.set(key,photos.open));
      }
    }
    const actions=ui.main.querySelector('.heading .actions');
    if(actions&&ui.review){const review=document.createElement('button');review.type='button';review.id='document-review';review.className='accent';review.textContent='Zapisz i sprawdź';review.onclick=ui.review;actions.append(review);}
    if(!ui.main.dataset.flowValidationBound){
      ui.main.addEventListener('invalid',event=>{for(let p=event.target.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;},true);
      ui.main.dataset.flowValidationBound='true';
    }
  }
  function embeddedPreview(frame,html){
    // Export uses the dedicated saved preview. Embedded views have one outer export action.
    frame.srcdoc=html.replace('</head>','<style>#print-document{display:none!important}</style></head>');
  }
  function focus(main){const target=main.querySelector('h1')||main;target.tabIndex=-1;target.focus({preventScroll:true});}
  return {uid,configure,get state(){return state;},path,steps,variantLabel,summary,persistCreate,recovery,decorateEditor,embeddedPreview,focus,
    reset(){state=null;transient=null;},prepare(value){transient=value;},get prepared(){return transient;}};
})();
