function result = nsw_observation(returns)
%NSW_OBSERVATION Frozen NSW-v1/NSE-v1/NSCEN-v1 definition.
values = double(returns(:));
segmentLength = 64;
overlap = 32;
nfft = 64;
energyFloor = 1e-24;
if numel(values) < segmentLength || any(~isfinite(values))
    error('NSW:InvalidInput', 'Returns must be finite and at least 64 points.');
end
centered = values - mean(values);
nse = mean(centered .^ 2);
result = struct('nse_v1', nse, 'nscen_v1', NaN, 'nsw_v1', NaN, ...
    'parseval_error', 0.0);
if nse <= energyFloor
    return;
end
n = (0:segmentLength-1)';
window = 0.5 - 0.5 * cos(2 * pi * n / segmentLength);
hop = segmentLength - overlap;
starts = 1:hop:(numel(values) - segmentLength + 1);
positivePower = zeros(nfft / 2, 1);
for startIndex = starts
    segment = centered(startIndex:startIndex + segmentLength - 1) .* window;
    transformed = fft(segment, nfft);
    oneSided = abs(transformed(1:nfft / 2 + 1)) .^ 2;
    oneSided(2:end-1) = 2 * oneSided(2:end-1);
    positivePower = positivePower + oneSided(2:end);
end
positivePower = positivePower / numel(starts);
rawTotal = sum(positivePower);
if rawTotal <= energyFloor
    result.parseval_error = nse;
    return;
end
positivePower = positivePower * (nse / rawTotal);
frequencies = (1:nfft / 2)' / nfft;
probability = positivePower / sum(positivePower);
centroid = sum(probability .* frequencies);
bandwidth = sqrt(sum(probability .* (frequencies - centroid) .^ 2));
result.nscen_v1 = centroid / 0.5;
result.nsw_v1 = bandwidth / 0.5;
result.parseval_error = abs(sum(positivePower) - nse);
end

