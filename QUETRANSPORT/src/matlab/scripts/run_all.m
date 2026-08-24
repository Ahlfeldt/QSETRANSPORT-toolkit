%% QUETRANSPORT: RUN THE COMPLETE MATLAB WORKFLOW
% This convenience script runs the two transparent teaching scripts in order.
% The paths are recomputed on each line because each teaching script clears
% its own workspace when it starts.
run(fullfile(fileparts(mfilename('fullpath')),'invert_baseline.m'));
run(fullfile(fileparts(mfilename('fullpath')),'run_counterfactual.m'));
