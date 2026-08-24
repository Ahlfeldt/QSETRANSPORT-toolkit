function inversion = qt_invert_baseline(data,travelTime,param,config)
%QT_INVERT_BASELINE Recover ARSW fundamentals conditional on parameters.
% OPTION 1: one observed baseline floor-space rent enters both the commercial
% and residential inversion conditions. It is neither land rent nor a wedge.
% The ARSW solver still determines distinct endogenous commercial (q) and
% residential (Q) bid rents where a location specializes in one land use; in
% mixed-use locations, no-arbitrage imposes q=Q.
observed = [data.rent data.rent ...
    data.employment data.population data.landArea];
Aguess = double(data.employment>0);
Bguess = double(data.population>0);
converged = 0;
Agap = Inf;
Bgap = Inf;
maximumPasses = config.numerics.maximum_inversion_passes;
rng(1,'twister');
for pass = 1:maximumPasses
    fprintf('Inversion pass %d of %d.\n',pass,maximumPasses);
    [A,B,wage,commutingProbability,expectedIncome,Hwork,Hres,CMA,ppj,ppi,...
        converged,Agap,Bgap] = cmodexog(observed,travelTime,data.N,Aguess,Bguess);
    fprintf('  workplace gap=%g; residence gap=%g workers.\n',Agap/10000,Bgap/10000);
    if converged==1
        break;
    end
    Aguess=A;
    Bguess=B;
end
assert(converged==1,['Baseline inversion failed after %d passes: ',...
    'workplace gap=%g, residence gap=%g workers.'],pass,Agap/10000,Bgap/10000);
[V,LD,LM,LR,theta] = cdensityE(observed,A,wage,expectedIncome,data.N);
[a,productivitySpillover] = cprod(observed,travelTime,data.N,A);
[b,amenitySpillover] = cres(observed,travelTime,data.N,B);
% Fundamentals columns 5 and 6 are the initial residential and commercial
% bid-rent guesses. Under option 1 both start from the same observed rent.
fund = [a b V data.landArea data.rent data.rent ...
    data.employment data.population wage expectedIncome theta];
reservationUtility = ubar(B,param,fund,travelTime,data.N);
inversion = struct('observed',observed,'A',A,'B',B,'a',a,'b',b,'V',V,...
    'LD',LD,'LM',LM,'LR',LR,'theta',theta,'wage',wage,...
    'expectedIncome',expectedIncome,'CMA',CMA,...
    'productivitySpillover',productivitySpillover,...
    'amenitySpillover',amenitySpillover,'fund',fund,...
    'reservationUtility',reservationUtility,'converged',converged,...
    'Agap',Agap,'Bgap',Bgap,'passes',pass,...
    'commutingProbability',commutingProbability,'Hwork',Hwork,'Hres',Hres,...
    'ppj',ppj,'ppi',ppi);
end
