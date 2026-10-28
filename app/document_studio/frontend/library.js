/* Library metadata is loaded on demand; editable snapshots remain in Repository. */
window.DocumentLibraryUI = (() => {
  const labels={draft:'Roboczy',in_review:'Do przeglądu',ready:'Gotowy do użycia',archived:'Zarchiwizowany'};
  let filters={search:'',family:'',template_id:'',document_status:'',archived:'exclude',sort:'updated_at',direction:'desc'}, offset=0, sequence=0;
  const limit=25;
  const date=value=>value?new Date(value).toLocaleString('pl-PL'):'Brak danych';
  async function open(ui) {
    const e=ui.escape;
    const options=(values,current)=>values.map(([v,l])=>`<option value="${e(v)}" ${v===current?'selected':''}>${e(l)}</option>`).join('');
    ui.main.innerHTML=`<section id="library-view"><div class="heading"><div><p class="eyebrow">TRIPSE / ZAPISANE DOKUMENTY</p><h1>Biblioteka dokumentów</h1><p class="muted">Pełna konfiguracja i snapshoty. Status „Gotowy” nie oznacza zatwierdzenia do publikacji.</p></div><button class="primary" data-go="templates">+ Nowy dokument</button></div><form id="library-filters" class="panel library-filters"><label>Szukaj po nazwie<input data-library-filter="search" maxlength="200" value="${e(filters.search)}" type="search"></label><label>Rodzina<select data-library-filter="family">${options([['','Wszystkie'],['offer','Oferty'],['pilot','Piloci'],['marketing','Marketing']],filters.family)}</select></label><label>Szablon<select data-library-filter="template_id">${options([['','Wszystkie'],...ui.templates.map(t=>[t.template_id,t.name])],filters.template_id)}</select></label><label>Status<select data-library-filter="document_status">${options([['','Wszystkie'],...Object.entries(labels)],filters.document_status)}</select></label><label>Archiwum<select data-library-filter="archived">${options([['exclude','Aktywne dokumenty'],['include','Aktywne i archiwalne'],['only','Tylko archiwum']],filters.archived)}</select></label><label>Sortowanie<select data-library-filter="sort">${options([['updated_at','Ostatnia modyfikacja'],['created_at','Data utworzenia'],['title','Nazwa']],filters.sort)}</select></label><label>Kierunek<select data-library-filter="direction">${options([['desc','Malejąco'],['asc','Rosnąco']],filters.direction)}</select></label><button type="button" id="library-reset">Wyczyść filtry</button></form><p id="library-state" role="status"></p><div id="library-results"></div><div class="actions library-pages"><button id="library-previous">← Poprzednie</button><span id="library-page"></span><button id="library-next">Następne →</button></div></section>`;
    const root=ui.main.querySelector('#library-view');let timer, working=false;const pending=new Map();
    async function load() {
      if(!root.isConnected)return;
      const version=++sequence;
      const query=new URLSearchParams({...Object.fromEntries(Object.entries(filters).filter(([,v])=>v!=='')),offset:String(offset),limit:String(limit)});
      root.querySelector('#library-state').textContent='Wczytywanie biblioteki…';
      try {
        const page=await ui.api('library?'+query);
        if(version!==sequence||!root.isConnected)return;
        if(offset>0&&offset>=page.total){offset=Math.max(0,Math.floor(Math.max(0,page.total-1)/limit)*limit);return load();}
        root.querySelector('#library-state').textContent=page.total?`Dokumenty: ${page.total}`:'Brak dokumentów pasujących do filtrów.';
        root.querySelector('#library-results').innerHTML=`<div class="library-grid">${page.items.map(row=>{
          const archived=row.document_status==='archived', preview='/api/document-studio/drafts/'+encodeURIComponent(row.document_id)+'/preview';
          return `<article class="panel library-document" data-document-id="${e(row.document_id)}"><div class="meta"><span class="tag">${e(ui.templates.find(t=>t.template_id===row.template_id)?.name||row.template_id)}</span><span class="tag">${e(labels[row.document_status])}</span></div><h2>${e(row.title)}</h2><p>${e(row.source_type==='trip'?'Wycieczka':'Kampania')}: ${e(row.source_title)}</p><dl class="library-metadata"><dt>Utworzono</dt><dd>${e(date(row.created_at))}</dd><dt>Zmodyfikowano</dt><dd>${e(date(row.updated_at))}</dd><dt>Rewizja</dt><dd>${row.revision}</dd></dl><div class="actions"><button data-go="edit-draft/${e(row.document_id)}" ${archived?'disabled':''}>Otwórz / Edytuj</button><a href="${preview}" target="_blank" rel="noopener">Podgląd</a><button data-go="revisions/${e(row.document_id)}">Historia</button><button data-library-action="duplicate">Duplikuj</button><button data-library-action="${archived?'restore':'archive'}">${archived?'Przywróć':'Archiwizuj'}</button></div>${archived?'<p class="muted">Przywróć dokument przed edycją. Podgląd i historia pozostają dostępne.</p>':`<div class="library-status"><label>Status biznesowy<select class="library-status-value">${options(Object.entries(labels).filter(([k])=>k!=='archived'),row.document_status)}</select></label><button data-library-action="status">Zmień status</button></div>`}</article>`;
        }).join('')}</div>`;
        root.querySelector('#library-page').textContent=page.total?`${offset+1}–${offset+page.items.length} z ${page.total}`:'0';
        root.querySelector('#library-previous').disabled=offset===0;
        root.querySelector('#library-next').disabled=!page.has_more;
        for(const button of root.querySelectorAll('[data-library-action]'))button.onclick=async()=>{
          if(working)return;
          const card=button.closest('[data-document-id]'),row=page.items.find(r=>r.document_id===card.dataset.documentId),action=button.dataset.libraryAction;
          if(action==='archive'&&!confirm('Przenieść dokument do archiwum? Treść i zdjęcia zostaną zachowane.'))return;
          working=true;ui.busy(true);card.querySelectorAll('button,select').forEach(b=>b.disabled=true);
          const key=`${row.document_id}/${action}/${row.revision}`;
          if(!pending.has(key))pending.set(key,crypto.randomUUID());
          const body={revision:row.revision,operation_id:pending.get(key)};
          if(action==='status')body.document_status=card.querySelector('.library-status-value').value;
          try {
            const result=await ui.api(`library/${encodeURIComponent(row.document_id)}/${action}`,{method:'POST',body:JSON.stringify(body)});
            pending.delete(key);
            let warning='';try{await ui.refresh();}catch{warning=' Licznik biblioteki wymaga odświeżenia.';}
            ui.message((action==='duplicate'?'Utworzono niezależną kopię.':`Zmiana zapisana. Rewizja ${result.revision}.`)+warning,!!warning);
            offset=0;await load();
          }catch(error){ui.message(error.message,true);await load();}
          finally{working=false;ui.busy(false);}
        };
      }catch(error){if(version===sequence&&root.isConnected)root.querySelector('#library-state').textContent='Nie udało się wczytać biblioteki: '+error.message;}
    }
    root.querySelector('#library-filters').onsubmit=event=>{event.preventDefault();clearTimeout(timer);load();};
    for(const field of root.querySelectorAll('[data-library-filter]'))field.addEventListener('input',()=>{
      filters[field.dataset.libraryFilter]=field.value;offset=0;clearTimeout(timer);timer=setTimeout(load,field.type==='search'?250:0);
    });
    root.querySelector('#library-reset').onclick=()=>{filters={search:'',family:'',template_id:'',document_status:'',archived:'exclude',sort:'updated_at',direction:'desc'};offset=0;open(ui);};
    root.querySelector('#library-previous').onclick=()=>{offset=Math.max(0,offset-limit);load();};
    root.querySelector('#library-next').onclick=()=>{offset+=limit;load();};
    await load();
  }
  async function history(identifier,ui) {
    const e=ui.escape,rows=await ui.api('library/'+encodeURIComponent(identifier)+'/revisions');
    const prefix='/api/document-studio/library/'+encodeURIComponent(identifier)+'/revisions/';
    ui.main.innerHTML=`<button data-go="drafts">← Wróć do biblioteki</button><div class="heading"><div><h1>Historia dokumentu</h1><p>${e(rows[0]?.title||'Dokument')}</p><p class="muted">Historia obejmuje zachowane zapisy od uruchomienia biblioteki. Nie odtwarzamy brakujących wcześniejszych wersji ani autorów.</p></div></div><div class="history-layout"><section class="panel"><label>Zapisana rewizja<select id="history-revision">${rows.map(row=>`<option value="${row.revision}">Rewizja ${row.revision} · ${e(date(row.updated_at))} · ${e(labels[row.document_status])}</option>`).join('')}</select></label><p id="history-author"></p><a id="history-preview" target="_blank" rel="noopener">Otwórz podgląd / roboczy PDF</a><p class="notice">Historia jest tylko do odczytu. Status „Gotowy” nie uchyla walidacji eksportu. Przywracanie treści dawnej wersji nie jest częścią tej iteracji.</p></section><iframe id="history-frame" title="Podgląd zapisanej rewizji"></iframe></div>`;
    const select=ui.main.querySelector('#history-revision');
    select.onchange=()=>{
      const row=rows.find(r=>String(r.revision)===select.value),href=prefix+select.value+'/preview';
      ui.main.querySelector('#history-author').textContent=row.updated_by?'Ostatni edytujący: '+row.updated_by:'Autor ostatniego zapisu nieustalony.';
      ui.main.querySelector('#history-preview').href=href;ui.main.querySelector('#history-frame').src=href;
    };
    if(rows.length)select.onchange();
  }
  return {open,history};
})();
