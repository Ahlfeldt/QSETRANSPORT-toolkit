/* Pyodide runs away from the UI thread so equilibrium iterations do not freeze
   map interaction. Existing toolkit modules are fetched from ../src/python and
   mounted without changing their source files. */
importScripts('https://cdn.jsdelivr.net/pyodide/v0.29.2/full/pyodide.js');

let pyodide;
const modelFiles=[
  'functions/__init__.py','functions/types.py',
  'functions/inversion/__init__.py','functions/inversion/baseline.py',
  'functions/equilibrium/__init__.py','functions/equilibrium/model.py'
];

function send(type,value={}){postMessage({type,...value});}

async function mountModel(){
  for(const relative of modelFiles){
    const response=await fetch(`../src/python/${relative}`);
    if(!response.ok)throw new Error(`Could not load existing model module: ${relative}`);
    const path=`/quet/${relative}`;
    const directory=path.slice(0,path.lastIndexOf('/'));
    pyodide.FS.mkdirTree(directory);
    pyodide.FS.writeFile(path,await response.text(),{encoding:'utf8'});
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/quet')");
}

async function initialise(){
  send('progress',{message:'Loading Python runtime…'});
  pyodide=await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.29.2/full/'});
  send('progress',{message:'Loading numerical packages…'});
  await pyodide.loadPackage(['numpy','pandas','scipy','networkx','shapely']);
  await mountModel();
  send('ready');
}

async function run(payload){
  send('progress',{message:'Inverting the baseline economy…'});
  pyodide.globals.set('web_request_json',JSON.stringify(payload));
  const resultJson=await pyodide.runPythonAsync(`
import json, time
import numpy as np
import pandas as pd
from functions.types import Parameters, ModelData
from functions.inversion import invert_baseline
from functions.equilibrium import solve_closure, solve_fixed_distribution

started = time.perf_counter()
r = json.loads(web_request_json)
use_spillovers = r.get('spillovers', 'with') == 'with'
config = {
    'model': {
        'production_share_labor': .80,
        'expenditure_share_consumption': .75,
        'commuting_time_coefficient': .014744,
        'commuting_elasticity': 6.6941,
        'productivity_spillover': .0710 if use_spillovers else 0.0,
        'productivity_spatial_decay': .3617,
        'amenity_spillover': .1553 if use_spillovers else 0.0,
        'amenity_spatial_decay': .7595,
        'construction_land_share': .25,
    },
    'numerics': {
        'tolerance_equilibrium': 1e-6,
        'maximum_iterations': 10000,
        'damping_equilibrium': .10,
        'print_every': 100000,
    },
}
param = Parameters.from_config(config)
ids = np.asarray(r['ids'], dtype=str)
population = np.asarray(r['population'], dtype=float)
employment = np.asarray(r['employment'], dtype=float)
employment *= population.sum() / employment.sum()
rent = np.asarray(r['rent'], dtype=float)
rent /= rent.mean()
land_area = np.asarray(r['land_area'], dtype=float)
table = pd.DataFrame({'location_id': ids, 'population': population,
                      'employment_model': employment,
                      'rent_floor_space': rent, 'land_area': land_area})
data = ModelData(table, ids, population, employment, rent, land_area)
t0 = np.asarray(r['travel_time_baseline'], dtype=float)
t1 = np.asarray(r['travel_time_counterfactual'], dtype=float)
inversion = invert_baseline(data, t0, param)
fundamentals_cf = inversion.fundamentals.copy()
shock = np.asarray(r['shocks'], dtype=float)
fundamentals_cf.productivity *= shock[:, 0]
fundamentals_cf.amenity *= shock[:, 1]
fundamentals_cf.density *= shock[:, 2]

def aggregate(base, cf):
    e0, e1 = base.endog, cf.endog
    floor0 = base.fundamentals.density * land_area ** param.construction_land_share
    floor1 = cf.fundamentals.density * land_area ** param.construction_land_share
    lr0 = param.construction_land_share * (e0[:,5]*e0[:,2]*floor0 + e0[:,4]*(1-e0[:,2])*floor0)
    lr1 = param.construction_land_share * (e1[:,5]*e1[:,2]*floor1 + e1[:,4]*(1-e1[:,2])*floor1)
    commute0 = float(np.sum(base.commuting_probability * t0))
    commute1 = float(np.sum(cf.commuting_probability * t1))
    values = [
        ('Expected utility', float(base.utility), float(cf.utility)),
        ('Population', float(base.population), float(cf.population)),
        ('GDP / output', float(e0[:,3].sum()), float(e1[:,3].sum())),
        ('Aggregate land rent', float(lr0.sum()), float(lr1.sum())),
        ('Mean commute time', commute0, commute1),
    ]
    cards = [{'label': label, 'baseline': b, 'counterfactual': c,
              'change': 100*(c/b-1) if b else 0.0} for label,b,c in values]
    local = {
        'employment': [e0[:,6].tolist(), e1[:,6].tolist()],
        'population': [e0[:,7].tolist(), e1[:,7].tolist()],
        'wage': [e0[:,0].tolist(), e1[:,0].tolist()],
        'rent_residential': [e0[:,4].tolist(), e1[:,4].tolist()],
        'rent_commercial': [e0[:,5].tolist(), e1[:,5].tolist()],
        'output': [e0[:,3].tolist(), e1[:,3].tolist()],
        'annual_land_rent': [lr0.tolist(), lr1.tolist()],
    }
    return {'cards': cards, 'local': local, 'iterations': int(cf.iterations),
            'converged': bool(cf.converged)}

closed0 = solve_closure('closed', param, inversion.fundamentals, t0)
closed1 = solve_closure('closed', param, fundamentals_cf, t1)
open0 = solve_closure('open', param, inversion.fundamentals, t0, inversion.reservation_utility)
open1 = solve_closure('open', param, fundamentals_cf, t1, inversion.reservation_utility)
fixed1 = solve_fixed_distribution(param, fundamentals_cf, t0, t1, closed0, data)
by_closure = {
    'closed': aggregate(closed0, closed1),
    'open': aggregate(open0, open1),
    'fixed_distribution': aggregate(closed0, fixed1),
}
for value in by_closure.values():
    value['elapsed_seconds'] = time.perf_counter() - started
result = dict(by_closure['closed'])
result['by_closure'] = by_closure
json.dumps(result)
  `);
  send('result',{payload:JSON.parse(resultJson)});
}

onmessage=async({data})=>{
  try{
    if(data.type==='init')await initialise();
    if(data.type==='run')await run(data.payload);
  }catch(error){send('error',{message:error?.message||String(error)});}
};
