function comparison = compare_nsw_phase_a(matlabReport, pythonReportUrl, outputPath)
%COMPARE_NSW_PHASE_A Compare MATLAB observations with the Python golden JSON.
if nargin < 3
    outputPath = 'nsw_phase_a_comparison.json';
end
pythonReport = webread(pythonReportUrl, weboptions('ContentType', 'json'));
names = fieldnames(matlabReport.observations);
metrics = {'nse_v1', 'nscen_v1', 'nsw_v1', 'parseval_error'};
maximumDifference = 0.0;
comparedValues = 0;
for nameIndex = 1:numel(names)
    name = names{nameIndex};
    matlabValues = matlabReport.observations.(name);
    pythonValues = pythonReport.observations.(name);
    if numel(matlabValues) ~= numel(pythonValues)
        error('NSW:ComparisonShape', 'Observation array sizes differ for %s.', name);
    end
    for itemIndex = 1:numel(matlabValues)
        for metricIndex = 1:numel(metrics)
            metric = metrics{metricIndex};
            left = matlabValues(itemIndex).(metric);
            right = pythonValues(itemIndex).(metric);
            if isempty(right) || (isnumeric(right) && isnan(right))
                if ~isnan(left)
                    error('NSW:ComparisonUndefined', 'Undefined mismatch for %s/%s.', name, metric);
                end
                continue;
            end
            difference = abs(double(left) - double(right));
            maximumDifference = max(maximumDifference, difference);
            comparedValues = comparedValues + 1;
        end
    end
end
tolerance = 1e-11;
comparison = struct('status', string(ternary(maximumDifference <= tolerance, 'PASS', 'FAIL')), ...
    'tolerance', tolerance, 'maximum_absolute_difference', maximumDifference, ...
    'compared_values', comparedValues, 'matlab_implementation', matlabReport.implementation, ...
    'python_report_sha256', pythonReport.report_sha256);
payload = jsonencode(comparison, PrettyPrint=true);
fileId = fopen(outputPath, 'w');
if fileId < 0
    error('NSW:ComparisonOutput', 'Cannot open comparison output file.');
end
cleanup = onCleanup(@() fclose(fileId));
fprintf(fileId, '%s\n', payload);
fprintf('NSW_CROSS_LANGUAGE_STATUS=%s MAX_ABS_DIFF=%.17g\n', ...
    comparison.status, comparison.maximum_absolute_difference);
if comparison.status ~= "PASS"
    error('NSW:ComparisonFailure', 'Cross-language tolerance exceeded.');
end
end

function value = ternary(condition, whenTrue, whenFalse)
if condition
    value = whenTrue;
else
    value = whenFalse;
end
end

