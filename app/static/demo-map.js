"use strict";
window.renderDemoMap = (plan, onSelectDay) => {
 const host=document.getElementById('map'); host.replaceChildren();
 const ns='http://www.w3.org/2000/svg';
 const make=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text)n.textContent=text;return n;};
 const svg=make('svg',{viewBox:'0 0 800 600',role:'img','aria-label':'Mapa demonstracyjna: schemat miejsc i połączeń, bez przebiegu dróg'});
 const group=make('g');svg.append(group);host.append(svg);
 const places=plan.places || [];if(!places.length){document.getElementById('map-status').textContent='Ten starszy plan demo nie ma danych mapy. Utwórz nowy plan ze strony głównej.';return;}
 const lng=places.map(p=>p.lng), lat=places.map(p=>p.lat), minX=Math.min(...lng), maxX=Math.max(...lng), minY=Math.min(...lat), maxY=Math.max(...lat);
 const scale=Math.min(620/Math.max(maxX-minX,.02),420/Math.max(maxY-minY,.02));
 // Spread close stops on this explicitly schematic map so pins remain usable.
 const positions=places.map(p=>[400+(p.lng-(minX+maxX)/2)*scale,300-(p.lat-(minY+maxY)/2)*scale]);
 for(let step=0;step<60;step++)for(let a=0;a<positions.length;a++)for(let b=a+1;b<positions.length;b++){
  const pa=positions[a],pb=positions[b];let dx=pb[0]-pa[0],dy=pb[1]-pa[1],distance=Math.hypot(dx,dy);
  if(distance<78){if(distance<.01){dx=1;dy=1;distance=Math.SQRT2;}const push=(78-distance)/2;pa[0]-=dx/distance*push;pa[1]-=dy/distance*push;pb[0]+=dx/distance*push;pb[1]+=dy/distance*push;}
 }
 const xy=p=>{const i=places.findIndex(v=>v.lng===p.lng&&v.lat===p.lat);return i>=0?positions[i]:[400,300];};
 group.append(make('rect',{x:-4000,y:-4000,width:8000,height:8000,fill:'#eaf0e7'}));
 for(let i=0;i<8;i++)group.append(make('path',{d:`M ${-200+i*160} -400 Q ${200+i*90} 200 ${-100+i*160} 1000`,fill:'none',stroke:'#d5e2d0','stroke-width':40}));
 const lines=[];
 plan.days.forEach((d,i)=>{if(d.routing_status!=='demo'||!d.demo_geometry)return;const points=d.demo_geometry.map(([lng,lat])=>xy({lng,lat}).join(',')).join(' ');const line=make('polyline',{points,fill:'none',stroke:['#28745d','#4667af'][i%2],'stroke-width':5,'stroke-dasharray':'10 7','stroke-linejoin':'round',tabindex:0,role:'button','aria-label':`Wybierz dzień ${d.number}`});line.addEventListener('click',()=>onSelectDay(d.number));line.addEventListener('keydown',e=>{if(e.key==='Enter')onSelectDay(d.number);});group.append(line);lines.push([d.number,line]);});
 const info=document.createElement('p');info.className='demo-point-info'; info.textContent='Kliknij punkt, aby poznać przystanek. Przeciągnij mapę, aby ją przesunąć.';host.append(info);
 places.forEach((p,i)=>{const [x,y]=xy(p);const pin=make('g',{tabindex:0,role:'button','aria-label':p.name});pin.append(make('circle',{cx:x,cy:y,r:11,fill:'#fff',stroke:'#28745d','stroke-width':3}),make('text',{x,y:y+4,'text-anchor':'middle','font-size':10,fill:'#233e35'},String(i+1)),make('text',{x:x+15,y:y-12,'font-size':12,fill:'#233e35','paint-order':'stroke',stroke:'#f6f7f2','stroke-width':4},p.name));const show=()=>{info.textContent=p.name+' · '+(p.description||'Przystanek demonstracyjny');};pin.addEventListener('click',show);pin.addEventListener('keydown',e=>{if(e.key==='Enter')show();});group.append(pin);});
 let box=[0,0,800,600],drag=null;
 const update=()=>svg.setAttribute('viewBox',box.join(' '));
 const fit=number=>{const ps=number===null?places:plan.days.find(d=>d.number===number)?.stops||places;const points=ps.map(xy);const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);const w=Math.max(Math.max(...xs)-Math.min(...xs)+160,240),h=Math.max(Math.max(...ys)-Math.min(...ys)+160,180);box=[(Math.min(...xs)+Math.max(...xs))/2-w/2,(Math.min(...ys)+Math.max(...ys))/2-h/2,w,h];update();};
 const zoom=f=>{const w=Math.min(2400,Math.max(80,box[2]*f)),h=w*box[3]/box[2];box=[box[0]+(box[2]-w)/2,box[1]+(box[3]-h)/2,w,h];update();};
 const controls=document.createElement('div');controls.className='map-controls';[['+','Powiększ',()=>zoom(.8)],['−','Pomniejsz',()=>zoom(1.25)],['↺','Dopasuj mapę',()=>fit(null)]].forEach(([text,label,click])=>{const b=document.createElement('button');b.textContent=text;b.title=label;b.setAttribute('aria-label',label);b.onclick=click;controls.append(b);});host.append(controls);
 svg.addEventListener('pointerdown',e=>{if(e.target.closest('[role=button]'))return;drag=[e.clientX,e.clientY,...box];svg.setPointerCapture(e.pointerId);});svg.addEventListener('pointermove',e=>{if(!drag)return;const rect=svg.getBoundingClientRect();box=[drag[2]-(e.clientX-drag[0])*drag[4]/rect.width,drag[3]-(e.clientY-drag[1])*drag[5]/rect.height,drag[4],drag[5]];update();});svg.addEventListener('pointerup',()=>drag=null);svg.addEventListener('pointercancel',()=>drag=null);
 window.selectDemoDay=number=>{lines.forEach(([day,line])=>{line.setAttribute('opacity',number===null||number===day?1:.2);line.setAttribute('stroke-width',number===day?8:5);});fit(number);};
 document.getElementById('map-status').hidden=true;
 document.getElementById('map-caption').textContent='DEMO · schemat połączeń, nie mapa drogowa. Czasy i dystanse są przykładowe. N ↑';fit(null);
};
