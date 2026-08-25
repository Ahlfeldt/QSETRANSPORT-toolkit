%% QUETRANSPORT 01: INVERT THE BASELINE EQUILIBRIUM
% Run this script section by section. All functions are stored separately.
clear; clc; close all; format shortG;

%% 1. LOCATE THE PROJECT AND READ THE SINGLE CONFIGURATION SNAPSHOT
scriptFile=mfilename('fullpath');
assert(~isempty(scriptFile),'Open this file in the MATLAB editor before running it.');
projectRoot=fileparts(fileparts(fileparts(fileparts(scriptFile))));
addpath(genpath(fullfile(projectRoot,'src','matlab','functions')));
config=qt_load_config(projectRoot);
param=qt_set_parameters(config);

%% 2. READ STANDARDIZED GRID DATA AND THE BASELINE TRAVEL-TIME MATRIX
data=qt_read_inputs(projectRoot);
fprintf('Reading a %d-by-%d baseline travel-time matrix.\n',data.N,data.N);
travelTimeBaseline=qt_read_matrix(projectRoot,'travel_times_baseline.csv',data.N);

%% 3. INVERT PRODUCTIVITY, AMENITIES, WAGES, AND STRUCTURAL DENSITY
fprintf('Starting ARSW-style baseline inversion for %d locations.\n',data.N);
inversion=qt_invert_baseline(data,travelTimeBaseline,param,config);

%% 4. SAVE THE INVERTED FUNDAMENTALS AND BASELINE DIAGNOSTICS
outputDir=qt_output_dir(projectRoot,config,'inversion');
if ~isfolder(outputDir); mkdir(outputDir); end
save(fullfile(outputDir,'baseline_inversion.mat'),'config','param','data','inversion','-v7.3');
primitiveTable=table(data.id,inversion.A,inversion.B,inversion.a,inversion.b,...
    inversion.wage,inversion.CMA,inversion.V,inversion.theta,...
    'VariableNames',{'location_id','productivity_total','amenity_total',...
    'productivity_fundamental','amenity_fundamental','effective_wage',...
    'commuting_market_access','structural_density','commercial_floor_share'});
writetable(primitiveTable,fullfile(outputDir,'inverted_primitives.csv'));
fprintf('Baseline inversion saved in %s\n',outputDir);
