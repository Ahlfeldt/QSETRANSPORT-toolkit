%% QUETRANSPORT: RUN THE COMPLETE MATLAB WORKFLOW
% This convenience script runs the main specification and optional sensitivity.
% The paths are recomputed on each line because each teaching script clears
% its own workspace when it starts.
run(fullfile(fileparts(mfilename('fullpath')),'invert_baseline.m'));
run(fullfile(fileparts(mfilename('fullpath')),'run_counterfactual.m'));
scriptDir=fileparts(mfilename('fullpath'));
projectRoot=fileparts(fileparts(fileparts(scriptDir)));
addpath(genpath(fullfile(projectRoot,'src','matlab','functions')));
config=qt_load_config(projectRoot);
if isfield(config.project,'run_no_spillover_comparison') && ...
        config.project.run_no_spillover_comparison
    run(fullfile(scriptDir,'run_no_spillovers.m'));
    qt_display_results(aggregateChangesAll);
else
    qt_display_results(aggregateChanges);
end
