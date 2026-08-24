function config = qt_load_config(projectRoot)
%QT_LOAD_CONFIG Read the resolved configuration created by the Python stage.
configFile = fullfile(projectRoot,'input','standardized','runtime_config.json');
assert(isfile(configFile),['Missing runtime_config.json. First run the Python ',...
    'pipeline with the selected project_config.yaml.']);
config = jsondecode(fileread(configFile));
end
