function data = qt_read_inputs(projectRoot)
%QT_READ_INPUTS Read standardized location data exported by Python.
locationFile = fullfile(projectRoot,'input','standardized','model','locations.csv');
assert(isfile(locationFile),'Missing standardized locations.csv: %s',locationFile);
T = readtable(locationFile,'TextType','string','VariableNamingRule','preserve');
required = {'location_id','population','employment_model','rent_floor_space','land_area'};
assert(all(ismember(required,T.Properties.VariableNames)),...
    'locations.csv does not satisfy the QUETRANSPORT data contract.');
data.table = T;
data.id = string(T.location_id);
data.population = double(T.population);
data.employment = double(T.employment_model);
% Option 1 has one observed baseline floor-space rent. It is used in both
% land-use demand equations during inversion and is not a land rent or wedge.
data.rent = double(T.rent_floor_space);
data.landArea = double(T.land_area);
assert(all(isfinite(data.rent) & data.rent>0),...
    'Observed floor-space rents must be finite and strictly positive.');
data.N = height(T);
assert(numel(unique(data.id))==data.N,'Location identifiers are not unique.');
assert(abs(sum(data.population)-sum(data.employment))<1e-6*sum(data.population),...
    'Aggregate model employment does not equal aggregate population.');
end
