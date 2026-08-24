function change = qt_percent_change(counterfactual,baseline)
%QT_PERCENT_CHANGE Compute 100*(counterfactual/baseline-1), retaining NaN at zero bases.
change = nan(size(baseline));
valid = isfinite(baseline) & isfinite(counterfactual) & baseline~=0;
change(valid)=100.*(counterfactual(valid)./baseline(valid)-1);
end
