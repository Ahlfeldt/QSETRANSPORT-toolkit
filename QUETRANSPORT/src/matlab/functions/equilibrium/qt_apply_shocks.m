function fundCounterfactual = qt_apply_shocks(projectRoot,data,fund)
%QT_APPLY_SHOCKS Apply optional multiplicative changes in local primitives.
% A hat of 1 leaves the inverted primitive unchanged; 1.10 raises it by 10%.
% Python has already validated and ordered the standardized file. MATLAB
% repeats the essential checks so a manually edited file cannot be misapplied.
shockFile = fullfile(projectRoot,'input','standardized','shocks','shocks.csv');
fundCounterfactual = fund;
if ~isfile(shockFile)
    fprintf(['No primitive-shock file: fundamental productivity, amenity, ',...
        'and structural density remain at baseline values.\n']);
    return;
end
S = readtable(shockFile,'TextType','string','VariableNamingRule','preserve');
required = {'location_id','productivity_hat','amenity_hat','structural_density_hat'};
assert(all(ismember(required,S.Properties.VariableNames)),...
    'Standardized shocks.csv does not satisfy the primitive-shock contract.');
assert(height(S)==data.N,'shocks.csv must contain exactly one row per model location.');
assert(all(string(S.location_id)==data.id),...
    'shocks.csv location_id values must match locations.csv in exactly the same order.');

% fund columns 1--3 contain the three exogenous local fundamentals held fixed
% in a pure transport counterfactual: a_i, b_i, and structural density phi_i.
definitions = {'productivity_hat',1;'amenity_hat',2;'structural_density_hat',3};
for k=1:size(definitions,1)
    name=definitions{k,1}; column=definitions{k,2};
    hat=double(S.(name));
    assert(all(isfinite(hat) & hat>0),'%s must be finite and positive.',name);
    fundCounterfactual(:,column)=fundCounterfactual(:,column).*hat;
end
fprintf('Applied optional primitive changes from %s.\n',shockFile);
end