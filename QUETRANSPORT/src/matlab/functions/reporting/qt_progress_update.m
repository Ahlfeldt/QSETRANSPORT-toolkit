
function qt_progress_update(label,iteration,maximumIteration,objective,completed,failed)
%QT_PROGRESS_UPDATE Print fixed-point iteration and objective information.
% The number of iterations required is unknown, so this function deliberately
% does not report a percentage or draw a progress bar. maximumIteration is only
% a safety limit and appears only when that limit is reached.

global progressPrintEvery;
if isempty(progressPrintEvery) || progressPrintEvery < 1
    progressPrintEvery = 25;
end
if nargin < 5; completed = false; end
if nargin < 6; failed = false; end
if ~completed && ~failed && iteration ~= 1 && mod(iteration,progressPrintEvery) ~= 0
    return;
end

if contains(lower(label),'inversion')
    objectiveName = 'maximum employment gap (workers)';
else
    objectiveName = 'maximum log target gap';
end

if completed
    fprintf('[%s] converged after %d iteration(s); %s=%.4g\n',...
        label,iteration,objectiveName,objective);
elseif failed
    fprintf('[%s] stopped at iteration limit %d; %s=%.4g\n',...
        label,maximumIteration,objectiveName,objective);
else
    fprintf('[%s] iteration %d; %s=%.4g\n',...
        label,iteration,objectiveName,objective);
end
drawnow;
end
