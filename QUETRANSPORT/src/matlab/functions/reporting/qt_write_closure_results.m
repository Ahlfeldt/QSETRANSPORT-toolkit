
function aggregate = qt_write_closure_results(projectRoot,data,inversion,baseline,...
    counterfactual,travelTimeBaseline,travelTimeCounterfactual,config)
%QT_WRITE_CLOSURE_RESULTS Save named local and aggregate equilibrium effects.
% Residential and commercial rents are prices per unit of FLOOR SPACE.
% Annual land rent is separately derived as the land share of floor revenue.
% Total travel time is the expected one-way commuting time multiplied by the
% modeled commuter population. It therefore captures route-choice changes and,
% in the open city, the change in the number of commuters.

closure = string(counterfactual.closure);
pct = qt_percent_change(counterfactual.endog,baseline.endog);
E0 = baseline.endog;
E1 = counterfactual.endog;

landShare = config.model.construction_land_share;

% The floor-supply primitive is column 3 of each scenario's fundamentals.
% Using scenario-specific values also handles an optional density shock.
floorSpace0 = baseline.fund(:,3).*(data.landArea.^landShare);
floorSpace1 = counterfactual.fund(:,3).*(data.landArea.^landShare);

% Solver column 3 is the commercial floor-space share; columns 5 and 6 are
% residential and commercial FLOOR-SPACE rents, respectively.
commercialFloor0 = E0(:,3).*floorSpace0;
residentialFloor0 = (1-E0(:,3)).*floorSpace0;
commercialFloor1 = E1(:,3).*floorSpace1;
residentialFloor1 = (1-E1(:,3)).*floorSpace1;

% Gross revenue paid by the two users of floor space.
floorRevenue0 = E0(:,6).*commercialFloor0 + E0(:,5).*residentialFloor0;
floorRevenue1 = E1(:,6).*commercialFloor1 + E1(:,5).*residentialFloor1;

% Annual land rent is the developer residual: the LAND SHARE of floor revenue.
% It is neither residential nor commercial floor-space rent and is not a
% capitalized land asset value.
landRent0 = landShare.*floorRevenue0;
landRent1 = landShare.*floorRevenue1;
landRentPct = qt_percent_change(landRent1,landRent0);

% The solvers return an N-by-N matrix of unconditional residence-workplace
% probabilities that sums to one. Weight every OD travel time by its equilibrium
% commuting probability, then multiply by modeled population to obtain total
% one-way commuter-minutes. Using dot avoids forming another large N-by-N array.
expectedTravelTime0 = dot(baseline.commutingProbability(:),travelTimeBaseline(:));
expectedTravelTime1 = dot(counterfactual.commutingProbability(:),travelTimeCounterfactual(:));
totalTravelTime0 = baseline.population.*expectedTravelTime0;
totalTravelTime1 = counterfactual.population.*expectedTravelTime1;
totalTravelTimePct = 100.*(totalTravelTime1./totalTravelTime0-1);
baselineFlowCounterfactualMeanTime = ...
    dot(baseline.commutingProbability(:),travelTimeCounterfactual(:));
meanCommuteTimePctBaselineFlows = ...
    100.*(baselineFlowCounterfactualMeanTime./expectedTravelTime0-1);
meanCommuteTimePctCounterfactualFlows = ...
    100.*(expectedTravelTime1./expectedTravelTime0-1);

% Save local land rent explicitly so the aggregate incidence calculation is
% transparent and can be reconstructed by summing the local level columns.
T = table(data.id,E0(:,7),E1(:,7),pct(:,7),E0(:,8),E1(:,8),pct(:,8),...
    E0(:,1),E1(:,1),pct(:,1),E0(:,5),E1(:,5),pct(:,5),...
    E0(:,6),E1(:,6),pct(:,6),E0(:,4),E1(:,4),pct(:,4),...
    landRent0,landRent1,landRentPct,...
    'VariableNames',{'location_id','employment_baseline','employment_counterfactual',...
    'employment_pct','population_baseline','population_counterfactual','population_pct',...
    'wage_baseline','wage_counterfactual','wage_pct',...
    'rent_residential_baseline','rent_residential_counterfactual','rent_residential_pct',...
    'rent_commercial_baseline','rent_commercial_counterfactual','rent_commercial_pct',...
    'output_baseline','output_counterfactual','output_pct',...
    'annual_land_rent_baseline','annual_land_rent_counterfactual','annual_land_rent_pct'});
outputDir = qt_output_dir(projectRoot,config,'simulation');
if ~isfolder(outputDir); mkdir(outputDir); end
writetable(T,fullfile(outputDir,sprintf('block_outcomes_%s_city.csv',closure)));

aggregate = table(closure,...
    100*(counterfactual.utility/baseline.utility-1),...
    100*(counterfactual.population/baseline.population-1),...
    100*(sum(E1(:,4),'omitnan')/sum(E0(:,4),'omitnan')-1),...
    100*(sum(landRent1,'omitnan')/sum(landRent0,'omitnan')-1),...
    meanCommuteTimePctBaselineFlows,meanCommuteTimePctCounterfactualFlows,...
    totalTravelTimePct,...
    'VariableNames',{'Closure','ExpectedUtilityPct','PopulationPct','GDPPct',...
    'TotalLandRentPct','ImmediateCommuteTimeChangePct',...
    'PostRelocationCommuteTimeChangePct','TotalCommuterMinutesChangePct'});
aggregate.ExpectedUtilityPct(abs(aggregate.ExpectedUtilityPct)<1e-10)=0;
aggregate.PopulationPct(abs(aggregate.PopulationPct)<1e-10)=0;
aggregate.TotalCommuterMinutesChangePct(...
    abs(aggregate.TotalCommuterMinutesChangePct)<1e-10)=0;
aggregate.ImmediateCommuteTimeChangePct(...
    abs(aggregate.ImmediateCommuteTimeChangePct)<1e-10)=0;
aggregate.PostRelocationCommuteTimeChangePct(...
    abs(aggregate.PostRelocationCommuteTimeChangePct)<1e-10)=0;
end
