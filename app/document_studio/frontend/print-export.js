/* Controlled DOM only. Preview and window.print share the same measured pages. */
window.documentReady=false;
window.layoutErrors=[];
window.layoutDiagnostics=[];
window.layoutMetrics={};
const pageRoot=document.querySelector('#pages');
function newPage(){
  const wrap=document.querySelector('#page-template').content.firstElementChild.cloneNode(true);
  pageRoot.append(wrap);return wrap.querySelector('.page-body');
}
function fits(body){return body.scrollHeight<=body.clientHeight+1&&body.scrollWidth<=body.clientWidth+1;}
function issue(kind,section,message){window.layoutDiagnostics.push({kind,section,message});window.layoutErrors.push(message);}
function titleOf(block){return block?.querySelector('h1,h2,h3,.eyebrow')?.textContent.trim()||'Treść dokumentu';}
function dayContext(block){
  const context=block.dataset.context,heading=block.querySelector('h1,h2');
  if(context&&heading&&!heading.textContent.startsWith(context)&&!heading.querySelector('.day-context')){
    const label=document.createElement('span');label.className='day-context';label.textContent=context;heading.prepend(label);
  }
}
function continued(heading){
  const copy=heading.cloneNode(true);
  copy.querySelector('.row-continuation-label')?.remove();
  if(!copy.querySelector('.continuation-label')){
    const label=document.createElement('span');label.className='continuation-label';label.textContent=' · cd.';copy.append(label);
  }
  return copy;
}
function atomic(node){return node.nodeType===1&&(node.matches('h1,h2,h3,thead,img,svg,.photo,.card-meta,.date-label,.operation-status')||!node.childNodes.length);}
function tokenNeedsSplit(token,target,body){
  if(!token)return false;
  const style=getComputedStyle(target),probe=document.createElement('div');
  probe.style.cssText='position:fixed;visibility:hidden;white-space:pre-wrap;overflow-wrap:anywhere;left:0;top:0;';
  probe.style.width=Math.max(1,target.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight))+'px';
  for(const property of ['fontFamily','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing'])probe.style[property]=style[property];
  probe.textContent=token;document.body.append(probe);
  const height=probe.getBoundingClientRect().height;probe.remove();
  const block=target.closest('.block'),heading=block?.querySelector('h1,h2'),thead=block?.querySelector('thead');
  const context=(heading?.getBoundingClientRect().height||0)+(thead?.getBoundingClientRect().height||0)+parseFloat(getComputedStyle(body).paddingTop)+parseFloat(style.paddingTop)+parseFloat(style.paddingBottom);
  return height>body.clientHeight-context;
}
/* Move a fitting prefix of a disposable DOM clone, preserving source characters. */
function takeText(source,target,body){
  const value=source.data,part=document.createTextNode('');target.append(part);
  let lo=0,hi=value.length;
  while(lo<hi){const mid=Math.ceil((lo+hi)/2);part.data=value.slice(0,mid);if(fits(body))lo=mid;else hi=mid-1;}
  let end=lo;
  const prefix=value.slice(0,end);
  const paragraph=prefix.lastIndexOf('\n\n'),line=prefix.lastIndexOf('\n'),space=prefix.search(/\s+\S*$/u);
  const boundary=paragraph>=end*.45?paragraph+2:line>=end*.6?line+1:space>0?space+1:0;
  if(boundary)end=boundary;
  // A short word, time or address moves intact to the next fragment. Only a
  // genuinely page-sized unbroken token needs a character-level fallback.
  if(!boundary&&end<value.length&&!tokenNeedsSplit(value.match(/^\S+/u)?.[0],target,body)){part.remove();return false;}
  if(end>0&&end<value.length&&/[\uD800-\uDBFF]/.test(value[end-1]))end--;
  if(!end){part.remove();return false;}
  part.data=value.slice(0,end);source.data=value.slice(end);if(!source.data)source.remove();return true;
}
function takeChildren(source,target,body){
  let moved=false;
  while(source.firstChild){
    const node=source.firstChild;target.append(node);
    if(fits(body)){moved=true;continue;}
    source.prepend(node);
    if(node.nodeType===3){if(takeText(node,target,body))moved=true;break;}
    if(atomic(node))break;
    const shell=node.cloneNode(false);target.append(shell);
    if(takeChildren(node,shell,body)){moved=true;if(!node.childNodes.length)node.remove();}
    else shell.remove();
    break;
  }
  return moved;
}
function tableShell(table){
  const result=table.cloneNode(false);
  for(const node of table.children)if(node.tagName!=='TBODY')result.append(node.cloneNode(true));
  result.append(document.createElement('tbody'));return result;
}
function splitTable(block,body){
  const table=block.querySelector(':scope > table');if(!table?.tBodies[0])return null;
  const head=block.cloneNode(false),tail=block.cloneNode(false);
  const heading=block.querySelector(':scope > h2,:scope > .eyebrow');
  if(heading){head.append(heading.cloneNode(true));tail.append(continued(heading));}
  const first=tableShell(table),rest=tableShell(table);head.append(first);tail.append(rest);body.append(head);
  const rows=[...table.tBodies[0].rows].map((row,i)=>{const copy=row.cloneNode(true);copy.dataset.flowRow ||= String(i+1);return copy;});
  let index=0;
  for(;index<rows.length;index++){
    const row=rows[index];first.tBodies[0].append(row);
    if(fits(body))continue;
    const rowHeight=row.getBoundingClientRect().height;
    row.remove();
    const renderedHeading=head.querySelector('h2,.eyebrow'),headingStyle=renderedHeading?getComputedStyle(renderedHeading):null;
    const contextHeight=(renderedHeading?.getBoundingClientRect().height||0)+(headingStyle?parseFloat(headingStyle.marginTop)+parseFloat(headingStyle.marginBottom):0)+first.tHead.getBoundingClientRect().height+parseFloat(getComputedStyle(head).paddingTop)+parseFloat(getComputedStyle(body).paddingTop);
    // Ordinary operational rows stay intact. Only a row taller than a fresh
    // page's table body needs cell-level fragmentation.
    if(rowHeight<=body.clientHeight-contextHeight){rest.tBodies[0].append(row);index++;break;}
    const prefix=row.cloneNode(false),suffix=row.cloneNode(false);suffix.classList.add('row-continuation');
    const cells=[...row.cells];
    for(const cell of cells){prefix.append(cell.cloneNode(false));suffix.append(cell.cloneNode(false));}
    first.tBodies[0].append(prefix);
    let moved=false;
    cells.forEach((cell,i)=>{
      if(takeChildren(cell,prefix.cells[i],body))moved=true;
      suffix.cells[i].append(...cell.childNodes);
    });
    if(!moved||!prefix.textContent.trim()){
      [...prefix.cells].forEach((cell,i)=>suffix.cells[i].prepend(...cell.childNodes));
      prefix.remove();rest.tBodies[0].append(suffix);
    }
    else if([...suffix.cells].some(cell=>cell.childNodes.length))rest.tBodies[0].append(suffix);
    index++;break;
  }
  for(;index<rows.length;index++)rest.tBodies[0].append(rows[index]);
  const next=rest.tBodies[0].rows[0];
  if(next?.classList.contains('row-continuation')&&tail.querySelector('h2')){
    const label=document.createElement('span');label.className='row-continuation-label';label.textContent=' · wiersz '+next.dataset.flowRow;tail.querySelector('h2').append(label);
  }
  if(!first.tBodies[0].rows.length||!fits(body)){head.remove();return null;}
  return {head,tail:rest.tBodies[0].rows.length?tail:null};
}
function splitBlock(block,body){
  if(block.querySelector(':scope > table'))return splitTable(block,body);
  const work=block.cloneNode(true),head=block.cloneNode(false);body.append(head);
  const heading=block.querySelector('h2,h1'),moved=takeChildren(work,head,body);
  const content=head.querySelector('p,li,td,.photo');
  if(!moved||!content||(!content.textContent.trim()&&!content.matches('.photo'))||!fits(body)){head.remove();return null;}
  if(work.childNodes.length&&head.querySelectorAll('p,li').length===1&&content.matches('p,li')&&content.getBoundingClientRect().height<parseFloat(getComputedStyle(content).lineHeight)*3){head.remove();return null;}
  if(!work.childNodes.length)return {head,tail:null};
  work.classList.add('is-continuation');
  if(heading&&!work.querySelector('h1,h2')){
    const target=work.querySelector(':scope > .card-copy')||work;
    target.prepend(continued(heading));
  }
  return {head,tail:work};
}
function fitPreview(){
  for(const wrap of pageRoot.children){
    const sheet=wrap.firstElementChild,style=getComputedStyle(sheet),width=parseFloat(style.width),height=parseFloat(style.height);
    const scale=Math.min(1,Math.max(200,document.documentElement.clientWidth-24)/width);
    wrap.style.width=width*scale+'px';wrap.style.height=height*scale+'px';sheet.style.transform='scale('+scale+')';
  }
}
function geometryIssues(){
  for(const body of pageRoot.querySelectorAll('.page-body')){
    if(!fits(body))issue('layout',titleOf(body),'Sekcja «'+titleOf(body)+'» przekracza obszar strony. Sprawdź niepodzielny element lub szerokość tabeli.');
  }
}
async function prepareDocument(){
  const started=performance.now();await document.fonts.ready;
  const source=document.querySelector('#source-blocks'),blocks=[...source.children];
  await Promise.all([...source.querySelectorAll('img')].map(async img=>{
    try{await img.decode();}catch{issue('resource',titleOf(img.closest('.block')),'Nie udało się załadować zdjęcia w sekcji «'+titleOf(img.closest('.block'))+'». Wybierz dostępne zdjęcie lub usuń przypisanie.');}
  }));
  let body=newPage(),fragments=0,processed=0;
  for(const original of blocks){
    let block=original;block.remove();
    while(block){
      body.append(block);
      if(body.children.length===1)dayContext(block);
      if(fits(body)){block=null;continue;}
      const height=block.getBoundingClientRect().height;block.remove();
      if(height>body.clientHeight||block.matches('.document-section')||block.querySelector(':scope > table')){
        const split=splitBlock(block,body);
        if(split){fragments++;block=split.tail;if(block)body=newPage();continue;}
      }
      if(body.children.length){
        const previous=body,last=previous.lastElementChild;body=newPage();
        if(last&&(last.matches('.day-section')||block.matches('.cta,.keep-with-previous'))){
          body.append(last,block);
          if(fits(body)){block=null;continue;}
          block.remove();previous.append(last);
        }
        continue;
      }
      body.append(block);block.classList.add('compact');
      if(fits(body)){block=null;continue;}
      block.remove();const split=splitBlock(block,body);
      if(split){fragments++;block=split.tail;if(block)body=newPage();continue;}
      body.append(block);
      issue('layout',titleOf(block),'Sekcja «'+titleOf(block)+'» zawiera element, którego nie można zmieścić na stronie. Sprawdź nagłówek, zdjęcie lub pojedynczy wiersz tabeli.');
      block=null;
    }
    if(++processed%12===0)await new Promise(resolve=>setTimeout(resolve,0));
  }
  for(const wrap of [...pageRoot.children])if(!wrap.querySelector('.page-body').children.length)wrap.remove();
  if(!pageRoot.children.length)issue('layout','Dokument','Dokument nie zawiera treści do wydruku.');
  geometryIssues();
  const pages=[...pageRoot.querySelectorAll('.sheet')];
  pages.forEach((sheet,i)=>sheet.querySelector('.page-number').textContent=(i+1)+' / '+pages.length);
  const valid=document.body.dataset.valid==='true'&&!window.layoutErrors.length;
  document.body.classList.toggle('layout-error',!!window.layoutErrors.length);
  document.querySelector('#print-document').disabled=!valid;
  document.querySelector('#layout-status').textContent=window.layoutErrors.join(' ')||(valid?'Gotowe · '+pages.length+' str. W druku wybierz skalę 100%, grafikę tła i wyłącz nagłówki przeglądarki.':'Błąd walidacji danych: eksport zablokowany. Sprawdź uwagi do dokumentu.');
  window.layoutMetrics={preparationMs:performance.now()-started,pages:pages.length,splitFragments:fragments};
  fitPreview();window.documentReady=true;
}
document.querySelector('#print-document').addEventListener('click',()=>{
  if(window.documentReady&&!window.layoutErrors.length&&document.body.dataset.valid==='true')window.print();
});
window.addEventListener('resize',fitPreview);
prepareDocument().catch(()=>{
  issue('preparation','Dokument','Nie udało się przygotować wydruku. Odśwież podgląd i sprawdź zasoby.');
  document.body.classList.add('layout-error');document.querySelector('#layout-status').textContent=window.layoutErrors.join(' ');
  document.querySelector('#print-document').disabled=true;window.documentReady=true;
});
