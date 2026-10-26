/* Edits document-local fields; never calls PUT /trips. */
window.TripDocumentEditor = (() => {
  let draft, assets, ui, saving=false, timer, generation=0;
  const $ = selector=>document.querySelector(selector);
  const e = value=>ui.escape(value ?? '');
  const groups = {flights:'Przeloty',transfers:'Transfery',accommodations:'Noclegi',activity_bookings:'Rezerwacje atrakcji',schedule:'Harmonogram dzienny',open_items:'Sprawy do potwierdzenia'};
  function field(label,path,value,type='text',extra='') {
    return `<label>${label}<input data-d-field="${path}" type="${type}" value="${e(value)}" ${extra}></label>`;
  }
  function area(label,path,value){return `<label>${label}<textarea data-d-field="${path}" maxlength="20000">${e(Array.isArray(value)?value.join('\n'):value)}</textarea></label>`;}
  function select(label,path,value,choices){return `<label>${label}<select data-d-field="${path}">${choices.map(([key,title])=>`<option value="${e(key)}" ${String(value??'')===String(key)?'selected':''}>${e(title)}</option>`).join('')}</select></label>`;}
  function offerFields() {
    const offer=draft.offer_data;
    return `<section class="panel"><h2>Oferta dla klienta</h2><p class="notice">Pola oferty są oddzielone od logistyki pilota. Używaj wyłącznie treści przeznaczonych dla klienta.</p>
      ${area('Podsumowanie','offer_data.summary',offer.summary)}${area('Główne zalety (każda w osobnym wierszu)','offer_data.highlights',offer.highlights)}
      ${area('Zakwaterowanie / proponowany standard','offer_data.accommodation',offer.accommodation)}${area('Transport','offer_data.transport',offer.transport)}
      ${area('W cenie (każde świadczenie w osobnym wierszu)','offer_data.included',offer.included)}${area('Poza ceną (każdy element w osobnym wierszu)','offer_data.excluded',offer.excluded)}
      ${select('Zdjęcie okładki','offer_data.cover_asset_id',offer.cover_asset_id,[['','Neutralny placeholder'],...assets.map(a=>[a.asset_id,a.original_name])])}
      <label>Zdjęcia kierunku (możesz zaznaczyć kilka)<select multiple data-d-field="offer_data.photo_asset_ids">${assets.map(a=>`<option value="${a.asset_id}" ${offer.photo_asset_ids.includes(a.asset_id)?'selected':''}>${e(a.original_name)}</option>`).join('')}</select></label>
      <p class="muted">Zdjęcia z biblioteki demo. Wgraj własny JPG/PNG/WebP w sekcji poniżej.</p></section>
      <section class="panel"><h2>Cena i zakres oferty</h2><label class="document-check"><input type="checkbox" data-d-field="offer_data.concept_only" ${offer.concept_only?'checked':''}>Świadomie wybieram wersję koncepcyjną BEZ WYCENY</label>
      <div class="fields">${field('Kwota','offer_data.price.amount',offer.price.amount,'number','min="0" step="0.01"')}${select('Waluta','offer_data.price.currency',offer.price.currency,[['PLN','PLN'],['EUR','EUR'],['USD','USD']])}
      ${select('Jednostka','offer_data.price.unit',offer.price.unit,[['person','Za osobę'],['group','Za grupę']])}${field('Założona liczba uczestników','offer_data.price.participant_count',offer.price.participant_count,'number','min="1" step="1"')}
      ${select('Status kwoty','offer_data.price.status',offer.price.status,[['unknown','Do ustalenia'],['example','FIKCYJNY PRZYKŁAD DEMO'],['confirmed','Potwierdzona przez organizatora']])}</div>
      ${area('Założenia i warunki ceny','offer_data.price.assumptions',offer.price.assumptions)}${field('Źródło potwierdzenia ceny (nie drukuje się)','offer_data.price.source',offer.price.source,'text','maxlength="1000"')}
      ${area('Publiczny kontakt / CTA dla klienta','offer_data.cta',offer.cta)}</section>`;
  }
  function pilotFields() {
    const pilot=draft.pilot_data;
    return `<section class="panel"><h2>Organizacja wyjazdu</h2><div class="notice">WEWNĘTRZNE. Tylko dla uprawnionych użytkowników. Nie wpisuj PIN-ów ani kodów dostępu.</div>
      ${field('Pilot','pilot_data.leader',pilot.leader,'text','maxlength="200"')}${field('Liczba uczestników','pilot_data.participant_count',pilot.participant_count,'number','min="1" step="1"')}${area('Miejsce i lokalna godzina zbiórki / strefa','pilot_data.meeting',pilot.meeting)}
      <h3>Kontakty organizacyjne</h3>${pilot.contacts.map((contact,index)=>`<div class="document-entry">${field('Rola / organizacja',`pilot_data.contacts.${index}.label`,contact.label,'text','required maxlength="200"')}${field('Kontakt',`pilot_data.contacts.${index}.value`,contact.value,'text','maxlength="1000"')}<button type="button" class="danger" data-d-remove="contacts.${index}">Usuń kontakt</button></div>`).join('')}<button type="button" data-d-add="contacts">+ Dodaj kontakt</button>
      ${area('Wewnętrzne notatki pilota','pilot_data.internal_notes',pilot.internal_notes)}</section>` + Object.entries(groups).map(([group,title])=>`<section class="panel"><div class="section-heading"><h2>${title}</h2><button type="button" data-d-add="${group}">+ Dodaj wpis</button></div>${pilot[group].map((entry,index)=>eventFields(group,index,entry)).join('')}${pilot[group].length?'':'<p class="muted">Brak wpisów — do ustalenia.</p>'}</section>`).join('');
  }
  function eventFields(group,index,entry) {
    const path=`pilot_data.${group}.${index}`;
    return `<div class="document-entry">${field('Nazwa zdarzenia / noclegu',path+'.title',entry.title,'text','required maxlength="200"')}
      ${select('Dzień programu',path+'.day_id',entry.day_id,[['','Dotyczy całej wycieczki'],...draft.trip_snapshot.days.map(d=>[d.day_id,`Dzień ${d.day_number}: ${d.title}`])])}
      <div class="fields">${field('Lokalny początek (opcjonalnie)',path+'.start_local',entry.start_local?.slice(0,16),'datetime-local')}${field('Lokalny koniec (opcjonalnie)',path+'.end_local',entry.end_local?.slice(0,16),'datetime-local')}
      ${field('Strefa IANA początku',path+'.time_zone',entry.time_zone,'text','placeholder="Atlantic/Reykjavik" maxlength="100"')}${field('Strefa końca (pusta = jak początek)',path+'.end_time_zone',entry.end_time_zone,'text','maxlength="100"')}</div>
      ${select('Status',path+'.status',entry.status,[['unknown','Do ustalenia'],['planned','Planowane'],['confirmed','Potwierdzone']])}
      ${area('Szczegóły / obowiązki / termin potwierdzenia',path+'.details',entry.details)}${field('Źródło (wymagane przy potwierdzeniu)',path+'.source',entry.source,'text','maxlength="1000"')}
      ${field('Numer rezerwacji (bez PIN-u i kodów dostępu)',path+'.booking_reference',entry.booking_reference,'text','maxlength="200"')}<button type="button" class="danger" data-d-remove="${group}.${index}">Usuń wpis</button></div>`;
  }
  function draw() {
    ui.main.innerHTML=`<button class="text-button back" data-go="drafts/${e(draft.document_id)}">← Zapisany dokument</button><div class="heading"><div><p class="eyebrow">${e(draft.template_id)} · REWIZJA <span id="d-revision">${draft.revision}</span></p><h1>${draft.template_id==='offer.private'?'Oferta indywidualna':'Rozpiska pilota'}</h1><p class="muted">Snapshot wycieczki ${e(draft.trip_snapshot.title)} · zmiany pozostają w dokumencie.</p></div><div class="actions"><button class="primary" id="d-save">Zapisz draft</button><button class="accent" id="d-export">Podgląd / PDF</button></div></div>
      <div class="trip-document-layout"><div class="trip-document-controls"><form id="d-form"><section class="panel"><h2>Metryka dokumentu</h2>${draft.demo_example?'<p class="notice">FIKCYJNY PRZYKŁAD DEMO — dane nie są rzeczywistą ofertą ani rezerwacją.</p>':''}
      ${field('Tytuł dokumentu','title',draft.title,'text','required maxlength="200"')}${field('Termin / jawna etykieta dat','date_label',draft.date_label,'text','maxlength="200" placeholder="Termin do ustalenia"')}</section>
      ${draft.template_id==='offer.private'?offerFields():pilotFields()}
      <section class="panel"><h2>Program — treści tego dokumentu</h2><p class="muted">Puste pole pozostawia treść bazowego snapshotu. Edycja nie zmienia Trip ani innych dokumentów.</p>${draft.trip_snapshot.days.map((day,index)=>`<div class="document-entry"><p class="eyebrow">DZIEŃ ${day.day_number}</p>${field('Własny tytuł',`day_overrides.${index}.title`,draft.day_overrides[index].title,'text',`maxlength="200" placeholder="${e(day.title)}"`)}${area('Własny opis',`day_overrides.${index}.description`,draft.day_overrides[index].description)}</div>`).join('')}</section></form>
      ${draft.template_id==='offer.private'?'<section class="panel"><h2>Wgraj zdjęcie okładki</h2><input type="file" id="d-file" accept="image/jpeg,image/png,image/webp"><label class="document-check"><input type="checkbox" id="d-rights">Mam prawo użyć zdjęcia w ofercie.</label><button id="d-upload">Wgraj i wybierz</button></section>':''}</div>
      <aside class="trip-document-preview"><div id="d-validation" role="status">Przygotowanie podglądu…</div><iframe id="d-preview" title="Podgląd oferty lub rozpiski pilota"></iframe></aside></div>`;
    $('#d-form').addEventListener('submit',event=>event.preventDefault());
    $('#d-form').addEventListener('input',change);
    $('#d-form').addEventListener('change',event=>{if(event.target.tagName==='SELECT')change(event);});
    $('#d-save').addEventListener('click',save);
    $('#d-export').addEventListener('click',async()=>{
      const tab=window.open('about:blank','_blank');if(!tab){ui.message('Zezwól na otwarcie podglądu PDF.',true);return;}
      if(await save()){tab.opener=null;tab.location.href=`/api/document-studio/drafts/${draft.document_id}/preview`;}else tab.close();
    });
    ui.main.querySelectorAll('[data-d-add]').forEach(button=>button.addEventListener('click',()=>{
      const group=button.dataset.dAdd;
      draft.pilot_data[group].push(group==='contacts'?{label:'Kontakt organizacyjny',value:''}:{entry_id:crypto.randomUUID().replaceAll('-',''),day_id:null,title:'Nowy wpis',start_local:null,end_local:null,time_zone:'Atlantic/Reykjavik',end_time_zone:'',status:'unknown',details:'',booking_reference:'',source:''});ui.dirty(true);draw();
    }));
    ui.main.querySelectorAll('[data-d-remove]').forEach(button=>button.addEventListener('click',()=>{const[group,index]=button.dataset.dRemove.split('.');draft.pilot_data[group].splice(Number(index),1);ui.dirty(true);draw();}));
    if($('#d-upload'))$('#d-upload').addEventListener('click',upload);
    preview();
  }
  function change(event) {
    const path=event.target.dataset.dField;if(!path)return;
    const keys=path.split('.');let target=draft;for(const key of keys.slice(0,-1))target=target[key];
    const key=keys.at(-1);let value=event.target.value;
    if(event.target.type==='checkbox')value=event.target.checked;
    if(event.target.multiple)value=[...event.target.selectedOptions].map(o=>o.value);
    if(['highlights','included','excluded'].includes(key))value=value.split('\n').filter(x=>x.trim());
    if(['participant_count'].includes(key))value=value?Number(value):null;
    if(['amount','start_local','end_local','cover_asset_id','day_id'].includes(key))value ||= null;
    target[key]=value;ui.dirty(true);clearTimeout(timer);timer=setTimeout(preview,500);
  }
  async function preview() {
    const version=++generation;if(!$('#d-preview'))return;
    const body=JSON.stringify({draft});
    try{
      const [issues,response]=await Promise.all([ui.api('trip-documents/validate',{method:'POST',body}),fetch('/api/document-studio/trip-documents/preview',{method:'POST',headers:{'Content-Type':'application/json'},body})]);
      if(!response.ok)throw new Error('Nie udało się przygotować podglądu. Sprawdź dane.');
      const html=await response.text();if(version!==generation||!$('#d-preview'))return;
      $('#d-validation').innerHTML=issues.length?`<details open><summary>Uwagi: ${issues.length}</summary><ul>${issues.map(i=>`<li class="${i.severity}">${e(i.message)}</li>`).join('')}</ul></details>`:'Dane kompletne. Dokument pozostaje wersją roboczą.';
      $('#d-preview').srcdoc=html;
    }catch(error){if(version===generation&&$('#d-validation'))$('#d-validation').textContent=error.message;}
  }
  async function save() {
    if(saving||!$('#d-form').reportValidity())return false;
    saving=true;ui.busy(true);$('#d-save').disabled=true;
    try{
      const update={revision:draft.revision,title:draft.title,date_label:draft.date_label,editorial_notes:draft.editorial_notes,day_overrides:draft.day_overrides,offer_data:draft.offer_data,pilot_data:draft.pilot_data};
      draft=await ui.api('drafts/'+draft.document_id,{method:'PUT',body:JSON.stringify(update)});
      ui.dirty(false);await ui.refresh();$('#d-revision').textContent=draft.revision;ui.message('Draft zapisany. Rewizja '+draft.revision+'.');preview();return true;
    }catch(error){ui.message(error.message,true);return false;}finally{saving=false;ui.busy(false);if($('#d-save'))$('#d-save').disabled=false;}
  }
  async function upload() {
    const file=$('#d-file').files[0];if(!file||!$('#d-rights').checked){ui.message('Wybierz zdjęcie i potwierdź prawo użycia.',true);return;}
    try{
      const response=await fetch('/api/document-studio/assets?'+new URLSearchParams({filename:file.name,rights_confirmed:'true'}),{method:'POST',headers:{'Content-Type':file.type},body:file});
      const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Błąd uploadu');
      assets.push(result);draft.offer_data.cover_asset_id=result.asset_id;ui.dirty(true);draw();ui.message('Zdjęcie wgrane. Zapisz draft.');
    }catch(error){ui.message(error.message,true);}
  }
  return {async open(source,context){
    if(!['offer.private','pilot.basic'].includes(source.template_id)||!source.trip_snapshot)throw new Error('Ten edytor obsługuje ofertę indywidualną i rozpiskę podstawową pilota.');
    generation++;clearTimeout(timer);draft=JSON.parse(JSON.stringify(source));ui=context;assets=await ui.api('assets');
    draft.day_overrides=draft.trip_snapshot.days.map(day=>draft.day_overrides.find(o=>o.day_id===day.day_id)||{day_id:day.day_id,title:'',description:''});
    draft.offer_data ||= draft.template_id==='offer.private'?{summary:'',highlights:[],accommodation:'',transport:'',included:[],excluded:[],price:{amount:null,currency:'PLN',unit:'person',participant_count:null,status:'unknown',assumptions:'',source:''},concept_only:false,cta:'',cover_asset_id:null,cover_position:{x:50,y:50,zoom:1},photo_asset_ids:[]}:null;
    draft.pilot_data ||= draft.template_id==='pilot.basic'?{leader:'',participant_count:null,meeting:'',flights:[],transfers:[],accommodations:[],activity_bookings:[],schedule:[],contacts:[],open_items:[],internal_notes:''}:null;
    draw();
  }};
})();
