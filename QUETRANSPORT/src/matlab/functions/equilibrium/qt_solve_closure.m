function result = qt_solve_closure(closure,param,fund,travelTime,N,reservationUtility)
%QT_SOLVE_CLOSURE Solve one ARSW equilibrium under the requested city closure.
switch lower(string(closure))
    case "closed"
        [endog,commutingProbability,population,converged,utility] = ...
            smodendog(param,fund,travelTime,N);
        path = [];
    case "open"
        [endog,commutingProbability,population,utility,converged,path] = ...
            ussmodendog(param,fund,travelTime,N,reservationUtility);
    otherwise
        error('Closure must be closed or open.');
end
assert(converged==1,'%s-city equilibrium did not converge.',closure);
result = struct('closure',char(closure),'endog',endog,'fund',fund,...
    'commutingProbability',commutingProbability,'population',population,...
    'utility',utility,'converged',converged,'convergencePath',path);
end
