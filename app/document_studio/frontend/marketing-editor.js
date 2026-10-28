/* Campaign editing is separate from the existing trip editor and the renderer. */
window.MarketingEditor = (() => {
  let campaign, catalog, assets, ui, timer, generation = 0, format = 'a4', saving = false, documentDraft=null, sourceFilters={}, campaignCreating=false;
  const find = selector => document.querySelector(selector);
  const clone = value => JSON.parse(JSON.stringify(value));
  const normalize = () => {
    const value = clone(campaign);
    value.items.forEach(item => item.date_range_or_label = item.date_range_or_label.trim() || 'Termin do ustalenia');
    return value;
  };
  const position = () => ({x:50,y:50,zoom:1});
  function field(label, path, value, extra = '') {
    return `<label>${label}<input data-m-field="${path}" value="${ui.escape(value ?? '')}" ${extra}></label>`;
  }
  function area(label, path, value, max = 500) {
    return `<label>${label}<textarea data-m-field="${path}" maxlength="${max}">${ui.escape(value ?? '')}</textarea></label>`;
  }
  function photoFields(path, imageId, crop, hero = false) {
    crop ||= position();
    const imageField = hero ? 'hero_asset_id' : path + '.image_asset_id';
    const cropField = hero ? 'hero_position' : path + '.image_position';
    return `<label>${hero ? 'Główne zdjęcie kolekcji' : 'Zdjęcie kierunku'}<select data-m-field="${imageField}"><option value="">Neutralny placeholder</option>${assets.map(asset=>`<option value="${asset.asset_id}" ${asset.asset_id===imageId?'selected':''}>${ui.escape(asset.original_name)} (${asset.width}×${asset.height})</option>`).join('')}</select></label>
      <div class="crop-fields">${[['x','Kadr poziomo',0,100,1],['y','Kadr pionowo',0,100,1],['zoom','Powiększenie',1,3,.05]].map(([key,label,min,max,step])=>`<label>${label}<input type="range" data-m-field="${cropField}.${key}" min="${min}" max="${max}" step="${step}" value="${crop[key]}"></label>`).join('')}</div>`;
  }
  function draw() {
    const e = ui.escape;
    ui.main.innerHTML = `<button class="text-button back" data-go="${documentDraft?'drafts':ui.flow?DocumentFlow.path(ui.flow):'campaigns/'+e(campaign.campaign_id)}">← ${documentDraft?'Wróć do biblioteki':ui.flow?'Wybór programu':'Kampania'}</button>
    <div class="heading marketing-heading"><div><p class="eyebrow">MATERIAŁY MARKETINGOWE</p><h1>Studio kolekcji</h1><p class="muted">Edytuj treść, ułóż kierunki i sprawdź dokument przed drukiem.</p></div><div class="actions"><button id="m-save" class="primary">${documentDraft?'Zapisz dokument':'Zapisz kampanię'}</button><button id="m-export" class="accent" ${documentDraft?'':'data-source-continue data-source-saved="'+(!campaignCreating)+'"'}>${documentDraft?'Zapisz i otwórz PDF':'Kontynuuj do dokumentu'}</button></div></div>
    <div class="marketing-layout"><div class="marketing-controls"><form id="m-form"><section class="panel"><h2>Kampania</h2>${documentDraft?'<p>Rodzaj danych dokumentu: '+e(SourcePicker.origins[documentDraft.data_origin||'unknown'])+'</p>':SourcePicker.originField(campaign.data_origin||'unknown','campaign-origin')}<div class="fields"><div class="full">${field('Tytuł kampanii','title',campaign.title,'required maxlength="200"')}</div>
    <label>Kompozycja<select data-m-field="layout_variant"><option value="new_trips" ${campaign.layout_variant==='new_trips'?'selected':''}>Nowe kierunki</option><option value="theme_collection" ${campaign.layout_variant==='theme_collection'?'selected':''}>Kolekcja tematyczna</option></select></label>
    ${field('Sezon / podtytuł','season',campaign.season,'maxlength="200"')}${field('Opcjonalny prowadzący','leader',campaign.leader,'maxlength="200"')}
    <div class="full">${field('Temat przewodni','theme',campaign.theme,'maxlength="200"')}</div><div class="full">${area('Wprowadzenie','description',campaign.description,1000)}</div><div class="full">${area('CTA / kontakt','cta',campaign.cta,600)}</div></div>
    <div id="m-hero" ${campaign.layout_variant==='theme_collection'?'':'hidden'}>${photoFields('',campaign.hero_asset_id,campaign.hero_position,true)}</div></section>
    <section class="panel"><h2>Kierunki kolekcji</h2><p class="muted">Tytuły i opisy w kampanii nie zmieniają wycieczek źródłowych.</p><div id="m-items">${campaign.items.map((item,index)=> {
      const trip = catalog.find(t=>t.trip_id===item.trip_id);
      return `<article class="marketing-item" data-m-item="${index}"><div class="section-heading"><h3>${index+1}. ${e(trip?.destinations.join(' · ') || 'Kierunek')}</h3><div class="actions"><button type="button" data-m-move="${index},-1" aria-label="Przesuń kierunek ${index+1} w górę" ${index===0?'disabled':''}>↑</button><button type="button" data-m-move="${index},1" aria-label="Przesuń kierunek ${index+1} w dół" ${index===campaign.items.length-1?'disabled':''}>↓</button><button type="button" class="danger" data-m-remove="${index}">Usuń</button></div></div>
      ${field('Tytuł w dokumencie',`items.${index}.display_title`,item.display_title || trip?.title,'maxlength="200"')}${field('Pilot / prowadzący (opcjonalnie)',`items.${index}.leader`,item.leader,'maxlength="200"')}
      ${field('Termin lub etykieta',`items.${index}.date_range_or_label`,item.date_range_or_label,'maxlength="200" placeholder="Termin do ustalenia"')}
      ${area('Krótki opis',`items.${index}.short_hook`,item.short_hook)}
      ${field('Wyróżniki (oddziel przecinkami)',`items.${index}.highlights`,item.highlights.join(', '),'maxlength="1000"')}
      <label>Oznaczenie<select data-m-field="items.${index}.badge">${[['concept','Propozycja'],['new','Nowość'],['pilot','Pilotaż']].map(([key,label])=>`<option value="${key}" ${(item.badge || 'concept')===key?'selected':''}>${label}</option>`).join('')}</select></label>
      ${photoFields(`items.${index}`,item.image_asset_id,item.image_position)}</article>`;
    }).join('')}</div><div id="m-trip-picker"></div><button type="button" id="m-add">+ Dodaj kierunek</button></section>${documentDraft?window.SectionEditor.html(documentDraft,assets):''}</form>
    <section class="panel"><h2>Twoje zdjęcia</h2><p class="muted">JPG, PNG lub WebP · do 8 MB i 24 MP. Zdjęcia pozostają w prywatnym magazynie demo.</p><label>Przypisz nowe zdjęcie<select id="m-upload-target"><option value="hero">Zdjęcie główne kolekcji</option>${campaign.items.map((item,i)=>`<option value="${i}">Kierunek ${i+1}</option>`).join('')}</select></label><label>Plik zdjęcia<input type="file" id="m-file" accept="image/jpeg,image/png,image/webp"></label><label class="rights-check"><input type="checkbox" id="m-rights">Mam prawo użyć tego zdjęcia w tym materiale.</label><button type="button" id="m-upload">Wgraj i wybierz zdjęcie</button><p id="m-upload-status" role="status"></p></section></div>
    <div class="marketing-preview"><div class="preview-heading"><div><p class="eyebrow">PODGLĄD NA ŻYWO</p><small>Kolory, typografia i tekstowy znak TRIPSE są propozycją roboczą.</small></div><label>Format<select id="m-format"><option value="a4" ${format==='a4'?'selected':''}>A4 / PDF</option><option value="social" ${format==='social'?'selected':''}>1080 × 1350</option></select></label></div><div id="m-validation" role="status"></div><iframe id="m-preview" title="Podgląd dokumentu marketingowego"></iframe></div></div>`;
    if(documentDraft)window.SectionEditor.bind(ui.main,documentDraft,{assets,dirty:ui.dirty,preview:()=>{clearTimeout(timer);timer=setTimeout(preview,500);},draw});
    if(find('#campaign-origin'))find('#campaign-origin').onchange=()=>{campaign.data_origin=find('#campaign-origin').value;ui.dirty(true);};
    find('#m-form').addEventListener('submit',event=>event.preventDefault());
    find('#m-form').addEventListener('input',changeField);
    find('#m-form').addEventListener('change',event=> {if(event.target.tagName==='SELECT') changeField(event);});
    find('#m-format').addEventListener('change',event=>{format=event.target.value;preview();});
    find('#m-save').addEventListener('click',()=>save());
    find('#m-export').addEventListener('click',exportDocument);
    find('#m-upload').addEventListener('click',upload);
    const picker=SourcePicker.mount(find('#m-trip-picker'),{entries:catalog,id:'m-add-trip',state:sourceFilters,exclude:()=>campaign.items.map(item=>item.trip_id)});
    find('#m-add').addEventListener('click',()=>{
      const tripId=picker.values[0]; if(!tripId)return;
      campaign.items.push({trip_id:tripId,display_title:'',short_hook:'',date_range_or_label:'Termin do ustalenia',highlights:[],image_asset_id:null,image_position:position(),badge:'concept',publication_status:'draft'});
      ui.dirty(true);draw();
    });
    ui.main.querySelectorAll('[data-m-remove]').forEach(button=>button.addEventListener('click',()=>{
      campaign.items.splice(Number(button.dataset.mRemove),1);ui.dirty(true);draw();
    }));
    ui.main.querySelectorAll('[data-m-move]').forEach(button=>button.addEventListener('click',()=>{
      const [index,offset]=button.dataset.mMove.split(',').map(Number);
      [campaign.items[index],campaign.items[index+offset]]=[campaign.items[index+offset],campaign.items[index]];ui.dirty(true);draw();
    }));
    if(documentDraft)DocumentFlow.decorateEditor(documentDraft,{...ui,review:async()=>{if(await save())ui.review();}});
    else {
      const banner=document.createElement('div');banner.innerHTML=DocumentFlow.steps(2,ui.flow||{template:'marketing.collection',variant:campaign.layout_variant,kind:'campaign',sourceId:campaign.campaign_id})+'<section class="panel flow-source-info"><strong>Przygotowanie kampanii</strong><p>Zapisz wspólną kolekcję wycieczek. Dopiero „Kontynuuj do dokumentu” utworzy jej niezależną wersję do dalszej edycji.</p></section>';ui.main.prepend(banner);
      if(ui.pause){const pause=document.createElement('button');pause.type='button';pause.textContent='Zapisz kampanię i wróć później';pause.onclick=async()=>{if(!ui.isDirty()&&!campaignCreating||await save())ui.pause();};ui.main.querySelector('.heading .actions').append(pause);}
      find('#m-export').disabled=campaignCreating||ui.isDirty();
    }
    for(const fields of ui.main.querySelectorAll('.crop-fields')){const details=document.createElement('details');details.className='flow-crop';details.innerHTML='<summary>Dopasuj kadr zdjęcia</summary>';fields.before(details);details.append(fields);}
    preview();
  }
  function changeField(event) {
    const field=event.target.dataset.mField;if(!field)return;
    const keys=field.split('.');let target=campaign;
    for(const key of keys.slice(0,-1)){target[key]??={};target=target[key];}
    const key=keys.at(-1);let value=event.target.value;
    if(key==='highlights')value=value.split(',').map(x=>x.trim()).filter(Boolean);
    if(event.target.type==='range')value=Number(value);
    if(key==='hero_asset_id'||key==='image_asset_id')value ||= null;
    if(key==='leader')value ||= null;target[key]=value;ui.dirty(true);
    find('#m-hero').hidden=campaign.layout_variant!=='theme_collection';
    clearTimeout(timer);timer=setTimeout(preview,450);
  }
  async function preview() {
    const version=++generation;
    const panel=find('#m-validation');if(!panel)return;
    if(!campaign.title.trim() || !campaign.items.length){panel.textContent='Podaj tytuł kampanii i dodaj co najmniej jeden kierunek.';find('#m-preview').srcdoc='';return;}
    const body=JSON.stringify(documentDraft?{draft:{...documentDraft,title:campaign.title,layout_variant:campaign.layout_variant,campaign_snapshot:normalize(),campaign_trip_snapshots:campaign.items.map(item=>documentDraft.campaign_trip_snapshots.find(t=>t.trip_id===item.trip_id)||catalog.find(t=>t.trip_id===item.trip_id))},output_format:format}:{campaign:normalize(),output_format:format});
    try {
      const [issues,response]=await Promise.all([
        ui.api(documentDraft?'trip-documents/validate':'marketing/validate',{method:'POST',body}),
        fetch('/api/document-studio/'+(documentDraft?'trip-documents/preview':'marketing/preview'),{method:'POST',headers:{'Content-Type':'application/json'},body})
      ]);
      if(!response.ok)throw new Error('Nie udało się zbudować podglądu. Sprawdź pola kampanii.');
      const html=await response.text();
      if(version!==generation || !find('#m-preview'))return;
      panel.innerHTML=issues.some(i=>i.severity==='error')?`<ul>${issues.filter(i=>i.severity==='error').map(i=>`<li>${ui.escape(i.message)}</li>`).join('')}</ul>`:`<span>${issues.length?'Uwagi: '+issues.length+' (m.in. placeholdery i nieustalone terminy).':'Pola dokumentu są kompletne.'}</span>`;
      find('#m-preview').srcdoc=html;
    }catch(error){if(version===generation && find('#m-validation'))find('#m-validation').textContent=error.message;}
  }
  async function save() {
    if(saving)return false;
    if(!find('#m-form').reportValidity() || !campaign.items.length){ui.message('Podaj tytuł i dodaj co najmniej jeden kierunek.',true);return false;}
    saving=true;ui.busy(true);ui.main.inert=true;find('#m-save').disabled=true;
    try{
      if(documentDraft){Object.assign(documentDraft,await ui.api('drafts/'+documentDraft.document_id,{method:'PUT',body:JSON.stringify({revision:documentDraft.revision,title:campaign.title,sections:documentDraft.sections,campaign_snapshot:normalize()})}));campaign=clone(documentDraft.campaign_snapshot);}else {campaign=campaignCreating?await ui.persistCreate('campaigns',normalize()):await ui.api('campaigns/'+campaign.campaign_id,{method:'PUT',body:JSON.stringify(normalize())});campaignCreating=false;find('#m-export').dataset.sourceSaved='true';ui.sourceSaved?.(campaign);}
      ui.dirty(false);let warning='';try{await ui.refresh();}catch{warning=' Biblioteka wymaga odświeżenia.';}ui.message((documentDraft?'Dokument zapisany. Możesz kontynuować edycję lub przejść do sprawdzenia.':'Kampania zapisana.')+warning,!!warning);return true;
    }catch(error){ui.message(error.message,true);ui.recovery?.(error);return false;}
    finally{saving=false;ui.busy(false);ui.main.inert=false;if(find('#m-save'))find('#m-save').disabled=false;}
  }
  async function exportDocument() {
    if(saving)return;
    if(!documentDraft){
      if(campaignCreating||ui.isDirty()){ui.message('Najpierw zapisz kampanię.',true);return;}
      await ui.continueSource(campaign);return;
    }
    const tab=window.open('about:blank','_blank');if(!tab){ui.message('Zezwól na otwarcie podglądu PDF.',true);return;}
    if(await save()){tab.opener=null;tab.location.href=`/api/document-studio/drafts/${documentDraft.document_id}/preview?output_format=${format}`;}else tab.close();
  }

  async function upload() {
    const file=find('#m-file').files[0],rights=find('#m-rights').checked;
    if(!file||!rights){ui.message('Wybierz zdjęcie i potwierdź prawo do użycia.',true);return;}
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>8*1024*1024){ui.message('Wybierz JPG/PNG/WebP do 8 MB.',true);return;}
    const target=find('#m-upload-target').value;
    find('#m-upload').disabled=true;
    try{
      const response=await fetch('/api/document-studio/assets?'+new URLSearchParams({filename:file.name,rights_confirmed:'true'}),{method:'POST',headers:{'Content-Type':file.type},body:file});
      const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Nie udało się wgrać zdjęcia.');
      assets.push(result);
      if(target==='hero')campaign.hero_asset_id=result.asset_id;else campaign.items[Number(target)].image_asset_id=result.asset_id;
      ui.dirty(true);draw();ui.message('Zdjęcie wgrane. Zapisz kampanię, aby zachować wybór.');
    }catch(error){ui.message(error.message,true);if(find('#m-upload'))find('#m-upload').disabled=false;}
  }
  return {async open(source,trips,context){
    const version=++generation;clearTimeout(timer);
    let initialized=context.draft||null;
    if(initialized?.sections===null)initialized=await context.api('trip-documents/initialize',{method:'POST',body:JSON.stringify({draft:initialized})});
    const loadedAssets=await context.api('assets');
    if(version!==generation||context.isCurrent&&!context.isCurrent())return;
    campaign=clone(source);catalog=trips;ui=context;format='a4';documentDraft=initialized;sourceFilters={};
    if(documentDraft){campaign.layout_variant=documentDraft.layout_variant;campaign.title=documentDraft.title;}
    campaignCreating=!!context.creating;assets=loadedAssets;draw();
  }};
})();
