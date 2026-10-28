/* Shared source filtering. Origin labels organize data; they grant no permissions. */
window.SourcePicker = (() => {
  const categories={private:'Wyjazd indywidualny / prywatny',self_guide:'Self-Guide',school:'Wycieczka szkolna',incentive:'Wyjazd firmowy / incentive',group:'Wyjazd grupowy / zorganizowany',other:'Pozostałe'};
  const origins={business:'Dane biznesowe',demo:'DEMO',synthetic_test:'TEST — syntetyczne',unknown:'Pochodzenie nieustalone'};
  const suggested={'offer.private':'private','offer.self_guide':'self_guide','offer.school':'school','offer.incentive':'incentive'};
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fold=value=>String(value??'').toLocaleLowerCase('pl').replaceAll('ł','l').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  function matches(item, f={}) {
    const origin=item.data_origin||'unknown', cats=item.categories||[];
    if(f.origin&&f.origin!=='regular'&&origin!==f.origin)return false;
    if((!f.origin||f.origin==='regular')&&!(origin==='business'||origin==='unknown'||f.demo&&origin==='demo'||f.test&&origin==='synthetic_test'))return false;
    if(!f.all&&f.category==='unassigned'&&cats.length)return false;
    if(!f.all&&f.category&&f.category!=='unassigned'&&!cats.includes(f.category)&&!(f.unassigned&&!cats.length))return false;
    return fold([item.title,...(item.destinations||[])].join(' ')).includes(fold(f.search));
  }
  const categoryFields=(values=[],name='categories')=>`<fieldset class="source-categories"><legend>Kategorie wycieczki</legend>${Object.entries(categories).map(([key,label])=>`<label><input type="checkbox" name="${escape(name)}" value="${key}" ${values.includes(key)?'checked':''}>${label}</label>`).join('')}</fieldset>`;
  const originField=(value='business',id='data-origin')=>`<label>Pochodzenie danych<select id="${escape(id)}"><option value="business" ${value==='business'?'selected':''}>Dane biznesowe TRIPSE</option><option value="demo" ${value==='demo'?'selected':''}>Przykład DEMO</option><option value="unknown" ${value==='unknown'?'selected':''}>Pochodzenie nieustalone</option>${value==='synthetic_test'?'<option value="synthetic_test" selected>TEST — rekord automatyczny</option>':''}</select></label><small>Oznaczenie organizacyjne nie potwierdza wiarygodności informacji.</small>`;
  function mount(root, config) {
    let entries=config.entries, selected=new Set(config.selected||[]);
    const multiple=!!config.multiple, campaign=config.kind==='campaign';
    const filters=Object.assign({category:config.category||'',search:'',origin:'regular',demo:false,test:false,all:false,unassigned:false},config.state||{});
    const filtersHTML=`<div class="source-filters">${campaign?'':`<label>Filtr kategorii wycieczek<select data-source-filter="category"><option value="">Wszystkie kategorie</option>${Object.entries(categories).map(([v,l])=>`<option value="${v}" ${filters.category===v?'selected':''}>${l}</option>`).join('')}<option value="unassigned">Nieprzypisane</option></select></label>`}<label>Szukaj ${campaign?'kampanii':'wycieczki po nazwie lub kierunku'}<input type="search" maxlength="200" data-source-filter="search"></label></div>
      <details class="source-advanced"><summary>Filtry dodatkowe</summary><div class="source-filters">${campaign?'':'<label><input type="checkbox" data-source-filter="all"> Pokaż wszystkie kategorie</label><label><input type="checkbox" data-source-filter="unassigned"> Uwzględnij nieprzypisane</label>'}<label>Pochodzenie danych<select data-source-filter="origin"><option value="regular">Biznesowe i nieustalone</option><option value="business">Tylko biznesowe</option><option value="unknown">Tylko nieustalone</option><option value="demo">Tylko DEMO</option><option value="synthetic_test">Tylko TEST — administracyjne</option></select></label><label><input type="checkbox" data-source-filter="demo"> Pokaż dane DEMO</label><label><input type="checkbox" data-source-filter="test"> Uwzględnij syntetyczne dane TEST</label></div></details>`;
    root.innerHTML=filtersHTML+`<p class="source-filter-summary muted"></p><p class="source-result-state" role="status"></p><label>${campaign?'Kampania':multiple?'Wycieczki kolekcji':'Wycieczka'}${multiple?' — wybierz co najmniej jedną (wymagane)':''}<select id="${escape(config.id)}" ${multiple?'size="4" multiple':''} aria-label="${campaign?'Kampanie':'Wycieczki'} — lista"></select></label>${multiple?'<div class="source-selected" aria-live="polite"></div>':''}`;
    const select=root.querySelector('#'+config.id);
    let visible=[];
    function draw() {
      const category=root.querySelector('[data-source-filter="category"]');if(category){category.disabled=filters.all;category.value=filters.all?'':filters.category;}
      for(const key of ['demo','test'])root.querySelector('[data-source-filter="'+key+'"]').closest('label').hidden=filters.origin!=='regular';
      const scope=filters.all||!filters.category?'wszystkie kategorie':filters.category==='unassigned'?'nieprzypisane':categories[filters.category];
      const origin=filters.origin==='regular'?'biznesowe i nieustalone'+(filters.demo?', DEMO':'')+(filters.test?', TEST':''):origins[filters.origin];
      root.querySelector('.source-filter-summary').textContent=(campaign?'':'Zakres: '+scope+(filters.unassigned&&!filters.all?' oraz nieprzypisane':'')+'. ')+'Dane: '+origin+'.';
      visible=entries.filter(x=>!(config.exclude?.()||[]).includes(x.trip_id||x.campaign_id)&&matches(x,filters));
      if(!multiple&&![...selected].every(id=>visible.some(x=>(x.trip_id||x.campaign_id)===id)))selected.clear();
      select.innerHTML=(multiple?'':'<option value="">— Wybierz '+(campaign?'kampanię':'wycieczkę')+' —</option>')+visible.map(x=>{
        const id=x.trip_id||x.campaign_id;
        const info=campaign?`${x.layout_variant==='theme_collection'?'Kolekcja tematyczna':'Nowe kierunki'} · ${x.items.length} kierunków`:`${(x.destinations||[]).join(', ')||'Kierunek nieustalony'} · ${x.duration_days} dni · ${(x.categories||[]).map(c=>categories[c]).join(', ')||'Nieprzypisane'}`;
        return `<option value="${escape(id)}" title="${escape(x.title+' — '+info+' · '+origins[x.data_origin||'unknown'])}" ${selected.has(id)?'selected':''}>${escape(x.title)} — ${escape(info)} · ${escape(origins[x.data_origin||'unknown'])}</option>`;
      }).join('');
      if(!multiple)select.value=[...selected][0]||'';
      let current=root.querySelector('.source-current');
      if(!current){current=document.createElement('p');current.className='source-current';current.setAttribute('aria-live','polite');select.closest('label').after(current);}
      const chosen=entries.find(x=>(x.trip_id||x.campaign_id)===[...selected][0]);
      current.textContent=chosen&&!multiple?[chosen.title,campaign?`${chosen.items.length} kierunków`:`${(chosen.destinations||[]).join(', ')} · ${chosen.duration_days} dni · ${(chosen.categories||[]).map(c=>categories[c]).join(', ')||'Nieprzypisane'}`,origins[chosen.data_origin||'unknown']].join(' — '):'';
      const state=root.querySelector('.source-result-state');
      state.textContent=visible.length?`Pasujące ${campaign?'kampanie':'wycieczki'}: ${visible.length}`:!entries.length?`Nie masz jeszcze ${campaign?'zapisanych kampanii':'przygotowanych wycieczek'}. Wybierz utworzenie nowej ${campaign?'kampanii':'wycieczki'}.`:`Brak ${campaign?'kampanii':'wycieczek'} pasujących do filtrów. Zmień kategorię lub wyszukiwanie; dodatkowe możliwości znajdziesz w filtrach dodatkowych.`;
      if(multiple){
        const summary=root.querySelector('.source-selected');
        summary.innerHTML='<p>Wybrane kierunki: '+selected.size+'</p>'+[...selected].map(id=>`<button type="button" data-remove-source="${escape(id)}">${escape(entries.find(x=>x.trip_id===id)?.title||id)} ×</button>`).join('');
        summary.querySelectorAll('[data-remove-source]').forEach(b=>b.onclick=()=>{selected.delete(b.dataset.removeSource);draw();config.onChange?.([...selected]);});
      }
      config.onChange?.([...selected]);
      config.onResults?.(visible);
    }
    select.onchange=()=>{
      if(multiple){
        const chosen=new Set([...select.selectedOptions].map(option=>option.value));
        for(const x of visible)if(!chosen.has(x.trip_id||x.campaign_id))selected.delete(x.trip_id||x.campaign_id);
        for(const option of select.selectedOptions)if(option.value)selected.add(option.value);
      }else selected=new Set(select.value?[select.value]:[]);
      // Rendering preserves selected entries across category/search changes in multi-select mode.
      draw();
    };
    root.querySelectorAll('[data-source-filter]').forEach(field=>field.oninput=()=>{
      filters[field.dataset.sourceFilter]=field.type==='checkbox'?field.checked:field.value;
      if(config.state)Object.assign(config.state,filters);
      const category=root.querySelector('[data-source-filter="category"]');if(category)category.disabled=filters.all;
      draw();
    });
    if(config.cards)select.closest('label').hidden=true;
    for(const field of root.querySelectorAll('[data-source-filter]')){const value=filters[field.dataset.sourceFilter];if(field.type==='checkbox')field.checked=!!value;else field.value=value;}
    const category=root.querySelector('[data-source-filter="category"]');if(category)category.disabled=filters.all;
    draw();
    return {get values(){return [...selected];},refresh(){draw();},reveal(item){
      const id=item.trip_id||item.campaign_id;entries=entries.filter(x=>(x.trip_id||x.campaign_id)!==id).concat(item);
      filters.category='';filters.all=true;filters.search='';filters.origin=item.data_origin||'unknown';
      for(const field of root.querySelectorAll('[data-source-filter]')){const value=filters[field.dataset.sourceFilter];if(field.type==='checkbox')field.checked=!!value;else field.value=value;}
      selected=new Set([id]);draw();
    }};
  }
  return {categories,origins,suggested,matches,categoryFields,originField,mount};
})();
