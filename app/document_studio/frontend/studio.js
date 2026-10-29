/* Local, dependency-free editor. User text is escaped before inserting HTML. */
const $ = s => document.querySelector(s);
const main = $('#main');
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const e = escapeHTML;
const id = () => crypto.randomUUID().replaceAll('-', '');
let trips = [], campaigns = [], templates = [], current = null, dirty = false, creating = false, busy = false;
let messageTimer, activeHash = '', routeGeneration = 0, preparation=null, canEdit=true;
function message(text, error = false) {
  clearTimeout(messageTimer); const box = $('#message'); box.textContent = text;
  box.className = error ? 'error' : ''; box.hidden = false;
  messageTimer = setTimeout(() => box.hidden = true, error ? 12000 : 5000);
}
async function api(path, options = {}) {
  const response = await fetch('/api/document-studio/' + path, {
    ...options, headers: {'Content-Type':'application/json'}, cache:'no-store'
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail;
    const error=new Error(Array.isArray(detail)?detail.map(x=>`${x.loc.slice(1).join('.')}: ${x.msg}`).join('; '):detail||'Nie udało się wykonać operacji.');error.status=response.status;throw error;
  }
  return data;
}
async function refresh() {
  const data = await Promise.all(['trips','campaigns','library?limit=1&archived=include','templates','access'].map(x => api(x)));
  [trips,campaigns,,templates]=data;canEdit=data[4].can_edit;
  document.querySelector('[data-nav="templates"]').hidden=!canEdit;
  $('#trip-count').textContent = trips.length; $('#campaign-count').textContent = campaigns.length; $('#draft-count').textContent = data[2].total;
}
function navigate(path) {
  if (busy) return;
  if (dirty && !confirm('Masz niezapisane zmiany. Opuścić ten widok?')) return;
  dirty = false;
  if (location.hash === '#' + path) route(); else location.hash = path;
}
function heading(kicker, title, subtitle, action = '') {
  return `<div class="heading"><div><p class="eyebrow">${kicker}</p><h1>${e(title)}</h1><p class="muted">${e(subtitle)}</p></div>${action}</div>`;
}
const statusLabels = {idea:'Pomysł', draft:'Wersja robocza', planned:'Zaplanowana', confirmed:'Potwierdzona', completed:'Zakończona', cancelled:'Anulowana'};
function cards(view) {
  const entries=view==='trips'?trips:campaigns;
  const names={trips:['BIBLIOTEKA PODRÓŻY','Twoje wycieczki','Jeden program. Wiele możliwości dokumentu.'],campaigns:['KOLEKCJE KIERUNKÓW','Kampanie','Kilka podróży połączonych jednym pomysłem.']};
  main.innerHTML=heading(...names[view],!canEdit?'':view==='trips'?'<button class="primary" data-go="trips/new">+ Nowa wycieczka</button>':'<button class="primary" data-go="campaigns/new">+ Nowa kampania</button>')+'<section id="source-library-filters" class="panel"></section><div id="source-library-results"></div>';
  SourcePicker.mount($('#source-library-filters'),{entries,kind:view==='trips'?'trip':'campaign',id:'library-source-select',cards:true,onResults:visible=>{
    $('#source-library-results').innerHTML=`<div class="cards">${visible.map(x=>{
      const resourceId=x.trip_id||x.campaign_id;
      const label=view==='trips'?x.destinations.join(' · ')||'Kierunek nieustalony':x.season||'Kolekcja';
      const description=view==='trips'?x.description:x.items.map(i=>trips.find(t=>t.trip_id===i.trip_id)?.title||i.trip_id).join(' · ');
      return `<article class="card" data-source-id="${e(resourceId)}"><div class="card-top">${e(label)}</div><span class="tag">${view==='trips'?`${x.duration_days} dni · ${e(statusLabels[x.status])}`:`${x.items.length} kierunków`}</span><span class="tag">${e(SourcePicker.origins[x.data_origin||'unknown'])}</span>${view==='trips'?`<p>${e((x.categories||[]).map(c=>SourcePicker.categories[c]).join(' · ')||'Nieprzypisane')}</p>`:''}<h2>${e(x.title)}</h2><p class="muted">${e(description)}</p><button class="open" data-go="${view}/${e(resourceId)}">Otwórz →</button></article>`;
    }).join('')}</div>${visible.length?'':`<div class="panel empty">Brak pasujących ${view==='trips'?'wycieczek':'kampanii'}. Zmień filtry lub utwórz nową.</div>`}`;
  }});
}

function input(label, field, value, type = 'text', extra = '') {
  return `<label>${label}<input data-field="${field}" type="${type}" value="${e(value)}" ${extra}></label>`;
}
function textarea(label, field, value) {
  return `<label>${label}<textarea data-field="${field}" maxlength="20000">${e(value)}</textarea></label>`;
}
function documentTools(sourceType) {
  if(!canEdit)return '';
  return `<aside class="panel document-tools"><h2>Dokument z ${sourceType==='trip'?'tej wycieczki':'tej kampanii'}</h2><p>Wybierzesz rodzaj dokumentu, zachowując ${sourceType==='trip'?'tę wycieczkę':'tę kampanię'}.</p><button type="button" id="create-draft" data-program-document="${sourceType}">${sourceType==='trip'?'Utwórz dokument z tej wycieczki':'Utwórz materiał z tej kampanii'}</button></aside>`;
}
function setDirty(value){
  dirty=value;
  if($('#document-save-state'))$('#document-save-state').textContent=value?'Masz niezapisane zmiany.':'Zmiany zostały zapisane.';
  if($('#source-completeness')&&current)$('#source-completeness').textContent='Dni z opisem: '+current.days.filter(day=>day.public_description.trim()).length+'/'+current.days.length+' · Atrakcje: '+current.days.reduce((sum,day)=>sum+day.stops.length,0)+'. To nie jest potwierdzenie gotowości programu.';
  if($('#source-save-state')&&current)$('#source-save-state').textContent=current.days.length+' dni · '+(value||creating?'Program wymaga zapisania':'Program zapisany');
  for(const button of main.querySelectorAll('[data-source-continue]')){button.disabled=value||button.dataset.sourceSaved!=='true';button.classList.toggle('primary',!button.disabled);}
  if($('#create-draft')?.dataset.programDocument==='trip')$('#create-draft').disabled=value||creating;
  if($('#save-trip')&&preparation)$('#save-trip').classList.toggle('primary',value||creating);
}
function forward(path){dirty=false;navigate(path);}
function replaceRoute(path){history.replaceState(null,'','#'+path);activeHash=location.hash;}
async function createDocument(source,flow){
  if(busy)return;
  const snapshotRevision=flow.expectedRevision||source.revision;
  flow.attempt ||= DocumentFlow.uid();
  const sourceId=source.trip_id||source.campaign_id;flow.sourceId=sourceId;
  const query=new URLSearchParams({attempt:flow.attempt,rev:String(snapshotRevision)});if(flow.demo)query.set('demo','1');
  replaceRoute(`create-document/${flow.template}/${flow.variant}/${flow.kind}/${sourceId}?${query}`);
  busy=true;main.inert=true;
  try{
    const draft=await DocumentFlow.persistCreate('drafts',{document_id:flow.attempt,source_revision:snapshotRevision,
      template_id:flow.template,source_type:flow.kind,source_id:sourceId,layout_variant:flow.variant,demo_example:!!flow.demo},api);
    let warning='';try{await refresh();}catch{warning=' Lista wymaga odświeżenia.';}
    busy=false;DocumentFlow.reset();forward('edit-draft/'+draft.document_id);message('Dokument utworzony. Edytujesz teraz jego niezależną wersję.'+warning,!!warning);
  }catch(error){if(error.recovery){flow.uncertain=true;setDirty(true);}message(error.message,true);DocumentFlow.recovery(error,main);}
  finally{busy=false;main.inert=false;}
}

function templateCatalog(fixed=null) {
  const selectedVariant=DocumentFlow.state?.template==='marketing.collection'?DocumentFlow.state.variant:fixed?.layout_variant||'new_trips';
  const groups=[['offer','Typy ofert','↗'],['pilot','Rozpiski dla pilotów','▤'],['marketing','Oferty marketingowe','◈']];
  main.innerHTML=DocumentFlow.steps(1)+heading('DOCUMENT STUDIO','Utwórz nowy dokument','Wybierz rodzaj dokumentu. Następnie przygotujesz program, a na końcu sprawdzisz i zapiszesz dokument.')+(fixed?`<section class="panel"><strong>${fixed.trip_id?'Wycieczka':'Kampania'}: ${e(fixed.title)}</strong><p>Wybierz rodzaj dokumentu dla ${fixed.trip_id?'tej wycieczki':'tej kampanii'}.</p></section>`:'')+'<div class="actions flow-shortcuts"><button data-go="drafts">Otwórz zapisany dokument</button><button data-go="trips">Zarządzaj programami wycieczek</button><button data-go="campaigns">Zarządzaj kampaniami</button></div>'+groups.filter(([family])=>!fixed||(fixed.trip_id?family!=='marketing':family==='marketing')).map(([family,label,icon])=>`<section class="template-group"><h2>${label}</h2><div class="template-row">${templates.filter(t=>t.family===family&&(!fixed||t.source_type===(fixed.trip_id?'trip':'campaign'))).map(t=>`<article class="card template-card"><span class="template-icon" aria-hidden="true">${icon}</span><h3>${e(t.name)}</h3><p>${e(t.description)}</p>${family==='marketing'?'<label>Wariant<select class="catalog-variant"><option value="new_trips" '+(selectedVariant==='new_trips'?'selected':'')+'>Nowości / nowe kierunki</option><option value="theme_collection" '+(selectedVariant==='theme_collection'?'selected':'')+'>Kolekcja tematyczna</option></select></label>':''}<button class="primary" data-create-template="${e(t.template_id)}">Wybierz</button></article>`).join('')}</div></section>`).join('');
  for(const button of main.querySelectorAll('[data-create-template]'))button.onclick=()=>{DocumentFlow.reset();navigate('create-document/'+button.dataset.createTemplate+'/'+(button.closest('article').querySelector('select')?.value||'standard')+(fixed?'/'+(fixed.trip_id?'trip/':'campaign/')+(fixed.trip_id||fixed.campaign_id):''));};
}
function sourceChooser(templateId,variant,selected=null,options={}) {
  const template=templates.find(t=>t.template_id===templateId);
  if(!template||!template.layout_variants.includes(variant))throw new Error('Nieprawidłowy rodzaj lub wariant dokumentu.');
  const marketing=template.source_type==='campaign',kind=marketing?'campaign':'trip';
  const flow=DocumentFlow.configure(templateId,variant,kind,selected?.trip_id||selected?.campaign_id,options);
  flow.expectedRevision=options.rev?Number(options.rev):null;
  const base=`create-document/${templateId}/${variant}`,isNew=options.mode==='new'&&!selected;
  const fixed=selected?`templates/${kind}/${selected.trip_id||selected.campaign_id}`:'templates';
  main.innerHTML=DocumentFlow.steps(2,flow)+heading('RODZAJ DOKUMENTU: '+template.name,selected?'Sprawdź '+(marketing?'kampanię':'wycieczkę'):isNew?'Nowa '+(marketing?'kampania':'wycieczka'):'Wybierz '+(marketing?'kampanię':'wycieczkę'),marketing?DocumentFlow.variantLabel(variant):'Kategoria porządkuje wycieczki. Rodzaj dokumentu został już wybrany.',`<button data-go="${fixed}">← Rodzaj dokumentu</button>`)+
    (selected?'':`<nav class="source-paths" aria-label="Sposób przygotowania ${marketing?'kampanii':'wycieczki'}"><button type="button" data-go="${base}" ${!isNew?'aria-current="page" disabled':''}>Wybierz istniejącą ${marketing?'kampanię':'wycieczkę'}</button><button type="button" class="source-new" data-go="${base}?mode=new" ${isNew?'aria-current="page" disabled':''}>Utwórz nową ${marketing?'kampanię':'wycieczkę'}</button></nav>`);
  if(isNew){newSourceForm({templateId,variant,kind,flow});return;}
  main.insertAdjacentHTML('beforeend',`<form id="source-form" class="panel">${selected?'':'<div id="source-picker"></div>'}<div id="source-summary"></div><div id="source-demo-option"></div><div class="actions"><button type="submit" class="primary" id="source-create" disabled>Kontynuuj do dokumentu</button><button type="button" id="edit-source" hidden>Edytuj ${marketing?'kampanię':'program wycieczki'}</button>${selected?`<button type="button" data-go="${base}">Zmień ${marketing?'kampanię':'wycieczkę'}</button>`:''}</div></form>`);
  const entries=(marketing?campaigns:trips).filter(x=>!selected||(x.trip_id||x.campaign_id)!==(selected.trip_id||selected.campaign_id));if(selected)entries.push(selected);
  let chosen=selected;
  function choose(source){
    chosen=source;$('#edit-source').hidden=!source;$('#source-create').disabled=!source;
    $('#source-summary').innerHTML=source?DocumentFlow.summary(source,kind):'';
    $('#source-demo-option').innerHTML='';
  }
  if(selected)choose(selected);
  else SourcePicker.mount($('#source-picker'),{entries,kind,id:'source-select',category:SourcePicker.suggested[templateId],onChange:values=>choose(entries.find(x=>(x.trip_id||x.campaign_id)===values[0]))});
  $('#edit-source').onclick=()=>{
    if(flow.uncertain){message('Najpierw sprawdź wynik poprzedniego zapisu.',true);return;}
    if(chosen)navigate(`prepare-${kind}/${templateId}/${variant}/${chosen.trip_id||chosen.campaign_id}`+(flow.demo?'?demo=1':''));
  };
  $('#source-form').onsubmit=async event=>{
    event.preventDefault();if(busy||!chosen)return;
    if(flow.uncertain&&(chosen.trip_id||chosen.campaign_id)!==flow.sourceId){message('Najpierw sprawdź wynik poprzedniego zapisu.',true);return;}
    await createDocument(chosen,flow);
  };
}
function newSourceForm({templateId,variant,kind,flow,standalone=false}){
  const marketing=kind==='campaign',prepared=DocumentFlow.prepared;
  const previous=prepared&&(marketing?prepared.campaign_id:prepared.trip_id)?prepared:null;
  main.insertAdjacentHTML('beforeend',`<form id="source-form" class="panel"><div id="new-source"><h2>Podstawowe informacje</h2><label>Nazwa ${marketing?'kampanii':'wycieczki'} (wymagana)<input id="source-title" required maxlength="200" value="${e(previous?.title||(marketing?'Nowa kolekcja':'Nowa wycieczka'))}"></label>${marketing?`${standalone?'<label>Kompozycja kampanii<select id="source-variant"><option value="new_trips">Nowe kierunki</option><option value="theme_collection">Kolekcja tematyczna</option></select></label>':''}<div id="source-trip-picker"></div><label>Wspólny temat (opcjonalny)<input id="source-theme" maxlength="200" value="${e(previous?.theme||'')}"></label>`:`<label>Kierunek (możesz uzupełnić później)<input id="source-destination" maxlength="200" value="${e(previous?.destinations.join(', ')||'')}"></label><label>Liczba dni (wymagana)<input id="source-days" type="number" required min="1" max="60" value="${previous?.days.length||2}"></label>`}<details class="source-options"><summary>${marketing?'Pochodzenie danych':'Kategorie i pochodzenie danych'}</summary>${marketing?'':SourcePicker.categoryFields(previous?.categories||(SourcePicker.suggested[templateId]?[SourcePicker.suggested[templateId]]:[]),'source-categories')}${SourcePicker.originField(previous?.data_origin||'business','source-origin')}</details><p class="notice">To przygotowanie ${marketing?'kampanii':'programu'}. Na następnym ekranie uzupełnisz treść i jawnie ją zapiszesz. Dokument nie powstanie przy zapisie ${marketing?'kampanii':'wycieczki'}.</p></div><button type="submit" class="primary" id="source-create">Przygotuj ${marketing?'kampanię':'program'}</button></form>`);
  const tripPicker=marketing?SourcePicker.mount($('#source-trip-picker'),{entries:trips,id:'source-trips',multiple:true,selected:previous?.items.map(i=>i.trip_id)}):null;
  $('#source-form').addEventListener('input',()=>setDirty(true));
  $('#source-form').addEventListener('change',()=>setDirty(true));
  $('#source-form').onsubmit=event=>{
    event.preventDefault();if(busy||!$('#source-form').reportValidity())return;
    const title=$('#source-title').value.trim(),data_origin=$('#source-origin').value;
    if(!title){message('Uzupełnij nazwę.',true);return;}
    let source;
    if(marketing){
      if(!tripPicker.values.length){message('Wybierz co najmniej jedną wycieczkę.',true);return;}
      source={...(previous||{}),campaign_id:previous?.campaign_id||id(),title,data_origin,layout_variant:standalone?$('#source-variant').value:variant,theme:$('#source-theme').value,season:previous?.season||'',cta:previous?.cta||'',description:previous?.description||'',hero_asset_id:previous?.hero_asset_id||null,hero_position:previous?.hero_position||{x:50,y:50,zoom:1},leader:previous?.leader||null,items:tripPicker.values.map(trip_id=>previous?.items.find(i=>i.trip_id===trip_id)||({trip_id,display_title:'',short_hook:'',date_range_or_label:'Termin do ustalenia',highlights:[],image_asset_id:null,image_position:{x:50,y:50,zoom:1},badge:'concept',publication_status:'draft',leader:null}))};
    }else{
      const count=Number($('#source-days').value);if(!Number.isInteger(count)||count<1||count>60){message('Podaj od 1 do 60 dni.',true);return;}
      source=previous||newTrip();Object.assign(source,{title,data_origin,categories:[...main.querySelectorAll('[name="source-categories"]:checked')].map(x=>x.value),destinations:$('#source-destination').value.split(',').map(x=>x.trim()).filter(Boolean),duration_days:count,days:Array.from({length:count},(_,i)=>source.days[i]||({day_id:id(),day_number:i+1,title:'Dzień '+(i+1)+' — do opracowania',stops:[],public_description:'',internal_notes:''}))});
    }
    DocumentFlow.prepare(source);forward(standalone?'marketing/new':`prepare-${kind}/${templateId}/${variant}/new`);return;
  };
}
function newTrip(){return {trip_id:id(),title:'Nowa wycieczka',categories:[],data_origin:'business',destinations:[],description:'',start_date:null,end_date:null,duration_days:1,status:'draft',days:[{day_id:id(),day_number:1,title:'Rozpoczęcie podróży',stops:[],public_description:'',internal_notes:''}]};}

function renderTrip() {
  main.innerHTML = (preparation?DocumentFlow.steps(2,preparation):'')+`<button class="text-button back" data-go="${preparation?DocumentFlow.path(preparation):'trips'}">← ${preparation?'Wybór programu':'Wszystkie programy wycieczek'}</button>` + heading('EDYTOR WYCIECZKI', current.title, `${current.days.length} dni · ${creating?'Program wymaga zapisania':'Program zapisany'}`, '<button type="submit" form="trip-form" class="primary" id="save-trip">Zapisz program wycieczki</button>') +
    `<div class="editor-grid"><form id="trip-form"><section class="panel"><h2>Podstawowe informacje</h2><details class="source-options"><summary>Kategorie i pochodzenie danych</summary>${SourcePicker.categoryFields(current.categories)}${SourcePicker.originField(current.data_origin||'unknown','trip-origin')}</details><div class="fields"><div class="full">${input('Nazwa wycieczki','title',current.title,'text','required maxlength="200"')}</div><div class="full">${input('Kierunki (oddziel przecinkami)','destinations',current.destinations.join(', '),'text','maxlength="1000"')}</div><label>Status<select data-field="status">${Object.entries(statusLabels).map(([k,v])=>`<option value="${k}" ${current.status===k?'selected':''}>${v}</option>`).join('')}</select></label>${input('Data rozpoczęcia (opcjonalna)','start_date',current.start_date,'date')}<div class="full">${textarea('Opis wycieczki','description',current.description)}</div></div><p class="muted" id="date-summary">${dateSummary()}</p></section><section class="panel"><div class="section-heading"><div><p class="eyebrow">DZIEŃ PO DNIU</p><h2>Program podróży</h2></div><button type="button" id="add-day">+ Dodaj dzień</button></div><div id="days">${current.days.map(dayHTML).join('')}</div>${current.days.length ? '' : '<p class="muted">Dodaj pierwszy dzień programu.</p>'}</section></form>${preparation?'<aside class="panel document-tools"><h2>'+e(templates.find(t=>t.template_id===preparation.template)?.name)+'</h2><p>Uzupełnij program i zapisz go. Sam zapis nie tworzy dokumentu.</p><p id="source-completeness" class="muted"></p><button type="button" id="flow-continue" data-source-continue data-source-saved="'+(!creating)+'" '+(dirty||creating?'disabled':'')+'>Kontynuuj do dokumentu</button><button type="button" id="flow-pause">Zapisz program i wróć później</button></aside>':documentTools('trip')}</div>`;
  main.querySelector('.heading .muted').id='source-save-state';setDirty(dirty);
  $('#trip-form').addEventListener('submit', async event => {event.preventDefault(); await saveTrip();});
  $('#trip-form').addEventListener('input', updateTripField);
  main.querySelectorAll('[name="categories"]').forEach(field=>field.onchange=()=>{current.categories=[...main.querySelectorAll('[name="categories"]:checked')].map(x=>x.value);setDirty(true);});
  $('#trip-origin').onchange=()=>{current.data_origin=$('#trip-origin').value;setDirty(true);};
  if(preparation){
    $('#flow-continue').onclick=()=>{if(!dirty&&!creating)createDocument(current,preparation);};
    $('#flow-pause').onclick=async()=>{if((!dirty&&!creating)||await saveTrip()){forward('trips');message('Program zapisany. Dokument nie został utworzony.');}};
  }else setupDocumentTools('trip');
}
function dateSummary() {
  return current.start_date && current.days.length ? `Zakończenie: ${displayDate(endDate())}. Termin wynika z liczby dni programu.` : 'Termin do ustalenia. Liczba dni wynika z programu.';
}
function dateOffset(start, offset) { const date = new Date(start + 'T12:00:00Z'); date.setUTCDate(date.getUTCDate() + offset); return date.toISOString().slice(0,10); }
function endDate() { return current.start_date && current.days.length ? dateOffset(current.start_date,current.days.length-1) : null; }
function displayDate(date) { return date ? date.split('-').reverse().join('.') : 'Termin do ustalenia'; }
function dayHTML(day, index) {
  return `<section class="day" data-day="${index}"><div class="day-heading"><p class="day-label">DZIEŃ ${index+1}</p><button type="button" class="danger" data-remove-day="${index}">Usuń dzień</button></div><div class="fields"><div class="full">${input('Tytuł dnia',`days.${index}.title`,day.title,'text','required maxlength="200"')}</div><div class="full">${textarea('Opis dnia',`days.${index}.public_description`,day.public_description)}</div></div><div>${day.stops.map((s,si)=>`<div class="stop"><div class="stop-heading"><strong>Atrakcja ${si+1}</strong><button type="button" class="danger" data-remove-stop="${index}.${si}">Usuń atrakcję</button></div><div class="fields">${input('Nazwa',`days.${index}.stops.${si}.name`,s.name,'text','required maxlength="200"')}${input('Lokalizacja',`days.${index}.stops.${si}.location`,s.location)}<div class="full">${textarea('Opis atrakcji',`days.${index}.stops.${si}.description`,s.description)}</div></div><p class="muted">${e(s.verification_status === 'verified' ? 'Zweryfikowana' : s.verification_status === 'proposed' ? 'Propozycja — do weryfikacji' : s.verification_status === 'rejected' ? 'Odrzucona' : 'Niezweryfikowana')}${s.estimated_visit_duration_min ? ` · szacowany czas: ${s.estimated_visit_duration_min} min` : ''}</p></div>`).join('')}</div><button type="button" class="text-button" data-add-stop="${index}">+ Dodaj atrakcję</button></section>`;
}
function updateTripField(event) {
  const path = event.target.dataset.field; if (!path) return;
  const keys = path.split('.'); let target = current;
  for (const key of keys.slice(0,-1)) target = target[key];
  const key = keys.at(-1); let value = event.target.value;
  if (key === 'destinations') value = value.split(',').map(s=>s.trim()).filter(Boolean);
  if (key === 'start_date') value ||= null;
  target[key] = value; setDirty(true);
  if (key === 'start_date') $('#date-summary').textContent = dateSummary();
  $('#save-trip').textContent = 'Zapisz program wycieczki';
}
async function saveTrip() {
  if(busy||!$('#trip-form').reportValidity())return false;
  busy=true;main.inert=true;$('#save-trip').disabled=true;
  try{
    current.duration_days=current.days.length;current.end_date=endDate();
    current.days.forEach((day,i)=>{day.day_number=i+1;day.date=current.start_date?dateOffset(current.start_date,i):null;});
    if(creating){
      replaceRoute(preparation?`prepare-trip/${preparation.template}/${preparation.variant}/${current.trip_id}`:'trips/'+current.trip_id);
      current=await DocumentFlow.persistCreate('trips',current,api);
    }else current=await api('trips/'+current.trip_id,{method:'PUT',body:JSON.stringify(current)});
    creating=false;setDirty(false);
    let warning='';try{await refresh();}catch{warning=' Lista programów wymaga odświeżenia.';}
    if(preparation){preparation.sourceId=current.trip_id;replaceRoute(`prepare-trip/${preparation.template}/${preparation.variant}/${current.trip_id}`+(preparation.demo?'?demo=1':''));}
    else replaceRoute('trips/'+current.trip_id);
    renderTrip();message('Program wycieczki zapisany.'+warning,!!warning);return true;
  }catch(error){message(error.message,true);DocumentFlow.recovery(error,main);return false;}
  finally{busy=false;main.inert=false;if($('#save-trip'))$('#save-trip').disabled=false;}
}

function renderCampaign(campaign) {
  main.innerHTML = '<button class="text-button back" data-go="campaigns">← Wszystkie kampanie</button>' + heading('KAMPANIA',campaign.title,`${campaign.season} · ${campaign.items.length} kierunki`) + `<div class="editor-grid"><div><section class="panel"><p class="eyebrow">WSPÓLNY POMYSŁ</p><h2>${e(campaign.theme || 'Nowe kierunki')}</h2><p>${e(campaign.cta)}</p><div class="notice">Kampania łączy wycieczki we wspólną kolekcję. Z niej możesz przygotować niezależny materiał marketingowy.</div></section>${campaign.items.map(item=>{const trip=trips.find(t=>t.trip_id===item.trip_id);return `<article class="panel"><span class="tag">${e(item.date_range_or_label)}</span><h2>${e(trip?.title || item.trip_id)}</h2><p>${e(item.short_hook)}</p><p class="muted">${e(item.highlights.join(' · '))}</p><button data-go="trips/${e(item.trip_id)}">Otwórz wycieczkę →</button></article>`;}).join('')}</div>${documentTools('campaign')}</div>`;
  setupDocumentTools('campaign',campaign.campaign_id);
  if(!canEdit)return;
  const edit = document.createElement('button');
  edit.className = 'primary'; edit.dataset.go = 'marketing/' + campaign.campaign_id;
  edit.textContent = 'Edytuj kampanię';
  main.querySelector('.heading').append(edit);
}
function setupDocumentTools(sourceType,sourceId) {
  if(!canEdit)return;
  if(sourceType==='trip')$('#create-draft').disabled=dirty||creating;
  $('#create-draft').onclick=()=>{
    if(busy)return;
    if(dirty||sourceType==='trip'&&creating){message('Najpierw zapisz program wycieczki. Zapis nie utworzy dokumentu.',true);return;}
    DocumentFlow.reset();navigate(`templates/${sourceType}/${sourceId||current.trip_id}`);
  };
}

function snapshotHTML(trip) {
  return `<section class="panel"><p class="eyebrow">DANE WYCIECZKI · REWIZJA ${trip.revision}</p><h2>${e(trip.title)}</h2><p>${e(trip.description)}</p><p class="muted">${e(trip.destinations.join(' · '))} · ${trip.duration_days} dni · ${e(displayDate(trip.start_date))}</p>${trip.days.map(d=>`<section class="snapshot-day"><p class="day-label">DZIEŃ ${d.day_number}</p><h3>${e(d.title)}</h3><p class="notes">${e(d.public_description)}</p><ul>${d.stops.map(s=>`<li><strong>${e(s.name)}</strong> — ${e(s.location)}<br>${e(s.description)} <span class="tag">${e(s.verification_status)}</span></li>`).join('')}</ul>${d.internal_notes?`<p class="notes">Notatka wewnętrzna: ${e(d.internal_notes)}</p>`:''}</section>`).join('')}</section>`;
}
function renderDraft(draft) {
  const template=templates.find(t=>t.template_id===draft.template_id);
  main.innerHTML = '<button class="text-button back" data-go="drafts">← Dokumenty robocze</button>' + heading('ZAPISANY DOKUMENT',draft.title,template?.name || draft.template_id) + `<section class="panel draft-header"><div class="meta"><span class="tag">Wersja robocza</span><span>Szablon ${e(draft.template_version)}</span><span>Poufność: ${e(draft.confidentiality)}</span><span>${e(new Date(draft.created_at).toLocaleString('pl-PL'))}</span></div><p class="notice">Podgląd danych roboczych. Dokument nie jest gotowy do publikacji. Cena, rezerwacje, logistyka, źródła i prawa do zdjęć wymagają osobnego uzupełnienia oraz weryfikacji.</p>${draft.editorial_notes ? `<h3>Notatka redakcyjna</h3><p class="notes">${e(draft.editorial_notes)}</p>` : ''}</section>${draft.campaign_snapshot?`<section class="panel"><h2>${e(draft.campaign_snapshot.title)}</h2><p>${e(draft.campaign_snapshot.cta)}</p>${draft.campaign_snapshot.items.map(i=>`<p><strong>${e(i.short_hook)}</strong> · ${e(i.date_range_or_label)}</p>`).join('')}</section>`:''}${(draft.trip_snapshot?[draft.trip_snapshot]:draft.campaign_trip_snapshots).map(snapshotHTML).join('')}`;
  if (draft.template_id === 'marketing.collection') {
    const actions = document.createElement('div'); actions.className = 'actions marketing-document-actions';
    for (const [format,label] of [['a4','Podgląd A4 / PDF'],['social','Układ 1080 × 1350']]) {
      const link = document.createElement('a');
      link.href = `/api/document-studio/drafts/${encodeURIComponent(draft.document_id)}/preview?output_format=${format}`;
      link.target = '_blank'; link.rel = 'noopener'; link.textContent = label; actions.append(link);
    }
    main.querySelector('.heading').after(actions);
  }
  if (templates.some(t=>t.template_id===draft.template_id)) {
    const actions = document.createElement('div'); actions.className = 'actions marketing-document-actions';
    const button=document.createElement('button');button.className='primary';button.dataset.go='edit-draft/'+draft.document_id;button.textContent='Edytuj dokument';button.disabled=draft.document_status==='archived'||!canEdit;
    const link=document.createElement('a');link.href=`/api/document-studio/drafts/${draft.document_id}/preview`;link.target='_blank';link.rel='noopener';link.textContent='Podgląd A4 / PDF';
    actions.append(button,link);main.querySelector('.heading').after(actions);
  }
}
async function reviewDocument(draft,isCurrent) {
  const source=draft.trip_snapshot||draft.campaign_snapshot,kind=draft.trip_snapshot?'trip':'campaign';
  const flow={template:draft.template_id,variant:draft.layout_variant,kind,sourceId:source.trip_id||source.campaign_id};
  const name=templates.find(t=>t.template_id===draft.template_id)?.name||'Dokument';
  main.innerHTML=DocumentFlow.steps(4,flow,draft.document_id)+heading('SPRAWDZENIE I ZAPIS',draft.title,name,
    `<div class="actions"><button data-go="edit-draft/${draft.document_id}" ${draft.document_status==='archived'||!canEdit?'disabled':''}>Wróć do edycji</button><button data-go="drafts">Biblioteka dokumentów</button></div>`)+
    `<section class="panel flow-review-state"><h2>Ostatni zapis</h2><p>Zapisano: ${e(new Date(draft.updated_at).toLocaleString('pl-PL'))}. ${draft.document_status==='archived'?'Dokument zarchiwizowany.':''}</p><p>Status biznesowy: ${e({draft:'Roboczy',in_review:'Do przeglądu',ready:'Gotowy do użycia',archived:'Archiwum'}[draft.document_status])}. Status nie oznacza formalnego zatwierdzenia.</p><details><summary>Informacje o zapisie</summary><p>Numer zapisu: ${draft.revision} · ${e(draft.template_id)} · ${e(draft.confidentiality)}</p></details><div id="review-validation" role="status">Sprawdzanie wymaganych pól…</div></section>`+
    DocumentFlow.summary({...source,title:kind==='campaign'?(campaigns.find(c=>c.campaign_id===source.campaign_id)?.title||source.title):source.title},kind)+`<section class="panel"><div class="actions">${draft.template_id==='marketing.collection'?'<label>Format<select id="review-format"><option value="a4">A4</option><option value="social">1080 × 1350</option></select></label>':''}<a class="button-link primary" id="review-export" target="_blank" rel="noopener">Podgląd i eksport PDF</a></div><p>Sprawdzasz zapisany dokument. Eksport nie jest archiwizacją PDF ani zgodą na publikację.</p><p id="review-preview-state" role="status"></p><iframe id="review-preview" title="Podgląd zapisanego dokumentu"></iframe></section>`;
  let previewVersion=0;
  const format=$('#review-format'),show=async()=>{
    const version=++previewVersion;
    const url=`/api/document-studio/library/${draft.document_id}/revisions/${draft.revision}/preview?output_format=${format?.value||'a4'}`;
    $('#review-export').href=url;$('#review-preview-state').textContent='Ładowanie podglądu…';
    try{
      const response=await fetch(url,{cache:'no-store'});
      if(!response.ok)throw new Error('Nie udało się pobrać podglądu ('+response.status+').');
      const html=await response.text();if(!isCurrent()||version!==previewVersion)return;
      // Same srcdoc embedding as the editors; keep cloud X-Frame-Options: DENY.
      // A fresh frame also avoids format changes adding browser history entries.
      const frame=$('#review-preview'),replacement=frame.cloneNode(false);frame.replaceWith(replacement);DocumentFlow.embeddedPreview(replacement,html);
      $('#review-preview-state').textContent='';
    }catch(error){if(isCurrent()&&version===previewVersion)$('#review-preview-state').textContent=error.message;}
  };
  if(format)format.onchange=show;show();
  if(!canEdit){$('#review-validation').textContent='Dostęp tylko do odczytu. Uwagi i możliwość druku sprawdzisz w podglądzie poniżej.';return;}
  try{
    const issues=await api('trip-documents/validate',{method:'POST',body:JSON.stringify({draft})});if(!isCurrent())return;
    const errors=issues.filter(i=>i.severity==='error');
    $('#review-validation').innerHTML=`<p>${errors.length?'Wymaga uzupełnienia: '+errors.length:'Brak błędów walidacji danych. Nadal sprawdź treść i układ.'}</p><details ${errors.length?'open':''}><summary>Uwagi do dokumentu: ${issues.length}</summary><ul>${issues.map(i=>`<li class="${i.severity}">${e(i.message)}</li>`).join('')}</ul></details>`;
  }catch(error){if(isCurrent())$('#review-validation').textContent='Nie udało się pobrać listy uwag. Sprawdź je w podglądzie dokumentu. '+error.message;}
}
async function exampleCatalog(identifier, load, context) {
  const entries=await load('examples');
  if(!identifier){
    main.innerHTML=heading('DANE FIKCYJNE','Przykładowe dokumenty DEMO','Dziewięć kompletnych przykładów. Otwórz podgląd, następnie utwórz własną kopię.')+`<div class="cards">${entries.map(x=>`<article class="card" data-example-id="${e(x.example_id)}"><span class="tag">${e(x.example_id)} · DEMO</span><h2>${e(x.title)}</h2><p>${e(x.template_id)} · ${e(x.layout_variant)}</p><p>PRZYKŁAD DEMO — DANE FIKCYJNE</p><button data-go="examples/${e(x.example_id)}">Otwórz przykład</button></article>`).join('')}</div>`;
    return;
  }
  const item=entries.find(x=>x.example_id===identifier);if(!item)throw new Error('Nie znaleziono przykładu.');
  main.innerHTML=heading('PRZYKŁAD DEMO — DANE FIKCYJNE',item.title,'Chroniony wzorzec. Edycja odbywa się na niezależnej kopii.','<button data-go="examples">← Przykłady</button>')+`<section class="panel"><p>${e(item.template_id)} · ${e(item.layout_variant)}</p>${canEdit?'<button id="copy-example" class="primary">Utwórz kopię do edycji</button>':''}<a target="_blank" rel="noopener" href="/api/document-studio/examples/${encodeURIComponent(identifier)}/preview">Podgląd / PDF</a></section><iframe id="example-preview" title="Podgląd przykładu DEMO" style="width:100%;height:75vh"></iframe>`;
  const response=await fetch('/api/document-studio/examples/'+encodeURIComponent(identifier)+'/preview');
  if(!response.ok)throw new Error('Nie udało się otworzyć podglądu.');
  const html=await response.text();if(!context.isCurrent())return;DocumentFlow.embeddedPreview($('#example-preview'),html);
  const operation_id=crypto.randomUUID();
  if($('#copy-example'))$('#copy-example').onclick=async()=>{
    if(busy)return;busy=true;$('#copy-example').disabled=true;
    try{const copy=await api('examples/'+encodeURIComponent(identifier)+'/copy',{method:'POST',body:JSON.stringify({operation_id})});await refresh();busy=false;forward('edit-draft/'+copy.document_id);}
    catch(error){message(error.message,true);}finally{busy=false;if($('#copy-example'))$('#copy-example').disabled=false;}
  };
}

async function route() {
  if(busy){history.replaceState(null,'',location.pathname+activeHash);return;}
  if(dirty&&!confirm('Masz niezapisane zmiany. Opuścić ten widok?')){history.replaceState(null,'',location.pathname+activeHash);return;}
  activeHash=location.hash;const version=++routeGeneration;
  const isCurrent=()=>version===routeGeneration;
  const load=async path=>{const value=await api(path);if(!isCurrent())throw new Error('Stale navigation');return value;};
  const [raw,query='']=location.hash.slice(1).split('?'),parts=raw.split('/'),options=Object.fromEntries(new URLSearchParams(query));
  options.demo=options.demo==='1';
  const view=parts[0]||(canEdit?'templates':'drafts'),resourceId=parts[1];dirty=false;current=null;preparation=null;
  const nav=['prepare-trip','prepare-campaign','create-document'].includes(view)?'templates':view==='marketing'?'campaigns':['edit-draft','review-draft','revisions'].includes(view)?'drafts':view;
  document.querySelectorAll('[data-nav]').forEach(button=>button.classList.toggle('active',button.dataset.nav===nav));
  const context={main,escape:e,api,message,refresh,dirty:setDirty,isDirty:()=>dirty,busy:value=>busy=value,isCurrent,persistCreate:(kind,value)=>DocumentFlow.persistCreate(kind,value,api),recovery:error=>DocumentFlow.recovery(error,main)};
  try{
    if(!canEdit&&['templates','create-document','prepare-trip','prepare-campaign'].includes(view)){forward('drafts');return;}
    if(!canEdit&&view==='edit-draft'){forward('review-draft/'+resourceId);return;}
    if(!canEdit&&view==='marketing'){forward('campaigns/'+resourceId);return;}
    if(!['templates','create-document','prepare-trip','prepare-campaign','trips','campaigns','drafts','marketing','edit-draft','review-draft','revisions','examples'].includes(view))throw new Error('Nie znaleziono widoku.');
    if(view==='examples')await exampleCatalog(resourceId,load,context);
    else if(view==='templates'){
      const fixed=parts[1]&&parts[2]?await load((parts[1]==='trip'?'trips/':'campaigns/')+encodeURIComponent(parts[2])):null;
      templateCatalog(fixed);
    }
    else if(view==='create-document'){
      const template=templates.find(t=>t.template_id===resourceId),variant=parts[2]||'standard';
      if(!template||!template.layout_variants.includes(variant)||parts[3]&&parts[3]!==template.source_type)throw new Error('Nieprawidłowy rodzaj lub źródło dokumentu.');
      if(options.rev&&(!Number.isInteger(Number(options.rev))||Number(options.rev)<1))throw new Error('Nieprawidłowy link do zapisu.');
      if(options.attempt){
        try{
          const stored=await load('drafts/'+encodeURIComponent(options.attempt)),source=stored.trip_snapshot||stored.campaign_snapshot;
          if(stored.template_id!==resourceId||(source.trip_id||source.campaign_id)!==parts[4])throw new Error('Ten zapis dotyczy innego programu. Sprawdź bibliotekę.');
          forward('edit-draft/'+stored.document_id);return;
        }catch(error){if(error.status!==404)throw error;}
      }
      const selected=parts[4]?await load((template.source_type==='trip'?'trips/':'campaigns/')+encodeURIComponent(parts[4])):null;
      sourceChooser(resourceId,variant,selected,options);
    }
    else if(view==='drafts'&&!resourceId)await DocumentLibraryUI.open({main,escape:e,api,templates,message,refresh,canEdit,busy:value=>busy=value});
    else if(view==='revisions'&&resourceId)await DocumentLibraryUI.history(resourceId,{main,escape:e,api:load});
    else if(view==='prepare-trip'||view==='prepare-campaign'){
      const kind=view==='prepare-trip'?'trip':'campaign',template=templates.find(t=>t.template_id===resourceId),variant=parts[2],identifier=parts[3];
      if(!template||template.source_type!==kind||!template.layout_variants.includes(variant)||!identifier)throw new Error('Nieprawidłowy link przygotowania programu.');
      if(identifier==='new')options.mode='new';
      preparation=DocumentFlow.configure(resourceId,variant,kind,identifier==='new'?undefined:identifier,options);
      if(kind==='trip'){
        creating=identifier==='new';if(creating&&!DocumentFlow.prepared?.trip_id)throw new Error('Program nie został zapisany. Wróć do wyboru wycieczki i przygotuj nowy program.');
        current=creating?DocumentFlow.prepared:await load('trips/'+encodeURIComponent(identifier));
        if(creating)DocumentFlow.prepare(current);dirty=creating;renderTrip();
      }else{
        const fresh=identifier==='new';
        if(fresh&&!DocumentFlow.prepared?.campaign_id)throw new Error('Kampania nie została zapisana. Wróć do wyboru kampanii i przygotuj nową.');
        const source=fresh?DocumentFlow.prepared:await load('campaigns/'+encodeURIComponent(identifier));
        if(fresh)DocumentFlow.prepare(source);
        const flow=preparation;
        await MarketingEditor.open(source,trips,{...context,creating:fresh,flow,
          sourceSaved:campaign=>{flow.sourceId=campaign.campaign_id;replaceRoute(`prepare-campaign/${flow.template}/${flow.variant}/${campaign.campaign_id}`);},
          continueSource:campaign=>createDocument(campaign,flow),pause:()=>{forward('campaigns');message('Kampania zapisana. Dokument nie został utworzony.');}});
        if(fresh)setDirty(true);
      }
    }
    else if(view==='campaigns'&&resourceId==='new'){
      if(!canEdit){forward('campaigns');return;}
      DocumentFlow.reset();main.innerHTML=heading('KAMPANIE MARKETINGOWE','Nowa kampania','Wybierz wycieczki dla wspólnej kolekcji. Dokument możesz utworzyć później.','<button data-go="campaigns">← Kampanie</button>');
      newSourceForm({kind:'campaign',standalone:true});
    }
    else if(!resourceId)cards(view);
    else if(view==='trips'){
      if(!canEdit&&resourceId==='new'){forward('trips');return;}
      creating=resourceId==='new';current=creating?newTrip():await load('trips/'+encodeURIComponent(resourceId));renderTrip();if(creating)setDirty(true);
      if(!canEdit){main.insertAdjacentHTML('afterbegin','<p class="notice">Dostęp tylko do odczytu.</p>');main.querySelectorAll('input,textarea,select,button').forEach(el=>{if(!el.dataset.go)el.disabled=true;});$('#save-trip').hidden=true;}
    }
    else if(view==='marketing')await MarketingEditor.open(resourceId==='new'?(DocumentFlow.prepared?.campaign_id?DocumentFlow.prepared:(()=>{throw new Error('Niezapisana kampania nie jest dostępna po odświeżeniu. Utwórz nową kampanię z biblioteki.');})()):await load('campaigns/'+encodeURIComponent(resourceId)),trips,{...context,creating:resourceId==='new',sourceSaved:campaign=>replaceRoute('marketing/'+campaign.campaign_id),pause:()=>forward('campaigns'),
      continueSource:campaign=>navigate('templates/campaign/'+campaign.campaign_id)});
    else if(view==='edit-draft'){
      const draft=await load('drafts/'+encodeURIComponent(resourceId));
      if(draft.document_status==='archived')throw new Error('Przywróć dokument z archiwum przed edycją. Podgląd znajdziesz w bibliotece.');
      const editorContext={...context,sourceTitle:draft.campaign_snapshot?campaigns.find(c=>c.campaign_id===draft.campaign_snapshot.campaign_id)?.title:null,review:()=>forward('review-draft/'+draft.document_id)};
      if(draft.template_id==='marketing.collection')await MarketingEditor.open(draft.campaign_snapshot,trips,{...editorContext,draft});
      else await TripDocumentEditor.open(draft,editorContext);
    }
    else if(view==='review-draft')await reviewDocument(await load('drafts/'+encodeURIComponent(resourceId)),isCurrent);
    else if(view==='campaigns')renderCampaign(await load('campaigns/'+encodeURIComponent(resourceId)));
    else renderDraft(await load('drafts/'+encodeURIComponent(resourceId)));
    if(isCurrent())DocumentFlow.focus(main);
  }catch(error){if(!isCurrent())return;main.innerHTML='<section class="panel"><h1>Nie udało się otworzyć danych</h1><p>'+e(error.message)+'</p><button data-go="drafts">Wróć do biblioteki</button></section>';DocumentFlow.focus(main);}
}

document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.nav)navigate(button.dataset.nav);
  if(button.dataset.go)navigate(button.dataset.go);
  if(!current || busy)return;
  if(button.id==='add-day'){current.days.push({day_id:id(),day_number:current.days.length+1,title:'Nowy dzień',stops:[],public_description:'',internal_notes:''});setDirty(true);renderTrip();}
  if(button.dataset.removeDay!==undefined && confirm('Usunąć dzień wraz z jego atrakcjami?')){current.days.splice(Number(button.dataset.removeDay),1);setDirty(true);renderTrip();}
  if(button.dataset.addStop!==undefined){current.days[Number(button.dataset.addStop)].stops.push({stop_id:id(),name:'Nowa atrakcja',location:'',description:'',verification_status:'unverified'});setDirty(true);renderTrip();}
  if(button.dataset.removeStop!==undefined){const [d,s]=button.dataset.removeStop.split('.').map(Number);current.days[d].stops.splice(s,1);setDirty(true);renderTrip();}
});
window.addEventListener('hashchange',route);
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
refresh().then(route).catch(error=>{main.innerHTML='<section class="panel"><h1>Studio jest niedostępne</h1><p>'+e(error.message)+'</p><button onclick="location.reload()">Spróbuj ponownie</button></section>';});
