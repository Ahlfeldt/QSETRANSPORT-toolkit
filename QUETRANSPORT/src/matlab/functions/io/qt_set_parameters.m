function param = qt_set_parameters(config)
%QT_SET_PARAMETERS Expose configured ARSW parameters to the legacy-style functions.
global alpha beta kappa epsilon lambda delta rho eta eps constructionLandShare progressPrintEvery;
alpha = config.model.production_share_labor;
beta = config.model.expenditure_share_consumption;
epsilon = config.model.commuting_elasticity;
kappa = config.model.commuting_time_coefficient;
lambda = config.model.productivity_spillover;
delta = config.model.productivity_spatial_decay;
eta = config.model.amenity_spillover;
rho = config.model.amenity_spatial_decay;
constructionLandShare = config.model.construction_land_share;
progressPrintEvery = config.numerics.print_every;
eps = config.numerics.tolerance_equilibrium;
param = [kappa epsilon lambda delta eta rho];
assert(alpha>0 && alpha<1,'production_share_labor must lie between zero and one.');
assert(beta>0 && beta<1,'expenditure_share_consumption must lie between zero and one.');
assert(abs(config.model.construction_capital_share+constructionLandShare-1)<1e-10,...
    'Construction capital and land shares must sum to one.');
end
