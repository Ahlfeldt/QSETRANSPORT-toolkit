import{buildRunPackage}from'./run-package.js';
import{gridMapSize}from'./map-layout.js';
const AABPL={global:{meta:'https://raw.githubusercontent.com/Ahlfeldt/AABPL-toolkit/main/DATA/GlobalCities/metro-data.csv',folder:'GlobalCities'},us:{meta:'https://raw.githubusercontent.com/Ahlfeldt/AABPL-toolkit/main/DATA/USMSAs/metro-data.csv',folder:'USMSAs'}};
const $=id=>document.getElementById(id);
const locationLimit=()=>matchMedia('(max-width: 768px)').matches?1000:2000;
function updateLocationLimit(){$('location-limit').textContent='Maximum '+locationLimit().toLocaleString();}
const state={cities:[],collection:'global',cellSizes:{global:'2',us:'5'},drawn:null,selectedShock:null,worker:null,ready:false,prepared:false,results:null,pendingRun:null,lastRun:null,cityLayer:null,gridLayer:null,preparedGrid:null,baselineLines:[],baselineStations:[],baselineLayer:null};

L.drawLocal.draw.handlers.polyline.tooltip.start='Click to start the transport line.';
L.drawLocal.draw.handlers.polyline.tooltip.cont='Click to add another segment. Double-click to finish.';
L.drawLocal.draw.handlers.polyline.tooltip.end='Click to add another segment. Double-click to finish.';
const qtPolylineAddHooks=L.Draw.Polyline.prototype.addHooks,qtPolylineRemoveHooks=L.Draw.Polyline.prototype.removeHooks;
L.Draw.Polyline.include({
  addHooks:function(){qtPolylineAddHooks.call(this);if(this._map)this._map.on('dblclick',this._qtFinishOnDoubleClick,this);},
  removeHooks:function(){if(this._map)this._map.off('dblclick',this._qtFinishOnDoubleClick,this);qtPolylineRemoveHooks.call(this);},
  _updateFinishHandler:function(){},
  _qtFinishOnDoubleClick:function(e){if(this._markers.length<2)return;const n=this._markers.length;if(n>2&&this._map.latLngToContainerPoint(this._markers[n-1].getLatLng()).distanceTo(this._map.latLngToContainerPoint(this._markers[n-2].getLatLng()))<3)this.deleteLastVertex();this._finishShape();L.DomEvent.stop(e);},
  _endPoint:function(clientX,clientY,e){
    if(this._mouseDownOrigin){
      const point=L.point(clientX,clientY),dragDistance=point.distanceTo(this._mouseDownOrigin),now=Date.now(),doubleClick=this._qtLastTap&&now-this._qtLastTap.time<450&&point.distanceTo(this._qtLastTap.point)<24;
      if(doubleClick&&this._markers.length>1){this._qtLastTap=null;this._finishShape();}
      else if(dragDistance<9*(window.devicePixelRatio||1)){this.addVertex(e.latlng);this._qtLastTap={point,time:now};}
      this._enableNewMarkers();
    }
    this._mouseDownOrigin=null;
  }
});

const map=L.map('map',{zoomControl:true,zoomSnap:.1}).setView([51.5074,-.1278],9);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
state.drawn=new L.FeatureGroup().addTo(map);
map.addControl(new L.Control.Draw({edit:{featureGroup:state.drawn},draw:{rectangle:false,circle:false,circlemarker:false,marker:{icon:new L.Icon.Default()},polyline:{shapeOptions:{color:'#b74338',weight:4}},polygon:{allowIntersection:false,shapeOptions:{color:'#28735a',fillOpacity:.22}}}}));

map.on(L.Draw.Event.CREATED,e=>{e.layer.feature=e.layer.feature||{type:'Feature',properties:{}};e.layer.feature.properties.kind=e.layerType==='polygon'?'shock':e.layerType==='marker'?'station':'transport';state.drawn.addLayer(e.layer);if(e.layerType==='polygon'){state.selectedShock=e.layer;$('shock-editor').hidden=false;}updateRunState();});
map.on('draw:edited',updateRunState);map.on('draw:deleted',updateRunState);
let restoreDoubleClickZoom=false;map.on(L.Draw.Event.DRAWSTART,e=>{if(e.layerType==='polyline'){restoreDoubleClickZoom=map.doubleClickZoom.enabled();map.doubleClickZoom.disable();}});map.on(L.Draw.Event.DRAWSTOP,e=>{if(e.layerType==='polyline'&&restoreDoubleClickZoom){map.doubleClickZoom.enable();restoreDoubleClickZoom=false;}});

function parseCSV(text){const rows=[];let row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){const c=text[i],n=text[i+1];if(c==='"'&&quoted&&n==='"'){cell+='"';i++;}else if(c==='"')quoted=!quoted;else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&n==='\n')i++;row.push(cell);if(row.some(Boolean))rows.push(row);row=[];cell='';}else cell+=c;}if(cell||row.length){row.push(cell);rows.push(row);}const headers=rows.shift();return rows.map(r=>Object.fromEntries(headers.map((h,i)=>[h,r[i]??''])));}
function splitPlace(name){const parts=name.split(',').map(x=>x.trim());return{city:parts[0],country:parts.slice(1).join(', ')||'Other'};}
function regionFor(country){const groups={Europe:['United Kingdom','France','Germany','Italy','Spain','Netherlands','Belgium','Austria','Sweden','Norway','Denmark','Finland','Poland','Portugal','Greece','Ireland','Switzerland','Czech Republic','Hungary','Romania','Russia','Turkey'],Americas:['United States','Canada','Mexico','Brazil','Argentina','Chile','Colombia','Peru'],Asia:['Japan','China','India','Indonesia','Thailand','Singapore','South Korea','Philippines','Malaysia','Vietnam','Pakistan','Bangladesh'],Africa:['South Africa','Egypt','Nigeria','Kenya','Morocco','Ghana','Ethiopia'],Oceania:['Australia','New Zealand']};return Object.entries(groups).find(([,v])=>v.includes(country))?.[0]||'Other';}
function fillSelect(el,values,allLabel){el.innerHTML='';if(allLabel)el.add(new Option(allLabel,''));values.forEach(v=>el.add(new Option(v.label??v.name,v.value??v.name)));}
function filterCities(){const region=$('region').value,country=$('country').value;const eligible=state.cities.filter(c=>(!region||c.region===region)&&(!country||(c.states||[c.country]).includes(country))).sort((a,b)=>a.metro_name.localeCompare(b.metro_name,undefined,{sensitivity:'base'}));fillSelect($('city'),eligible.map(c=>({label:c.metro_name,value:c.metro_id})));const preferred=eligible.find(c=>state.collection==='global'?c.metro_id==='61':c.metro_id==='35620');if(preferred)$('city').value=preferred.metro_id;updateRunState();}
function updateFilters(){const region=$('region').value,countries=[...new Set(state.cities.filter(c=>!region||c.region===region).flatMap(c=>c.states||[c.country]))].sort();fillSelect($('country'),countries.map(name=>({name})),state.collection==='us'?'All states':'All countries');filterCities();}
function updateRunState(){const c=state.cities.find(x=>x.metro_id===$('city').value),label=state.prepared?'Run counterfactual':`Prepare ${c?.city||'city'}`,disabled=!state.ready||!c;$('run').textContent=label;$('run').disabled=disabled;$('mobile-run').textContent=label;$('mobile-run').disabled=disabled;}
function setRuntime(kind,label){const el=document.querySelector('.runtime');el.className=`runtime ${kind}`;$('runtime-label').textContent=label;}

function sizePreparedMap(){
  const stage=document.querySelector('.mainstage');
  if(innerWidth<=768||!state.gridLayer){stage.style.removeProperty('--grid-map-height');stage.style.removeProperty('--grid-map-width');return;}
  const bounds=state.gridLayer.getBounds(),northWest=map.project(bounds.getNorthWest(),0),southEast=map.project(bounds.getSouthEast(),0);
  // Re-measure after the toolbar wraps or a page scrollbar changes the available width.
  for(let pass=0;pass<3;pass++){
    const toolbar=document.querySelector('.map-toolbar'),top=(toolbar?.offsetTop||0)+(toolbar?.offsetHeight||80)+12;
    const header=document.querySelector('.topbar').getBoundingClientRect().height;
    const size=gridMapSize(stage.clientWidth,Math.max(160,innerHeight-header),southEast.x-northWest.x,southEast.y-northWest.y,top);
    stage.style.setProperty('--grid-map-height',`${size.height}px`);
    stage.style.setProperty('--grid-map-width',`${size.width}px`);
  }
}

function fitPreparedGrid(){
  if(!state.gridLayer)return;
  sizePreparedMap();
  map.invalidateSize();
  const bounds=state.gridLayer.getBounds(),toolbar=document.querySelector('.map-toolbar');
  const top=(toolbar?.offsetTop||0)+(toolbar?.offsetHeight||80)+12;
  map.fitBounds(bounds,{paddingTopLeft:[20,top],paddingBottomRight:[20,20],animate:false});
  const gridTop=map.latLngToContainerPoint(bounds.getNorthWest()).y;
  map.panBy([0,gridTop-top],{animate:false});
}

function quetransportHexGrid(bounds,cellSizeKm){
  const [west,south,east,north]=bounds,lat0=(south+north)/2;
  const kmPerLon=111.32*Math.cos(lat0*Math.PI/180),kmPerLat=110.574;
  const width=(east-west)*kmPerLon,height=(north-south)*kmPerLat;
  const side=Math.sqrt(2*cellSizeKm**2/(3*Math.sqrt(3)));
  const dx=Math.sqrt(3)*side,dy=1.5*side;
  const columns=Math.ceil(width/dx)+3,rows=Math.ceil(height/dy)+3;
  const x0=width/2-(columns-1)*dx/2,y0=height/2+(rows-1)*dy/2;
  const features=[];
  for(let row=0;row<rows;row++)for(let column=0;column<columns;column++){
    const cx=x0+column*dx+(row%2?dx/2:0),cy=y0-row*dy;
    const ring=[];
    for(let k=0;k<6;k++){const angle=(30+60*k)*Math.PI/180;ring.push([west+(cx+side*Math.cos(angle))/kmPerLon,south+(cy+side*Math.sin(angle))/kmPerLat]);}
    ring.push(ring[0]);features.push(turf.polygon([ring]));
  }
  return turf.featureCollection(features);
}

async function loadCities(){state.collection=$('collection').value;setRuntime('','Loading AABPL catalogue…');try{const res=await fetch(AABPL[state.collection].meta);if(!res.ok)throw new Error(`AABPL catalogue returned ${res.status}`);state.cities=parseCSV(await res.text()).map(c=>state.collection==='us'?{...c,metro_id:c.cbsafp,metro_name:c.metro_name,...splitPlace(c.metro_name),states:(splitPlace(c.metro_name).country||'').split('-'),region:'US'}:{...c,...splitPlace(c.metro_name)}).filter(c=>c.metro_id&&c.metro_name&&!c.metro_name.startsWith('Mean,')).map(c=>({...c,region:state.collection==='us'?'US':regionFor(c.country)}));}catch(err){state.cities=state.collection==='global'?[{metro_id:'61',metro_name:'London, United Kingdom',city:'London',country:'United Kingdom',region:'Europe'}]:[];$('status-panel').innerHTML=`<strong>Catalogue unavailable</strong><span>${err.message}</span>`;}$('region-filter').hidden=state.collection==='us';$('country-label').textContent=state.collection==='us'?'State':'Country';$('city-label').textContent=state.collection==='us'?'US metropolitan area':'Global city';fillSelect($('region'),[...new Set(state.cities.map(c=>c.region))].sort().map(name=>({name})),'All regions');updateFilters();$('cell-size').value=state.cellSizes[state.collection];setRuntime('ready','Python model ready');resetPrepared();}

function startWorker(){state.worker=new Worker('pyodide-worker.js');state.worker.onmessage=({data})=>{if(data.type==='ready'){state.ready=true;setRuntime('ready','Python model ready');updateRunState();}else if(data.type==='progress'){setRuntime('',data.message);}else if(data.type==='result'){state.results=data.payload;if(state.pendingRun)state.lastRun={...state.pendingRun,result:data.payload,completed_at:new Date().toISOString()};state.pendingRun=null;renderResults(data.payload);setRuntime('ready','Simulation complete');updateRunState();}else if(data.type==='error'){state.pendingRun=null;setRuntime('error','Simulation stopped');$('status-panel').innerHTML=`<strong>Could not complete run</strong><span>${data.message}</span>`;updateRunState();}};state.worker.postMessage({type:'init'});}

function scenario(){const features=[];state.drawn.eachLayer(layer=>{const f=layer.toGeoJSON();f.properties={...(layer.feature?.properties||{})};features.push(f);});return{collection:state.collection,city_id:$('city').value,cell_shape:$('cell-shape').value,cell_size_km:+$('cell-size').value,off_network_speed_kmh:+$('off-speed').value,on_network_speed_kmh:+$('on-speed').value,spillovers:$('spillovers').value,max_cells:locationLimit(),features};}
function resetPrepared(){state.prepared=false;state.preparedGrid=null;if(state.gridLayer){map.removeLayer(state.gridLayer);state.gridLayer=null;}if(state.cityLayer){map.removeLayer(state.cityLayer);state.cityLayer=null;}$('cell-count').textContent='Select Prepare to build the model grid';$('status-panel').hidden=false;$('status-panel').innerHTML='<strong>City selected</strong><span>Prepare the city to download its AABPL source grid and construct the chosen model cells.</span>';updateRunState();}

async function prepareCity(){
  const request=scenario(),city=state.cities.find(c=>c.metro_id===request.city_id);
  setRuntime('',`Downloading ${city.city} grid…`);
  $('status-panel').innerHTML=`<strong>Downloading ${city.city}</strong><span>Reading the AABPL source grid from GitHub…</span>`;
  const url=`https://raw.githubusercontent.com/Ahlfeldt/AABPL-toolkit/main/SHAPEFILES/${AABPL[request.collection].folder}/grid_${request.city_id}.zip`;
  const response=await fetch(url);
  if(!response.ok)throw new Error(`AABPL grid download returned ${response.status}`);
  if(typeof shp!=='function')throw new Error('The browser shapefile reader did not load.');
  setRuntime('',`Reading ${city.city} geometry…`);
  let source=await shp(await response.arrayBuffer());
  if(Array.isArray(source))source=source[0];
  if(!source?.features?.length)throw new Error('The AABPL archive contained no readable grid features.');
  const normalized=source.features.map(f=>({...f,properties:Object.fromEntries(Object.entries(f.properties||{}).map(([key,value])=>[key.toLowerCase(),value]))}));
  const active=normalized.filter(f=>{const p=f.properties;return Number(p.devle)>0||Number(p.pop_sh)>0||Number(p.emp_sh)>0;});
  const activeCollection=turf.featureCollection(active);
  const bounds=turf.bbox(activeCollection);
  setRuntime('',`Constructing ${request.cell_size_km} km ${request.cell_shape} cells…`);
  const options={units:'kilometers',mask:turf.bboxPolygon(bounds)};
  // QUETRANSPORT defines cell_size_km as the square side and gives hexagons
  // the same target area. Turf instead expects a hexagon side length. For a
  // regular hexagon A = 3*sqrt(3)*s^2/2, so convert the requested target area.
  const generated=request.cell_shape==='hexagon'?quetransportHexGrid(bounds,request.cell_size_km):turf.squareGrid(bounds,request.cell_size_km,options);
  const generatedCellArea=generated.features.length?turf.area(generated.features[0])/1e6:0;
  const sourcePoints=turf.featureCollection(active.map(f=>{
    const p=f.properties||{},densityKey=Object.keys(p).find(key=>key.startsWith('pop_den')),density=Number(densityKey?p[densityKey]:0);
    return turf.point(turf.centroid(f).geometry.coordinates,{population:Math.max(0,density*turf.area(f)/1e6),employment_weight:Math.max(0,Number(p.emp_sh)||0),developed:Number(p.devle)>0?1:0});
  }));
  let attributed=turf.collect(generated,sourcePoints,'population','population_values');
  attributed=turf.collect(attributed,sourcePoints,'employment_weight','employment_values');
  attributed=turf.collect(attributed,sourcePoints,'developed','developed_values');
  const sum=values=>(values||[]).reduce((a,b)=>a+(Number(b)||0),0);
  const retained=attributed.features.filter(f=>sum(f.properties.population_values)>0||sum(f.properties.employment_values)>0||sum(f.properties.developed_values)>0);
  const totalPopulation=retained.reduce((a,f)=>a+sum(f.properties.population_values),0);
  const totalEmploymentWeight=retained.reduce((a,f)=>a+sum(f.properties.employment_values),0);
  retained.forEach((f,i)=>{const population=sum(f.properties.population_values);f.properties={location_id:String(i+1),population,employment:totalEmploymentWeight>0?sum(f.properties.employment_values)/totalEmploymentWeight*totalPopulation:population,land_area:turf.area(f)};});
  if(retained.length>request.max_cells){
    $('cell-count').textContent=`${retained.length.toLocaleString()} retained cells — too many`;
    throw new Error(`This choice produces approximately ${retained.length.toLocaleString()} cells. Choose a larger cell size to stay below ${request.max_cells.toLocaleString()}.`);
  }
  state.preparedGrid=turf.featureCollection(retained);
  state.gridLayer=L.geoJSON(state.preparedGrid,{renderer:L.canvas(),style:{color:'#176b87',weight:1,fillColor:'#54a9bd',fillOpacity:.18}}).addTo(map);
  fitPreparedGrid();
  state.prepared=true;
  $('cell-count').textContent=`${retained.length.toLocaleString()} retained model cells`;
  $('status-panel').innerHTML=`<strong>${city.metro_name} prepared</strong><span>${retained.length.toLocaleString()} ${request.cell_shape} cells at ${request.cell_size_km} km (${generatedCellArea.toFixed(2)} km² each). Draw an intervention or run a fundamentals-only baseline comparison.</span>`;
  setRuntime('ready','Python model ready');
  updateRunState();
}

// TTMATRIX-style origin routing: build the network once, solve shortest paths
// from its access nodes, and retain direct off-network travel as an OD option.
function buildNetworkMatrix(centres,direct,lines,stations,offSpeed,onSpeed){
  const n=centres.length,result=direct.map(row=>row.slice());
  if(!lines.length)return result;
  const lengths=lines.map(line=>turf.length(line,{units:'kilometers'}));
  const breaks=lines.map((line,i)=>[{location:0,point:turf.along(line,0,{units:'kilometers'})},{location:lengths[i],point:turf.along(line,lengths[i],{units:'kilometers'})}]);
  for(let a=0;a<lines.length;a++)for(let b=a+1;b<lines.length;b++)for(const point of turf.lineIntersect(lines[a],lines[b]).features){const pa=turf.nearestPointOnLine(lines[a],point,{units:'kilometers'}),pb=turf.nearestPointOnLine(lines[b],point,{units:'kilometers'});breaks[a].push({location:pa.properties.location,point});breaks[b].push({location:pb.properties.location,point});}
  function nearestNetworkPoint(point){let best=null;lines.forEach((line,lineIndex)=>{const snapped=turf.nearestPointOnLine(line,point,{units:'kilometers'});if(!best||snapped.properties.dist<best.dist)best={lineIndex,point:snapped,location:snapped.properties.location,dist:snapped.properties.dist};});return best;}
  const accessPoints=(stations.length?stations:centres).map(nearestNetworkPoint);
  accessPoints.forEach(access=>breaks[access.lineIndex].push({location:access.location,point:access.point}));
  const nodeIds=new Map(),adj=[];
  function node(point){const c=point.geometry.coordinates,key=`${c[0].toFixed(7)},${c[1].toFixed(7)}`;if(!nodeIds.has(key)){nodeIds.set(key,adj.length);adj.push([]);}return nodeIds.get(key);}
  function edge(a,b,weight){if(a===b||weight<=1e-10)return;adj[a].push([b,weight]);adj[b].push([a,weight]);}
  breaks.forEach(points=>{points.sort((a,b)=>a.location-b.location);const unique=points.filter((p,i)=>!i||Math.abs(p.location-points[i-1].location)>1e-8);for(let i=1;i<unique.length;i++)edge(node(unique[i-1].point),node(unique[i].point),unique[i].location-unique[i-1].location);});
  const accessNodes=accessPoints.map(a=>node(a.point));
  function shortest(source){const dist=Array(adj.length).fill(Infinity),heap=[[0,source]];dist[source]=0;while(heap.length){const top=heap[0],last=heap.pop();if(heap.length){heap[0]=last;let i=0;while(true){let child=i*2+1;if(child>=heap.length)break;if(child+1<heap.length&&heap[child+1][0]<heap[child][0])child++;if(heap[i][0]<=heap[child][0])break;[heap[i],heap[child]]=[heap[child],heap[i]];i=child;}}const [distance,u]=top;if(distance!==dist[u])continue;for(const [v,w] of adj[u])if(distance+w<dist[v]){dist[v]=distance+w;heap.push([dist[v],v]);let i=heap.length-1;while(i){const parent=(i-1)>>1;if(heap[parent][0]<=heap[i][0])break;[heap[parent],heap[i]]=[heap[i],heap[parent]];i=parent;}}}return dist;}
  const networkDistances=accessNodes.map(source=>shortest(source));
  if(!stations.length){for(let i=0;i<n;i++)for(let j=i;j<n;j++){const route=(accessPoints[i].dist+accessPoints[j].dist)/offSpeed*60+networkDistances[i][accessNodes[j]]/onSpeed*60;result[i][j]=Math.min(result[i][j],route);result[j][i]=result[i][j];}}
  else{const access=centres.map(c=>accessPoints.map(s=>turf.distance(c,s.point,{units:'kilometers'})/offSpeed*60)),stationRoutes=accessNodes.map((_,a)=>accessNodes.map(nodeB=>networkDistances[a][nodeB]/onSpeed*60));for(let i=0;i<n;i++){const bestTo=accessNodes.map((_,b)=>Math.min(...accessNodes.map((__,a)=>access[i][a]+stationRoutes[a][b])));for(let j=i;j<n;j++){let route=Infinity;for(let b=0;b<accessNodes.length;b++)route=Math.min(route,bestTo[b]+access[j][b]);result[i][j]=Math.min(result[i][j],route);result[j][i]=result[i][j];}}}
  return result;
}

function buildTravelMatrices(grid,features,offSpeed,onSpeed){
  const centres=grid.features.map(turf.centroid),n=centres.length,direct=Array.from({length:n},()=>Array(n).fill(0));
  for(let i=0;i<n;i++)for(let j=i;j<n;j++){const value=i===j?1:turf.distance(centres[i],centres[j],{units:'kilometers'})/offSpeed*60;direct[i][j]=value;direct[j][i]=value;}
  const additions=features.filter(f=>f.properties.kind==='transport'&&f.geometry.type==='LineString'),drawnStations=features.filter(f=>f.properties.kind==='station'&&f.geometry.type==='Point');
  const baseline=buildNetworkMatrix(centres,direct,state.baselineLines,state.baselineStations,offSpeed,onSpeed);
  const counterfactual=buildNetworkMatrix(centres,direct,[...state.baselineLines,...additions],[...state.baselineStations,...drawnStations],offSpeed,onSpeed);
  return{baseline,counterfactual};
}

function modelPayload(request){
  const cells=state.preparedGrid.features,travel=buildTravelMatrices(state.preparedGrid,request.features,request.off_network_speed_kmh,request.on_network_speed_kmh);
  const shocks=cells.map(cell=>{const centre=turf.centroid(cell);let productivity=1,amenity=1,density=1;for(const feature of request.features.filter(f=>f.properties.kind==='shock'))if(turf.booleanPointInPolygon(centre,feature)){productivity*=1+(Number(feature.properties.productivity_pct)||0)/100;amenity*=1+(Number(feature.properties.amenity_pct)||0)/100;density*=1+(Number(feature.properties.structural_density_pct)||0)/100;}return[productivity,amenity,density];});
  const population=cells.map(c=>Math.max(c.properties.population,1e-6)),employment=cells.map(c=>Math.max(c.properties.employment,1e-6));
  const meanPop=population.reduce((a,b)=>a+b,0)/population.length;
  const rent=population.map((p,i)=>Math.pow(p/meanPop,.25)*(1+.1*Math.sin((i+1)*12.9898)));
  return{...request,travel_routing:{method:'ttmatrix_origin_routing',station_candidates:'all'},ids:cells.map(c=>c.properties.location_id),population,employment,rent,land_area:cells.map(c=>c.properties.land_area),travel_time_baseline:travel.baseline,travel_time_counterfactual:travel.counterfactual,shocks};
}
function mixColour(a,b,t){t=Math.max(0,Math.min(1,t));const x=a.match(/\w\w/g).map(v=>parseInt(v,16)),y=b.match(/\w\w/g).map(v=>parseInt(v,16));return'#'+x.map((v,i)=>Math.round(v+(y[i]-v)*t).toString(16).padStart(2,'0')).join('');}
function formatCellValue(value,view){if(!Number.isFinite(value))return'No data';if(view==='pct')return`${value>=0?'+':''}${value.toFixed(2)}%`;return Math.abs(value)>=1000?value.toLocaleString(undefined,{maximumFractionDigits:0}):value.toLocaleString(undefined,{maximumSignificantDigits:4});}
function updateResultMap(result){
  if(!result?.local||!state.gridLayer)return;
  const outcome=$('outcome').value,view=$('result-view').value,pair=result.local[outcome];if(!pair)return;
  const baseline=pair[0],counterfactual=pair[1],values=baseline.map((v,i)=>view==='baseline'?v:view==='counterfactual'?counterfactual[i]:view==='absolute'?counterfactual[i]-v:(Math.abs(v)>1e-12?100*(counterfactual[i]/v-1):NaN));
  const finite=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!finite.length)return;const percentile=p=>finite[Math.min(finite.length-1,Math.max(0,Math.floor(p*(finite.length-1))))];
  const change=view==='pct'||view==='absolute';let lo,hi,scale;if(change){scale=Math.max(Math.abs(percentile(.025)),Math.abs(percentile(.975)),1e-12);lo=-scale;hi=scale;}else{lo=percentile(.025);hi=percentile(.975);scale=Math.max(hi-lo,1e-12);}
  let index=0;state.gridLayer.eachLayer(layer=>{const value=values[index],base=baseline[index],cf=counterfactual[index];let fill='#cbd3d7';if(Number.isFinite(value)){if(change)fill=value<0?mixColour('f7f7f2','176b87',Math.abs(value)/scale):mixColour('f7f7f2','b74338',value/scale);else fill=mixColour('eef5f6','176b87',(value-lo)/scale);}layer.setStyle({color:'#ffffff',weight:.55,fillColor:fill,fillOpacity:.78});layer.bindTooltip(`<strong>Cell ${index+1}</strong><br>${formatCellValue(value,view)}<br><span>Baseline ${formatCellValue(base,'baseline')} · Counterfactual ${formatCellValue(cf,'counterfactual')}</span>`,{sticky:true});index++;});
  const legend=$('map-legend');legend.hidden=false;legend.classList.toggle('level',!change);$('legend-min').textContent=formatCellValue(lo,view);$('legend-max').textContent=formatCellValue(hi,view);
}
function activeResult(){const closure=document.querySelector('.tabs button.active')?.dataset.closure;return state.results?.by_closure?.[closure]||state.results;}
function renderResults(result){const firstResults=$('results').hidden;$('results').hidden=false;$('status-panel').hidden=true;document.body.classList.remove('mobile-results-collapsed');$('results-handle').setAttribute('aria-expanded','true');const city=state.cities.find(c=>c.metro_id===$('city').value)?.metro_name||'Scenario',spec=$('spillovers').value==='with'?'with spillovers':'without spillovers';$('result-title').textContent=`${city} · ${spec}`;$('cards').innerHTML=(result.cards||[]).map(c=>`<article class="card"><div class="value">${c.change>=0?'+':''}${c.change.toFixed(2)}%</div><div class="label">${c.label}</div><div class="levels">Baseline ${c.baseline.toPrecision(4)} · Counterfactual ${c.counterfactual.toPrecision(4)}</div></article>`).join('');$('convergence').textContent=`${spec.charAt(0).toUpperCase()+spec.slice(1)} · converged in ${result.iterations} iterations · ${result.elapsed_seconds.toFixed(2)} s`;updateResultMap(result);if(firstResults)requestAnimationFrame(fitPreparedGrid);}

async function readShapefileZip(file,kind){
  if(!file)return[];let parsed=await shp(await file.arrayBuffer());if(!Array.isArray(parsed))parsed=[parsed];
  const features=parsed.flatMap(collection=>collection?.features||[]),output=[];
  for(const feature of features){const geometry=feature.geometry;if(!geometry)continue;if(kind==='line'&&geometry.type==='LineString')output.push(turf.lineString(geometry.coordinates));else if(kind==='line'&&geometry.type==='MultiLineString')geometry.coordinates.forEach(coords=>output.push(turf.lineString(coords)));else if(kind==='station'&&geometry.type==='Point')output.push(turf.point(geometry.coordinates));else if(kind==='station'&&geometry.type==='MultiPoint')geometry.coordinates.forEach(coords=>output.push(turf.point(coords)));}
  if(!output.length)throw new Error(`The ZIP contains no ${kind==='line'?'line':'point'} geometry.`);return output;
}
function updateBaselineStatus(){const stations=state.baselineStations.length?`${state.baselineStations.length.toLocaleString()} stations`:'continuous access';$('baseline-status').textContent=state.baselineLines.length?`${state.baselineLines.length.toLocaleString()} baseline lines loaded · ${stations}. Drawn lines will be added in the counterfactual.`:'No baseline network supplied.';$('clear-baseline').hidden=!state.baselineLines.length&&!state.baselineStations.length;$('run-note').textContent=state.baselineLines.length?'Baseline uses the uploaded network. The counterfactual adds the drawn lines. Structural parameters use toolkit defaults.':'Baseline travel is direct off-network travel. Structural parameters use the toolkit defaults.';}
async function loadBaselineNetwork(){try{setRuntime('','Reading baseline network…');state.baselineLines=await readShapefileZip($('baseline-network').files[0],'line');if(state.baselineLayer)map.removeLayer(state.baselineLayer);state.baselineLayer=L.geoJSON(turf.featureCollection(state.baselineLines),{style:{color:'#4f6672',weight:2,opacity:.7,dashArray:'5 4'}}).addTo(map);updateBaselineStatus();setRuntime('ready','Python model ready');}catch(error){state.baselineLines=[];$('baseline-network').value='';$('baseline-status').textContent=`Could not load network: ${error.message}`;setRuntime('error','Baseline network not loaded');}}
async function loadBaselineStations(){try{setRuntime('','Reading baseline stations…');state.baselineStations=await readShapefileZip($('baseline-stations').files[0],'station');updateBaselineStatus();setRuntime('ready','Python model ready');}catch(error){state.baselineStations=[];$('baseline-stations').value='';$('baseline-status').textContent=`Could not load stations: ${error.message}`;setRuntime('error','Baseline stations not loaded');}}
function clearBaseline(){state.baselineLines=[];state.baselineStations=[];$('baseline-network').value='';$('baseline-stations').value='';if(state.baselineLayer){map.removeLayer(state.baselineLayer);state.baselineLayer=null;}updateBaselineStatus();}

$('collection').addEventListener('change',loadCities);$('region').addEventListener('change',updateFilters);$('country').addEventListener('change',filterCities);$('city').addEventListener('change',resetPrepared);$('cell-shape').addEventListener('change',resetPrepared);$('cell-size').addEventListener('change',()=>{state.cellSizes[state.collection]=$('cell-size').value;resetPrepared();});
$('baseline-network').addEventListener('change',loadBaselineNetwork);$('baseline-stations').addEventListener('change',loadBaselineStations);$('clear-baseline').addEventListener('click',clearBaseline);
$('clear-drawings').addEventListener('click',()=>{state.drawn.clearLayers();$('shock-editor').hidden=true;state.selectedShock=null;updateRunState();});
$('save-shock').addEventListener('click',()=>{if(!state.selectedShock)return;state.selectedShock.feature.properties={kind:'shock',productivity_pct:+$('prod-change').value,amenity_pct:+$('amen-change').value,structural_density_pct:+$('density-change').value};$('shock-editor').hidden=true;});
$('run').addEventListener('click',async()=>{const request=scenario();if(state.preparedGrid?.features.length>request.max_cells)return alert('This device allows up to '+request.max_cells.toLocaleString()+' locations. Choose a larger cell size and prepare again.');if(request.on_network_speed_kmh<=0||request.off_network_speed_kmh<=0)return alert('Travel speeds must be positive.');$('run').disabled=true;$('mobile-run').disabled=true;try{if(!state.prepared){await prepareCity();return;}setRuntime('','Constructing travel-time matrices…');const payload=modelPayload(request),city=state.cities.find(c=>c.metro_id===request.city_id),sourceGridUrl=`https://raw.githubusercontent.com/Ahlfeldt/AABPL-toolkit/main/SHAPEFILES/${AABPL[request.collection].folder}/grid_${request.city_id}.zip`;state.pendingRun={started_at:new Date().toISOString(),city:{id:request.city_id,name:city?.metro_name||request.city_id},settings:structuredClone(request),drawn_features:turf.featureCollection(structuredClone(request.features)),baseline_network:turf.featureCollection(structuredClone(state.baselineLines)),baseline_stations:turf.featureCollection(structuredClone(state.baselineStations)),prepared_grid:structuredClone(state.preparedGrid),model_input:structuredClone(payload),source_grid_url:sourceGridUrl};setMobileSetup(false);state.worker.postMessage({type:'run',payload});}catch(error){state.pendingRun=null;setRuntime('error','Preparation stopped');$('status-panel').innerHTML=`<strong>Could not prepare run</strong><span>${error.message}</span>`;updateRunState();}finally{if(!state.prepared)updateRunState();}});
document.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('active',x===b));if(state.results)renderResults(state.results.by_closure?.[b.dataset.closure]||state.results);}));
$('outcome').addEventListener('change',()=>updateResultMap(activeResult()));
$('result-view').addEventListener('change',()=>updateResultMap(activeResult()));
$('download-zip').addEventListener('click',async()=>{const button=$('download-zip'),label=button.textContent;button.disabled=true;button.textContent='Rendering maps…';try{const pack=await buildRunPackage(state.lastRun),blob=new Blob([pack.bytes],{type:'application/zip'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=pack.filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(error){alert(error.message);}finally{button.disabled=false;button.textContent=label;}});
function setMobileSetup(open){document.body.classList.toggle('mobile-controls-open',open);$('mobile-setup').setAttribute('aria-expanded',String(open));$('mobile-backdrop').hidden=!open;setTimeout(()=>map.invalidateSize(),240);}
$('mobile-setup').addEventListener('click',()=>setMobileSetup(true));$('mobile-close').addEventListener('click',()=>setMobileSetup(false));$('mobile-backdrop').addEventListener('click',()=>setMobileSetup(false));
const standaloneMode=new URLSearchParams(location.search).get('standalone')==='1';
if(standaloneMode){document.body.classList.add('fullscreen-session');$('mobile-fullscreen').textContent='Exit';$('mobile-fullscreen').setAttribute('aria-label','Exit full screen');}
function standaloneUrl(){const url=new URL(location.href);url.searchParams.set('standalone','1');return url.href;}
async function leaveFullscreen(){document.body.classList.remove('fullscreen-session');if(document.fullscreenElement&&document.exitFullscreen)await document.exitFullscreen();else if(standaloneMode){window.close();if(!window.closed){const url=new URL(location.href);url.searchParams.delete('standalone');location.replace(url.href);}}$('mobile-fullscreen').textContent='Full screen';$('mobile-fullscreen').setAttribute('aria-label','Enter full screen');setTimeout(()=>map.invalidateSize(),100);}
$('mobile-fullscreen').addEventListener('click',async()=>{if(document.body.classList.contains('fullscreen-session'))return leaveFullscreen();if(!document.fullscreenEnabled||!document.documentElement.requestFullscreen){window.open(standaloneUrl(),'_blank','noopener');return;}document.body.classList.add('fullscreen-session');$('mobile-fullscreen').textContent='Exit';$('mobile-fullscreen').setAttribute('aria-label','Exit full screen');try{await document.documentElement.requestFullscreen({navigationUI:'hide'});}catch(error){document.body.classList.remove('fullscreen-session');window.open(standaloneUrl(),'_blank','noopener');}setTimeout(()=>map.invalidateSize(),100);});
document.addEventListener('fullscreenchange',()=>{if(document.fullscreenElement)document.body.classList.add('fullscreen-session');setTimeout(()=>map.invalidateSize(),100);});
$('fullscreen-exit').addEventListener('click',leaveFullscreen);
$('fullscreen-setup').addEventListener('click',()=>{if(innerWidth<=768)setMobileSetup(true);else $('scenario-controls').scrollIntoView({block:'start'});});
$('mobile-run').addEventListener('click',()=>$('run').click());
function toggleMobileResults(){const collapsed=document.body.classList.toggle('mobile-results-collapsed');$('results-handle').setAttribute('aria-expanded',String(!collapsed));setTimeout(()=>map.invalidateSize(),240);}
$('results-handle').addEventListener('click',toggleMobileResults);let sheetY=null;$('results-handle').addEventListener('pointerdown',event=>{sheetY=event.clientY;});$('results-handle').addEventListener('pointerup',event=>{if(sheetY!==null&&Math.abs(event.clientY-sheetY)>35){const collapse=event.clientY>sheetY;document.body.classList.toggle('mobile-results-collapsed',collapse);$('results-handle').setAttribute('aria-expanded',String(!collapse));sheetY=null;}});
document.addEventListener('keydown',event=>{if(event.key==='Escape')setMobileSetup(false);});updateLocationLimit();
window.addEventListener('resize',()=>{updateLocationLimit();if(innerWidth>768)setMobileSetup(false);map.invalidateSize();requestAnimationFrame(fitPreparedGrid);});

if(location.protocol==='file:'){
  setRuntime('error','Open through the local web server');
  $('status-panel').innerHTML='<strong>A web server is required</strong><span>This application uses Pyodide and browser workers, which browsers block on file pages. Start webtool/START_WEBTOOL.py and open the HTTP address it displays.</span>';
  $('run-note').textContent='Start START_WEBTOOL.py, then use the http://localhost address. The application cannot run directly from a file address.';
}else{
  loadCities();
  startWorker();
}
