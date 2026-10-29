/* Shared typed section form. No HTML, script, or free-form JSON input. */
window.SectionEditor = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const names = {text:'Tekst',list:'Lista punktowana',image:'Zdjęcie z opisem',gallery:'Galeria',table:'Tabela',callout:'Wyróżniony blok',day:'Sekcja dzienna',logistics:'Logistyka dnia',knowledge:'Materiały merytoryczne',source:'Dane szablonu'};
  function field(label,path,value,type='text',mode='') {
    return `<label>${esc(label)}<input data-s-field="${path}" data-s-mode="${mode}" type="${type}" value="${esc(value)}" ${type==='number'?'min="0" step="any"':''}></label>`;
  }
  function area(label,path,value,mode='') {return `<label>${esc(label)}<textarea data-s-field="${path}" data-s-mode="${mode}" maxlength="20000">${esc(value)}</textarea></label>`;}
  function select(label,path,value,options,mode='') {return `<label>${esc(label)}<select data-s-field="${path}" data-s-mode="${mode}">${options.map(([v,l])=>`<option value="${esc(v)}" ${String(v)===String(value??'')?'selected':''}>${esc(l)}</option>`).join('')}</select></label>`;}
  function content(draft,s,i,assets) {
    const path=`sections.${i}`, days=draft.trip_snapshot?.days||[];
    let html = '';
    if (!s.role) html+=select('Powiązany dzień',path+'.day_id',s.day_id,[['','Cały dokument'],...days.map(d=>[d.day_id,`Dzień ${d.day_number}: ${d.title}`])],'nullable');
    if(s.kind==='list')html+=area('Punkty — każdy w osobnym wierszu',path+'.items',s.items.join('\n'),'lines');
    if(s.kind==='table')html+=area('Nagłówki kolumn — każdy w osobnym wierszu',path+'.columns',s.columns.join('\n'),'lines')+area('Wiersze tabeli — komórki oddziel tabulatorem',path+'.rows',s.rows.map(r=>r.join('\t')).join('\n'),'table');
    if(['image','gallery'].includes(s.kind)) {
      html+=s.images.map((image,j)=>select('Zdjęcie',`${path}.images.${j}.asset_id`,image.asset_id,[['','Placeholder'],...assets.map(a=>[a.asset_id,a.original_name])],'nullable')+area('Opis zdjęcia',`${path}.images.${j}.caption`,image.caption)+['x','y','zoom'].map(k=>field(`Kadr ${k}`,`${path}.images.${j}.position.${k}`,image.position[k],'number','number')).join('')+`<button type="button" data-s-image-remove="${i},${j}">Usuń zdjęcie</button>`).join('');
      html+=`<button type="button" data-s-image-add="${i}" ${s.kind==='image'&&s.images.length?'disabled':''}>+ Zdjęcie</button>`;
    }
    if(s.logistics) {
      html+=field('Data tego dnia w dokumencie',path+'.logistics.date',s.logistics.date,'date','nullable');
      for(const [key,label] of Object.entries({route_start:'Początek trasy',route_end:'Koniec trasy',drive_km:'Dystans jazdy km',walk_km:'Dystans pieszy km',elevation_gain_m:'Przewyższenie m',drive_minutes:'Czas jazdy min',activity_minutes:'Czas aktywności min',time_zone:'Strefa IANA'})) {
        const numeric=['drive_km','walk_km','elevation_gain_m','drive_minutes','activity_minutes'].includes(key);
        html+=field(label,path+'.logistics.'+key,s.logistics[key],numeric?'number':'text',numeric?'number':'');
      }
      html+=select('Nocleg ze wspólnej logistyki',path+'.logistics.accommodation_entry_id',s.logistics.accommodation_entry_id,[['','Wpisy przypisane do dnia'],...(draft.pilot_data?.accommodations||[]).map(e=>[e.entry_id,e.title])],'nullable');
      html+=select('Weryfikacja metryk',path+'.logistics.verification_status',s.logistics.verification_status,[['unverified','Niezweryfikowane'],['proposed','Proponowane'],['verified','Zweryfikowane — wymagane źródło'],['rejected','Odrzucone']])+area('Źródło pomiaru',path+'.logistics.source',s.logistics.source);
      html+=area('Notatki organizacyjne',path+'.logistics.organizational_notes',s.logistics.organizational_notes)+area('Ryzyka / plan B',path+'.logistics.plan_b',s.logistics.plan_b);
    }
    if(s.knowledge) {
      const k=s.knowledge;
      html+=`<p class="notice">${esc(k.part)} · wyłącznie miejsca programu. Treści wpisujesz ręcznie; system nie generuje faktów.</p>`;
      for(const [key,label] of Object.entries({facts:'Najważniejsze informacje / opisy atrakcji',history:'Historia regionu',geology_nature:'Geologia i przyroda',culture:'Kultura i zwyczaje',connection:'Co łączy miejsca?',observations:'Na co zwrócić uwagę?',stories:'Ciekawostki / historie',pilot_notes:'Dodatkowe informacje dla pilota'}))html+=area(label,path+'.knowledge.'+key,k[key]);
      html+=select('Status weryfikacji',path+'.knowledge.verification_status',k.verification_status,[['unverified','Niezweryfikowane'],['proposed','Propozycja'],['verified','Zweryfikowane — wymaga źródeł i dat'],['rejected','Odrzucone']]);
      html+=k.sources.map((source,j)=>field('Dokładny tytuł / URL / odniesienie',`${path}.knowledge.sources.${j}.reference`,source.reference)+field('Data sprawdzenia',`${path}.knowledge.sources.${j}.checked_on`,source.checked_on,'date','nullable')+`<button type="button" data-s-source-remove="${i},${j}">Usuń źródło</button>`).join('')+`<button type="button" data-s-source-add="${i}">+ Dodaj źródło</button>`;
    }
    return html;
  }
  function html(draft,assets) {
    return `<section class="panel section-editor"><h2>Treść i kolejność sekcji</h2><p class="muted">Sekcje szablonu mogą być ukryte, ale ich brak pozostaje w walidacji. Zmiany dotyczą tylko tego dokumentu.</p>${(draft.sections||[]).map((s,i)=>`<article class="document-entry" data-section-id="${esc(s.section_id)}"><details ${['knowledge','logistics'].includes(s.kind)?'':'open'}><summary>${esc(s.title)}</summary><div class="section-heading"><strong>${i+1}. ${esc(names[s.kind])}</strong><div class="actions"><button type="button" data-s-move="${i},-1" ${i===0?'disabled':''}>W górę</button><button type="button" data-s-move="${i},1" ${i===draft.sections.length-1?'disabled':''}>W dół</button>${s.role?'':`<button type="button" data-s-remove="${i}">Usuń sekcję</button>`}</div></div><label class="document-check"><input type="checkbox" data-s-field="sections.${i}.visible" ${s.visible?'checked':''}>Widoczna w dokumencie</label>${field('Tytuł sekcji',`sections.${i}.title`,s.title)}${area(s.kind==='source'?'Dodatkowe uwagi sekcji — pola źródłowe edytujesz powyżej':'Treść',`sections.${i}.body`,s.body)}${content(draft,s,i,assets)}</details></article>`).join('')}<label>Nowa sekcja<select id="s-new-kind">${Object.entries(names).filter(([key])=>!['source','logistics','knowledge'].includes(key)).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}${draft.template_id==='pilot.knowledge'?'<option value="knowledge">Dodatkowa część merytoryczna</option>':''}</select></label><button type="button" id="s-add">+ Dodaj sekcję</button></section>`;
  }
  function bind(host,draft,ui) {
    const changed=()=>{ui.dirty(true);ui.preview();};
    const redraw=()=>{draft.sections.forEach((s,i)=>s.order=i);ui.dirty(true);ui.draw();};
    host.querySelector('.section-editor')?.addEventListener('input',event=>{
      const el=event.target,path=el.dataset.sField;if(!path)return;
      const keys=path.split('.');let target=draft;for(const k of keys.slice(0,-1))target=target[k];
      let v=el.type==='checkbox'?el.checked:el.value;
      if(el.dataset.sMode==='lines')v=v.split('\n').filter(x=>x.trim());
      if(el.dataset.sMode==='table')v=v?v.split('\n').map(r=>r.split('\t')):[];
      if(el.dataset.sMode==='number')v=v===''?null:Number(v);
      if(el.dataset.sMode==='nullable')v ||= null;
      target[keys.at(-1)]=v;changed();
    });
    for(const button of host.querySelectorAll('[data-s-move]'))button.onclick=()=>{const[i,offset]=button.dataset.sMove.split(',').map(Number);[draft.sections[i],draft.sections[i+offset]]=[draft.sections[i+offset],draft.sections[i]];redraw();};
    for(const button of host.querySelectorAll('[data-s-remove]'))button.onclick=()=>{draft.sections.splice(Number(button.dataset.sRemove),1);redraw();};
    for(const button of host.querySelectorAll('[data-s-image-add]'))button.onclick=()=>{draft.sections[Number(button.dataset.sImageAdd)].images.push({asset_id:null,caption:'',position:{x:50,y:50,zoom:1}});redraw();};
    for(const button of host.querySelectorAll('[data-s-source-add]'))button.onclick=()=>{draft.sections[Number(button.dataset.sSourceAdd)].knowledge.sources.push({reference:'Źródło do uzupełnienia',checked_on:null});redraw();};
    for(const button of host.querySelectorAll('[data-s-image-remove],[data-s-source-remove]'))button.onclick=()=>{const isImage=!!button.dataset.sImageRemove;const[i,j]=(button.dataset.sImageRemove||button.dataset.sSourceRemove).split(',').map(Number);(isImage?draft.sections[i].images:draft.sections[i].knowledge.sources).splice(j,1);redraw();};
    const upload=document.createElement('div');upload.className='document-entry';
    upload.innerHTML='<h3>Dodaj zdjęcie do prywatnej biblioteki</h3><input id="s-file" type="file" accept="image/jpeg,image/png,image/webp"><label class="document-check"><input id="s-rights" type="checkbox">Mam prawo użyć zdjęcia w dokumencie.</label><button type="button" id="s-upload">Wgraj zdjęcie</button>';
    host.querySelector('.section-editor').append(upload);
    upload.querySelector('#s-upload').onclick=async()=>{
      const file=upload.querySelector('#s-file').files[0];
      if(!file||!upload.querySelector('#s-rights').checked){alert('Wybierz zdjęcie i potwierdź prawo do użycia.');return;}
      if(file.size>8*1024*1024){alert('Zdjęcie przekracza limit 8 MB.');return;}
      const button=upload.querySelector('#s-upload');button.disabled=true;
      try {
        const r=await fetch('/api/document-studio/assets?'+new URLSearchParams({filename:file.name,rights_confirmed:'true'}),{method:'POST',headers:{'Content-Type':file.type},body:file});
        const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Nie udało się wgrać zdjęcia.');
        ui.assets.push(data);redraw();
      }catch(error){alert(error.message);button.disabled=false;}
    };
    host.querySelector('#s-add').onclick=()=>{
      const kind=host.querySelector('#s-new-kind').value;
      const section={section_id:crypto.randomUUID().replaceAll('-',''),role:null,kind,title:names[kind],body:'',order:draft.sections.length,visible:true,day_id:null,items:[],images:[],columns:kind==='table'?['Nazwa','Opis']:[],rows:[],logistics:null,knowledge:null};
      if(kind==='knowledge') {
        section.day_id=draft.trip_snapshot.days[0]?.day_id||null;
        section.knowledge={part:'narrative',stop_ids:[],facts:'',history:'',geology_nature:'',culture:'',connection:'',observations:'',stories:'',pilot_notes:'',verification_status:'unverified',sources:[]};
      }
      draft.sections.push(section);redraw();
    };
  }
  return {html,bind};
})();
