function projectRoot = qt_project_root()
%QT_PROJECT_ROOT Return the QUETRANSPORT root from this function's location.
thisFile = mfilename('fullpath');
ioFolder = fileparts(thisFile);
functionsFolder = fileparts(ioFolder);
matlabFolder = fileparts(functionsFolder);
srcFolder = fileparts(matlabFolder);
projectRoot = fileparts(srcFolder);
end
