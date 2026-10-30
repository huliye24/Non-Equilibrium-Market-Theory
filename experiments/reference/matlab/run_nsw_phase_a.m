function report = run_nsw_phase_a(outputPath)
%RUN_NSW_PHASE_A Independent MATLAB semantic validation and golden output.
if nargin < 1
    outputPath = 'nsw_phase_a_matlab.json';
end
sizeValue = 128;
sineWave = @(frequency, amplitude) amplitude * sin(2*pi*frequency*(0:sizeValue-1)');
chirpWave = @(first, last) sin(2*pi*(first*(0:sizeValue-1)' + ...
    0.5*((last-first)/(sizeValue-1))*(0:sizeValue-1)'.^2));

base = nsw_observation(sineWave(4/64, 1));
half = nsw_observation(sineWave(4/64, 0.5));
doubleValue = nsw_observation(sineWave(4/64, 2));
low = nsw_observation(sineWave(4/64, 1));
high = nsw_observation(sineWave(16/64, 1));
separations = [2, 6, 12];
dual = repmat(base, 1, numel(separations));
for index = 1:numel(separations)
    left = (16 - separations(index)/2) / 64;
    right = (16 + separations(index)/2) / 64;
    dual(index) = nsw_observation(sineWave(left, 1) + sineWave(right, 1));
end
state = 20261030;
fixedNoise = zeros(sizeValue, 1);
for index = 1:sizeValue
    state = mod(1664525 * state + 1013904223, 2^32);
    fixedNoise(index) = state / 2^32 - 0.5;
end
white = nsw_observation(fixedNoise);
ends = [0.10, 0.22, 0.38];
chirps = repmat(base, 1, numel(ends));
for index = 1:numel(ends)
    chirps(index) = nsw_observation(chirpWave(0.04, ends(index)));
end
zeroValue = nsw_observation(zeros(sizeValue, 1));
constant = nsw_observation(0.002 * ones(sizeValue, 1));
sample = (0:sizeValue-1)';
modulatedValues = (1 + 0.6*sin(2*pi*sample/sizeValue)) .* sineWave(8/64, 1);
mod1 = nsw_observation(modulatedValues);
mod3 = nsw_observation(3 * modulatedValues);

closeEnough = @(left, right, tolerance) abs(left-right) <= tolerance;
checks = struct();
checks.amplitude_energy_square_law = closeEnough(half.nse_v1*16, doubleValue.nse_v1, 1e-12);
checks.amplitude_centroid_invariant = closeEnough(half.nscen_v1, doubleValue.nscen_v1, 1e-12);
checks.amplitude_bandwidth_invariant = closeEnough(half.nsw_v1, doubleValue.nsw_v1, 1e-12);
checks.frequency_shift_moves_centroid = high.nscen_v1 > low.nscen_v1 + 0.25;
checks.frequency_shift_preserves_narrow_bandwidth = abs(high.nsw_v1-low.nsw_v1) < 0.015;
checks.dual_frequency_separation_widens = dual(1).nsw_v1 < dual(2).nsw_v1 && dual(2).nsw_v1 < dual(3).nsw_v1;
checks.white_noise_wider_than_single_tone = white.nsw_v1 > base.nsw_v1 + 0.15;
checks.chirp_span_widens_monotonically = chirps(1).nsw_v1 < chirps(2).nsw_v1 && chirps(2).nsw_v1 < chirps(3).nsw_v1;
checks.zero_energy_is_undefined = isnan(zeroValue.nscen_v1) && isnan(zeroValue.nsw_v1);
checks.constant_return_is_undefined = isnan(constant.nscen_v1) && isnan(constant.nsw_v1);
checks.modulated_global_scale_energy_square_law = closeEnough(mod1.nse_v1*9, mod3.nse_v1, 1e-12);
checks.modulated_global_scale_bandwidth_invariant = closeEnough(mod1.nsw_v1, mod3.nsw_v1, 1e-12);

observations = struct('single_tone', base, 'half_amplitude', half, ...
    'double_amplitude', doubleValue, 'low_frequency', low, ...
    'high_frequency', high, 'dual_frequency', dual, ...
    'white_noise_seed_20261030', white, 'chirp', chirps, 'zero', zeroValue, ...
    'constant', constant, 'modulated', mod1, 'modulated_scaled_3x', mod3);
allObservations = [base, half, doubleValue, low, high, dual, white, chirps, ...
    zeroValue, constant, mod1, mod3];
maxParseval = max([allObservations.parseval_error]);
checks.parseval_error_within_tolerance = maxParseval <= 1e-14;
checkValues = struct2cell(checks);
passed = all(cellfun(@(value) logical(value), checkValues));
report = struct('experiment', 'NSW-V1-PHASE-A-DETERMINISTIC', ...
    'status', string(ternary(passed, 'PASS', 'FAIL')), ...
    'implementation', ['matlab-' version('-release')], ...
    'config', struct('window', 128, 'segment_length', 64, 'overlap', 32, ...
        'nfft', 64, 'window_function', 'periodic_hann', 'dc_removed', true), ...
    'checks', checks, 'observations', observations, ...
    'max_parseval_error', maxParseval, 'execution_mode', 'RESEARCH_ONLY', ...
    'live_enabled', false);
payload = jsonencode(report, PrettyPrint=true);
fileId = fopen(outputPath, 'w');
if fileId < 0
    error('NSW:Output', 'Cannot open output file.');
end
cleanup = onCleanup(@() fclose(fileId));
fprintf(fileId, '%s\n', payload);
fprintf('NSW_PHASE_A_STATUS=%s\n', report.status);
if ~passed
    error('NSW:SemanticFailure', 'One or more frozen semantic checks failed.');
end
end

function value = ternary(condition, whenTrue, whenFalse)
if condition
    value = whenTrue;
else
    value = whenFalse;
end
end

