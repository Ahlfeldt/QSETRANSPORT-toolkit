function result = qt_solve_fixed_distribution(param,fundCounterfactual,...
    travelTimeBaseline,travelTimeCounterfactual,baseline,data,config)
%QT_SOLVE_FIXED_DISTRIBUTION Evaluate transport with baseline locations fixed.
% This is an accounting benchmark, not a market-clearing closure. Baseline OD
% assignments, residence population, workplace employment, floor-space rents,
% and land allocation are held fixed. Counterfactual travel times change direct
% commuting costs and the travel-time-weighted productivity and amenity kernels.
% With fixed inputs, productivity changes pass proportionally into output/wages.

kappa = param(1);
lambda = param(3);
delta = param(4);
eta = param(5);
rho = param(6);
alpha = config.model.production_share_labor;
landShare = config.model.construction_land_share;

E0 = baseline.endog;
E1 = E0;
employment = E0(:,7);
populationByResidence = E0(:,8);
theta = E0(:,3);
landArea = data.landArea;
commutingProbability = baseline.commutingProbability;

% Recompute transport-mediated effective densities at fixed local quantities.
productivityKernel = exp(-delta.*travelTimeCounterfactual);
amenityKernel = exp(-rho.*travelTimeCounterfactual);
productivityEffectiveDensity = productivityKernel*(employment./landArea);
amenityEffectiveDensity = amenityKernel*(populationByResidence./landArea);
productivity = fundCounterfactual(:,1).*(productivityEffectiveDensity.^lambda);
amenity = fundCounterfactual(:,2).*(amenityEffectiveDensity.^eta);

% Hold land allocation fixed. With fixed labour and floor-space inputs, output
% and the competitive wage move with total productivity.
floorSpace = fundCounterfactual(:,3).*(landArea.^landShare);
commercialFloor = theta.*floorSpace;
output = zeros(data.N,1);
wage = zeros(data.N,1);
activeWork = employment>0;
output(activeWork) = productivity(activeWork).*(employment(activeWork).^alpha).*...
    (commercialFloor(activeWork).^(1-alpha));
wage(activeWork) = alpha.*output(activeWork)./employment(activeWork);

% Baseline OD assignments are fixed. Recompute resident labour income only to
% keep the returned accounting objects internally interpretable; residential
% rents remain fixed, so no housing-market-clearing claim is made.
residentIncome = baseline.population.*(commutingProbability*wage);
E1(:,1) = wage;
E1(:,2) = residentIncome;
E1(:,4) = output;
E1(:,10) = productivity;
E1(:,11) = amenity;

% For an unchanged OD pair, the proportional indirect-utility change is the
% amenity change times the wage change times exp(-kappa*change in travel time).
% Baseline floor-space rents cancel because they are held fixed. Taking the
% baseline-flow-weighted log change gives an exact proportional benchmark.
positiveRoutes = commutingProbability>0;
logAmenityChange = zeros(data.N,1);
logWageChange = zeros(data.N,1);
activeResidence = populationByResidence>0;
logAmenityChange(activeResidence) = ...
    log(amenity(activeResidence)./E0(activeResidence,11));
logWageChange(activeWork) = log(wage(activeWork)./E0(activeWork,1));
amenityComponent = sum(sum(commutingProbability.*logAmenityChange));
productivityWageComponent = sum(sum(commutingProbability.*logWageChange'));
commutingComponent = -kappa.*sum(commutingProbability(positiveRoutes).*...
    (travelTimeCounterfactual(positiveRoutes)-travelTimeBaseline(positiveRoutes)));
logWelfareChange = amenityComponent+productivityWageComponent+commutingComponent;

result = struct('closure','fixed_distribution','endog',E1,...
    'fund',fundCounterfactual,'commutingProbability',commutingProbability,...
    'population',baseline.population,...
    'utility',baseline.utility.*exp(logWelfareChange),'converged',1,...
    'convergencePath',[],'isAccountingBenchmark',true,...
    'welfareComponents',struct(...
        'commutingLogChange',commutingComponent,...
        'productivityWageLogChange',productivityWageComponent,...
        'amenityLogChange',amenityComponent,...
        'totalLogChange',logWelfareChange,...
        'commutingPct',100.*(exp(commutingComponent)-1),...
        'productivityWagePct',100.*(exp(productivityWageComponent)-1),...
        'amenityPct',100.*(exp(amenityComponent)-1),...
        'totalPct',100.*(exp(logWelfareChange)-1)));
end
