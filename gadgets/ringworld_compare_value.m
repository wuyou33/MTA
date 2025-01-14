% MANUALLY LOAD THE RESULTS FIRST

expectation_list = [ ...
    "error_value_togtd_0", ...
    "error_value_togtd_20", ...
    "error_value_togtd_40", ...
    "error_value_togtd_60", ...
    "error_value_togtd_80", ...
    "error_value_togtd_100", ...
    "error_value_greedy", ...
    "error_value_mta"];
LineColors = [linspecer(numel(expectation_list) - 2); [1, 0, 0]; [0, 0, 1];];
num_points = 201;

CURVES = []; LEGENDS = {};
figure();
MIN = inf;
BANDWIDTH = 0.5;

for result_index = 1: numel(expectation_list)
    result_name  = expectation_list(result_index);
    try
        eval(sprintf('results_mean = %s_mean;', result_name));
        eval(sprintf('results_std = %s_std;', result_name));
    catch ME
        continue;
    end
    X = get_statistics2(results_mean, num_points, true);
    MEAN = results_mean(X);
    MIN = min(min(MEAN), MIN);
    INTERVAL = repmat(MEAN, 2, 1) + BANDWIDTH * [-results_std(X); results_std(X)];
    INTERVAL(INTERVAL <= 0) = eps;
    [CURVE, ~] = band_drawer(X, MEAN, INTERVAL, LineColors(result_index, :)); %X, MEAN, INTERVAL, COLOR
    CURVES = [CURVES, CURVE];
    if strcmp(result_name, "error_value_mta")
        LEGEND = "MTA";
    elseif strcmp(result_name, "error_value_togtd_0")
        LEGEND = "GTD(0)";
    elseif strcmp(result_name, "error_value_togtd_20000")
        LEGEND = "GTD(0.2)";
    elseif strcmp(result_name, "error_value_togtd_40000")
        LEGEND = "GTD(0.4)";
    elseif strcmp(result_name, "error_value_togtd_60000")
        LEGEND = "GTD(0.6)";
    elseif strcmp(result_name, "error_value_togtd_80000")
        LEGEND = "GTD(0.8)";
    elseif strcmp(result_name, "error_value_togtd_100000")
        LEGEND = "GTD(1)";
    elseif strcmp(result_name, "error_value_greedy")
        LEGEND = "greedy";
    end
    LEGENDS = [LEGENDS, LEGEND];
end

L = legend(CURVES, LEGENDS);
set(L, 'FontName', 'Book Antiqua', 'FontSize', 18);
set(L, 'Location', 'southwest');
set(gca, 'xscale', 'log');
set(gca, 'yscale', 'log');
axis([1, inf, MIN, inf]);
set(gca, 'FontSize', 16);
set(gca, 'FontName', 'Book Antiqua');
drawnow;