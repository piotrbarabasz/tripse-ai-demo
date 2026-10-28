/* Local, dependency-free editor. User text is escaped before inserting HTML. */
const $ = s => document.querySelector(s);
const main = $('#main');
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const e = escapeHTML;
const id = () => crypto.randomUUID().replaceAll('-', '');
let trips = [], campaigns = [], drafts = [], templates = [], current = null, dirty = false, creating = false, busy = false;
let messageTimer, activeHash = '';
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
    throw new Error(Array.isArray(detail) ? detail.map(x => `${x.loc.slice(1).join('.')}: ${x.msg}`).join('; ') : detail || 'Nie udało się wykonać operacji.');
  }
  return data;
}
async function refresh() {
  [trips, campaigns, drafts, templates] = await Promise.all(['trips','campaigns','drafts','templates'].map(x => api(x)));
  $('#trip-count').textContent = trips.length; $('#campaign-count').textContent = campaigns.length; $('#draft-count').textContent = drafts.length;
}
function navigate(path) {
  if (busy) return;
  if (dirty && !confirm('Masz niezapisane zmiany. Opuścić wycieczkę?')) return;
  dirty = false;
  if (location.hash === '#' + path) route(); else location.hash = path;
}
function heading(kicker, title, subtitle, action = '') {
  return `<div class="heading"><div><p class="eyebrow">${kicker}</p><h1>${e(title)}</h1><p class="muted">${e(subtitle)}</p></div>${action}</div>`;
}
const statusLabels = {idea:'Pomysł', draft:'Wersja robocza', planned:'Zaplanowana', confirmed:'Potwierdzona', completed:'Zakończona', cancelled:'Anulowana'};
function cards(view) {
  const entries = view === 'trips' ? trips : view === 'campaigns' ? campaigns : drafts;
  const names = {trips:['BIBLIOTEKA PODRÓŻY','Twoje wycieczki','Jeden program. Wiele możliwości dokumentu.'],campaigns:['KOLEKCJE KIERUNKÓW','Kampanie','Kilka podróży połączonych jednym pomysłem.'],drafts:['ZAPISANE SNAPSHOTY','Dokumenty robocze','Zachowane dane źródłowe i wybrany typ dokumentu.']};
  main.innerHTML = heading(...names[view], view === 'trips' ? '<button class="primary" data-go="trips/new">+ Nowa wycieczka</button>' : '') +
    `<div class="cards">${entries.map(x => {
      const resourceId = x.trip_id || x.campaign_id || x.document_id;
      const label = view === 'trips' ? x.destinations.join(' · ') || 'Nowy kierunek' : view === 'campaigns' ? x.season || 'Kolekcja' : templates.find(t=>t.template_id===x.template_id)?.name || x.template_id;
      const description = view === 'trips' ? x.description : view === 'campaigns' ? x.items.map(i=>trips.find(t=>t.trip_id===i.trip_id)?.title || i.trip_id).join(' · ') : 'Niezależny snapshot danych. Źródłowa wycieczka może być dalej edytowana.';
      return `<article class="card"><div class="card-top">${e(label)}</div><span class="tag">${view === 'trips' ? `${x.duration_days} dni · ${e(statusLabels[x.status])}` : view === 'campaigns' ? `${x.items.length} kierunki` : 'Wersja robocza'}</span><h2>${e(x.title)}</h2><p class="muted">${e(description)}</p><button class="open" data-go="${view}/${e(resourceId)}">Otwórz →</button></article>`;
    }).join('')}</div>${entries.length ? '' : '<div class="panel empty">Nie ma jeszcze zapisanych dokumentów. Otwórz wycieczkę lub kampanię i wybierz typ dokumentu.</div>'}`;
}
function input(label, field, value, type = 'text', extra = '') {
  return `<label>${label}<input data-field="${field}" type="${type}" value="${e(value)}" ${extra}></label>`;
}
function textarea(label, field, value) {
  return `<label>${label}<textarea data-field="${field}" maxlength="20000">${e(value)}</textarea></label>`;
}
function documentTools(sourceType) {
  const options = templates.filter(t => t.source_type === sourceType);
  return `<aside class="panel document-tools"><p class="eyebrow">NASTĘPNY KROK</p><h2>Utwórz dokument</h2><label>Typ dokumentu<select id="template">${options.map(t=>`<option value="${e(t.template_id)}">${e(t.name)}</option>`).join('')}</select></label><p id="template-description" class="muted"></p><label id="variant-label" ${sourceType === 'trip' ? 'hidden' : ''}>Wariant<select id="variant">${(options[0]?.layout_variants || []).map(v=>`<option value="${e(v)}">${v==='new_trips'?'Nowe kierunki':v==='theme_collection'?'Kolekcja tematyczna':'Standard'}</option>`).join('')}</select></label><label>Notatka do dokumentu<textarea id="editorial-notes" maxlength="20000" placeholder="Opcjonalna uwaga redakcyjna"></textarea></label><div class="notice">Zapiszemy wersję roboczą ze snapshotem danych. Wszystkie osiem typów ma edytor sekcji i podgląd roboczy. Oferta indywidualna zachowuje kontrolę ceny i eksportu.</div><button class="accent" id="create-draft">Zapisz dokument roboczy</button><small>Wycieczka zostanie najpierw zapisana, jeśli zawiera zmiany.</small></aside>`;
}
function templateCatalog() {
  const groups=[['offer','Typy ofert','↗'],['pilot','Rozpiski dla pilotów','▤'],['marketing','Oferty marketingowe','◈']];
  main.innerHTML=heading('DOCUMENT STUDIO','Co chcesz przygotować?','Wybierz rodzaj dokumentu, a następnie wycieczkę lub kampanię.')+groups.map(([family,label,icon])=>`<section class="template-group"><h2>${label}</h2><div class="template-row">${templates.filter(t=>t.family===family).map(t=>`<article class="card template-card"><span class="template-icon" aria-hidden="true">${icon}</span><h3>${e(t.name)}</h3><p>${e(t.description)}</p>${family==='marketing'?'<label>Wariant<select class="catalog-variant"><option value="new_trips">Nowości / nowe kierunki</option><option value="theme_collection">Kolekcja tematyczna</option></select></label>':''}<button class="primary" data-create-template="${e(t.template_id)}">Utwórz dokument</button></article>`).join('')}</div></section>`).join('');
  for(const button of main.querySelectorAll('[data-create-template]'))button.onclick=()=>navigate('create-document/'+button.dataset.createTemplate+'/'+(button.closest('article').querySelector('select')?.value||'standard'));
}
function sourceChooser(templateId,variant) {
  const template=templates.find(t=>t.template_id===templateId);
  if(!template||!template.layout_variants.includes(variant))throw new Error('Nieprawidłowy typ lub wariant dokumentu.');
  const marketing=template.source_type==='campaign', entries=marketing?campaigns:trips;
  main.innerHTML=heading('NOWY DOKUMENT',template.name,'Typ dokumentu jest już wybrany. Wybierz źródło danych.','<button data-go="templates">← Katalog</button>')+`<form id="source-form" class="panel"><p>${e(template.description)}</p><label>${marketing?'Kampania':'Wycieczka'}<select id="source-select">${entries.map(x=>`<option value="${e(x.campaign_id||x.trip_id)}">${e(x.title)}</option>`).join('')}<option value="new">+ Utwórz nową ${marketing?'kampanię':'wycieczkę'}</option></select></label><div id="new-source" hidden><label>Nazwa<input id="source-title" maxlength="200" value="${marketing?'Nowa kolekcja':'Nowa wycieczka'}"></label>${marketing?`<label>Wycieczki do kolekcji<select id="source-trips" multiple>${trips.map(t=>`<option value="${t.trip_id}">${e(t.title)}</option>`).join('')}</select></label><label>Wspólny temat<input id="source-theme" maxlength="200"></label>`:'<label>Kierunek<input id="source-destination" maxlength="200"></label><label>Liczba dni<input id="source-days" type="number" min="1" max="60" value="2"></label>'}</div><button class="primary" id="source-create">Utwórz i otwórz edytor</button><p class="muted">Nieznane daty, ceny i rezerwacje pozostaną nieustalone.</p></form>`;
  const select=$('#source-select');select.onchange=()=>{$('#new-source').hidden=select.value!=='new';};select.onchange();
  $('#source-form').onsubmit=async event=>{
    event.preventDefault();if(busy)return;busy=true;$('#source-create').disabled=true;
    try {
      let sourceId=select.value;
      if(sourceId==='new') {
        const title=$('#source-title').value.trim();if(!title)throw new Error('Uzupełnij nazwę.');
        if(marketing) {
          const selected=[...$('#source-trips').selectedOptions].map(o=>o.value);if(!selected.length)throw new Error('Wybierz co najmniej jedną wycieczkę.');
          const source=await api('campaigns',{method:'POST',body:JSON.stringify({title,theme:$('#source-theme').value,layout_variant:variant,cta:'Kontakt do uzupełnienia — wersja robocza',items:selected.map(trip_id=>({trip_id}))})});sourceId=source.campaign_id;
        } else {
          const count=Number($('#source-days').value);if(!Number.isInteger(count)||count<1||count>60)throw new Error('Podaj od 1 do 60 dni.');
          const destination=$('#source-destination').value.trim();
          const source=await api('trips',{method:'POST',body:JSON.stringify({title,destinations:destination?[destination]:[],duration_days:count,days:Array.from({length:count},(_,i)=>({day_number:i+1,title:'Dzień '+(i+1)+' — do opracowania'}))})});sourceId=source.trip_id;
        }
        // Keep the created source selected if draft creation fails, avoiding duplicates.
        await refresh();select.add(new Option(title,sourceId));select.value=sourceId;select.onchange();
      }
      const draft=await api('drafts',{method:'POST',body:JSON.stringify({template_id:templateId,source_type:template.source_type,source_id:sourceId,layout_variant:variant})});
      await refresh();busy=false;navigate('edit-draft/'+draft.document_id);
    }catch(error){message(error.message,true);}finally{busy=false;if($('#source-create'))$('#source-create').disabled=false;}
  };
}

function renderTrip() {
  main.innerHTML = `<button class="text-button back" data-go="trips">← Wszystkie wycieczki</button>` + heading('EDYTOR WYCIECZKI', current.title, `${current.days.length} dni · ${creating ? 'Nowa wycieczka' : 'Rewizja ' + current.revision}`, '<button type="submit" form="trip-form" class="primary" id="save-trip">Zapisz wycieczkę</button>') +
    `<div class="editor-grid"><form id="trip-form"><section class="panel"><h2>Podstawowe informacje</h2><div class="fields"><div class="full">${input('Nazwa wycieczki','title',current.title,'text','required maxlength="200"')}</div><div class="full">${input('Kierunki (oddziel przecinkami)','destinations',current.destinations.join(', '),'text','maxlength="1000"')}</div><label>Status<select data-field="status">${Object.entries(statusLabels).map(([k,v])=>`<option value="${k}" ${current.status===k?'selected':''}>${v}</option>`).join('')}</select></label>${input('Data rozpoczęcia (opcjonalna)','start_date',current.start_date,'date')}<div class="full">${textarea('Opis wycieczki','description',current.description)}</div></div><p class="muted" id="date-summary">${dateSummary()}</p></section><section class="panel"><div class="section-heading"><div><p class="eyebrow">DZIEŃ PO DNIU</p><h2>Program podróży</h2></div><button type="button" id="add-day">+ Dodaj dzień</button></div><div id="days">${current.days.map(dayHTML).join('')}</div>${current.days.length ? '' : '<p class="muted">Dodaj pierwszy dzień programu.</p>'}</section></form>${documentTools('trip')}</div>`;
  $('#trip-form').addEventListener('submit', async event => {event.preventDefault(); await saveTrip();});
  $('#trip-form').addEventListener('input', updateTripField);
  setupDocumentTools('trip');
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
  target[key] = value; dirty = true;
  if (key === 'start_date') $('#date-summary').textContent = dateSummary();
  $('#save-trip').textContent = 'Zapisz zmiany';
}
async function saveTrip() {
  if (busy || !$('#trip-form').reportValidity()) return false;
  busy = true; $('#save-trip').disabled = true;
  try {
    current.duration_days = current.days.length; current.end_date = endDate();
    current.days.forEach((d,i)=> {d.day_number = i+1; d.date = current.start_date ? dateOffset(current.start_date,i) : null;});
    current = await api('trips' + (creating ? '' : '/' + current.trip_id), {method:creating ? 'POST' : 'PUT',body:JSON.stringify(current)});
    creating = false; dirty = false; await refresh();
    history.replaceState(null,'','#trips/' + current.trip_id); renderTrip(); message('Wycieczka zapisana.'); return true;
  } catch(error) {message(error.message,true); return false;}
  finally {busy = false; if ($('#save-trip')) $('#save-trip').disabled = false;}
}
function renderCampaign(campaign) {
  main.innerHTML = '<button class="text-button back" data-go="campaigns">← Wszystkie kampanie</button>' + heading('KAMPANIA',campaign.title,`${campaign.season} · ${campaign.items.length} kierunki`) + `<div class="editor-grid"><div><section class="panel"><p class="eyebrow">WSPÓLNY POMYSŁ</p><h2>${e(campaign.theme || 'Nowe kierunki')}</h2><p>${e(campaign.cta)}</p><div class="notice">Kampania demonstracyjna. Terminy, opisy i programy są fikcyjne; zdjęcia nie zostały dodane.</div></section>${campaign.items.map(item=>{const trip=trips.find(t=>t.trip_id===item.trip_id);return `<article class="panel"><span class="tag">${e(item.date_range_or_label)}</span><h2>${e(trip?.title || item.trip_id)}</h2><p>${e(item.short_hook)}</p><p class="muted">${e(item.highlights.join(' · '))}</p><button data-go="trips/${e(item.trip_id)}">Otwórz wycieczkę →</button></article>`;}).join('')}</div>${documentTools('campaign')}</div>`;
  setupDocumentTools('campaign',campaign.campaign_id);
  const edit = document.createElement('button');
  edit.className = 'primary'; edit.dataset.go = 'marketing/' + campaign.campaign_id;
  edit.textContent = 'Edytuj kolekcję / podgląd PDF';
  main.querySelector('.heading').append(edit);
}
function setupDocumentTools(sourceType, sourceId) {
  if (sourceType === 'trip' && current?.trip_id === 'demo-iceland') {
    const label = document.createElement('label'); label.className = 'demo-preset';
    label.innerHTML = '<input type="checkbox" id="demo-example">Wypełnij fikcyjnym przykładem DEMO (oferta / rozpiska podstawowa)';
    $('#create-draft').before(label);
  }
  const description = () => $('#template-description').textContent = templates.find(t=>t.template_id===$('#template').value)?.description || '';
  $('#template').addEventListener('change',description); description();
  $('#create-draft').addEventListener('click',async () => {
    if (busy) return;
    const templateId=$('#template').value, variant=$('#variant').value, notes=$('#editorial-notes').value;
    const demoExample = !!$('#demo-example')?.checked && ['offer.private','pilot.basic'].includes(templateId);
    if (sourceType==='trip' && (dirty || creating) && !await saveTrip()) return;
    busy = true; $('#create-draft').disabled = true;
    try {
      const draft = await api('drafts',{method:'POST',body:JSON.stringify({template_id:templateId,source_type:sourceType,source_id:sourceId || current.trip_id,layout_variant:variant,editorial_notes:notes,demo_example:demoExample})});
      await refresh(); busy=false; navigate('drafts/' + draft.document_id); message('Dokument roboczy zapisany ze snapshotem danych.');
    } catch(error){message(error.message,true);} finally{busy=false;if($('#create-draft'))$('#create-draft').disabled=false;}
  });
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
    const button=document.createElement('button');button.className='primary';button.dataset.go='edit-draft/'+draft.document_id;button.textContent='Edytuj dokument';
    const link=document.createElement('a');link.href=`/api/document-studio/drafts/${draft.document_id}/preview`;link.target='_blank';link.rel='noopener';link.textContent='Podgląd A4 / PDF';
    actions.append(button,link);main.querySelector('.heading').after(actions);
  }
}
async function route() {
  if (dirty && !confirm('Masz niezapisane zmiany. Opuścić wycieczkę?')) {
    history.replaceState(null,'',location.pathname + activeHash); return;
  }
  activeHash = location.hash;
  const parts = location.hash.slice(1).split('/');
  const view = parts[0] || 'templates', resourceId = parts[1]; dirty=false; current=null;
  document.querySelectorAll('[data-nav]').forEach(b=>b.classList.toggle('active',b.dataset.nav===(view==='marketing'?'campaigns':view==='edit-draft'?'drafts':view)));
  try {
    if (!['templates','create-document','trips','campaigns','drafts','marketing','edit-draft'].includes(view)) throw new Error('Nie znaleziono widoku.');
    if(view==='templates')templateCatalog();
    else if(view==='create-document')sourceChooser(resourceId,parts[2]||'standard');
    else if (!resourceId) cards(view);
    else if (view==='trips') {
      creating = resourceId==='new';
      current = creating ? {trip_id:id(),title:'Nowa wycieczka',destinations:[],description:'',start_date:null,end_date:null,duration_days:1,status:'draft',days:[{day_id:id(),day_number:1,title:'Rozpoczęcie podróży',stops:[],public_description:'',internal_notes:''}]} : await api('trips/' + encodeURIComponent(resourceId));
      renderTrip();
    } else if(view==='marketing') await window.MarketingEditor.open(await api('campaigns/' + encodeURIComponent(resourceId)), trips, {
      main, escape:e, api, message, refresh, dirty:value=>dirty=value, busy:value=>busy=value,
    });
    else if(view==='edit-draft') {
      const draft=await api('drafts/'+encodeURIComponent(resourceId));
      const context={main,escape:e,api,message,refresh,dirty:value=>dirty=value,busy:value=>busy=value};
      if(draft.template_id==='marketing.collection')await window.MarketingEditor.open(draft.campaign_snapshot,trips,{...context,draft});
      else await window.TripDocumentEditor.open(draft,context);
    }
    else if(view==='campaigns') renderCampaign(await api('campaigns/' + encodeURIComponent(resourceId)));
    else renderDraft(await api('drafts/' + encodeURIComponent(resourceId)));
  }catch(error){main.innerHTML='<section class="panel"><h1>Nie udało się otworzyć danych</h1><p>'+e(error.message)+'</p><button data-go="trips">Wróć do wycieczek</button></section>';}
}
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.nav)navigate(button.dataset.nav);
  if(button.dataset.go)navigate(button.dataset.go);
  if(!current || busy)return;
  if(button.id==='add-day'){current.days.push({day_id:id(),day_number:current.days.length+1,title:'Nowy dzień',stops:[],public_description:'',internal_notes:''});dirty=true;renderTrip();}
  if(button.dataset.removeDay!==undefined && confirm('Usunąć dzień wraz z jego atrakcjami?')){current.days.splice(Number(button.dataset.removeDay),1);dirty=true;renderTrip();}
  if(button.dataset.addStop!==undefined){current.days[Number(button.dataset.addStop)].stops.push({stop_id:id(),name:'Nowa atrakcja',location:'',description:'',verification_status:'unverified'});dirty=true;renderTrip();}
  if(button.dataset.removeStop!==undefined){const [d,s]=button.dataset.removeStop.split('.').map(Number);current.days[d].stops.splice(s,1);dirty=true;renderTrip();}
});
window.addEventListener('hashchange',route);
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
refresh().then(route).catch(error=>{main.innerHTML='<section class="panel"><h1>Studio jest niedostępne</h1><p>'+e(error.message)+'</p><button onclick="location.reload()">Spróbuj ponownie</button></section>';});
