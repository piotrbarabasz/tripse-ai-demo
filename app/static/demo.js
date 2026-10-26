"use strict";
(() => {
 const $ = id => document.getElementById(id);
 let conversation = sessionStorage.getItem('tripse-conversation') || crypto.randomUUID();
 sessionStorage.setItem('tripse-conversation',conversation);
 let last = null, busy = false, pending = false, known = new Set();
 function bubble(text, kind='bot') {
  const node = document.createElement('div'); node.className = 'bubble '+kind;
  const parts = text.split(/(https?:\/\/[^\s]+)/g);
  parts.forEach(part => { try { const u = new URL(part); if (/^\/trip\/[A-Za-z0-9_-]{43}$/.test(u.pathname)) { const a=document.createElement('a'); a.href=u.pathname; a.textContent='Otwórz plan i mapę →'; node.append(a); return; } } catch (_) {} node.append(document.createTextNode(part)); });
  $('messages').append(node); node.scrollIntoView({block:'nearest'});
 }
 async function api(url, opts) {const r=await fetch(url,opts); const data=await r.json(); if(!r.ok) throw new Error(typeof data.detail==='string'?data.detail:'Nieprawidłowe dane.'); return data;}
 async function poll(){
  try { const data=await api('/api/demo/conversations/'+conversation); data.messages.forEach(m=>{if(!known.has(m.id)){known.add(m.id);bubble(m.text);}});
   const j=data.jobs.at(-1); $('progress').textContent=j ? `Zadanie ${j.trip_id.slice(0,8)} · ${j.stage || (j.status==='queued'?' W kolejce · oczekiwanie na przetwarzanie':j.status)}${j.delivery_status==='pending'?'  · odpowiedź oczekuje na wysyłkę':''}` : 'Gotowe na twoją wiadomość.';
  } catch(e){$('progress').textContent=e.message;}
 }
 async function submit(replay=false){if(busy)return;busy=true;$('send').disabled=true;
  try {if(!replay && !(pending && last?.conversation===conversation && last.text===$('chat-text').value && last.case===$('case').value)){last={conversation,message_id:crypto.randomUUID(),text:$('chat-text').value,case:$('case').value};bubble(last.text,'user');}
   pending=true;
   const result=await api('/api/demo/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(last)});
   pending=false;
   if(result.status==='duplicate')bubble('Duplikat zdarzenia: zachowano to samo zadanie '+result.trip_id+'.');
   $('replay').disabled=false; await poll();
  }catch(e){bubble(e.message,'error');}finally{busy=false;$('send').disabled=false;$('replay').disabled=!last;}
 }
 $('chat-form').addEventListener('submit',e=>{e.preventDefault();submit();});
 $('replay').onclick=()=>submit(true);
 $('new-chat').onclick=()=>{conversation=crypto.randomUUID();sessionStorage.setItem('tripse-conversation',conversation);known.clear();last=null;pending=false;$('messages').replaceChildren();$('replay').disabled=true;poll();};
 api('/api/demo/scenarios').then(data=>{for(const s of data.scenarios){const b=document.createElement('button');b.className='secondary-button';b.textContent=s.name;b.onclick=()=>{$('chat-text').value=s.text;$('chat-text').focus();};$('examples').append(b);}for(const [value,label] of Object.entries(data.cases)){const o=document.createElement('option');o.value=value;o.textContent=label;$('case').append(o);}$('chat-text').value=data.scenarios[0].text;}).catch(e=>bubble(e.message,'error'));
 poll();setInterval(poll,1000);
})();
