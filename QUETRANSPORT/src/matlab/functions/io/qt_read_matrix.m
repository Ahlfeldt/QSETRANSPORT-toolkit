function matrix = qt_read_matrix(projectRoot,fileName,N)
%QT_READ_MATRIX Read a labeled standardized travel-time matrix in minutes.
path = fullfile(projectRoot,'input','standardized','travel_times',fileName);
assert(isfile(path),'Missing standardized travel-time matrix: %s',path);
matrix = readmatrix(path);
if isequal(size(matrix),[N+1 N+1])
    matrix = matrix(2:end,2:end);
elseif isequal(size(matrix),[N N+1])
    matrix = matrix(:,2:end);
elseif isequal(size(matrix),[N+1 N])
    matrix = matrix(2:end,:);
end
assert(isequal(size(matrix),[N N]),'Travel matrix has wrong dimensions.');
assert(all(isfinite(matrix(:))) && all(matrix(:)>=0),...
    'Travel matrix contains negative, missing, or infinite values.');
end
