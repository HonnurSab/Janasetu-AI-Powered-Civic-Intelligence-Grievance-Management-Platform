/* ==============================================================
   Janasetu — app.js (Premium Civic UI)
   Same API surface as before. New UX: event delegation via
   data-action, master-detail complaint drawer, inline SVG donut,
   citizen wizard, GIS workspace w/ hotspots, AI console.
   ============================================================== */

let role='citizen', active='overview', me=null, uiLang='en',
    activeMap=null, reportMarker=null, selectedLocation=null, mapMode='cluster',
    complaintsCache=[], auditCache=null, drawerId=null, drawerTab='details',
    wizard={step:1,text:'',district:'',ward:'',address:'',location:null,prediction:null,files:[]};

/* Basemap library for the GIS view. 'streets' is the original default map
   and stays untouched — the others are additional, switchable base layers. */
const BASEMAPS={
  streets:{label:'Streets',kn:'ಬೀದಿ',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'},
  satellite:{label:'Satellite',kn:'ಉಪಗ್ರಹ',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Esri, Maxar, Earthstar Geographics, GIS User Community'},
  terrain:{label:'Terrain',kn:'ಭೂಪ್ರದೇಶ',tiles:['https://a.tile.opentopomap.org/{z}/{x}/{y}.png','https://b.tile.opentopomap.org/{z}/{x}/{y}.png','https://c.tile.opentopomap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenTopoMap (CC-BY-SA) · SRTM'},
  night:{label:'Night',kn:'ರಾತ್ರಿ',tiles:['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png','https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png','https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors © CARTO'}
};
let basemapMode='streets';
const KARNATAKA_DISTRICT_GEOJSON='https://raw.githubusercontent.com/udit-001/india-maps-data/main/geojson/states/karnataka.geojson';
const KARNATAKA_TALUK_GEOJSON='https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IND_3.json';
let boundaryMode='districts', boundaryData=null;

/* All 31 Karnataka districts — used for the register form and the GIS
   district filter/summary so every district is selectable, not just a
   handful of Bengaluru-area ones. */
const KARNATAKA_DISTRICTS=['Bagalkot','Ballari','Belagavi','Bengaluru Rural','Bengaluru Urban','Bidar','Chamarajanagar','Chikkaballapura','Chikkamagaluru','Chitradurga','Dakshina Kannada','Davanagere','Dharwad','Gadag','Hassan','Haveri','Kalaburagi','Kodagu','Kolar','Koppal','Mandya','Mysuru','Raichur','Ramanagara','Shivamogga','Tumakuru','Udupi','Uttara Kannada','Vijayanagara','Vijayapura','Yadgir'];

const navs={
  citizen:[['overview','Home','ಮುಖಪುಟ'],['map','Civic Map','ನಾಗರಿಕ ನಕ್ಷೆ'],['report','Report Issue','ದೂರು ಸಲ್ಲಿಸಿ'],['complaints','My Complaints','ನನ್ನ ದೂರುಗಳು'],['assistant','AI Knowledge','AI ಸಹಾಯಕ']],
  department:[['overview','My Dashboard','ಡ್ಯಾಶ್‌ಬೋರ್ಡ್'],['map','Operations Map','ಕಾರ್ಯಾಚರಣೆ ನಕ್ಷೆ'],['complaints','Assigned Queue','ನಿಯೋಜಿತ ದೂರುಗಳು'],['assistant','AI Knowledge','AI ಸಹಾಯಕ']],
  admin:[['overview','Command Center','ಕಮಾಂಡ್ ಸೆಂಟರ್'],['map','GIS Intelligence','GIS ನಕ್ಷೆ'],['complaints','Complaint Queue','ದೂರುಗಳ ಸಾಲು'],['departments','Departments','ಇಲಾಖೆಗಳು'],['citizens','Citizens','ನಾಗರಿಕರು'],['officers','Officers','ಅಧಿಕಾರಿಗಳು'],['audit','Audit Log','ಆಡಿಟ್ ದಾಖಲೆ'],['assistant','AI Knowledge','AI ಸಹಾಯಕ']]
};
const T={
  en:{public:'Public statistics are aggregated. Individual citizen records remain private.',reportTitle:'Report a Civic Issue',reportHint:'Describe the issue in English or Kannada, attach evidence and confirm the location.',mapTitle:'Civic GIS Intelligence'},
  kn:{public:'ಸಾರ್ವಜನಿಕ ಅಂಕಿಅಂಶಗಳು ಒಟ್ಟು ರೂಪದಲ್ಲಿವೆ. ವೈಯಕ್ತಿಕ ನಾಗರಿಕ ಮಾಹಿತಿಯನ್ನು ಖಾಸಗಿಯಾಗಿ ಇಡಲಾಗುತ್ತದೆ.',reportTitle:'ನಾಗರಿಕ ಸಮಸ್ಯೆ ವರದಿ ಮಾಡಿ',reportHint:'ಸಮಸ್ಯೆಯನ್ನು ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ವಿವರಿಸಿ, ಸಾಕ್ಷ್ಯವನ್ನು ಸೇರಿಸಿ ಮತ್ತು ಸ್ಥಳವನ್ನು ದೃಢೀಕರಿಸಿ.',mapTitle:'ನಾಗರಿಕ GIS ಬುದ್ಧಿಮತ್ತೆ'}
};
const CAT_PALETTE=['#0f9c8f','#f2a530','#2563eb','#dc2626','#7c3aed','#0ea5e9','#16a34a','#db2777'];

/* ---------------- core helpers ---------------- */
async function get(u){const r=await fetch(u);if(r.status===401){location='/login';throw new Error('Authentication required')}const j=await r.json();if(!r.ok)throw new Error(j.error||'Request failed');return j}
async function postJson(u,body,timeoutMs){
  const ctrl=new AbortController();
  const timer=timeoutMs?setTimeout(()=>ctrl.abort(),timeoutMs):null;
  let r;
  try{r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{}),signal:ctrl.signal})}
  catch(e){if(e.name==='AbortError')throw Object.assign(new Error('Timed out waiting for a response.'),{payload:{error:'timeout'}});throw e}
  finally{if(timer)clearTimeout(timer)}
  if(r.status===401){location='/login';throw new Error('Authentication required')}
  let j; try{j=await r.json()}catch(e){throw Object.assign(new Error('Unexpected response from server.'),{payload:{error:'bad_response'}})}
  if(!r.ok)throw Object.assign(new Error(j.error||'Request failed'),{payload:j});
  return j;
}
function esc(s=''){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function byId(id){return document.getElementById(id)}
function qs(sel,root=document){return root.querySelector(sel)}

/* ---------------- init & navigation ---------------- */
async function init(){
  const x=await get('/api/me'); me=x.user; role=me.role;
  byId('profileName').textContent=role==='admin'?'Administrator':role==='department'?(me.officer_name||'Department Officer'):(me.citizen_name||'Resident');
  byId('profileSub').textContent=role==='admin'?'City / State Control Room':role==='department'?me.department:'Private citizen account';
  byId('roleBadge').textContent=role==='admin'?'ADMINISTRATOR':role==='department'?'DEPARTMENT OFFICER':'CITIZEN';
  renderNav();
  document.addEventListener('click',onDocClick);
  byId('langToggleBtn')?.addEventListener('click',toggleLanguage);
  byId('refreshBtn')?.addEventListener('click',()=>loadAll());
  loadAll();
}
function label(item){return uiLang==='kn'?item[2]:item[1]}
function renderNav(){byId('nav').innerHTML=navs[role].map(x=>`<button class="${active===x[0]?'active':''}" data-action="switch-view" data-view="${x[0]}"><span>${label(x)}</span></button>`).join('')}
function switchView(v){
  if(activeMap){try{activeMap.remove()}catch(e){} activeMap=null}
  active=v; wizard={step:1,text:'',district:me?.district||'Bengaluru Urban',ward:me?.ward||'',address:'',location:null,prediction:null};
  renderNav();
  const app=byId('app');
  if(app){app.style.opacity='0';app.style.transform='translateY(6px)';app.style.transition='opacity .18s ease, transform .18s ease';
    setTimeout(()=>{loadAll();requestAnimationFrame(()=>{app.style.opacity='1';app.style.transform='translateY(0)'})},120)}
  else loadAll();
}
function toggleLanguage(){uiLang=uiLang==='en'?'kn':'en';document.documentElement.lang=uiLang==='kn'?'kn':'en';byId('langLabel').textContent=uiLang==='en'?'ಕನ್ನಡ':'English';renderNav();loadAll()}

/* ---------------- event delegation: all click actions ---------------- */
function onDocClick(e){
  const t=e.target.closest('[data-action]'); if(!t) return;
  const a=t.dataset.action;
  switch(a){
    case 'switch-view': switchView(t.dataset.view); break;
    case 'open-drawer': openDrawer(t.dataset.id); break;
    case 'close-drawer': closeDrawer(); break;
    case 'drawer-tab': drawerTab=t.dataset.tab; renderDrawerBody(); break;
    case 'change-status': changeStatus(t.dataset.id,t.dataset.status); break;
    case 'map-apply': renderOperationalMap(); break;
    case 'map-mode': setMapMode(t.dataset.mode); break;
    case 'map-basemap': setBasemap(t.dataset.basemap); break;
    case 'boundary-mode': setBoundaryMode(t.dataset.mode); break;
    case 'state-view': showKarnatakaView(); break;
    case 'use-location': useMyLocation(); break;
    case 'classify-issue': classifyIssue(); break;
    case 'wizard-step': wizardStep(t.dataset.dir); break;
    case 'submit-complaint': submitComplaint(); break;
    case 'ask-ai': askAI(); break;
    case 'rebuild-rag': break;
    case 'create-officer': createOfficer(); break;
    case 'focus-hotspot': focusHotspot(parseFloat(t.dataset.lat),parseFloat(t.dataset.lng)); break;
    case 'filter-district': filterByDistrict(t.dataset.district); break;
    case 'close-boundary': byId('boundaryInfo')?.classList.remove('open'); break;
    case 'open-resolve': openResolvePanel(t.dataset.id); break;
    case 'submit-resolution': submitResolution(t.dataset.id); break;
  }
}

/* ---------------- shared widgets ---------------- */
function kpi(a,b,c=''){const n=Number(b);const animatable=Number.isFinite(n)&&String(b).trim()===String(n);return `<div class="card kpi"><small>${a}</small><b class="${c}" ${animatable?`data-count="${n}">0`:`>${b}`}</b></div>`}
function animateCounters(){document.querySelectorAll('[data-count]').forEach(el=>{const target=Number(el.getAttribute('data-count'))||0;const dur=650;const start=performance.now();function step(now){const p=Math.min(1,(now-start)/dur);const eased=1-Math.pow(1-p,3);el.textContent=Math.round(eased*target).toLocaleString();if(p<1)requestAnimationFrame(step)}requestAnimationFrame(step)})}

function donutSVG(entries){
  const total=entries.reduce((s,d)=>s+d.value,0)||1;
  const r=54,cx=70,cy=70,circ=2*Math.PI*r;
  let cum=0;
  const rings=entries.map((d,i)=>{
    const frac=d.value/total, dash=frac*circ, seg=
      `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${d.color}" stroke-width="17"
        stroke-dasharray="${dash.toFixed(2)} ${(circ-dash).toFixed(2)}" stroke-dashoffset="${(-cum).toFixed(2)}"
        transform="rotate(-90 ${cx} ${cy})" stroke-linecap="butt"/>`;
    cum+=dash; return seg;
  }).join('');
  return `<svg viewBox="0 0 140 140" width="152" height="152" role="img" aria-label="Category distribution donut chart">
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--canvas-sunken)" stroke-width="17"/>
    ${rings}
    <circle cx="${cx}" cy="${cy}" r="${r-11}" fill="var(--canvas-raised)"/>
    <text x="${cx}" y="${cy-4}" text-anchor="middle" font-family="Space Grotesk,sans-serif" font-size="22" font-weight="600" fill="var(--text-900)">${total}</text>
    <text x="${cx}" y="${cy+15}" text-anchor="middle" font-family="IBM Plex Sans,sans-serif" font-size="10" fill="var(--text-500)">total cases</text>
  </svg>`;
}
function donutLegend(entries){return `<div class="donutLegend">${entries.map(d=>`<div class="legendItem"><span class="legendDot" style="background:${d.color}"></span>${esc(d.label)}<b>${d.value}</b></div>`).join('')}</div>`}

/* ---------------- router ---------------- */
async function loadAll(){
  if(active==='assistant')return assistantView();
  if(active==='map')return mapView();
  if(active==='report')return reportView();
  if(active==='complaints')return complaintsView();
  if(active==='departments')return departmentsView();
  if(active==='citizens')return citizensView();
  if(active==='officers')return officersView();
  if(active==='audit')return auditView();
  return overviewView();
}

/* ---------------- AI console ---------------- */
async function assistantView(){
  byId('title').textContent=uiLang==='kn'?'Janasetu AI ಸಹಾಯಕ':'Janasetu AI Assistant';
  byId('subtitle').textContent=uiLang==='kn'?'ವೇಗವಾದ ಸ್ಥಳೀಯ ನಾಗರಿಕ AI ಸಹಾಯ.':'Fast local AI assistance for Karnataka civic services.';
  byId('app').innerHTML=`<div class="dashboardGrid"><div class="card span2"><div class="cardhead"><div><span class="eyebrow">JANASETU FAST AI</span><h2>Ask Janasetu</h2></div><span class="privacy">Instant rules + Local AI</span></div><p class="muted">Common civic questions answer instantly. Other questions use the smallest installed Ollama model; if the model is slow, Janasetu returns a safe fallback instead of timing out.</p><textarea id="aiQuestion" class="ragQuestion" rows="6" spellcheck="true" autocomplete="off" placeholder="Example: Who handles pothole complaints?"></textarea><div class="resultActions"><button type="button" id="aiAskButton" class="primary" data-action="ask-ai">Ask AI</button></div><div id="aiAnswer"></div></div><div class="card"><span class="eyebrow">FAST AI STATUS</span><h2>Local Ollama</h2><div id="aiStatus" class="muted">Checking…</div><p class="small muted">Recommended for speed: <b>qwen3:0.6b</b>. Run <code>setup_fast_ai.bat</code> once to install it.</p></div></div>`;
  try{const st=await get('/api/ai/status');byId('aiStatus').innerHTML=st.ollama?`<b>Ready</b><br><small>Selected: ${esc(st.selected_model||'—')}</small>`:`<b>Ollama offline</b><br><small>Instant civic answers still work.</small>`}catch(e){byId('aiStatus').textContent='Status unavailable.'}
  const q=byId('aiQuestion'); if(q)q.focus();
}
async function askAI(){
  const q=byId('aiQuestion'),box=byId('aiAnswer'); if(!q||!box)return;
  const question=q.value.trim(); if(!question){q.focus();return alert('Enter a question.')}
  const btn=byId('aiAskButton'); if(btn){btn.disabled=true;btn.textContent='Answering…'}
  box.innerHTML='<div class="predictionCard">Getting a fast Janasetu answer…</div>';
  try{
    const x=await postJson('/api/ai/ask',{question},35000);
    if(x.ok){box.innerHTML=`<div class="successBox"><b>AI answer</b><p>${esc(x.answer||'No answer returned.').replace(/\n/g,'<br>')}</p><small>${x.fast_path?'Instant Janasetu answer':'Local model: '+esc(x.model||'Ollama')}${x.warning?'<br>'+esc(x.warning):''}</small></div>`}
    else{box.innerHTML=`<div class="errorBox"><b>Could not get an answer</b><p>${esc(x.error||'The AI service did not return an answer.')}</p></div>`}
  }catch(e){box.innerHTML='<div class="successBox"><b>Janasetu assistant</b><p>The local model is busy. Common routing, evidence and complaint workflow questions are still available instantly; try a shorter civic question.</p></div>'}
  finally{if(btn){btn.disabled=false;btn.textContent='Ask AI'}}
}

/* ---------------- command center / overview ---------------- */
async function overviewView(){
  const [s,cats]=await Promise.all([get('/api/summary'),get('/api/categories')]);
  const pub=role==='citizen'?await get('/api/public-overview'):null;
  byId('eyebrow').textContent=role==='citizen'?'CITIZEN PORTAL':role==='department'?'DEPARTMENT OPERATIONS':'ADMINISTRATOR COMMAND CENTER';
  byId('title').textContent=role==='citizen'?(uiLang==='kn'?'ನಿಮ್ಮ ನಗರದ ನಾಗರಿಕ ಸ್ಥಿತಿ':'Civic health in your city'):role==='department'?'Department operations':'City & State Civic Command Center';
  byId('subtitle').textContent=role==='citizen'?T[uiLang].public:role==='department'?'Authorized workload, SLA and spatial operational intelligence.':'City-wide service demand, department performance, GIS hotspots and accountability.';

  const cards=role==='citizen'
    ?[kpi(uiLang==='kn'?'ನನ್ನ ದೂರುಗಳು':'My complaints',s.total,'','switch-view'),kpi('Open',s.open,'blue','switch-view'),kpi('Resolved',s.resolved,'good','switch-view'),kpi('Critical',s.critical,'danger','switch-view')]
    :[kpi('Cases in scope',s.total),kpi('Open',s.open,'blue','switch-view'),kpi('Resolved',s.resolved,'good','switch-view'),kpi('SLA at risk',s.sla_breached,'danger','switch-view')];

  const entries=Object.entries(cats).slice(0,8).map(([k,v],i)=>({label:k,value:v,color:CAT_PALETTE[i%CAT_PALETTE.length]}));
  const donut=entries.length?donutSVG(entries):'<p class="muted">No data yet</p>';
  const legend=entries.length?donutLegend(entries):'';

  const publicBlock=pub?`<div class="card span2"><div class="cardhead"><div><span class="eyebrow">PUBLIC CIVIC HEALTH</span><h2>${uiLang==='kn'?'ನಗರದ ಸಮಸ್ಯೆಗಳ ಒಟ್ಟು ಚಿತ್ರ':'City-wide issue picture'}</h2></div><span class="privacy">🔒 No personal identities</span></div><div class="grid3">${pub.wards.slice(0,6).map(x=>`<div class="mini"><b>${esc(x.ward)}</b><span>${x.issues} reported issues</span></div>`).join('')}</div></div>`:'';

  byId('app').innerHTML=`<div class="grid">${cards.join('')}</div><div class="dashboardGrid">${publicBlock}<div class="card"><div class="cardhead"><h2>Issue mix</h2><span class="muted">${role==='citizen'?'Private account scope':'Operational scope'}</span></div><div class="donutRow">${donut}${legend}</div></div><div class="card intelligence"><span class="eyebrow">JANASETU INTELLIGENCE</span><h2>${role==='citizen'?'Privacy by design':'Operational priorities'}</h2><p class="muted">${role==='citizen'?T[uiLang].public:'Use the GIS map to identify spatial clusters, high-risk cases and service pressure by location.'}</p><button class="secondaryButton" data-action="switch-view" data-view="map">Open GIS Intelligence</button></div></div>`;
  animateCounters();
}

/* ---------------- GIS workspace ---------------- */
function mapStyle(){const b=BASEMAPS[basemapMode]||BASEMAPS.streets;return {version:8,sources:{base:{type:'raster',tiles:b.tiles,tileSize:b.tileSize,attribution:b.attribution}},layers:[{id:'base',type:'raster',source:'base'}]}}
function newMap(container,center=[77.5946,12.9716],zoom=11.2){return new maplibregl.Map({container,style:mapStyle(),center,zoom,attributionControl:true})}
function fitFeatures(map,features){if(!features.length)return;const b=new maplibregl.LngLatBounds();features.forEach(f=>b.extend(f.geometry.coordinates));if(!b.isEmpty())map.fitBounds(b,{padding:60,maxZoom:14,duration:800})}

async function mapView(){
  byId('title').textContent=T[uiLang].mapTitle;
  byId('subtitle').textContent=role==='citizen'?'Public map uses aggregated locations to protect resident privacy.':'Authorized operational map with filters, hotspots and complaint details.';
  const hasHotspots=role!=='citizen';
  const districtOptions=`<option value="">${uiLang==='kn'?'ಎಲ್ಲಾ ಜಿಲ್ಲೆಗಳು':'All districts'}</option>`+KARNATAKA_DISTRICTS.map(d=>`<option value="${d}">${d}</option>`).join('');
  byId('app').innerHTML=`<div class="gisLayout"><div class="mapPanel"><div class="mapToolbar"><div><span class="eyebrow">GIS COMMAND MAP</span><h2>${role==='citizen'?'Public Civic Map':role==='department'?'Department Operations Map':'City / State Geospatial Intelligence'}</h2></div><div class="mapFilters"><select id="mapDistrict">${districtOptions}</select><select id="mapCategory"><option value="">All categories</option><option>Roads & Footpaths</option><option>Garbage & Sanitation</option><option>Water Supply</option><option>Streetlights & Electricity</option><option>Drainage & Flooding</option><option>Public Safety</option></select><select id="mapPriority"><option value="">All priorities</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select><button data-action="map-apply">Apply</button><button class="mapModeBtn active" data-action="map-mode" data-mode="cluster">Clusters</button><button type="button" class="boundaryBtn" data-action="state-view">Karnataka</button><button class="mapModeBtn" data-action="map-mode" data-mode="heat">Heatmap</button><span class="boundaryGroup"><button type="button" class="boundaryBtn active" data-action="boundary-mode" data-mode="districts">Districts</button><button type="button" class="boundaryBtn" data-action="boundary-mode" data-mode="taluks">Taluks</button></span><span class="basemapGroup"><span class="basemapLabel">${uiLang==='kn'?'ನಕ್ಷೆ':'Map'}</span>${Object.entries(BASEMAPS).map(([k,b])=>`<button type="button" class="basemapBtn${basemapMode===k?' active':''}" data-action="map-basemap" data-basemap="${k}">${uiLang==='kn'?b.kn:b.label}</button>`).join('')}</span></div></div><div class="mapLegend"><span><i class="dot critical"></i>Critical</span><span><i class="dot high"></i>High</span><span><i class="dot medium"></i>Medium</span><span><i class="dot low"></i>Low</span><span class="privacy">${role==='citizen'?'🔒 Aggregated public locations':'🔐 Authorized exact locations'}</span></div><div id="mainMap" class="professionalMap"></div><div id="boundaryInfo" class="boundaryInfo"></div><div id="mapStats" class="mapStats"></div></div><div class="sidePanel"><div class="hotspotPanel"><h3>${uiLang==='kn'?'ಜಿಲ್ಲಾವಾರು ದಾಖಲಾದ ಪ್ರಕರಣಗಳು':'District-wise registered cases'}</h3><div id="districtList" class="hotspotList"><p class="muted small">Loading…</p></div></div>${hasHotspots?'<div class="hotspotPanel"><h3>Top hotspots</h3><div id="hotspotList" class="hotspotList"><p class="muted small">Loading…</p></div></div>':''}</div></div>`;
  await renderOperationalMap();
  loadDistrictSummary();
  if(hasHotspots) loadHotspots();
}
function showKarnatakaView(){const sel=byId('mapDistrict');if(sel)sel.value='';boundaryMode='districts';document.querySelectorAll('.boundaryBtn').forEach(b=>b.classList.toggle('active',b.dataset.mode==='districts'));renderOperationalMap().then(()=>{if(activeMap)activeMap.flyTo({center:[76.2,15.3],zoom:6.25,duration:1000})})}
function boundaryFeatureName(props={}){
  const values=Object.entries(props||{});
  const preferred=['district','DISTRICT','dtname','DTNAME','name','NAME','District','district_name','taluk','TALUK','subdistrict','SUBDISTRICT','sdtname','NAME_3','NAME_2'];
  for(const k of preferred){if(props[k])return String(props[k]).replace(/ District$/i,'').trim()}
  for(const [k,v] of values){if(typeof v==='string' && KARNATAKA_DISTRICTS.some(d=>v.toLowerCase().includes(d.toLowerCase()))) return v}
  return '';
}
async function loadBoundaryLayer(map){
  const url=boundaryMode==='taluks'?KARNATAKA_TALUK_GEOJSON:KARNATAKA_DISTRICT_GEOJSON;
  try{
    const r=await fetch(url,{cache:'force-cache'}); if(!r.ok)throw new Error('Boundary source unavailable');
    boundaryData=await r.json();
    if(boundaryMode==='taluks' && boundaryData?.features){boundaryData={...boundaryData,features:boundaryData.features.filter(f=>String(f.properties?.NAME_1||'').toLowerCase()==='karnataka')}}
    if(map.getSource('admin-boundaries'))map.removeSource('admin-boundaries');
    map.addSource('admin-boundaries',{type:'geojson',data:boundaryData});
    const fillId='admin-boundary-fill', lineId='admin-boundary-line', labelId='admin-boundary-labels';
    if(map.getLayer(fillId))map.removeLayer(fillId); if(map.getLayer(lineId))map.removeLayer(lineId); if(map.getLayer(labelId))map.removeLayer(labelId);
    map.addLayer({id:fillId,type:'fill',source:'admin-boundaries',paint:{'fill-color':'#0f9c8f','fill-opacity':0.045}});
    map.addLayer({id:lineId,type:'line',source:'admin-boundaries',paint:{'line-color':boundaryMode==='taluks'?'#f2a530':'#0f6f8a','line-width':boundaryMode==='taluks'?1:1.7,'line-opacity':0.8}});
    map.addLayer({id:labelId,type:'symbol',source:'admin-boundaries',layout:{'text-field':['coalesce',['get','dtname'],['get','district'],['get','name'],['get','taluk'],['get','sdtname'],['get','NAME_3'],['get','NAME_2'], ''],'text-size':10,'text-font':['Open Sans Regular']},paint:{'text-color':'#10213a','text-halo-color':'#fff','text-halo-width':1.2}});
    map.on('click',fillId,e=>{
      const f=e.features?.[0]; if(!f)return;
      const name=boundaryFeatureName(f.properties); if(!name)return;
      if(boundaryMode==='districts'){
        const sel=byId('mapDistrict'); if(sel){const match=[...sel.options].find(o=>o.value.toLowerCase()===name.toLowerCase() || name.toLowerCase().includes(o.value.toLowerCase())); if(match){sel.value=match.value; renderOperationalMap();}}
        showBoundaryPanel(name);
      }else showBoundaryPanel(name,'Taluk');
    });
    map.on('mouseenter',fillId,()=>map.getCanvas().style.cursor='pointer');
    map.on('mouseleave',fillId,()=>map.getCanvas().style.cursor='');
  }catch(e){console.warn('Boundary layer unavailable',e)}
}
async function showBoundaryPanel(name,level='District'){
  const panel=byId('boundaryInfo'); if(!panel)return;
  let cases=[];
  try{const data=await get(role==='citizen'?'/api/public-overview':'/api/map/district-summary'); cases=role==='citizen'?(data.districts||[]).filter(x=>x.district===name):(data||[]).filter(x=>x.district===name)}catch(e){}
  const count=Number(cases[0]?.count||cases[0]?.issues||0);
  panel.innerHTML=`<div class="boundaryInfoHead"><span class="eyebrow">${level.toUpperCase()} INTELLIGENCE</span><button type="button" data-action="close-boundary">×</button></div><h3>${esc(name)}</h3><div class="boundaryMetric"><b>${count}</b><span>registered cases</span></div><div class="boundaryRows"><div><span>High risk</span><b>${cases[0]?.high_risk??'—'}</b></div><div><span>Resolved</span><b>${cases[0]?.resolved??'—'}</b></div></div><p class="muted small">Click a complaint marker for its complete case file. Selecting a district filters the operational map.</p>`;
  panel.classList.add('open');
}
function setBoundaryMode(mode){
  boundaryMode=mode==='taluks'?'taluks':'districts';
  document.querySelectorAll('.boundaryBtn').forEach(b=>b.classList.toggle('active',b.dataset.mode===boundaryMode));
  if(activeMap)loadBoundaryLayer(activeMap);
}
async function renderOperationalMap(){
  if(activeMap){activeMap.remove();activeMap=null}
  const endpoint=role==='citizen'?'/api/map/public':'/api/map/complaints';
  let data=await get(endpoint);
  const category=byId('mapCategory')?.value||'',priority=byId('mapPriority')?.value||'',district=byId('mapDistrict')?.value||'';
  if(district)data=data.filter(x=>x.district===district);
  if(role!=='citizen'){if(category)data=data.filter(x=>x.category===category);if(priority)data=data.filter(x=>x.priority===priority)}
  activeMap=newMap('mainMap');
  activeMap.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'top-right');
  activeMap.addControl(new maplibregl.FullscreenControl(),'top-right');
  activeMap.addControl(new maplibregl.ScaleControl({maxWidth:140,unit:'metric'}),'bottom-left');
  activeMap.on('load',()=>{
    const feats=data.filter(x=>x.lat!=null&&x.lng!=null).map(x=>({type:'Feature',geometry:{type:'Point',coordinates:[x.lng,x.lat]},properties:x}));
    const geo={type:'FeatureCollection',features:feats};
    activeMap.addSource('issues',{type:'geojson',data:geo,cluster:true,clusterMaxZoom:14,clusterRadius:45});
    activeMap.addSource('issues-raw',{type:'geojson',data:geo});
    activeMap.addLayer({id:'heat',type:'heatmap',source:'issues-raw',maxzoom:16,layout:{visibility:mapMode==='heat'?'visible':'none'},paint:{'heatmap-weight':['interpolate',['linear'],['coalesce',['get','count'],1],0,0,20,1],'heatmap-intensity':['interpolate',['linear'],['zoom'],7,.6,14,2.2],'heatmap-radius':['interpolate',['linear'],['zoom'],7,12,14,34],'heatmap-opacity':['interpolate',['linear'],['zoom'],7,.8,16,0]}});
    activeMap.addLayer({id:'clusters',type:'circle',source:'issues',filter:['has','point_count'],layout:{visibility:mapMode==='cluster'?'visible':'none'},paint:{'circle-radius':['step',['get','point_count'],18,10,24,50,32],'circle-opacity':.86,'circle-stroke-width':3,'circle-stroke-color':'#fff','circle-color':['step',['get','point_count'],'#0f9c8f',10,'#7c3aed',40,'#dc2626']}});
    activeMap.addLayer({id:'cluster-count',type:'symbol',source:'issues',filter:['has','point_count'],layout:{'text-field':['get','point_count_abbreviated'],'text-size':12,visibility:mapMode==='cluster'?'visible':'none'},paint:{'text-color':'#fff'}});
    activeMap.addLayer({id:'points',type:'circle',source:'issues',filter:['!',['has','point_count']],layout:{visibility:mapMode==='cluster'?'visible':'none'},paint:{'circle-radius':role==='citizen'?10:9,'circle-stroke-width':2,'circle-stroke-color':'#fff','circle-color':['match',['get','priority'],'Critical','#dc2626','High','#f0801f','Medium','#d9a318','Low','#1f9d55','#2563eb']}});
    activeMap.on('click','clusters',e=>{const f=activeMap.queryRenderedFeatures(e.point,{layers:['clusters']})[0];activeMap.getSource('issues').getClusterExpansionZoom(f.properties.cluster_id).then(z=>activeMap.easeTo({center:f.geometry.coordinates,zoom:z}))});
    activeMap.on('click','points',e=>{
      const p=e.features[0].properties;
      if(role==='citizen'){new maplibregl.Popup({offset:12}).setLngLat(e.lngLat).setHTML(`<div class="mapPopup"><b>${p.count||1} aggregated reports</b><span>${esc(p.category||'Civic issues')}</span><small>Exact citizen locations are hidden.</small></div>`).addTo(activeMap)}
      else{new maplibregl.Popup({offset:12,maxWidth:'320px'}).setLngLat(e.lngLat).setHTML(`<div class="mapPopup"><span class="popupId">${esc(p.complaint_id)}</span><b>${esc(p.category)}</b><span>${esc(p.department)}</span><div><em>${esc(p.priority)}</em> · ${esc(p.status)}</div><small>${esc(p.ward||'')} · ${esc(p.district||'')}</small><button type="button" class="tableButton" data-action="open-drawer" data-id="${esc(p.complaint_id)}">Open case →</button></div>`).addTo(activeMap)}
    });
    activeMap.on('mouseenter','points',()=>activeMap.getCanvas().style.cursor='pointer');
    activeMap.on('mouseleave','points',()=>activeMap.getCanvas().style.cursor='');
    loadBoundaryLayer(activeMap);
    fitFeatures(activeMap,feats);
  });
  byId('mapStats').innerHTML=`<div><b>${data.length}</b><span>${role==='citizen'?'public map cells':'mapped complaints'}</span></div>${role!=='citizen'?`<div><b>${data.filter(x=>x.priority==='Critical').length}</b><span>critical</span></div><div><b>${data.filter(x=>x.status!=='Resolved').length}</b><span>open</span></div><div><b>${new Set(data.map(x=>x.ward).filter(Boolean)).size}</b><span>wards</span></div>`:''}`;
}
function setMapMode(mode){
  mapMode=mode;
  document.querySelectorAll('.mapModeBtn').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  if(!activeMap||!activeMap.getLayer('heat'))return renderOperationalMap();
  const heat=mode==='heat'?'visible':'none',clusters=mode==='cluster'?'visible':'none';
  activeMap.setLayoutProperty('heat','visibility',heat);
  ['clusters','cluster-count','points'].forEach(id=>activeMap.getLayer(id)&&activeMap.setLayoutProperty(id,'visibility',clusters));
}
function setBasemap(mode){
  if(!BASEMAPS[mode]||mode===basemapMode)return;
  basemapMode=mode;
  document.querySelectorAll('.basemapBtn').forEach(b=>b.classList.toggle('active',b.dataset.basemap===mode));
  renderOperationalMap();
}
async function loadHotspots(){
  try{
    const data=await get('/api/map/hotspots');
    const list=byId('hotspotList'); if(!list)return;
    if(!data.length){list.innerHTML='<p class="muted small">No spatial clusters yet.</p>';return}
    list.innerHTML=data.slice(0,15).map((h,i)=>`<button type="button" class="hotspotItem" data-action="focus-hotspot" data-lat="${h.lat}" data-lng="${h.lng}"><span class="hotspotRank">${i+1}</span><span class="hotspotMeta"><b>${esc(h.category||'Mixed issues')}</b><small>${h.count} reports · ${h.high_risk||0} high-risk</small></span></button>`).join('');
  }catch(e){const list=byId('hotspotList'); if(list)list.innerHTML='<p class="muted small">Hotspot data unavailable.</p>'}
}
function focusHotspot(lat,lng){if(!activeMap||Number.isNaN(lat)||Number.isNaN(lng))return;activeMap.flyTo({center:[lng,lat],zoom:15.5,duration:900})}

async function loadDistrictSummary(){
  const list=byId('districtList'); if(!list)return;
  try{
    let data;
    if(role==='citizen'){
      const pub=await get('/api/public-overview');
      data=(pub.districts||[]).map(d=>({district:d.district,count:d.issues}));
    }else{
      data=await get('/api/map/district-summary');
    }
    if(!data.length){list.innerHTML='<p class="muted small">No registered cases yet.</p>';return}
    const total=data.reduce((s,d)=>s+Number(d.count||0),0)||1;
    list.innerHTML=data.slice(0,31).map((d,i)=>`<button type="button" class="hotspotItem districtItem" data-action="filter-district" data-district="${esc(d.district)}"><span class="hotspotRank">${i+1}</span><span class="hotspotMeta"><b>${esc(d.district||'Unknown')}</b><small>${d.count} case${d.count===1?'':'s'}${d.high_risk!=null?` · ${d.high_risk} high-risk`:''}</small></span><span class="districtBar"><span style="width:${Math.max(4,Math.round((Number(d.count||0)/total)*100))}%"></span></span></button>`).join('');
  }catch(e){list.innerHTML='<p class="muted small">District summary unavailable.</p>'}
}
function filterByDistrict(district){
  const sel=byId('mapDistrict'); if(!sel)return;
  sel.value=district||'';
  renderOperationalMap();
}

/* ---------------- citizen wizard (report an issue) ---------------- */
function reportView(){
  byId('title').textContent=T[uiLang].reportTitle;
  byId('subtitle').textContent='Everything you need to report an issue — description, AI routing, location and evidence — on one page.';
  if(!wizard.district) wizard.district=me?.district||'Bengaluru Urban';
  if(!wizard.ward) wizard.ward=me?.ward||'';
  byId('app').innerHTML=`<div class="singleReportShell">
    <div class="reportHero card"><div><span class="eyebrow">ONE-PAGE CIVIC REPORT</span><h2>Report a civic issue</h2><p class="muted">Describe what happened. Janasetu will classify it, route it to the right department and preserve your evidence.</p></div><div class="liveAssist"><span class="pulseDot"></span> AI routing ready</div></div>
    <div class="reportOnePageGrid">
      <div class="reportMain card">
        <div class="sectionTitle"><span class="sectionNumber">01</span><div><b>Describe the issue</b><small>English or Kannada</small></div></div>
        <textarea id="reportText" rows="7" placeholder="ಉದಾ: ನಮ್ಮ ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಇದೆ... / Example: Large pothole near the bus stop...">${esc(wizard.text)}</textarea>
        <div class="reportInline"><button type="button" class="secondaryButton" data-action="classify-issue">✦ AI classify</button><span class="muted small">AI suggests category, department and priority. You remain in control.</span></div>
        <div id="reportPrediction">${wizard.prediction?`<div class="predictionCard"><span>AI prediction</span><b>${esc(wizard.prediction.category)} → ${esc(wizard.prediction.department)}</b><small>${wizard.prediction.language==='kn'?'Kannada detected':'English detected'} · confidence ${wizard.prediction.confidence}%</small></div>`:''}</div>
        <div class="sectionTitle gapTop"><span class="sectionNumber">02</span><div><b>Priority & classification</b><small>Review the AI suggestion</small></div></div>
        <div class="choiceGrid"><label><input type="radio" name="reportPriority" value="Critical"> <span><b>Critical</b><small>Immediate public safety risk</small></span></label><label><input type="radio" name="reportPriority" value="High" checked> <span><b>High</b><small>Needs prompt attention</small></span></label><label><input type="radio" name="reportPriority" value="Medium"> <span><b>Medium</b><small>Routine service issue</small></span></label><label><input type="radio" name="reportPriority" value="Low"> <span><b>Low</b><small>Low urgency</small></span></label></div>
        <label class="gapTop">Issue category <select id="reportCategory"><option value="">Auto-detect from description</option><option>Roads & Footpaths</option><option>Garbage & Sanitation</option><option>Water Supply</option><option>Drainage & Flooding</option><option>Streetlights & Electricity</option><option>Public Safety</option><option>Other</option></select><small class="muted">If you submit only a photo/video with no description, choose a category.</small></label>
        <div class="sectionTitle gapTop"><span class="sectionNumber">03</span><div><b>Location</b><small>District, locality and map position</small></div></div>
        <div class="locationInputs"><label>District<select id="reportDistrict">${KARNATAKA_DISTRICTS.map(d=>`<option ${d===wizard.district?'selected':''}>${d}</option>`).join('')}</select></label><label>Ward / locality<input id="reportWard" value="${esc(wizard.ward)}" placeholder="Whitefield, Mahadevapura…"></label><label class="span2">Address / landmark<input id="reportAddress" value="${esc(wizard.address)}" placeholder="Optional address or landmark"></label></div>
        <div class="sectionTitle gapTop"><span class="sectionNumber">04</span><div><b>Evidence</b><small>Photos, videos and documents</small></div></div>
        <div class="uploadZone premiumUpload"><input id="reportAttachments" type="file" multiple accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm,.pdf,.doc,.docx"><div class="uploadIcon">＋</div><div><b>Add evidence</b><span>Up to 5 images · 10 MB each · 1 video · max 60 sec / 100 MB · documents 20 MB</span></div></div><div id="reportFilePreview" class="filePreview"></div><div id="reportFileError" class="small"></div>
        <div id="res" class="reportResult"></div>
        <div class="submitBar"><div><span class="privacy">🔒 Your exact location is visible only to authorized operational roles</span></div><button type="button" class="primary bigSubmit" data-action="submit-complaint">Submit complaint →</button></div>
      </div>
      <div class="reportSide"><div class="card locationCard"><div class="cardhead"><div><span class="eyebrow">LIVE MAP</span><h2>Pin the issue</h2></div><button class="gpsButton" data-action="use-location">◎ Use my location</button></div><div id="reportMap" class="reportMap"></div><div class="coords"><span>Latitude <b id="lat">${wizard.location?wizard.location.lat.toFixed(6):'—'}</b></span><span>Longitude <b id="lng">${wizard.location?wizard.location.lng.toFixed(6):'—'}</b></span></div><p class="muted small">Click the map or drag the marker to the exact issue location.</p></div><div class="card reportTrust"><span class="eyebrow">WHAT HAPPENS NEXT</span><div class="trustStep"><b>1</b><span><strong>AI routes</strong><small>Category and department are suggested instantly.</small></span></div><div class="trustStep"><b>2</b><span><strong>Department acts</strong><small>Authorized officers receive the case and evidence.</small></span></div><div class="trustStep"><b>3</b><span><strong>You see resolution</strong><small>Updates, completion notes and proof return to your account.</small></span></div></div></div>
    </div></div>`;
  byId('reportText').addEventListener('input',e=>wizard.text=e.target.value);
  byId('reportDistrict').addEventListener('change',e=>wizard.district=e.target.value);
  byId('reportWard').addEventListener('input',e=>wizard.ward=e.target.value);
  byId('reportAddress').addEventListener('input',e=>wizard.address=e.target.value);
  byId('reportCategory')?.addEventListener('change',e=>wizard.category=e.target.value);
  byId('reportAttachments').addEventListener('change',e=>{wizard.files=[...e.target.files];const err=validateReportFiles(wizard.files);if(err){byId('reportFileError').innerHTML=`<span class="danger">${esc(err)}</span>`;e.target.value='';wizard.files=[]}else{byId('reportFileError').textContent='';previewReportFiles()}});
  setTimeout(initReportMap,30);
}
function validateReportFiles(files){
  const imgs=files.filter(f=>f.type.startsWith('image/')), vids=files.filter(f=>f.type.startsWith('video/'));
  if(files.length>6)return 'Maximum 6 evidence files per complaint.';
  if(imgs.length>5)return 'Maximum 5 images per complaint.';
  if(vids.length>1)return 'Maximum 1 video per complaint.';
  for(const f of files){if(f.type.startsWith('image/')&&f.size>10*1024*1024)return `${f.name} exceeds the 10 MB image limit.`;if(f.type.startsWith('video/')&&f.size>100*1024*1024)return `${f.name} exceeds the 100 MB video limit.`;if(!f.type.startsWith('image/')&&!f.type.startsWith('video/')&&f.size>20*1024*1024)return `${f.name} exceeds the 20 MB document limit.`}return ''}
function previewReportFiles(){const box=byId('reportFilePreview');if(!box)return;box.innerHTML=(wizard.files||[]).map(f=>`<span>${f.type.startsWith('image/')?'📷':f.type.startsWith('video/')?'🎥':'📄'} ${esc(f.name)} <small>${(f.size/1024/1024).toFixed(1)} MB${f.type.startsWith('video/')?' · server checks ≤60 sec':''}</small></span>`).join('')}

function renderPrediction(x){const res=byId('reportPrediction')||byId('res'); if(res) res.innerHTML=`<div class="predictionCard"><span>AI prediction</span><b>${esc(x.category)} → ${esc(x.department)}</b><small>${x.language==='kn'?'Kannada detected · ':'English detected · '}confidence ${x.confidence}%</small></div>`}
async function classifyIssue(){
  const text=(byId('reportText')?.value||byId('wizTxt')?.value||wizard.text).trim(); if(!text)return alert('Enter the complaint first.');
  wizard.text=text;
  const r=await fetch('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const x=await r.json();
  wizard.prediction={category:x.category,department:x.department,language:x.language,confidence:x.confidence};
  renderPrediction(wizard.prediction);
}
function initReportMap(){
  if(activeMap)activeMap.remove();
  activeMap=newMap('reportMap');
  activeMap.addControl(new maplibregl.NavigationControl(),'top-right');
  activeMap.on('load',()=>{if(wizard.location)setReportLocation(wizard.location.lat,wizard.location.lng,wizard.location.source||'manual')});
  activeMap.on('click',e=>setReportLocation(e.lngLat.lat,e.lngLat.lng,'map'));
}
function setReportLocation(lat,lng,source='manual'){
  wizard.location={lat,lng,source}; selectedLocation=wizard.location;
  const latEl=byId('lat'),lngEl=byId('lng');
  if(latEl)latEl.textContent=lat.toFixed(6); if(lngEl)lngEl.textContent=lng.toFixed(6);
  if(reportMarker)reportMarker.remove();
  reportMarker=new maplibregl.Marker({draggable:true}).setLngLat([lng,lat]).addTo(activeMap);
  reportMarker.on('dragend',()=>{const p=reportMarker.getLngLat();setReportLocation(p.lat,p.lng,'map')});
  activeMap.flyTo({center:[lng,lat],zoom:15});
}
function useMyLocation(){
  if(!navigator.geolocation)return alert('Geolocation is not supported by this browser.');
  navigator.geolocation.getCurrentPosition(p=>setReportLocation(p.coords.latitude,p.coords.longitude,'gps'),()=>alert('Location permission was not granted.'),{enableHighAccuracy:true,timeout:10000});
}
function previewWizardFiles(){
  wizard.files=[...byId('wizAttachments').files];
  byId('wizFilePreview').innerHTML=wizard.files.map(f=>`<span>${f.type.startsWith('image/')?'📷':f.type.startsWith('video/')?'🎥':'📄'} ${esc(f.name)} <small>${(f.size/1024/1024).toFixed(1)} MB</small></span>`).join('');
}
async function submitComplaint(){
  const text=(byId('reportText')?.value||wizard.text).trim();
  const category=byId('reportCategory')?.value||''; if(!text&&!(wizard.files||[]).length)return alert('Add a description or evidence before submitting.'); if(!text&&!category)return alert('For image/video-only complaints, choose the issue category.');
  wizard.text=text; wizard.district=byId('reportDistrict')?.value||wizard.district; wizard.ward=byId('reportWard')?.value||wizard.ward; wizard.address=byId('reportAddress')?.value||wizard.address;
  const priority=document.querySelector('input[name="reportPriority"]:checked')?.value||'High';
  const fd=new FormData(); fd.append('text',wizard.text); fd.append('category',category); fd.append('district',wizard.district); fd.append('ward',wizard.ward); fd.append('address',wizard.address); fd.append('priority',priority);
  if(wizard.location){fd.append('latitude',wizard.location.lat);fd.append('longitude',wizard.location.lng);fd.append('location_source',wizard.location.source)}
  (wizard.files||[]).forEach(f=>fd.append('attachments',f));
  const btn=document.querySelector('[data-action="submit-complaint"]'); if(btn){btn.disabled=true;btn.textContent='Submitting…'}
  try{
    const r=await fetch('/api/complaints',{method:'POST',body:fd}); const x=await r.json(); const res=byId('res');
    if(!r.ok){if(res)res.innerHTML=`<div class="errorBox">${esc(x.error||'Could not submit complaint')}</div>`;return}
    if(res)res.innerHTML=`<div class="successBox"><b>✓ Complaint ${esc(x.complaint_id)} submitted</b><span>Routed to ${esc(x.department)} · ${esc(x.category)} · ${x.confidence}% AI confidence</span><span>${x.attachments.length} evidence file(s) stored securely.</span></div>`;
    wizard={step:1,text:'',district:me?.district||'Bengaluru Urban',ward:me?.ward||'',address:'',location:null,prediction:null,files:[]};
  }catch(e){const res=byId('res');if(res)res.innerHTML=`<div class="errorBox">${esc(e.message||'Submission failed')}</div>`}
  finally{if(btn){btn.disabled=false;btn.textContent='Submit complaint →'}}
}

/* ---------------- complaints: master list + detail drawer ---------------- */
async function complaintsView(){
  complaintsCache=await get('/api/complaints');
  byId('title').textContent=role==='citizen'?(uiLang==='kn'?'ನನ್ನ ದೂರುಗಳು':'My Complaints'):'Operational Complaint Queue';
  const rowsHtml=complaintsCache.map(r=>`<tr class="rowClickable" data-action="open-drawer" data-id="${esc(r.complaint_id)}"><td><b>${esc(r.complaint_id)}</b><br><small>${new Date(r.created_at).toLocaleDateString()}</small></td><td>${esc(r.category)}<br><small>${r.original_language==='kn'?'ಕನ್ನಡ':'English'}</small></td><td>${esc(r.department)}</td><td>${esc(r.ward||'—')}</td>${role==='admin'?`<td>${esc(r.citizen_name||'')}</td>`:''}<td><span class="pill ${r.priority.toLowerCase()}">${esc(r.priority)}</span></td><td><span class="pill status">${esc(r.status)}</span></td><td>📎 ${r.attachment_count||0}</td></tr>`).join('');
  byId('app').innerHTML=`<div class="card"><div class="cardhead"><div><span class="eyebrow">${role==='citizen'?'PRIVATE ACCOUNT':'AUTHORIZED OPERATIONS'}</span><h2>${role==='citizen'?'Complaint history':'Live operational queue'}</h2></div><span class="privacy">${role==='citizen'?'🔒 Only your records':'🔐 Role-filtered records'}</span></div><p class="muted small">Click any row to open the case file.</p><div class="tablewrap"><table class="table"><thead><tr><th>ID</th><th>Category</th><th>Department</th><th>Ward</th>${role==='admin'?'<th>Citizen</th>':''}<th>Priority</th><th>Status</th><th>Files</th></tr></thead><tbody>${rowsHtml||'<tr><td colspan="9">No complaints found.</td></tr>'}</tbody></table></div></div>`;
}
function findComplaint(id){return complaintsCache.find(c=>c.complaint_id===id)}
async function openDrawer(id){
  drawerId=id; drawerTab='details';
  byId('drawerOverlay').classList.add('open');
  byId('complaintDrawer').classList.add('open');
  renderDrawerBody();
}
function closeDrawer(){byId('drawerOverlay').classList.remove('open');byId('complaintDrawer').classList.remove('open');drawerId=null}
async function renderDrawerBody(){
  const c=findComplaint(drawerId); if(!c)return;
  byId('drawerHeadId').textContent=c.complaint_id;
  byId('drawerHeadTitle').textContent=c.category;
  document.querySelectorAll('.drawerTab').forEach(b=>b.classList.toggle('active',b.dataset.tab===drawerTab));
  const body=byId('drawerBody');
  if(drawerTab==='details'){
    body.innerHTML=`<div class="caseHero"><span class="pill ${String(c.priority||'Medium').toLowerCase()}">${esc(c.priority)}</span><span class="pill status">${esc(c.status)}</span></div><div class="drawerField"><span>Department</span><b>${esc(c.department)}</b></div><div class="drawerField"><span>Location</span><b>${esc(c.address||c.ward||'—')} · ${esc(c.district||'—')}</b></div><div class="drawerField"><span>Filed</span><b>${new Date(c.created_at).toLocaleString()}</b></div><div class="drawerField"><span>Complaint</span><p>${esc(c.complaint_text||'—')}</p></div>${c.resolution_text?`<div class="resolutionCard"><span class="eyebrow">RESOLUTION</span><h4>${esc(c.resolution_text)}</h4>${c.resolution_action?`<p><b>Action:</b> ${esc(c.resolution_action)}</p>`:''}${c.resolution_remarks?`<p><b>Officer remarks:</b> ${esc(c.resolution_remarks)}</p>`:''}<small>Completed ${c.resolved_at?new Date(c.resolved_at).toLocaleString():'—'} · ${esc(c.resolution_by||'Authorized officer')}</small></div>`:''}${role!=='citizen'&&c.status!=='Resolved'?`<div class="drawerActions"><button type="button" class="tableButton" data-action="change-status" data-id="${esc(c.complaint_id)}" data-status="In Progress">Start</button><button type="button" class="primary" data-action="open-resolve" data-id="${esc(c.complaint_id)}">Resolve case</button><button type="button" class="tableButton" data-action="change-status" data-id="${esc(c.complaint_id)}" data-status="Rejected">Reject</button></div><div id="resolvePanel"></div>`:''}`;
  } else if(drawerTab==='timeline'){
    body.innerHTML='<p class="muted small">Loading timeline…</p>';
    try{const x=await get('/api/complaints/'+encodeURIComponent(c.complaint_id)+'/timeline');const events=(x.updates||[]).map(ev=>({title:ev.status||'Update',text:ev.comment||'',who:ev.officer_name||'Department',time:ev.timestamp}));if(x.audit)events.push(...x.audit.map(ev=>({title:ev.action,text:'',who:ev.user_role+' · '+(ev.user_id||''),time:ev.timestamp})));events.sort((a,b)=>new Date(a.time)-new Date(b.time));body.innerHTML=`<div class="timeline">${events.length?events.map(ev=>`<div class="timelineItem"><span class="timelineDot"></span><div class="timelineContent"><b>${esc(ev.title)}</b><p>${esc(ev.text)}</p><small>${esc(ev.who)} · ${new Date(ev.time).toLocaleString()}</small></div></div>`).join(''):'<p class="muted small">No updates yet.</p>'}</div>`}catch(e){body.innerHTML='<p class="muted small">Timeline unavailable.</p>'}
  } else if(drawerTab==='attachments') {
    body.innerHTML='<p class="muted small">Loading evidence…</p>';
    try{const files=await get('/api/complaints/'+encodeURIComponent(c.complaint_id)+'/evidence');body.innerHTML=files.length?`<div class="attachmentGrid">${files.map(f=>`<a class="evidenceCard ${f.purpose==='resolution'?'resolutionEvidence':''}" href="/api/evidence/${f.evidence_id}" target="_blank">${f.media_type==='video'&&f.thumbnail_url?`<img class="evidenceThumb" src="/api/evidence/${f.evidence_id}/thumbnail" alt="Video thumbnail">`:`<div class="evidenceIcon">${f.media_type==='image'?'▧':f.media_type==='video'?'▶':'▤'}</div>`}<div><b>${esc(f.original_name||'Evidence')}</b><small>${esc(f.purpose||'complaint')} · ${f.file_size?(f.file_size/1024/1024).toFixed(1)+' MB':'file'}${f.duration_seconds?' · '+Number(f.duration_seconds).toFixed(1)+' sec':''}</small><small>${f.latitude!=null?`📍 EXIF ${Number(f.latitude).toFixed(5)}, ${Number(f.longitude).toFixed(5)}`:'📍 Uses complaint/map location'} · ${esc(f.validation_status||'accepted')}</small></div></a>`).join('')}</div>`:'<p class="muted small">No attachments were submitted with this complaint.</p>'}catch(e){body.innerHTML='<p class="muted small">Evidence unavailable.</p>'}
  } else {
    body.innerHTML=c.resolution_text?`<div class="resolutionCard resolutionFull"><span class="eyebrow">CLOSED LOOP</span><h3>Case resolved</h3><h4>${esc(c.resolution_text)}</h4>${c.resolution_action?`<p><b>Action taken:</b> ${esc(c.resolution_action)}</p>`:''}${c.resolution_remarks?`<p><b>Officer remarks:</b> ${esc(c.resolution_remarks)}</p>`:''}<div class="resolutionMeta"><span>Completed</span><b>${c.resolved_at?new Date(c.resolved_at).toLocaleString():'—'}</b></div><div class="resolutionMeta"><span>Resolved by</span><b>${esc(c.resolution_by||'Authorized officer')}</b></div><p class="muted small">Resolution proof is available in the Evidence tab.</p></div>`:`<div class="emptyResolution"><div>◷</div><b>No resolution published yet</b><p class="muted small">The department will publish completion details and proof here once the case is resolved.</p></div>`;
  }
}

async function changeStatus(id,status){
  await fetch('/api/complaints/'+encodeURIComponent(id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status,comment:`Status changed to ${status}`})});
  auditCache=null;
  await complaintsView();
  if(drawerId===id){await renderDrawerBody()}
}

function openResolvePanel(id){
  const panel=byId('resolvePanel'); if(!panel)return;
  panel.innerHTML=`<div class="resolveForm"><span class="eyebrow">CLOSE THE LOOP</span><h4>Resolution details</h4><label>What was resolved?<textarea id="resolveText" rows="4" placeholder="Describe the work completed…"></textarea></label><label>Action taken<input id="resolveAction" placeholder="Repair, replacement, cleaning, inspection…"></label><label>Officer remarks<textarea id="resolveRemarks" rows="3" placeholder="Optional field notes…"></textarea></label><label class="uploadZone miniUpload"><input id="resolveFiles" type="file" multiple accept="image/*,video/*,.pdf,.doc,.docx"><b>＋ Add resolution proof</b><span>Before/after photos, completion report or video</span></label><button class="primary" type="button" data-action="submit-resolution" data-id="${esc(id)}">Publish resolution</button><div id="resolveResult"></div></div>`;
}
async function submitResolution(id){
  const fd=new FormData(); fd.append('resolution',byId('resolveText')?.value||'');fd.append('action',byId('resolveAction')?.value||'');fd.append('remarks',byId('resolveRemarks')?.value||'');[...(byId('resolveFiles')?.files||[])].forEach(f=>fd.append('resolution_files',f));
  const btn=document.querySelector('[data-action="submit-resolution"]');if(btn){btn.disabled=true;btn.textContent='Publishing…'}
  try{const r=await fetch('/api/complaints/'+encodeURIComponent(id)+'/resolve',{method:'POST',body:fd});const x=await r.json();if(!r.ok)throw new Error(x.error||'Could not resolve case');const rr=byId('resolveResult');if(rr)rr.innerHTML='<div class="successBox">Resolution published. The citizen can now see the completion record.</div>';auditCache=null;await complaintsView();if(drawerId===id){const c=findComplaint(id);drawerTab='details';renderDrawerBody()}}catch(e){const rr=byId('resolveResult');if(rr)rr.innerHTML=`<div class="errorBox">${esc(e.message)}</div>`}finally{if(btn){btn.disabled=false;btn.textContent='Publish resolution'}}
}

/* ---------------- departments / citizens / officers / audit ---------------- */
async function departmentsView(){
  const a=await get('/api/department-performance');
  byId('title').textContent='Department Performance';
  byId('app').innerHTML=`<div class="card"><div class="cardhead"><h2>Workload, resolution and SLA performance</h2></div><div class="tablewrap"><table class="table"><thead><tr><th>Department</th><th>Total</th><th>Open</th><th>Resolved</th><th>SLA risk</th><th>Resolution</th></tr></thead><tbody>${a.map(r=>`<tr><td><b>${esc(r.department)}</b></td><td>${r.total}</td><td>${r.open}</td><td>${r.resolved}</td><td><span class="pill ${r.breached?'critical':'low'}">${r.breached}</span></td><td>${r.resolution_rate||0}%</td></tr>`).join('')}</tbody></table></div></div>`;
}
async function citizensView(){
  const a=await get('/api/citizens');
  byId('title').textContent='Citizen Directory';
  byId('app').innerHTML=`<div class="card"><div class="cardhead"><div><span class="eyebrow">ADMIN ONLY</span><h2>Registered citizens</h2></div><span class="privacy">Personal data protected</span></div><div class="tablewrap"><table class="table"><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>District</th><th>Ward</th><th>Complaints</th></tr></thead><tbody>${a.map(r=>`<tr><td>${esc(r.citizen_id)}</td><td>${esc(r.name)}</td><td>${esc(r.email)}</td><td>${esc(r.phone||'—')}</td><td>${esc(r.district||'—')}</td><td>${esc(r.ward||'—')}</td><td>${r.complaints}</td></tr>`).join('')}</tbody></table></div></div>`;
}
async function officersView(){
  const [a,deps]=await Promise.all([get('/api/officers'),get('/api/departments')]);
  byId('title').textContent='Department Officers';
  byId('app').innerHTML=`<div class="dashboardGrid"><div class="card"><div class="cardhead"><h2>Officer registry</h2><span class="privacy">Admin managed</span></div><div class="tablewrap"><table class="table"><thead><tr><th>Officer</th><th>Department</th><th>Email</th><th>Status</th></tr></thead><tbody>${a.map(r=>`<tr><td>${esc(r.name)}</td><td>${esc(r.department)}</td><td>${esc(r.email)}</td><td><span class="pill low">${esc(r.status)}</span></td></tr>`).join('')}</tbody></table></div></div><div class="card officerCreate"><span class="eyebrow">CREATE CREDENTIALS</span><h2>Add department officer</h2><label>Name<input id="offName"></label><label>Official email<input id="offEmail" type="email"></label><label>Department<select id="offDep">${deps.map(d=>`<option value="${d.department_id}">${esc(d.name)}</option>`).join('')}</select></label><label>Temporary password<input id="offPwd" type="password" value="Dept@123"></label><button class="primary" data-action="create-officer">Create official account</button><div id="offRes"></div></div></div>`;
}
async function createOfficer(){
  const body={name:byId('offName').value,email:byId('offEmail').value,department_id:byId('offDep').value,password:byId('offPwd').value};
  try{await postJson('/api/officers',body);byId('offRes').innerHTML='<div class="successBox">Department login credentials created.</div>';setTimeout(officersView,700)}
  catch(e){alert(e.payload?.error||'Could not create officer account.')}
}
async function auditView(){
  auditCache=await get('/api/audit');
  byId('title').textContent='Audit Log';
  byId('app').innerHTML=`<div class="card"><div class="cardhead"><h2>Accountability trail</h2><span class="muted">Who did what and when</span></div><div class="tablewrap"><table class="table"><thead><tr><th>Time</th><th>Role</th><th>User</th><th>Action</th><th>Complaint</th></tr></thead><tbody>${auditCache.map(r=>`<tr><td>${new Date(r.timestamp).toLocaleString()}</td><td>${esc(r.user_role)}</td><td>${esc(r.user_id||'')}</td><td>${esc(r.action)}</td><td>${r.complaint_id?`<button type="button" class="tableButton" data-action="open-drawer" data-id="${esc(r.complaint_id)}">${esc(r.complaint_id)}</button>`:'—'}</td></tr>`).join('')}</tbody></table></div></div>`;
}

init();
