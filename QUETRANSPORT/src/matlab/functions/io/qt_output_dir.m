function outputDir = qt_output_dir(projectRoot,config,stage)
%QT_OUTPUT_DIR Resolve the output directory for a model specification.
% The main specification writes to outputs/<stage>. Sensitivity specifications
% may set config.reporting.result_variant without changing inputs or geography.
parts = {projectRoot,'outputs'};
if isfield(config,'reporting') && isfield(config.reporting,'result_variant')
    variant = strtrim(string(config.reporting.result_variant));
    if strlength(variant)>0
        assert(~contains(variant,["/","\"]),...
            'reporting.result_variant must be one folder name.');
        parts{end+1} = char(variant);
    end
end
parts{end+1} = stage;
outputDir = fullfile(parts{:});
end
