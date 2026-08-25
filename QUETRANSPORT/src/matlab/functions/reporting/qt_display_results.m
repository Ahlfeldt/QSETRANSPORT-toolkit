function qt_display_results(aggregateChanges,welfareDecomposition)
%QT_DISPLAY_RESULTS Display compact tables without changing CSV headers.

if ismember('Specification',aggregateChanges.Properties.VariableNames)
    % Collapse specification and closure into one readable scenario label so
    % the six-case comparison remains narrow enough for the MATLAB console.
    displayAggregate=aggregateChanges(:,2:end);
    shortSpec=aggregateChanges.Specification;
    shortSpec(shortSpec=="with_spillovers")="spill";
    shortSpec(shortSpec=="no_spillovers")="noSpill";
    shortClosure=aggregateChanges.Closure;
    shortClosure(shortClosure=="fixed_distribution")="fixed";
    displayAggregate.Closure=shortSpec+"_"+shortClosure;
else
    displayAggregate=aggregateChanges;
end
displayAggregate.Properties.VariableNames={...
    'Scenario','UtilityPct','PopPct','GDPPct','RentPct',...
    'TimeBasePct','TimePostPct','TotalMinPct'};

fprintf(['\nAll aggregate entries are percentage changes. TimeBase uses baseline ',...
    'commuting flows; TimePost uses scenario commuting flows; TotalMin ',...
    'also includes the change in commuter population.\n']);
disp(displayAggregate);

if nargin>=2 && ~isempty(welfareDecomposition)
    displayDecomposition=welfareDecomposition;
    displayDecomposition.Properties.VariableNames={...
        'Component','LogChange','EquivPct'};
    fprintf('Fixed-distribution welfare decomposition:\n');
    disp(displayDecomposition);
end
end
