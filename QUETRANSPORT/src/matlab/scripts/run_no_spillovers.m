%% QUETRANSPORT SENSITIVITY: ZERO PRODUCTIVITY AND AMENITY SPILLOVERS
% Re-invert the observed baseline and run all three scenarios with lambda=eta=0.
clear; clc; close all; format shortG;

%% 1. PROJECT, CONFIGURATION, AND ZERO-SPILLOVER PARAMETERS
scriptFile=mfilename('fullpath');
assert(~isempty(scriptFile),'Open this file in the MATLAB editor before running it.');
projectRoot=fileparts(fileparts(fileparts(fileparts(scriptFile))));
addpath(genpath(fullfile(projectRoot,'src','matlab','functions')));
config=qt_load_config(projectRoot);
config.model.productivity_spillover=0;
config.model.amenity_spillover=0;
config.reporting.result_variant='no_spillovers';
param=qt_set_parameters(config);

%% 2. READ THE COMMON STANDARDIZED INPUTS AND RE-INVERT THE BASELINE
data=qt_read_inputs(projectRoot);
travelTimeBaseline=qt_read_matrix(projectRoot,'travel_times_baseline.csv',data.N);
travelTimeCounterfactual=qt_read_matrix(projectRoot,'travel_times_counterfactual.csv',data.N);
fprintf('Starting zero-spillover baseline inversion for %d locations.\n',data.N);
inversion=qt_invert_baseline(data,travelTimeBaseline,param,config);

inversionDir=qt_output_dir(projectRoot,config,'inversion');
if ~isfolder(inversionDir); mkdir(inversionDir); end
save(fullfile(inversionDir,'baseline_inversion.mat'),...
    'config','param','data','inversion','-v7.3');
primitiveTable=table(data.id,inversion.A,inversion.B,inversion.a,inversion.b,...
    inversion.wage,inversion.CMA,inversion.V,inversion.theta,...
    'VariableNames',{'location_id','productivity_total','amenity_total',...
    'productivity_fundamental','amenity_fundamental','effective_wage',...
    'commuting_market_access','structural_density','commercial_floor_share'});
writetable(primitiveTable,fullfile(inversionDir,'inverted_primitives.csv'));

%% 3. SOLVE CLOSED AND OPEN CITIES
fundBaseline=inversion.fund;
fundCounterfactual=qt_apply_shocks(projectRoot,data,fundBaseline);
choice=lower(string(config.model.city_closure));
if choice=="both"; closures=["closed","open"]; else; closures=choice; end
aggregateTables=cell(numel(closures),1);
alluesults=struct();
for c=1:numel(closures)
    closure=closures(c);
    fprintf('Zero spillovers: solving %s-city baseline equilibrium.\n',closure);
    baseline=qt_solve_closure(closure,param,fundBaseline,travelTimeBaseline,...
        data.N,inversion.reservationUtility);
    fprintf('Zero spillovers: solving %s-city counterfactual equilibrium.\n',closure);
    counterfactual=qt_solve_closure(closure,param,fundCounterfactual,...
        travelTimeCounterfactual,data.N,inversion.reservationUtility);
    aggregateTables{c}=qt_write_closure_results(projectRoot,data,inversion,...
        baseline,counterfactual,travelTimeBaseline,travelTimeCounterfactual,config);
    alluesults.(char(closure))=struct('baseline',baseline,'counterfactual',counterfactual);
end
aggregateChanges=vertcat(aggregateTables{:});

%% 4. FIXED-DISTRIBUTION BENCHMARK WITH ZERO SPILLOVERS
if isfield(alluesults,'closed')
    fixedBaseline=alluesults.closed.baseline;
else
    fixedBaseline=qt_solve_closure("closed",param,fundBaseline,...
        travelTimeBaseline,data.N,inversion.reservationUtility);
end
fixedCounterfactual=qt_solve_fixed_distribution(param,fundCounterfactual,...
    travelTimeBaseline,travelTimeCounterfactual,fixedBaseline,data,config);
fixedAggregate=qt_write_closure_results(projectRoot,data,inversion,...
    fixedBaseline,fixedCounterfactual,travelTimeBaseline,...
    travelTimeCounterfactual,config);
aggregateChanges=vertcat(aggregateChanges,fixedAggregate);
alluesults.fixed_distribution=struct('baseline',fixedBaseline,...
    'counterfactual',fixedCounterfactual);

%% 5. SAVE ZERO-SPILLOVER TABLES SEPARATELY
outputDir=qt_output_dir(projectRoot,config,'simulation');
if ~isfolder(outputDir); mkdir(outputDir); end
components=fixedCounterfactual.welfareComponents;
fixedDistributionWelfareDecomposition=table(...
    ["commuting";"productivity_wage";"amenity";"combined"],...
    [components.commutingLogChange;components.productivityWageLogChange;...
     components.amenityLogChange;components.totalLogChange],...
    [components.commutingPct;components.productivityWagePct;...
     components.amenityPct;components.totalPct],...
    'VariableNames',{'Component','LogWelfareChange','EquivalentPct'});
writetable(fixedDistributionWelfareDecomposition,...
    fullfile(outputDir,'fixed_distribution_welfare_decomposition.csv'));
writetable(aggregateChanges,fullfile(outputDir,'aggregate_changes.csv'));
save(fullfile(outputDir,'counterfactual_results.mat'),'config','param','data',...
    'inversion','alluesults','aggregateChanges',...
    'fixedDistributionWelfareDecomposition','-v7.3');

% Replace the main aggregate table with the complete six-scenario table.
mainAggregatePath=fullfile(projectRoot,'outputs','simulation','aggregate_changes.csv');
if isfile(mainAggregatePath)
    mainAggregate=readtable(mainAggregatePath,'TextType','string');
    if ismember('Specification',mainAggregate.Properties.VariableNames)
        mainAggregate=mainAggregate(mainAggregate.Specification=="with_spillovers",:);
        mainAggregate.Specification=[];
    end
    mainAggregate.Specification=repmat("with_spillovers",height(mainAggregate),1);
    mainAggregate=movevars(mainAggregate,'Specification','Before',1);
    zeroAggregate=aggregateChanges;
    zeroAggregate.Specification=repmat("no_spillovers",height(zeroAggregate),1);
    zeroAggregate=movevars(zeroAggregate,'Specification','Before',1);
    aggregateChangesAll=vertcat(mainAggregate,zeroAggregate);
    writetable(aggregateChangesAll,mainAggregatePath);
    writetable(aggregateChangesAll,fullfile(projectRoot,'outputs','simulation',...
        'aggregate_changes_spillover_comparison.csv'));
end
