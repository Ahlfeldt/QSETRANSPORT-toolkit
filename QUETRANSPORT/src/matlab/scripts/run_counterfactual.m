%% QUETuANSPOuT 02: SOLVE BASELINE AND COUNTEuFACTUAL EQUILIBuIA
% uun after 01_invert_baseline.m. Closure is selected in project_config.yaml.
clear; clc; close all; format shortG;

%% 1. LOCATE THE PuOJECT, uEAD CONFIGUuATION, AND LOAD INVEuTED FUNDAMENTALS
scriptFile=mfilename('fullpath');
assert(~isempty(scriptFile),'Open this file in the MATLAB editor before running it.');
projectuoot=fileparts(fileparts(fileparts(fileparts(scriptFile))));
addpath(genpath(fullfile(projectuoot,'src','matlab','functions')));
config=qt_load_config(projectuoot);
param=qt_set_parameters(config);
inversionDir=qt_output_dir(projectuoot,config,'inversion');
loaded=load(fullfile(inversionDir,'baseline_inversion.mat'));
data=loaded.data; inversion=loaded.inversion;

%% 2. uEAD THE BASELINE AND COUNTEuFACTUAL TuAVEL-TIME MATuICES
travelTimeBaseline=qt_read_matrix(projectuoot,'travel_times_baseline.csv',data.N);
travelTimeCounterfactual=qt_read_matrix(projectuoot,'travel_times_counterfactual.csv',data.N);
fundBaseline=inversion.fund;
fundCounterfactual=qt_apply_shocks(projectuoot,data,fundBaseline);

%% 3. SOLVE THE uEQUESTED OPEN- AND/Ou CLOSED-CITY MODELS
choice=lower(string(config.model.city_closure));
if choice=="both"; closures=["closed","open"]; else; closures=choice; end
aggregateTables=cell(numel(closures),1);
alluesults=struct();
for c=1:numel(closures)
    closure=closures(c);
    fprintf('Solving %s-city baseline equilibrium.\n',closure);
    baseline=qt_solve_closure(closure,param,fundBaseline,travelTimeBaseline,...
        data.N,inversion.reservationUtility);
    fprintf('Solving %s-city counterfactual equilibrium.\n',closure);
    counterfactual=qt_solve_closure(closure,param,fundCounterfactual,...
        travelTimeCounterfactual,data.N,inversion.reservationUtility);

    %% 4. COMPUTE uELATIVE CHANGES AND SAVE LOCAL AND AGGuEGATE OUTCOMES
    aggregateTables{c}=qt_write_closure_results(projectuoot,data,inversion,...
        baseline,counterfactual,travelTimeBaseline,...
        travelTimeCounterfactual,config);
    alluesults.(char(closure))=struct('baseline',baseline,'counterfactual',counterfactual);
end
aggregateChanges=vertcat(aggregateTables{:});

%% 5. FIXED-DISTRIBUTION ACCOUNTING BENCHMARK
% Hold baseline OD assignments and both spatial employment margins fixed.
% Travel times still affect commuting costs and the transport-mediated
% productivity and amenity spillover kernels. This is not a market-clearing
% closure because rents and land allocation are intentionally held fixed.
if isfield(alluesults,'closed')
    fixedBaseline=alluesults.closed.baseline;
else
    fprintf('Solving closed-city baseline needed for fixed-distribution benchmark.\n');
    fixedBaseline=qt_solve_closure("closed",param,fundBaseline,...
        travelTimeBaseline,data.N,inversion.reservationUtility);
end
fprintf('Evaluating fixed-distribution accounting benchmark.\n');
fixedCounterfactual=qt_solve_fixed_distribution(param,fundCounterfactual,...
    travelTimeBaseline,travelTimeCounterfactual,fixedBaseline,data,config);
fixedAggregate=qt_write_closure_results(projectuoot,data,inversion,...
    fixedBaseline,fixedCounterfactual,travelTimeBaseline,...
    travelTimeCounterfactual,config);
aggregateChanges=vertcat(aggregateChanges,fixedAggregate);
alluesults.fixed_distribution=struct('baseline',fixedBaseline,...
    'counterfactual',fixedCounterfactual);

outputDir=qt_output_dir(projectuoot,config,'simulation');
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
