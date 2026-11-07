const encoder=new TextEncoder();

function crc32(bytes){
  let crc=0xffffffff;
  for(const byte of bytes){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
  return(crc^0xffffffff)>>>0;
}
function u16(value){return[value&255,(value>>>8)&255];}
function u32(value){return[value&255,(value>>>8)&255,(value>>>16)&255,(value>>>24)&255];}
function concat(parts){const size=parts.reduce((n,p)=>n+p.length,0),out=new Uint8Array(size);let offset=0;for(const part of parts){out.set(part,offset);offset+=part.length;}return out;}
function zipStore(entries){
  const local=[],central=[];let offset=0;
  for(const entry of entries){
    const name=encoder.encode(entry.name),data=typeof entry.content==='string'?encoder.encode(entry.content):entry.content,crc=crc32(data);
    const header=new Uint8Array([0x50,0x4b,0x03,0x04,...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0),...u32(crc),...u32(data.length),...u32(data.length),...u16(name.length),...u16(0)]);
    local.push(header,name,data);
    central.push(new Uint8Array([0x50,0x4b,0x01,0x02,...u16(20),...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0),...u32(crc),...u32(data.length),...u32(data.length),...u16(name.length),...u16(0),...u16(0),...u16(0),...u16(0),...u32(0),...u32(offset)]),name);
    offset+=header.length+name.length+data.length;
  }
  const centralBytes=concat(central),end=new Uint8Array([0x50,0x4b,0x05,0x06,...u16(0),...u16(0),...u16(entries.length),...u16(entries.length),...u32(centralBytes.length),...u32(offset),...u16(0)]);
  return concat([...local,centralBytes,end]);
}

function json(value){return JSON.stringify(value,null,2)+'\n';}
function csvCell(value){if(value===null||value===undefined)return'';const text=String(value);return /[",\r\n]/.test(text)?`"${text.replaceAll('"','""')}"`:text;}
function csv(rows){return rows.map(row=>row.map(csvCell).join(',')).join('\n')+'\n';}
function pct(base,counterfactual){return Math.abs(base)>1e-12?100*(counterfactual/base-1):null;}
function safeSlug(value){return String(value||'run').normalize('NFKD').replace(/[^a-zA-Z0-9]+/g,'-').replace(/^-|-$/g,'').toLowerCase()||'run';}

function closureCellCsv(closure,ids){
  const outcomes=Object.keys(closure.local||{}),header=['location_id'];
  for(const outcome of outcomes)header.push(`${outcome}_baseline`,`${outcome}_counterfactual`,`${outcome}_absolute_change`,`${outcome}_percentage_change`);
  const rows=[header];
  ids.forEach((id,i)=>{const row=[id];for(const outcome of outcomes){const base=closure.local[outcome][0][i],cf=closure.local[outcome][1][i];row.push(base,cf,cf-base,pct(base,cf));}rows.push(row);});
  return csv(rows);
}
function aggregateCsv(byClosure){
  const rows=[['closure','measure','baseline','counterfactual','percentage_change','converged','iterations','elapsed_seconds']];
  for(const [name,result] of Object.entries(byClosure))for(const card of result.cards||[])rows.push([name,card.label,card.baseline,card.counterfactual,card.change,result.converged,result.iterations,result.elapsed_seconds]);
  return csv(rows);
}

function mapColour(value,scale){
  const t=Math.min(1,Math.abs(value)/Math.max(scale,1e-12)),from=[247,247,242],to=value<0?[23,107,135]:[183,67,56];
  return`rgb(${from.map((v,i)=>Math.round(v+(to[i]-v)*t)).join(',')})`;
}
function mapBounds(features){const coords=[];for(const feature of features){const walk=value=>{if(typeof value?.[0]==='number')coords.push(value);else for(const child of value||[])walk(child);};walk(feature.geometry?.coordinates);}return{west:Math.min(...coords.map(c=>c[0])),east:Math.max(...coords.map(c=>c[0])),south:Math.min(...coords.map(c=>c[1])),north:Math.max(...coords.map(c=>c[1]))};}
function canvasBlob(canvas,type,quality){return new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error(`Could not render ${type} map.`)),type,quality));}
function dataUrlBytes(url){const raw=atob(url.slice(url.indexOf(',')+1)),out=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)out[i]=raw.charCodeAt(i);return out;}
function pdfWithJpeg(jpeg,width,height,title){
  const safeTitle=title.replace(/[^\x20-\x7e]/g,'?').replace(/[()\\]/g,' '),stream=encoder.encode(`BT /F1 13 Tf 36 ${height-28} Td (${safeTitle}) Tj ET\nq ${width-72} 0 0 ${height-72} 36 24 cm /Im0 Do Q`),objects=[null];
  objects.push(encoder.encode('<< /Type /Catalog /Pages 2 0 R >>'));objects.push(encoder.encode('<< /Type /Pages /Kids [3 0 R] /Count 1 >>'));objects.push(encoder.encode(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /Font << /F1 6 0 R >> /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>`));objects.push(concat([encoder.encode(`<< /Length ${stream.length} >>\nstream\n`),stream,encoder.encode('\nendstream')]));objects.push(concat([encoder.encode(`<< /Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`),jpeg,encoder.encode('\nendstream')]));objects.push(encoder.encode('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'));
  const parts=[encoder.encode('%PDF-1.4\n')],offsets=[0];let offset=parts[0].length;for(let i=1;i<objects.length;i++){offsets[i]=offset;const part=concat([encoder.encode(`${i} 0 obj\n`),objects[i],encoder.encode('\nendobj\n')]);parts.push(part);offset+=part.length;}const xref=offset;let table=`xref\n0 ${objects.length}\n0000000000 65535 f \n`;for(let i=1;i<objects.length;i++)table+=`${String(offsets[i]).padStart(10,'0')} 00000 n \n`;parts.push(encoder.encode(`${table}trailer\n<< /Size ${objects.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`));return concat(parts);
}
async function renderMapAssets(run){
  if(typeof document==='undefined')throw new Error('Map rendering requires a browser.');
  const width=1000,height=720,pad={left:54,right:34,top:82,bottom:62},bounds=mapBounds(run.prepared_grid.features),dx=Math.max(bounds.east-bounds.west,1e-9),dy=Math.max(bounds.north-bounds.south,1e-9),project=c=>[pad.left+(c[0]-bounds.west)/dx*(width-pad.left-pad.right),height-pad.bottom-(c[1]-bounds.south)/dy*(height-pad.top-pad.bottom)],assets=[];
  for(const [closureName,closure] of Object.entries(run.result.by_closure))for(const [outcome,[baseline,counterfactual]] of Object.entries(closure.local)){
    const values=baseline.map((v,i)=>pct(v,counterfactual[i])??0),sorted=values.map(Math.abs).sort((a,b)=>a-b),scale=Math.max(sorted[Math.floor(.975*(sorted.length-1))]||0,1e-12),canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,width,height);ctx.fillStyle='#17212b';ctx.font='bold 22px Arial';ctx.fillText(`${run.city.name} · ${outcome.replaceAll('_',' ')} · ${closureName.replaceAll('_',' ')}`,pad.left,32);ctx.font='14px Arial';ctx.fillStyle='#65717d';ctx.fillText('Counterfactual percentage change by model cell',pad.left,56);
    run.prepared_grid.features.forEach((feature,i)=>{const rings=feature.geometry.type==='Polygon'?feature.geometry.coordinates:feature.geometry.coordinates.flat();ctx.beginPath();for(const ring of rings)ring.forEach((coord,j)=>{const[x,y]=project(coord);j?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.fillStyle=mapColour(values[i],scale);ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=.55;ctx.stroke();});
    const scenarioFeatures=[...run.baseline_network.features,...run.baseline_stations.features,...run.drawn_features.features];for(const feature of scenarioFeatures){if(feature.geometry.type==='LineString'){ctx.beginPath();feature.geometry.coordinates.forEach((coord,i)=>{const[x,y]=project(coord);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.strokeStyle=feature.properties?.kind==='transport'?'#222':'#566b76';ctx.lineWidth=3;ctx.stroke();}else if(feature.geometry.type==='Point'){const[x,y]=project(feature.geometry.coordinates);ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fillStyle='#222';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=1.5;ctx.stroke();}else if(feature.geometry.type==='Polygon'){ctx.beginPath();for(const ring of feature.geometry.coordinates)ring.forEach((coord,i)=>{const[x,y]=project(coord);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.strokeStyle='#28735a';ctx.lineWidth=2;ctx.stroke();}}
    const grad=ctx.createLinearGradient(pad.left,height-32,pad.left+260,height-32);grad.addColorStop(0,'#176b87');grad.addColorStop(.5,'#f7f7f2');grad.addColorStop(1,'#b74338');ctx.fillStyle=grad;ctx.fillRect(pad.left,height-42,260,14);ctx.strokeStyle='#9aa9b1';ctx.strokeRect(pad.left,height-42,260,14);ctx.fillStyle='#43515d';ctx.font='12px Arial';ctx.fillText(`${-scale.toFixed(2)}%`,pad.left,height-12);ctx.fillText('0%',pad.left+126,height-12);ctx.fillText(`+${scale.toFixed(2)}%`,pad.left+225,height-12);ctx.fillText('QUETRANSPORT browser simulation',width-250,height-18);
    const png=new Uint8Array(await(await canvasBlob(canvas,'image/png')).arrayBuffer()),jpeg=dataUrlBytes(canvas.toDataURL('image/jpeg',.92)),slug=`maps/${closureName}/${outcome}`;assets.push({name:`${slug}.png`,content:png},{name:`${slug}.pdf`,content:pdfWithJpeg(jpeg,width,height,`${run.city.name} - ${outcome} - ${closureName}`)});
  }
  return assets;
}

export async function buildRunPackage(run,{includeMaps=true}={}){
  if(!run?.result?.by_closure||!run?.model_input||!run?.prepared_grid)throw new Error('A completed run is required before downloading a package.');
  const settings={...run.settings};delete settings.features;
  const scenario={package_format:'QUETRANSPORT run package v1',run_started_at:run.started_at,run_completed_at:run.completed_at,city:run.city,settings,counts:{prepared_cells:run.prepared_grid.features.length,drawn_features:run.drawn_features.features.length,baseline_lines:run.baseline_network.features.length,baseline_stations:run.baseline_stations.features.length},source_grid_url:run.source_grid_url};
  const files=[
    {name:'README.md',content:readme(scenario)},
    {name:'scenario/settings.json',content:json(scenario)},
    {name:'scenario/drawn_features.geojson',content:json(run.drawn_features)},
    {name:'scenario/baseline_network.geojson',content:json(run.baseline_network)},
    {name:'scenario/baseline_stations.geojson',content:json(run.baseline_stations)},
    {name:'inputs/prepared_grid.geojson',content:json(run.prepared_grid)},
    {name:'inputs/model_input.json',content:json(run.model_input)},
    {name:'results/all_closures.json',content:json(run.result)},
    {name:'results/aggregate_summary.csv',content:aggregateCsv(run.result.by_closure)}
  ];
  for(const [name,result] of Object.entries(run.result.by_closure))files.push({name:`results/${name}_cell_results.csv`,content:closureCellCsv(result,run.model_input.ids)});
  if(includeMaps)files.push(...await renderMapAssets(run));
  const stamp=(run.completed_at||new Date().toISOString()).replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z');
  return{filename:`quetransport-${safeSlug(run.city?.name)}-${stamp}.zip`,bytes:zipStore(files),files:files.map(file=>file.name)};
}

function readme(s){return`# QUETRANSPORT run package

This archive contains the complete browser scenario and results for **${s.city.name}**. It was generated by QUETRANSPORT from the run completed at ${s.run_completed_at}.

## Contents

- \`scenario/settings.json\`: run identity, city, grid, speed, spillover and source settings.
- \`scenario/drawn_features.geojson\`: drawn transport lines, stations and fundamentals polygons, including percentage changes.
- \`scenario/baseline_network.geojson\` and \`baseline_stations.geojson\`: uploaded baseline features after conversion to WGS84 GeoJSON; empty collections mean none were supplied.
- \`inputs/prepared_grid.geojson\`: the exact retained model cells with location IDs and baseline attributes.
- \`inputs/model_input.json\`: the exact numeric payload sent to the Python model, including baseline and counterfactual travel-time matrices and applied shock multipliers.
- \`results/all_closures.json\`: complete aggregate and cell-level results for closed city, open city and fixed distribution.
- \`results/aggregate_summary.csv\`: aggregate results in tabular form.
- \`results/*_cell_results.csv\`: baseline, counterfactual, absolute-change and percentage-change values for every outcome and location under each closure.
- \`maps/<closure>/<outcome>.png\` and \`.pdf\`: publication-ready maps of counterfactual percentage changes for every outcome under every closure.

## Reproduction

1. Open the QUETRANSPORT webtool and choose city ID \`${s.city.id}\` from the \`${s.settings.collection}\` collection.
2. Select ${s.settings.cell_size_km} km ${s.settings.cell_shape} cells, ${s.settings.off_network_speed_kmh} km/h off-network speed, ${s.settings.on_network_speed_kmh} km/h on-network speed, and the \`${s.settings.spillovers}\` spillover specification.
3. Recreate or import the GeoJSON features in \`scenario/\`. The original AAB-PL source grid is ${s.source_grid_url}.
4. Prepare the city and run the counterfactual. For an exact computational replay, use \`inputs/model_input.json\` with the QUETRANSPORT Python model; it preserves all arrays sent to Pyodide.
5. Compare the returned object with \`results/all_closures.json\`. Small elapsed-time differences are expected; numeric results should agree subject to the same software versions.

## Citation

Please cite Ahlfeldt, Redding, Sturm and Wolf (2015), *Econometrica* 83(6), and Ahlfeldt, Albers and Behrens (2026), *American Economic Review: Insights* 8(3), when referring to results generated by this toolkit.
`;}
