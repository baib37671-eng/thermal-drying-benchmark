function figs_matlab(sel)
% 用法：figs_matlab            → 出全部
%       figs_matlab('field')   → 只出指定图
% 图名：field=问题2 含水率时空场
%       shrink=图12 问题4 收缩域时空场（极坐标分档扇面 + 收缩包络 + 径向剖面）
%       shrinklaw=图16 收缩本构反演与失水下界（三维幕布 + 滞后份额）
HERE = fileparts(mfilename('fullpath'));
ROOT = fileparts(HERE);
FD  = fullfile(ROOT, 'data', 'processed', 'figdata');
OUT = fullfile(ROOT, 'results', 'figures');
ALL = {'envradius', 'field', 'shrink', 'shrinklaw', 'spacefall', 'ringsec', 'coresec'};
if nargin < 1 || isempty(sel)
    sel = ALL;
elseif ischar(sel)
    sel = {sel};
end
for k = 1:numel(sel)
    switch sel{k}
        case 'envradius', fig_envradius(FD, OUT);
        case 'field',  fig_field(FD, OUT);
        case 'shrink', fig_shrink(FD, OUT);
        % 'ablate' 已停用：图13 改由 R 侧 figs_r.R 的 ablpolar 出图，同一路径只保留一个写入者
        % case 'ablate', fig_ablate(FD, OUT);
        case 'shrinklaw', fig_shrinklaw(FD, OUT);
        case 'spacefall', fig_spacefall(FD, OUT);
        case 'ringsec',  fig_ringsec(FD, OUT);
        case 'coresec',  fig_coresec(FD, OUT);
        otherwise, warning('未知图名 %s', sel{k});
    end
end
end

% ---------------- 公用 ----------------
% 含水率 C 的顺序色阶锚点（全篇同量同色：图6/图12/图13 三张 C 场共用，R 侧 WARM() 同锚点）
% 路径 浅黄 -> 粉浅 -> 粉 -> 淡紫 -> 深紫，锚点全部取自图14 五色淡彩板。
% 首档一律不得取近白 #FDFBE9：C 场最低档占图面四成，落在纯白底上等于不画（色阶底部糊白）。
% 亮度逐档严格递减（237->210->179->168->118）⇒ 仍是合法顺序色阶，不产生假边界。
function A = warm_anchors()
A = [0.980 0.941 0.651;      % 浅黄 #FAF0A6
     1.000 0.780 0.714;      % 粉的浅档 #FFC7B6
     1.000 0.624 0.608;      % 粉   #FF9F9B
     0.702 0.624 0.859;      % 淡紫 #B39FDB
     0.490 0.435 0.659];     % 深紫 #7D6FA8
end

% 沿锚点路径等距取 n 色（亮度单调递减 ⇒ 无假边界，可安全承载顺序量）
function c = ramp_from(A, n)
q = linspace(0, 1, n).';  x = linspace(0, 1, size(A, 1));
c = [interp1(x, A(:, 1), q), interp1(x, A(:, 2), q), interp1(x, A(:, 3), q)];
end

function c = seq_cmap()
c = ramp_from(warm_anchors(), 220);
end

% 轴样式：fs 为字号（pt）。图面宽度定死后，印刷字号 = fs × (落版宽/画布宽)，
% 故需要"字大一点"的图直接给它更大的 fs（画布宽可同时收窄，两者叠加才是印刷增益）。
function style_ax(ax, fs)
if nargin < 2 || isempty(fs), fs = 7; end
set(ax, 'FontName', 'Microsoft YaHei', 'FontSize', fs, 'LineWidth', 0.4, ...
    'TickDir', 'in', 'TickLength', [0.012 0.012], 'XColor', [0.29 0.29 0.29], ...
    'YColor', [0.29 0.29 0.29], 'ZColor', [0.29 0.29 0.29], 'GridLineStyle', 'none');
grid(ax, 'off');
end

function save_png(fh, path)
exportgraphics(fh, path, 'Resolution', 600, 'BackgroundColor', 'white');
d = dir(path);
fprintf('  -> %-28s %7.0f kB\n', d.name, d.bytes / 1024);
close(fh);
end

% 分档色阶：含水率 C 暖阶的 n 档离散色（档数 = 色阶行数，逐档一色不撞色）
function c = band_cmap(n)
c = ramp_from(warm_anchors(), n);
end

% 含水率分档边界与档标（六档，边界压在数据值域 0.05–2.00 上）
function [FBR, FLB, COL] = bands()
FBR = [0.05 0.15 0.35 0.75 1.40 2.00 2.60];
e = char(8211);  FLB = cell(1, 6);
for i = 1:6, FLB{i} = sprintf('%.2f%s%.2f', FBR(i), e, FBR(i + 1)); end
COL = band_cmap(6);
end

% 完整包围盒：8 顶点 12 棱逐条画线（只画线不画面，故不是"背景填色块"）
function boxwire(ax, xl, yl, zl, c)
X = xl([1 2 2 1 1 2 2 1]);  Y = yl([1 1 2 2 1 1 2 2]);  Zb = zl([1 1 1 1 2 2 2 2]);
E = [1 2; 2 3; 3 4; 4 1; 5 6; 6 7; 7 8; 8 5; 1 5; 2 6; 3 7; 4 8];
for i = 1:size(E, 1)
    plot3(ax, X(E(i, :)), Y(E(i, :)), Zb(E(i, :)), '-', 'Color', c, 'LineWidth', 0.42);
end
end

% 干透前沿 r(t)：C 沿 r 单调递减，故 C 首次 <= cc 的那个半径即前沿（线性插值到 cc）
function fr = front_r(Z, ru, cc)
fr = nan(size(Z, 1), 1);
for k = 1:size(Z, 1)
    c = Z(k, :);
    j = find(c <= cc, 1);
    if isempty(j), continue; end
    if j == 1, fr(k) = 0; continue; end
    f = (cc - c(j - 1)) / (c(j) - c(j - 1));
    fr(k) = ru(j - 1) + f * (ru(j) - ru(j - 1));
end
end

% 按给定角度逐条铺扇面；隔两列挖两列留出辐条缝
function surf_fan(ax, thv, ru, Zu, FBR)
nr = numel(ru);  nu = numel(thv);
TH = repmat(thv, nr, 1);  RV = repmat(ru(:), 1, nu);
Zd = Zu.';
blk = mod(1:nu, 4);  Zd(:, blk == 3 | blk == 0) = NaN;
BD = min(max(discretize(Zd, FBR), 1), 6);
BD(isnan(Zd)) = NaN;       % NaN 单元必须留空：max(NaN,1)=1 会把域外与辐条缝刷成最浅档
surf(ax, RV .* cos(TH), RV .* sin(TH), zeros(size(Zd)), BD, ...
    'EdgeColor', 'none', 'FaceColor', 'flat');
end

% ---------------- 图2 环境边界与收缩轨迹核对（相平面分层核密度 + 半径轨迹 + 末段放大） ----------------
% (a) 把 env_att1.csv 的样本按采样时段(0-1/1-2/2-3/3-4 h)分四层，各层在 (T∞, C∞) 相平面上做核密度，
%     逐层抬到同一根 t 轴上叠放成四片"密度地板"（不是四张子图拼贴）；带宽取 Silverman
%     1.06*std*n^(-1/5)，故每片地板的脊宽就是该时段数据自身的散布，层间胖瘦差即是证据。
% (b) 附件2 半径轨迹 + 指数拟合 + 95% 残差带 + 末段 17.3x 放大（源框—锥形引线—inset 六件套）。
% 画布宽 17 cm 落版 0.94\textwidth ≈ 15.98 cm（倍率 0.94），故印刷字号 = 下面 pt 值 x 0.94。
function fig_envradius(FD, OUT)
WARM = [253 251 233; 250 240 166; 255 199 182; 255 159 155; 179 159 219; 125 111 168] / 255;
grnA = [216 243 223; 141 229 161; 79 158 103; 47 107 71] / 255;
AXG = [0.541 0.541 0.541];  PUR = [0.702 0.624 0.859];
FST = 8.0;                                  % 轴刻度/轴标题字号（印刷 ≈ 7.5 pt）
rampW = interp1(linspace(0, 1, 6), WARM, linspace(0, 1, 64));
D  = readmatrix(fullfile(FD, 'env_att1.csv'));
t = D(:, 1) / 3600;  T = D(:, 2);  C = D(:, 3);
T1 = min(T);  T2 = max(T);  C1 = min(C);  C2 = max(C);
W = ones(size(t));  W(t > 1 & t <= 2) = 2;  W(t > 2 & t <= 3) = 3;  W(t > 3) = 4;
NG = 600;  gT = linspace(T1 - 0.6, T2 + 0.6, NG);  gC = linspace(C1 - 0.0008, C2 + 0.0008, NG);
[GT, GC] = meshgrid(gT, gC);
ZC = [0.5 1.5 2.5 3.5];  HZ = 0.62;  THR = 0.18;
fh = figure('Units', 'centimeters', 'Position', [2 2 17 9.2], 'Color', 'w');
ax1 = axes(fh, 'Position', [0.055 0.090 0.370 0.761]);  hold(ax1, 'on');
colormap(ax1, rampW);
for k = 1:4
    sel = W == k;  Ts = T(sel);  Cs = C(sel);  n = numel(Ts);
    hT = 1.06 * std(Ts) * n^(-1/5);  hC = 1.06 * std(Cs) * n^(-1/5);
    fprintf('  层%d: n=%3d  h_T=%.3f C  h_C=%.5f (kg/kg)  %s\n', ...
        k, n, hT, hC, sprintf('T %.2f-%.2f', min(Ts), max(Ts)));
    Zk = zeros(NG);
    for i = 1:n
        Zk = Zk + exp(-0.5 * ((GT - Ts(i)) / hT).^2 - 0.5 * ((GC - Cs(i)) / hC).^2);
    end
    Zk = Zk / max(Zk(:));  Zp = Zk * HZ;  Zp(Zk < THR) = NaN;
    surf(ax1, GT, GC, ZC(k) + Zp, Zk, 'EdgeColor', 'none', 'FaceAlpha', 0.97);
end
xl = [T1 T2];  yl = [C1 C2];  zl = [0 4];
Xc = xl([1 2 2 1 1 2 2 1]);  Yc = yl([1 1 2 2 1 1 2 2]);  Zc = zl([1 1 1 1 2 2 2 2]);
Ew = [1 2; 2 3; 3 4; 4 1; 5 6; 6 7; 7 8; 8 5; 1 5; 2 6; 3 7; 4 8];
for k = 1:size(Ew, 1)
    plot3(ax1, Xc(Ew(k, :)), Yc(Ew(k, :)), Zc(Ew(k, :)), '-', 'Color', AXG, 'LineWidth', 0.4);
end
axis(ax1, [T1 T2 C1 C2 0 4]);  pbaspect(ax1, [1 1 1]);  view(ax1, 40, 16);  grid(ax1, 'off');
caxis(ax1, [0 1]);
set(ax1, 'FontName', 'Microsoft YaHei', 'FontSize', FST, 'LineWidth', 0.4, 'TickDir', 'in', ...
    'XColor', [0.29 0.29 0.29], 'YColor', [0.29 0.29 0.29], 'ZColor', [0.29 0.29 0.29], ...
    'TickLength', [0.010 0.010], 'TickLabelInterpreter', 'none');
xlabel(ax1, 'T_\infty / ^{\circ}C', 'FontName', 'Microsoft YaHei', 'FontSize', FST);
ylabel(ax1, 'C_\infty / (kg/kg)', 'FontName', 'Microsoft YaHei', 'FontSize', FST);
zlabel(ax1, 't / h', 'FontName', 'Microsoft YaHei', 'FontSize', FST);
xticks(ax1, [28 38 48]);  yticks(ax1, [0.02 0.035 0.05]);  zticks(ax1, [0 2 4]);
cb = colorbar(ax1, 'Position', [0.448 0.267 0.011 0.400]);
cb.Ticks = [0 0.5 1];  cb.Label.String = '核密度（归一）';
set(cb, 'FontName', 'Microsoft YaHei', 'FontSize', 7.5, 'Color', [0.29 0.29 0.29]);
cb.Label.FontName = 'Microsoft YaHei';  cb.Label.FontSize = 7.5;  cb.Label.Rotation = 270;
RA = readmatrix(fullfile(FD, 'radius_att2.csv'));
tR = RA(1:145, 1) / 3600;  Rr = RA(1:145, 2);
tf = RA(146:end, 1) / 3600;  Rf = RA(146:end, 3);
a = 1.2013707;  b = 0.7583912;  tau = 4.0132;
res = Rr - (a + b * exp(-tR / tau));  q95 = quantile(abs(res), 0.95);
ax2 = axes(fh, 'Position', [0.600 0.160 0.320 0.780]);  hold(ax2, 'on');
h3 = fill(ax2, [tf; flipud(tf)], [Rf - q95; flipud(Rf + q95)], grnA(2, :), ...
    'EdgeColor', grnA(3, :), 'LineWidth', 0.35);
h2 = plot(ax2, tf, Rf, '-', 'Color', grnA(4, :), 'LineWidth', 0.9);
h1 = plot(ax2, tR, Rr, 'o', 'MarkerSize', 2.0, 'MarkerEdgeColor', grnA(3, :), ...
    'MarkerFaceColor', 'none', 'LineWidth', 0.45);
yA = 1.32;  t50 = 51.0958;
plot(ax2, [tau t50], [yA yA], '-', 'Color', PUR, 'LineWidth', 0.6);
plot(ax2, tau, yA, '<', 'MarkerSize', 3, 'MarkerFaceColor', PUR, 'MarkerEdgeColor', PUR);
plot(ax2, t50, yA, '>', 'MarkerSize', 3, 'MarkerFaceColor', PUR, 'MarkerEdgeColor', PUR);
sx = [14 72];  sy = [1.190 1.245];
plot(ax2, [sx(1) sx(2) sx(2) sx(1) sx(1)], [sy(1) sy(1) sy(2) sy(2) sy(1)], ...
    '-', 'Color', grnA(3, :), 'LineWidth', 0.5);
lg = legend(ax2, [h3 h2 h1], {'95% 残差带', '指数拟合', '附件2 实测'}, ...
    'FontName', 'Microsoft YaHei', 'FontSize', 7, 'Location', 'northwest', 'Box', 'off');
lg.AutoUpdate = 'off';
set(ax2, 'FontName', 'Microsoft YaHei', 'FontSize', FST, 'LineWidth', 0.4, 'TickDir', 'in', ...
    'XColor', [0.29 0.29 0.29], 'YColor', [0.29 0.29 0.29], 'TickLength', [0.010 0.010], ...
    'Box', 'off', 'TickLabelInterpreter', 'none');
xlim(ax2, [0 72]);  ylim(ax2, [1.15 2.10]);
xlabel(ax2, 't / h', 'FontName', 'Microsoft YaHei', 'FontSize', FST);
ylabel(ax2, 'R / cm', 'FontName', 'Microsoft YaHei', 'FontSize', FST);
% inset 顶边必须让开 legend（legend 占数据的右上角一行，约 1.4 cm）；改画布高之后此处须随动
ax3 = axes(fh, 'Position', [0.700 0.370 0.235 0.337]);  hold(ax3, 'on');
fill(ax3, [tf; flipud(tf)], [Rf - q95; flipud(Rf + q95)], grnA(2, :), ...
    'EdgeColor', grnA(3, :), 'LineWidth', 0.35);
plot(ax3, tf, Rf, '-', 'Color', grnA(4, :), 'LineWidth', 0.9);
plot(ax3, tR, Rr, 'o', 'MarkerSize', 1.8, 'MarkerEdgeColor', grnA(3, :), ...
    'MarkerFaceColor', 'none', 'LineWidth', 0.45);
xlim(ax3, sx);  ylim(ax3, sy);
set(ax3, 'FontName', 'Microsoft YaHei', 'FontSize', 7, 'LineWidth', 0.4, 'TickDir', 'in', ...
    'XColor', [0.29 0.29 0.29], 'YColor', [0.29 0.29 0.29], 'TickLength', [0.008 0.008], ...
    'Box', 'on', 'TickLabelInterpreter', 'none', 'XTick', [14 43 72], 'YTick', [1.19 1.21 1.23]);
p2 = get(ax2, 'Position');  p3 = get(ax3, 'Position');
f2x = @(xd) p2(1) + p2(3) * xd / 72;
f2y = @(yd) p2(2) + p2(4) * (yd - 1.15) / 0.95;
annotation(fh, 'line', [f2x(sx(1)) p3(1)], [f2y(sy(2)) p3(2)], 'Color', grnA(3, :), 'LineWidth', 0.5);
annotation(fh, 'line', [f2x(sx(2)) p3(1) + p3(3)], [f2y(sy(2)) p3(2)], 'Color', grnA(3, :), 'LineWidth', 0.5);
save_png(fh, fullfile(OUT, 'fig02_env_radius.png'));
end

% ---------------- 图6 问题2 含水率时空场（3D 曲面 + 俯视分档场） ----------------
% 左：C(r,t) 三维曲面，完整包围盒 + 干透前沿轨迹；右：同一场按 6 档俯视分档 + 前沿曲线
% 色标只留右侧一条（左图 C 已由 z 轴承载，再给色bar 是同一信息的重复编码）
function fig_field(FD, OUT)
M = readmatrix(fullfile(FD, 'q2_profiles.csv'), 'NumHeaderLines', 1);
% 列序：t_s, r_cm, C, T_C
tu = unique(M(:, 1));
ru = unique(M(:, 2));
Z  = reshape(M(:, 3), numel(ru), numel(tu)).';        % [时间 × 半径]
th = tu / 3600;
it = unique(round(linspace(1, numel(tu), 300)));
ir = unique(round(linspace(1, numel(ru), 81)));
Zs = Z(it, ir);  ths = th(it);  rs = ru(ir);

CCR = 0.15;                              % 达标判据 C_cr（与 §5.6 全文一致）
PUR = [0.490 0.435 0.659];               % #7D6FA8：全文"判据"约定色
FBR = [0.05 0.15 0.35 0.75 1.40 2.00 2.60];
FR  = front_r(Z, ru, CCR);  m = ~isnan(FR);
k0  = find(m, 1);
fprintf('  C=%.2f 前沿：首越 t=%.4f h (r=%.4f)；24h r=%.4f；48h r=%.4f；到轴心 %.4f h\n', ...
    CCR, th(k0), FR(k0), interp1(th, FR, 24), interp1(th, FR, 48), th(find(FR <= 1e-9, 1)));

% 本图专用色阶：锚点仍取自图14 五色淡彩板（同量同色），但把最浅端整体上提。
% 原最浅档 #FAF0A6 亮度 236.7，在俯视图上要覆盖五成以上面板，落在白纸上读成空白；
% 六档改按等亮度步长 −20.8 取（222.0 → 118.0），相邻档不再出现"一深一浅"的错落。
KPAL6 = [0.991 0.854 0.685; 1.000 0.737 0.685; 1.000 0.630 0.612; ...
         0.668 0.593 0.826; 0.579 0.514 0.743; 0.490 0.435 0.659];
kseq = ramp_from(warm_anchors(), 220);
kseq = kseq(1 + round(0.1358 * (size(kseq, 1) - 1)) : end, :);   % 连续色阶同取 q≥0.1358 起点

fh = figure('Units', 'centimeters', 'Position', [2 2 16.8 7.6], 'Color', 'w');
tl = tiledlayout(fh, 1, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

ax1 = nexttile(tl);  hold(ax1, 'on');
surf(ax1, rs, ths, Zs, 'EdgeColor', 'none');  shading(ax1, 'interp');
colormap(ax1, kseq);
box(ax1, 'off');
boxwire(ax1, [rs(1) rs(end)], [ths(1) ths(end)], [min(Zs(:)) max(Zs(:))], [0.60 0.64 0.70]);
plot3(ax1, FR(m), th(m), (CCR + 4e-3) * ones(sum(m), 1), '-', 'Color', PUR, 'LineWidth', 1.7);
xlabel(ax1, '半径 r / cm');  ylabel(ax1, '时间 t / h');  zlabel(ax1, 'C / (kg/kg)');
view(ax1, [140 22]);  axis(ax1, 'tight');  style_ax(ax1, 12);

ax2 = nexttile(tl);  hold(ax2, 'on');
[RR, TT] = meshgrid(rs, ths);
surf(ax2, RR, TT, zeros(size(Zs)), discretize(Zs, FBR), ...
    'EdgeColor', 'none', 'FaceColor', 'flat');
view(ax2, 2);  colormap(ax2, KPAL6);  clim(ax2, [1 6]);
plot(ax2, FR(m), th(m), '-', 'Color', PUR, 'LineWidth', 1.7);
xlim(ax2, [0 2]);  ylim(ax2, [0 ths(end)]);
xticks(ax2, 0:0.5:2);  yticks(ax2, 0:12:72);
xlabel(ax2, '半径 r / cm');  ylabel(ax2, '时间 t / h');
style_ax(ax2, 12);  set(ax2, 'Box', 'off');
cb2 = colorbar(ax2);  cb2.Ticks = 1:6;
cb2.TickLabels = {'0.05', '0.15', '0.35', '0.75', '1.40', '2.00'};   % 各档下界（与图12 同口径）
cb2.Label.String = '含水率 C / (kg/kg)';
cb2.FontName = 'Microsoft YaHei';  cb2.FontSize = 11;  cb2.Label.FontSize = 12;  cb2.Box = 'off';
cb2.Color = [0.29 0.29 0.29];  cb2.TickDirection = 'in';

save_png(fh, fullfile(OUT, 'fig06_C_field.png'));
end

% ---------------- 图12 问题4 收缩域含水率时空场（极坐标分档扇面 + 收缩包络 + 径向剖面） ----------------
% (a) 上半个极坐标扇：C(r,t) 时空场按角度铺开，r>R(t) 真留白（不出任何数据）
% (b) 6/24/48 h 径向剖面叠套在同一套真实坐标上，各自止于真实外缘 R(t)
% 与 §5.6.5 图12 的读法声明句一一对应："时空场 + 收缩包络线 + 三个时刻的剖面切片"
function fig_shrink(FD, OUT)
[FBR, ~, COL] = bands();
grn = [0.310 0.620 0.404];                 % 收缩包络 R(t)：与图13"绿=R"约定一致
pur = [0.490 0.435 0.659];                 % 达标判据 C=0.15：与图13"紫=C 判据"约定一致
pgr = [0.720 0.700 0.850];  plg = [0.886 0.879 0.946];
gry = [0.40 0.40 0.46];
R0  = 2.0;

M4  = readmatrix(fullfile(FD, 'q4_profiles_6h.csv'), 'NumHeaderLines', 1);
tu4 = unique(M4(:, 1));  ru4 = unique(M4(:, 2));
Z4  = reshape(M4(:, 3), numel(ru4), numel(tu4)).';     % [时间 × 半径]，NaN = 已收缩掉

% 真实外缘 R(t)：q4_maxC 与表12 的 R(t) 列逐位一致（1.3740/1.2480/1.2140/1.2040/1.2000），
% 而剖面文件只有 0.025 cm 档、末节点落在真实外缘内侧，故"外缘线"一律取此文件
MQ = readmatrix(fullfile(FD, 'q4_maxC.csv'), 'NumHeaderLines', 1);
tq = MQ(:, 1) / 3600;  Rq = MQ(:, 3);

th = tu4(:) / 3600;  t1 = th(1);  TD = th(end);

% 时空场取全时段：ablation_field.csv 的 a4shr 即问题四"收缩域"整段场
% （0.5 h 一步、81 个径向节点、域外已存 NaN），与 q4_profiles_6h.csv 重叠处逐点一致（max 差 1e-4）
% 只用 6 h 起的那份剖面，扇面就只剩 1.374->1.200 cm 这一点点退域，看不出"收缩"本身
AF = readtable(fullfile(FD, 'ablation_field.csv'), 'VariableNamingRule', 'preserve');
AS = AF(strcmp(AF.tag, 'a4shr'), :);
nR = numel(unique(AS.r_cm));
ts = reshape(AS.t_s, nR, []).';            % 帧 x 节点（文件里每帧 81 行连续）
if any(std(ts, 0, 2) ~= 0), error('a4shr 不是按帧连续存储，reshape 不成立'); end
Za = reshape(AS.C, nR, []).';
% ⚠ 文件内一帧的节点是交错的（0,0.15,...,1.95 再 0.075,0.225,...），必须显式按 r 升序重排
[ra, ord] = sort(AS.r_cm(1:nR));
Za = Za(:, ord);
ta = ts(:, 1) / 3600;  t1a = ta(1);  tDa = ta(end);
RtrueA = interp1(tq, Rq, ta, 'linear', 'extrap');   % 末帧 51.0981 h 略超 q4_maxC 的末点，线性外推
for k = 1:size(Za, 1), Za(k, ra > RtrueA(k) + 1e-9) = NaN; end   % 域外留空
aF = (pi - pi * (ta - t1a) / (tDa - t1a)).';    % t1a -> 180°（左），tDa -> 0°（右）；行向量供 surf_fan
fprintf('  时空场 %d 帧 x %d 节点（%.4g -> %.4g h）；R %.4f -> %.4f cm（%d%% 收缩）\n', ...
    size(Za, 1), nR, t1a, tDa, RtrueA(1), RtrueA(end), round(100 * (1 - RtrueA(end) / RtrueA(1))));

fh = figure('Units', 'centimeters', 'Position', [2 2 17.4 8.5], 'Color', 'w');

% ---------------- (a) 上半个极坐标扇：C(r,t) 时空场 ----------------
ax = axes(fh, 'Position', [0.018 0.055 0.415 0.890]);  hold(ax, 'on');

tgc = linspace(0, 2 * pi, 500);
for rr = [0.5 1.0 1.5]                                   % 淡色同心环
    plot(ax, rr * cos(tgc), rr * sin(tgc), '-', 'Color', plg, 'LineWidth', 0.4);
end
plot(ax, R0 * cos(tgc), R0 * sin(tgc), '-', 'Color', pgr, 'LineWidth', 0.6);   % 初始外缘 r=2.0

% 半径轴走正下方：落在扇面之外的空白里，全程不被场遮住
plot(ax, [0 0], [0 -2.02], '-', 'Color', pgr, 'LineWidth', 0.55);
for rr = 0.5:0.5:2.0
    plot(ax, [-0.05 0.05], [-rr -rr], '-', 'Color', pgr, 'LineWidth', 0.45);
    text(ax, -0.12, -rr, sprintf('%.1f', rr), 'HorizontalAlignment', 'right', ...
        'VerticalAlignment', 'middle', 'FontName', 'Microsoft YaHei', ...
        'FontSize', 6.0, 'Color', gry);
end
text(ax, 0.36, -2.02, 'r / cm', 'HorizontalAlignment', 'left', ...
    'VerticalAlignment', 'middle', 'FontName', 'Microsoft YaHei', ...
    'FontSize', 6.6, 'Color', [0.30 0.30 0.36]);

% 时间轴：起点 0.5 h（收缩最快的区间必须标出）与表12 的 6/12/24/36/48 h，右端另标终点
for tt = [0.5 6 12 24 36 48]
    a = pi - pi * (tt - t1a) / (tDa - t1a);
    text(ax, 2.10 * cos(a), 2.10 * sin(a), sprintf('%g', tt), ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
        'FontName', 'Microsoft YaHei', 'FontSize', 5.8, 'Color', gry);
end
text(ax, 2.10, 0, sprintf('%.1f', tDa), 'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', 'FontName', 'Microsoft YaHei', ...
    'FontSize', 5.8, 'Color', gry);
text(ax, -2.10, -0.34, 't / h', 'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', 'FontName', 'Microsoft YaHei', ...
    'FontSize', 6.6, 'Color', [0.30 0.30 0.36]);

surf_fan(ax, aF, ra, Za, FBR);
colormap(ax, COL);  clim(ax, [1 6]);

% 收缩包络 R(t)：取真实外缘（与表12 的 R(t) 列逐位一致）
sel = tq >= t1a - 1e-9 & tq <= tDa + 1e-9;
aQ  = pi - pi * (tq - t1a) / (tDa - t1a);
plot3(ax, Rq(sel) .* cos(aQ(sel)), Rq(sel) .* sin(aQ(sel)), ...
    0.05 * ones(sum(sel), 1), '-', 'Color', grn, 'LineWidth', 1.5);

axis(ax, 'equal');  xlim(ax, [-2.34 2.34]);  ylim(ax, [-2.34 2.34]);
set(ax, 'XColor', 'none', 'YColor', 'none', 'Box', 'off', 'XTick', [], 'YTick', []);

cb = colorbar(ax, 'Position', [0.435 0.300 0.013 0.440]);
cb.Ticks = 1:6;
cb.TickLabels = {'0.05', '0.15', '0.35', '0.75', '1.40', '2.00'};   % 各档下界
cb.Box = 'off';  cb.LineWidth = 0.4;
cb.FontName = 'Microsoft YaHei';  cb.FontSize = 5.6;
cb.Label.String = '含水率 C / (kg/kg)';
cb.Label.FontName = 'Microsoft YaHei';  cb.Label.FontSize = 6.2;
cb.Label.Position = [3.5 0 0];                     % 标签移到色条正下方，避开右图纵轴标题
cb.Label.Rotation = 0;

% ---------------- (b) 6 / 24 / 48 h 径向剖面：同一套真实坐标上叠套 ----------------
% 三条剖面共用一套零点与刻度，故 C 轴每一行都成立（错位堆叠的"行偏移"会让刻度只对最后一行成立）
% 剖面一律止于各自的真实外缘 R(t)（取自 q4_maxC，与表12 的 R(t) 列逐位一致）；r>R(t) 不出任何数据
ax2 = axes(fh, 'Position', [0.560 0.135 0.425 0.820]);  hold(ax2, 'on');
CX  = [0.369 0.518 0.725; 0.780 0.722 0.298; 0.761 0.455 0.447];   % 6/24/48 h：蓝 / 黄 / 粉，取色板深档做线
CF  = [0.631 0.788 0.957; 0.980 0.941 0.651; 1.000 0.624 0.608];   % 同相浅档做面（图14 的"浅面深线"约定）
tt3 = [6 24 48];  AF3 = 0.40 * [1 1 1];  PR = cell(1, 3);
LO  = [0.10 0.06 0.06];        % 各时刻标注相对自身剖面的抬升量（24/48 h 压低、贴近各自剖面）
for j = 1:3
    k = find(abs(th - tt3(j)) < 1e-6, 1);
    c = Z4(k, :);  g = ~isnan(c);  idx = find(g);
    Rt = interp1(tq, Rq, tt3(j));                     % 表12 的真实外缘
    rq = linspace(0, Rt, 400);
    cq = max(interp1(ru4(idx), c(idx), rq, 'linear', 'extrap'), 0);   % 末段线性外推补到真实外缘
    PR{j} = struct('rq', rq, 'cq', cq, 'Rt', Rt);
end
for j = 1:3                                  % 先铺三张填充，再压判据线，最后上面线与切口
    rq = PR{j}.rq;  cq = PR{j}.cq;
    fill(ax2, [rq fliplr(rq)], [cq zeros(1, numel(rq))], CF(j, :), ...
        'EdgeColor', 'none', 'FaceAlpha', AF3(j));
end
plot(ax2, [0 1.62], 0.15 * [1 1], '--', 'Color', pur, 'LineWidth', 0.7);
for j = 1:3
    rq = PR{j}.rq;  cq = PR{j}.cq;  Rt = PR{j}.Rt;  col = CX(j, :);
    plot(ax2, rq, cq, '-', 'Color', col, 'LineWidth', 1.4);
    plot(ax2, Rt * [1 1], [0 cq(end)], '-', 'Color', grn, 'LineWidth', 1.3);  % R(t) 切口：高 = 该处真实 C
    text(ax2, 0.035, cq(1) + LO(j), sprintf('%d h', tt3(j)), 'HorizontalAlignment', 'left', ...
        'VerticalAlignment', 'middle', 'FontName', 'Microsoft YaHei', ...
        'FontSize', 6.0, 'Color', col);
    j15 = find(cq <= 0.15, 1, 'first');
    if isempty(j15)
        fprintf('  %2d h: 整段剖面都高于 0.15，尚未出现 0.15 前沿；止于 R=%.4f cm\n', tt3(j), Rt);
    else
        plot(ax2, rq(j15), 0.15, 'o', 'MarkerSize', 3.2, ...
            'MarkerFaceColor', 'w', 'MarkerEdgeColor', pur, 'LineWidth', 0.7);
        fprintf('  %2d h: 0.15 前沿 r=%.4f cm；止于 R=%.4f cm（表面 C=%.4f）\n', ...
            tt3(j), rq(j15), Rt, cq(end));
    end
end
xlim(ax2, [0 1.62]);  ylim(ax2, [0 2.02]);
set(ax2, 'XTick', 0:0.5:1.5, 'XTickLabel', {'0', '0.5', '1.0', '1.5'}, ...
    'YTick', 0:0.5:2.0, 'YTickLabel', {'0', '0.5', '1.0', '1.5', '2.0'}, ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.0, 'LineWidth', 0.4, ...
    'TickDir', 'in', 'TickLength', [0.012 0.012], ...
    'XColor', [0.29 0.29 0.29], 'YColor', [0.29 0.29 0.29], 'Box', 'off');
grid(ax2, 'off');
xlabel(ax2, 'r / cm');  ylabel(ax2, 'C / (kg/kg)');

save_png(fh, fullfile(OUT, 'fig12_shrink_field.png'));
end

% ---------------- 图13 2×2 反事实消融：几何 × 物性（交互作用图 + 乘法分解） ----------------
function fig_ablate(FD, OUT)
S = jsondecode(fileread(fullfile(FD, 'ablation.json')));
v = [S.a3_fix.td_h, S.a3_shr.td_h; S.a4_fix.td_h, S.a4_shr.td_h];   % 行=物性 · 列=几何
blu = [0.369 0.518 0.725];   % 附录3
red = [0.760 0.455 0.447];   % 附录4
pur = [0.490 0.435 0.659];   % 交互

G = v(1, 2) / v(1, 1);       % 几何主效应（收缩/固定）
P = v(2, 1) / v(1, 1);       % 物性主效应（附录4/附录3）
pred = v(1, 1) * G * P;      % 无交互时的乘法预测
I = v(2, 2) / pred;          % 交互因子

fh = figure('Units', 'centimeters', 'Position', [2 2 18.3 7.6], 'Color', 'w');
tl = tiledlayout(fh, 1, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

% ---- a) 交互作用图：两条线是否平行 ⇒ 有无交互 ----
ax1 = nexttile(tl); hold(ax1, 'on');
cm2 = [blu; red];
for i = 1:2
    plot(ax1, [1 2], v(i, :), '-o', 'LineWidth', 1.0, 'MarkerSize', 3.6, ...
        'Color', cm2(i, :), 'MarkerFaceColor', cm2(i, :));
end
set(ax1, 'YScale', 'log', 'XTick', [1 2], 'XTickLabel', {'固定 R', '收缩 R(t)'}, ...
    'XLim', [0.55 2.45], 'YLim', [20 170]);
text(ax1, 1, v(1, 1) * 1.13, sprintf('%.2f h', v(1, 1)), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.5, 'Color', blu);
text(ax1, 1, v(2, 1) * 1.06, sprintf('%.2f h', v(2, 1)), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.5, 'Color', red);
text(ax1, 2, v(1, 2) * 0.86, sprintf('%.2f h', v(1, 2)), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.5, 'Color', blu);
text(ax1, 2, v(2, 2) * 0.87, sprintf('%.2f h', v(2, 2)), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.5, 'Color', red);
text(ax1, 1.5, 30, sprintf('物性倍数  %.3f  →  %.3f', v(2, 1) / v(1, 1), v(2, 2) / v(1, 2)), ...
    'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 6.5, ...
    'Color', pur);
text(ax1, 1.5, 118, sprintf('几何倍数  %.4f  →  %.4f', v(1, 2) / v(1, 1), v(2, 2) / v(2, 1)), ...
    'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 6.5, ...
    'Color', pur);
xlabel(ax1, '几何设定'); ylabel(ax1, '达标时长 t_d / h（对数轴）');
style_ax(ax1); xlim(ax1, [0.55 2.45]); ylim(ax1, [20 170]);
legend(ax1, {'附录3 物性', '附录4 物性'}, 'Location', 'northeast', 'Box', 'off', ...
    'FontSize', 6, 'FontName', 'Microsoft YaHei');

% ---- b) 乘法分解：主效应 × 交互 = 净变化 ----
ax2 = nexttile(tl); hold(ax2, 'on');
y  = [v(1, 1), v(1, 1) * G, pred, v(2, 2)];
xs = 1:4;
plot(ax2, xs, y, '-', 'Color', [0.55 0.55 0.55], 'LineWidth', 0.6);
plot(ax2, xs([1 4]), y([1 4]), 'o', 'MarkerSize', 4.6, 'LineWidth', 0.9, ...
    'MarkerFaceColor', 'w', 'Color', [0.25 0.25 0.25]);
plot(ax2, xs([2 3]), y([2 3]), 'o', 'MarkerSize', 3.2, 'LineWidth', 0.7, ...
    'MarkerFaceColor', pur, 'Color', pur);
f = struct('x', {1.5, 2.5, 3.5}, 'f', {G, P, I}, ...
           's', {sprintf('几何 ×%.4f', G), sprintf('物性 ×%.4f', P), sprintf('交互 ×%.4f', I)});
for k = 1:3
    text(ax2, f(k).x, sqrt(y(k) * y(k + 1)), f(k).s, 'HorizontalAlignment', 'center', ...
        'FontName', 'Microsoft YaHei', 'FontSize', 6.4, 'Color', pur);
end
text(ax2, 1, y(1) * 1.10, sprintf('%.4f h\n（问题3）', y(1)), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.4, 'Color', [0.25 0.25 0.25]);
text(ax2, 4, y(4) * 0.88, sprintf('%.4f h\n（问题4）', y(4)), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.4, 'Color', [0.25 0.25 0.25]);
set(ax2, 'YScale', 'log', 'XTick', xs, ...
    'XTickLabel', {'基线', '几何', '无交互预测', '实测'}, 'XLim', [0.6 4.4], 'YLim', [18 190]);
xlabel(ax2, '乘法分解路径'); ylabel(ax2, '达标时长 t_d / h（对数轴）');
style_ax(ax2); xlim(ax2, [0.6 4.4]); ylim(ax2, [18 190]);
text(ax2, 2.5, 22, sprintf('净 %.4f  =  几何 %.4f × 物性 %.4f × 交互 %.4f', ...
    v(2, 2) / v(1, 1), G, P, I), 'HorizontalAlignment', 'center', ...
    'FontName', 'Microsoft YaHei', 'FontSize', 6.3, 'Color', [0.3 0.3 0.3]);

save_png(fh, fullfile(OUT, 'fig13_ablation_td.png'));
fprintf('  G=%.4f  P=%.4f  pred=%.4f  I=%.4f  net=%.4f\n', ...
    G, P, pred, I, v(2, 2) / v(1, 1));
end

% ---------------- 图13 面板（a）公用：三维"幕布"直纹面 + 完整包围盒 + ΔR 色标 ----------------
% ① 幕布：同一时刻两端点连成直母线，整片即直纹面；颜色 = 半径差 ΔR（色标给可核数值）。
% ② 完整包围盒：12 条棱全画，底面/右壁补灰面——只画两块灰面时盒子是"缺一半"的，立体感差。
% ③ 母线（ruliing）淡白细线：直纹面的定义线，兼作织物纹理，9 条按等时距布。
function drape3d(ax, tt, Cb, Ra, Rc, gap, Rmin)
red  = [0.760 0.455 0.447];
blu  = [0.369 0.518 0.725];
lred = [1.000 0.680 0.670];
lblu = [0.660 0.810 0.970];
gry  = [0.66 0.66 0.66];
wal  = [0.955 0.955 0.955];
boxc = [0.80 0.80 0.80];
dred = [0.62 0.30 0.30];

z0 = min([Rc; Ra]); z1 = max([Rc; Ra]);
c0 = min(Cb);       c1 = max(Cb);
t0 = min(tt);       t1 = max(tt);
zl = [z0 - 0.03, z1 + 0.10];
hold(ax, 'on');

% 完整包围盒：8 顶点 → 12 棱
BX = [t0 t1]; BY = [c0 c1]; BZ = zl;
VX = BX([1 2 2 1 1 2 2 1]); VY = BY([1 1 2 2 1 1 2 2]);
VZ = BZ([1 1 1 1 2 2 2 2]);
BE = [1 2; 2 3; 3 4; 4 1; 5 6; 6 7; 7 8; 8 5; 1 5; 2 6; 3 7; 4 8];
for i = 1:size(BE, 1)
    plot3(ax, VX(BE(i, :)), VY(BE(i, :)), VZ(BE(i, :)), '-', ...
        'Color', boxc, 'LineWidth', 0.4);
end

% 底面 + 右壁两面灰板。⚠️ 试过再加背墙（第三面）：纵深被填成灰色实体，幕布右段本就
% 色淡，压在灰底上对比全丢、整片发闷 ⇒ 只留两面，让盒子其余部分是"空气"。
fill3(ax, [t0 t1 t1 t0], [c0 c0 c1 c1], [z0 z0 z0 z0], wal, ...
    'FaceAlpha', 1.0, 'EdgeColor', 'none');
fill3(ax, [t1 t1 t1 t1], [c0 c1 c1 c0], [z0 z0 z1 z1], wal, ...
    'FaceAlpha', 1.0, 'EdgeColor', 'none');

% 失水致缩理论下界 R_min。⚠️ 不画跨底面的虚线框、也不画半透明面片：
% ① 幕布是覆盖整个 (t,C) 底面的帘面，俯视时它把下方的水平框挡掉大半，只剩碎线；
% ② FaceAlpha<1 的面片会被渲染器归入"后绘"通道，给幕布整体染上暖色，而幕布颜色
%    本身就是 ΔR 的编码 ⇒ 会污染数据读出。故改为在实测轨迹**穿越下界之处打点标注**
%    （该点在幕布的下边界上，属轮廓线、必不被遮挡），另沿前缘加一条下界水平虚线。
jmin = find(Ra <= Rmin, 1);
hP = plot3(ax, [t0 t1], [c0 c0], Rmin * [1 1], '--', 'Color', dred, 'LineWidth', 0.8);
% 穿越时刻由相邻两样本线性插值定出，不取首个越界样本的时刻：样本格是 5 min，
% 直接取格点会引入最多 5 min 的量化偏差，并与正文所报的时刻对不上。
tX = NaN; cX = NaN;
if ~isempty(jmin) && jmin > 1
    fw = (Rmin - Ra(jmin - 1)) / (Ra(jmin) - Ra(jmin - 1));
    tX = tt(jmin - 1) + fw * (tt(jmin) - tt(jmin - 1));
    cX = Cb(jmin - 1) + fw * (Cb(jmin) - Cb(jmin - 1));
    plot3(ax, tX, cX, Rmin, 'o', 'MarkerSize', 4.6, 'LineWidth', 0.9, ...
        'MarkerEdgeColor', dred, 'MarkerFaceColor', 'w');
    text(ax, tX, cX, Rmin - 0.055, sprintf('R_{min} = %.4f cm', Rmin), ...
        'FontName', 'Microsoft YaHei', 'FontSize', 6.5, 'Color', dred, ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'top');
end

% 投影：底面 = 失水剖面（两线共用，故灰）；右壁 = 两条 R(t) 各随主线配色
plot3(ax, tt, Cb, z0 * ones(size(tt)), '-', 'Color', gry, 'LineWidth', 0.5);
plot3(ax, t1 * ones(size(tt)), Cb, Ra, '-', 'Color', lred, 'LineWidth', 0.55);
plot3(ax, t1 * ones(size(tt)), Cb, Rc, '-', 'Color', lblu, 'LineWidth', 0.55);

% 幕布
surf(ax, [tt tt], [Cb Cb], [Ra Rc], [gap gap], ...
    'FaceColor', 'interp', 'EdgeColor', 'none', 'FaceAlpha', 1.0);
% 色阶：近白 → #8E7BC3 淡紫，两点线性。试过 (a) gamma 非线性压缩、(b) 深端压到 MUT 深紫，
% 两者都让画面更闷 ⇒ 保留这一版。（"视觉重量"来自成片色面，不是靠把颜色压黑。）
n = 160;
colormap(ax, [linspace(0.968, 0.557, n)', linspace(0.949, 0.486, n)', ...
              linspace(0.988, 0.765, n)']);
gt = max(gap) * 1.02;
st = 10 ^ floor(log10(gt)) / 2;          % 取 1-2-5 档的整数步长，避免 0.0675 这类脏刻度
if gt / st > 6, st = st * 2; end
caxis(ax, [0 ceil(gt / st) * st]);
cb = colorbar(ax);
cb.Label.String = '半径差 \DeltaR / cm（水律 − 实测）';
cb.Label.FontName = 'Microsoft YaHei'; cb.Label.FontSize = 7;
cb.FontName = 'Microsoft YaHei'; cb.FontSize = 7; cb.LineWidth = 0.4;
cb.Color = [0.29 0.29 0.29]; cb.TickDirection = 'in';
cb.Ticks = 0:st:ceil(gt / st) * st;
% ⚠️ 别把色标横放（Orientation='horizontal' + Layout.Tile='south'）：'south' 按整个
% tiledlayout 铺，会横穿到右面板底下，不是只占本 tile；要横放只能手改 cb.Position。

% 母线：等时距 9 条，淡白细线，兼作幕布纹理
tr = linspace(t0, t1, 11); tr = tr(2:end - 1);
for i = 1:numel(tr)
    j = find(tt >= tr(i), 1);
    if isempty(j), continue; end
    plot3(ax, [tt(j) tt(j)], [Cb(j) Cb(j)], [Ra(j) Rc(j)], '-', ...
        'Color', [0.93 0.91 0.97], 'LineWidth', 0.35);
end

% 两条空间轨迹压在幕布之上（幕布的两条边界即它们）
h1 = plot3(ax, tt, Cb, Ra, '-',  'Color', red, 'LineWidth', 1.15);
h2 = plot3(ax, tt, Cb, Rc, '--', 'Color', blu, 'LineWidth', 1.15);

% 半程点
ta = t50_of(tt, Ra); tc = t50_of(tt, Rc);
ia = find(tt >= ta, 1); ic = find(tt >= tc, 1);
plot3(ax, tt(ia), Cb(ia), Ra(ia), 'o', 'MarkerSize', 3.6, 'LineWidth', 0.8, ...
    'MarkerEdgeColor', red, 'MarkerFaceColor', 'w');
plot3(ax, tt(ic), Cb(ic), Rc(ic), 'o', 'MarkerSize', 3.6, 'LineWidth', 0.8, ...
    'MarkerEdgeColor', blu, 'MarkerFaceColor', 'w');

xlabel(ax, '时间 t / h'); ylabel(ax, '含水率 C / (kg/kg)');
zlabel(ax, '半径 R / cm');
view(ax, [-40 22]); axis(ax, 'tight');
axis(ax, [t0 t1 c0 c1 zl]);
style_ax(ax);
lg = legend(ax, [h1 h2 hP], ...
    {'附件2 实测', '纯失水律预测', sprintf('失水致缩下界 %.4f cm', Rmin)}, ...
    'Location', 'northeast');
lg.Box = 'off'; lg.FontName = 'Microsoft YaHei'; lg.FontSize = 6.5;
fprintf('  ΔR 峰值 %.4f cm @ t = %.2f h；半程 实测 %.4f / 纯失水 %.4f h；下界 %.4f cm 穿越于 t = %.4f h\n', ...
    max(gap), tt(find(gap == max(gap), 1)), ta, tc, Rmin, tX);
end

% ---------------- 滞后份额子图（失水完成份额 vs 收缩完成份额） ----------------
function lagB(ax, tt, Cb, Ra, Rc)
f   = @(v) (v(1) - v) ./ (v(1) - v(end));
fC  = f(Cb); fA = f(Ra); fS = f(Rc);
lred = [1.000 0.680 0.670];
lblu = [0.660 0.810 0.970];
hold(ax, 'on');
patch(ax, [fC; flipud(fC)], [min(fA, fC); flipud(max(fA, fC))], lred, ...
    'EdgeColor', 'none', 'FaceAlpha', 0.6);
patch(ax, [fC; flipud(fC)], [min(fS, fC); flipud(max(fS, fC))], lblu, ...
    'EdgeColor', 'none', 'FaceAlpha', 0.6);
h0 = plot(ax, [0 1], [0 1], ':', 'Color', [0.66 0.66 0.66], 'LineWidth', 0.8);
plot(ax, fC, fA, '-',  'Color', [0.760 0.455 0.447], 'LineWidth', 1.0);
plot(ax, fC, fS, '--', 'Color', [0.369 0.518 0.725], 'LineWidth', 1.0);
xlabel(ax, '失水完成份额 F（含水率口径）');
ylabel(ax, '收缩完成份额 F（半径口径）');
axis(ax, [0 1 0 1]);
xticks(ax, 0:0.25:1); yticks(ax, 0:0.25:1);
xticklabels(ax, {'0%', '25%', '50%', '75%', '100%'});
yticklabels(ax, {'0%', '25%', '50%', '75%', '100%'});
style_ax(ax);
lg = legend(ax, h0, {'完全同步线'}, 'Location', 'northwest');
lg.Box = 'off'; lg.FontName = 'Microsoft YaHei'; lg.FontSize = 6.5;
end

% ---------------- 图15 收缩本构反演与失水下界：三维幕布 + 滞后份额子图（右） ----------------
function fig_shrinklaw(FD, OUT)
[tt, Cb, Ra, Rc, gap] = load_shrink(FD);
% 失水下界取数值总表唯一口径：由 shrinklaw.py 计算并落盘，此处只读不算，避免同一物理量两条算路
sjson = jsondecode(fileread(fullfile(FD, 'shrinklaw_summary.json')));
Rmin  = sjson.R_min_cm;
fh = figure('Units', 'centimeters', 'Position', [2 2 18.3 8.6], 'Color', 'w');
tl = tiledlayout(fh, 1, 7, 'Padding', 'compact', 'TileSpacing', 'compact');
axA = nexttile(tl, [1 4]);
drape3d(axA, tt, Cb, Ra, Rc, gap, Rmin);
axB = nexttile(tl, [1 3]);
lagB(axB, tt, Cb, Ra, Rc);
save_png(fh, fullfile(OUT, 'fig16_shrinklaw.png'));
end

function [tt, Cb, Ra, Rc, gap] = load_shrink(FD)
% 列布局与 shrinkclosed.csv 一致：3=水律预测(幕布上界) 4=附件2实测(下界) 6=Cbar
M  = readmatrix(fullfile(FD, 'shrinklaw.csv'), 'NumHeaderLines', 1);
tt = M(:, 2); Rc = M(:, 3); Ra = M(:, 4); Cb = M(:, 6);
g  = ~isnan(tt) & ~isnan(Rc) & ~isnan(Ra) & ~isnan(Cb);
tt = tt(g); Rc = Rc(g); Ra = Ra(g); Cb = Cb(g);
[tt, o] = sort(tt); Rc = Rc(o); Ra = Ra(o); Cb = Cb(o);
gap = Rc - Ra;
end

function x = t50_of(t, v)
f = (v(1) - v) / (v(1) - v(end));
i = find(f >= 0.5, 1);
x = t(i - 1) + (0.5 - f(i - 1)) / (f(i) - f(i - 1)) * (t(i) - t(i - 1));
end

% ---------------- 候选③ §7.5 达标时长的空间分解：剖面瀑布 + 阈值切面 ----------------
% 数据全来自 公共内核/spacebreak.py 的一次运行，与候选①同源：
%   spacebreak_field.csv  (t,r) 温湿场（列：t_s t_h r_cm C T_C）
%   spacebreak_front.csv  干透前锋 C=C_cr（列：r_cm t_cross_h）
%   spacebreak_series.csv 同工况(Q3)轴心/表面序列（列：t_s t_h C_c C_s T_c T_s R）
% 热场对照取 q2_series.csv(Q2)，与正文第 7.5 节的口径一致。
% ---------------- 备选① §7.5 干壳生长的同心圆截面（俯视） ----------------
% 每个圆环用 spacebreak_field.csv 的实测 C(r) 逐节点上色，半径即该节点真实半径，
% 所以图上的环不是示意图，是数据本身；红圈为 C=0.15 干透壳前沿，由
% spacebreak_front.csv 反查"该时刻已穿越的最大半径"得到。与候选②同算路。
% ---------------- 备选③ §7.5 干壳推进的三维剖切圆柱 ----------------
% 把药材做成真实的三维圆柱块，切掉朝向观察者的一个楔形缺口：
%   顶面 = 同心环（该时刻实测 C(r) 上色）  两个剖面 = 径向分布
%   外壁 = 表面值  红弧/红线 = C=0.15 干透前锋
% ⚠ 圆柱高度只是为了让剖切可见，不是数据维度（题目未给药材长度），图注须写明。
function fig_coresec(FD, OUT)
M  = readmatrix(fullfile(FD, 'spacebreak_field.csv'), 'NumHeaderLines', 1);
tu = unique(M(:, 1)); ru = unique(M(:, 3));
Z  = reshape(M(:, 4), numel(ru), numel(tu)).';
th = tu / 3600;
FR = readmatrix(fullfile(FD, 'spacebreak_front.csv'), 'NumHeaderLines', 1);
FR = FR(~isnan(FR(:, 2)), :);  [~, o] = sort(FR(:, 1)); FR = FR(o, :);
ts = min(FR(:, 2)); tc = max(FR(:, 2)); R0 = max(ru);
BR = [0.05 0.15 0.35 0.75 1.40 2.60];  ZP = [0 0.2 0.4 0.6 0.8 1.0];
zof = @(c) interp1(BR, ZP, min(max(c, BR(1)), BR(end)), 'linear');
cmap = [linspace(0.906, 0.369, 200).', linspace(0.937, 0.518, 200).', linspace(0.980, 0.725, 200).'];

PA = deg2rad(24); PB = deg2rad(264);        % 保留扇区：缺口朝向观察者
NTH = 73;  THv = linspace(PA, PB, NTH);
HH  = 1.55;                                  % 柱高，仅作视觉厚度

tgt = [0, ts, 36, tc];
idx = arrayfun(@(x) find(abs(th - x) == min(abs(th - x)), 1), tgt);
idx(end) = numel(tu);

fh = figure('Units', 'centimeters', 'Position', [2 2 18.0 11.6], 'Color', 'w');
tl = tiledlayout(fh, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');
for j = 1:4
    ax = nexttile(tl); hold(ax, 'on');
    cv = Z(idx(j), :);  cv = cv(:).';
    cz = repmat(zof(cv), NTH, 1);
    [THm, RRm] = ndgrid(THv, ru);
    Xc = RRm .* cos(THm);  Yc = RRm .* sin(THm);
    surf(ax, Xc, Yc, HH * ones(size(Xc)), cz, 'EdgeColor', 'none', 'FaceColor', 'flat');
    [THw, ZZw] = ndgrid(THv, [0 HH]);                    % 外壁
    surf(ax, R0 * cos(THw), R0 * sin(THw), ZZw, zof(cv(1)) * ones(size(ZZw)), ...
        'EdgeColor', 'none', 'FaceColor', 'flat');
    [RRf, ZZf] = ndgrid(ru, [0 HH]);                     % 两个剖面
    for a = [1 NTH]
        surf(ax, RRf * cos(THv(a)), RRf * sin(THv(a)), ZZf, ...
            repmat(zof(cv(:)), 1, 2), 'EdgeColor', 'none', 'FaceColor', 'flat');
    end
    [~, iR] = min(abs(ru - R0));
    [~, i0] = min(abs(ru));
    ok = FR(:, 2) <= th(idx(j)) + 1e-4;
    rf = R0;  if any(ok), rf = min(FR(ok, 1)); end
    plot3(ax, R0 * cos(THv), R0 * sin(THv), (HH + 0.006) * ones(size(THv)), ...
        '-', 'Color', [0.63 0.63 0.63], 'LineWidth', 0.35);
    if rf > 1e-4
        plot3(ax, rf * cos(THv), rf * sin(THv), (HH + 0.012) * ones(size(THv)), ...
            '-', 'Color', [0.72 0.30 0.30], 'LineWidth', 1.1);
        for a = [1 NTH]
            plot3(ax, [rf rf] * cos(THv(a)), [rf rf] * sin(THv(a)), [0 HH], ...
                '-', 'Color', [0.72 0.30 0.30], 'LineWidth', 0.9);
        end
    end
    colormap(ax, cmap);  clim(ax, [0 1]);
    axis(ax, 'equal');  daspect(ax, [1 1 1]);
    xlim(ax, [-2.3 2.3]); ylim(ax, [-2.3 2.3]); zlim(ax, [-0.1 HH + 0.35]);
    view(ax, [-37.5 22]);  grid(ax, 'off');  box(ax, 'off');
    set(ax, 'XColor', 'none', 'YColor', 'none', 'ZColor', 'none');
    title(ax, sprintf('t = %.4f h   干透壳厚 %.2f cm', th(idx(j)), R0 - rf), ...
        'FontName', 'Microsoft YaHei', 'FontSize', 6.5, 'Color', [0.22 0.22 0.22]);
    fprintf('  柱%d  t = %7.4f h  壳厚 %.4f cm  前沿 r = %.4f cm\n', ...
        j, th(idx(j)), R0 - rf, rf);
end
cax = axes(fh, 'Position', [0.906 0.20 0.014 0.60]);
imagesc(cax, linspace(0, 1, 301).');  colormap(cax, cmap);  clim(cax, [0 1]);
set(cax, 'XColor', 'none', 'YColor', 'none', 'Box', 'off', 'XTick', [], 'YTick', []);
cb = colorbar(cax, 'Location', 'eastoutside');
cb.Ticks = ZP;  cb.TickLabels = {'0.05', '0.15', '0.35', '0.75', '1.40', '2.60'};
cb.FontName = 'Microsoft YaHei';  cb.FontSize = 5.8;  cb.Box = 'off';
cb.Label.String = '含水率 C / (kg/kg)';  cb.Label.FontSize = 6.0;
cb.Label.FontName = 'Microsoft YaHei';
save_png(fh, fullfile(OUT, 'cand_coresec.png'));
end

function fig_ringsec(FD, OUT)
M  = readmatrix(fullfile(FD, 'spacebreak_field.csv'), 'NumHeaderLines', 1);
tu = unique(M(:, 1)); ru = unique(M(:, 3));
Z  = reshape(M(:, 4), numel(ru), numel(tu)).';
th = tu / 3600;
FR = readmatrix(fullfile(FD, 'spacebreak_front.csv'), 'NumHeaderLines', 1);
FR = FR(~isnan(FR(:, 2)), :);  [~, o] = sort(FR(:, 1)); FR = FR(o, :);
ts = min(FR(:, 2)); tc = max(FR(:, 2)); cc = 0.15; R0 = max(ru);

tgt = [0, ts, 24, 36, 48, tc];
idx = arrayfun(@(x) find(abs(th - x) == min(abs(th - x)), 1), tgt);
idx(end) = numel(tu);
% 单色蓝阶：低端抬到淡蓝而非近白，否则干透壳在白底上会"消失"
cmap = [linspace(0.906, 0.369, 200).', linspace(0.937, 0.518, 200).', linspace(0.980, 0.725, 200).'];
% 色标用与全文热力图同一套断点做分段线性拉伸：否则核心区 C 只占全程量程一成，
% 环形会一片惨白；刻度仍按真实 C 标（非等距），不改变数值含义。
BR = [0.05 0.15 0.35 0.75 1.40 2.60];
ZP = [0 0.2 0.4 0.6 0.8 1.0];
zof = @(c) interp1(BR, ZP, min(max(c, BR(1)), BR(end)), 'linear');

fh = figure('Units', 'centimeters', 'Position', [2 2 18.0 5.0], 'Color', 'w');
W = 0.138; GAP = 0.012; H = 2.48 / 5.0; Y0 = 0.44;
fprintf('  ts = %.4f h  tc = %.4f h\n', ts, tc);
for j = 1:6
    ax = axes(fh, 'Position', [(j - 1) * (W + GAP) + 0.006, Y0, W, H]);
    hold(ax, 'on');
    zv = Z(idx(j), :);
    kk = 1 + round((size(cmap, 1) - 1) * zof(zv));
    for i = numel(ru):-1:1                      % 由外向内叠圆片 => 自然成环
        rectangle(ax, 'Position', [-ru(i) -ru(i) 2 * ru(i) 2 * ru(i)], 'Curvature', [1 1], ...
            'FaceColor', cmap(kk(i), :), 'EdgeColor', 'none');
    end
    rectangle(ax, 'Position', [-R0 -R0 2 * R0 2 * R0], 'Curvature', [1 1], ...
        'FaceColor', 'none', 'EdgeColor', [0.63 0.63 0.63], 'LineWidth', 0.4);
    ok = FR(:, 2) <= th(idx(j)) + 1e-4;         % t_hit 与 t_cross 的落盘舍入差（1e-6 h）
    rf = R0;                                    % 尚未有节点穿越时，前沿停在表面 => 壳厚 0
    if any(ok), rf = min(FR(ok, 1)); end
    if rf > 1e-6
        rectangle(ax, 'Position', [-rf -rf 2 * rf 2 * rf], 'Curvature', [1 1], ...
            'FaceColor', 'none', 'EdgeColor', [0.72 0.33 0.33], 'LineWidth', 0.9);
    end
    axis(ax, 'equal'); xlim(ax, [-2.3 2.3]); ylim(ax, [-2.3 2.3]);
    set(ax, 'XColor', 'none', 'YColor', 'none', 'Box', 'off', 'XTick', [], 'YTick', []);
    xlabel(ax, sprintf('t = %.4f h\n壳厚 %.2f cm', th(idx(j)), R0 - rf), ...
        'FontName', 'Microsoft YaHei', 'FontSize', 6.0, 'Color', [0.24 0.24 0.24]);
    fprintf('  盘%d  t = %7.4f h  壳厚 %.4f cm  前沿 r = %.4f cm\n', ...
        j, th(idx(j)), R0 - rf, rf);
end
cax = axes(fh, 'Position', [0.925 Y0 0.016 H]);
imagesc(cax, linspace(0, 1, 301).'); colormap(cax, cmap); clim(cax, [0 1]);
set(cax, 'XColor', 'none', 'YColor', 'none', 'Box', 'off', 'XTick', [], 'YTick', []);
cb = colorbar(cax, 'Location', 'eastoutside');
cb.Ticks = ZP; cb.TickLabels = {'0.05', '0.15', '0.35', '0.75', '1.40', '2.60'};
cb.FontName = 'Microsoft YaHei'; cb.FontSize = 5.8; cb.Box = 'off';
cb.Label.String = '含水率 C / (kg/kg)'; cb.Label.FontSize = 6.0;
cb.Label.FontName = 'Microsoft YaHei';
annotation(fh, 'textbox', [0 0.02 1 0.10], 'String', sprintf( ...
    '红圈 = 干透壳前沿 C = 0.15：自表面（%.4f h 首越）向内推进至轴心（%.4f h 首越），沿途耗时 %.4f h，占达标时长的 %.2f%%', ...
    ts, tc, tc - ts, 100 * (tc - ts) / tc), 'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', 'FontName', 'Microsoft YaHei', 'FontSize', 6.2, ...
    'Color', [0.28 0.28 0.28], 'EdgeColor', 'none', 'LineStyle', 'none');
save_png(fh, fullfile(OUT, 'cand_ring.png'));
end

function fig_spacefall(FD, OUT)
M  = readmatrix(fullfile(FD, 'spacebreak_field.csv'), 'NumHeaderLines', 1);
tu = unique(M(:, 1));
ru = unique(M(:, 3));
Z  = reshape(M(:, 4), numel(ru), numel(tu)).';      % [时间 × 半径]
th = tu / 3600;

FR = readmatrix(fullfile(FD, 'spacebreak_front.csv'), 'NumHeaderLines', 1);
FR = FR(~isnan(FR(:, 2)), :);
[~, of] = sort(FR(:, 1)); FR = FR(of, :);
ts = min(FR(:, 2));  tc = max(FR(:, 2));  cc = 0.15;

it = unique(round(linspace(1, numel(tu), 34)));      % 剖面条数：密而不糊
ir = unique(round(linspace(1, numel(ru), 140)));
rs = ru(ir);

fh = figure('Units', 'centimeters', 'Position', [2 2 18.3 8.6], 'Color', 'w');
tl = tiledlayout(fh, 2, 3, 'Padding', 'compact', 'TileSpacing', 'compact');

ax1 = nexttile(tl, [2 2]);
hold(ax1, 'on');
cmap = seq_cmap();
fill3(ax1, [rs(1) rs(end) rs(end) rs(1)], [th(1) th(1) th(end) th(end)], cc * [1 1 1 1], ...
    [0.760 0.455 0.447], 'FaceAlpha', 0.10, ...
    'EdgeColor', [0.760 0.455 0.447], 'LineWidth', 0.35);
for i = 1:numel(it)
    k  = 1 + round((size(cmap, 1) - 1) * (th(it(i)) - th(1)) / (th(end) - th(1)));
    plot3(ax1, rs, th(it(i)) * ones(size(rs)), Z(it(i), ir), '-', ...
        'Color', cmap(k, :), 'LineWidth', 0.55);
end
plot3(ax1, FR(:, 1), FR(:, 2), cc * ones(size(FR, 1), 1), '-', ...
    'Color', [0.62 0.30 0.30], 'LineWidth', 1.3);
plot3(ax1, 2.0, ts, cc, 'o', 'MarkerSize', 4.4, 'LineWidth', 0.9, ...
    'MarkerEdgeColor', [0.62 0.30 0.30], 'MarkerFaceColor', 'w');
plot3(ax1, 0.0, tc, cc, 'o', 'MarkerSize', 4.4, 'LineWidth', 0.9, ...
    'MarkerEdgeColor', [0.62 0.30 0.30], 'MarkerFaceColor', 'w');
text(ax1, 1.93, ts + 3.0, cc + 0.16, sprintf('表面达标 %.4f h', ts), ...
    'HorizontalAlignment', 'right', 'FontName', 'Microsoft YaHei', 'FontSize', 6.5, ...
    'Color', [0.62 0.30 0.30]);
text(ax1, 0.09, tc - 3.0, cc - 0.30, sprintf('轴心达标 %.4f h', tc), ...
    'HorizontalAlignment', 'left', 'FontName', 'Microsoft YaHei', 'FontSize', 6.5, ...
    'Color', [0.62 0.30 0.30]);
xlabel(ax1, '半径 r / cm'); ylabel(ax1, '时间 t / h');
zlabel(ax1, '含水率 C / (kg/kg)');
view(ax1, [-38 24]); grid(ax1, 'off'); style_ax(ax1);

ax2 = nexttile(tl, [1 1]);
X  = readmatrix(fullfile(FD, 'spacebreak_series.csv'), 'NumHeaderLines', 1);
Y  = readmatrix(fullfile(FD, 'q2_series.csv'), 'NumHeaderLines', 1);
nC = (X(:, 3) - X(:, 4)); nC = nC / max(nC);
% q2_series 列序：t_s C_center C_surf T_center_C T_surf_C
nT = abs(Y(:, 5) - Y(:, 4)); nT = nT / max(nT);
hold(ax2, 'on');
h10 = plot(ax2, [0 72], [0.1 0.1], ':', 'Color', [0.55 0.55 0.55], 'LineWidth', 0.7);
hC  = plot(ax2, X(:, 2), nC, '-', 'Color', [0.760 0.455 0.447], 'LineWidth', 1.0);
hT  = plot(ax2, Y(:, 2), nT, '-', 'Color', [0.490 0.435 0.658], 'LineWidth', 1.0);
xlabel(ax2, '时间 t / h'); ylabel(ax2, '空间差异（按峰值归一）');
axis(ax2, [0 72 0 1.02]); yticks(ax2, 0:0.25:1);
yticklabels(ax2, {'0%', '25%', '50%', '75%', '100%'});
style_ax(ax2);
lg = legend(ax2, [hC hT h10], {'含水率差（问题三）', '温差（问题二）', '峰值的 10%'}, ...
    'Location', 'northeast');
lg.Box = 'off'; lg.FontName = 'Microsoft YaHei'; lg.FontSize = 6.0;

ax3 = nexttile(tl, [1 1]);
hold(ax3, 'on');
fill(ax3, [0 ts ts 0], [0 0 1 1], [0.631 0.788 0.957], 'EdgeColor', 'w', 'LineWidth', 0.6);
fill(ax3, [ts tc tc ts], [0 0 1 1], [1.000 0.624 0.608], 'EdgeColor', 'w', 'LineWidth', 0.6);
text(ax3, ts / 2, 0.5, sprintf('%.2f%%', 100 * ts / tc), ...
    'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 6.2, ...
    'Color', [0.24 0.24 0.24]);
text(ax3, (ts + tc) / 2, 0.5, sprintf('%.2f%%', 100 * (tc - ts) / tc), ...
    'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 6.2, ...
    'Color', [0.24 0.24 0.24]);
% 面板很窄，两条说明只能上下排；用分段的同色文字把"哪条说哪段"绑死
text(ax3, 0.035 * tc, 1.72, sprintf('表面达标段  %.4f h', ts), ...
    'HorizontalAlignment', 'left', 'FontName', 'Microsoft YaHei', 'FontSize', 5.9, ...
    'Color', [0.329 0.451 0.643]);
text(ax3, 0.035 * tc, 1.18, sprintf('轴心补平段  %.4f h', tc - ts), ...
    'HorizontalAlignment', 'left', 'FontName', 'Microsoft YaHei', 'FontSize', 5.9, ...
    'Color', [0.660 0.353 0.349]);
xlim(ax3, [0 tc]); ylim(ax3, [0 2.02]);
set(ax3, 'YTick', []);
xlabel(ax3, '时间 t / h');
style_ax(ax3);

save_png(fh, fullfile(OUT, 'cand3_fall.png'));
fprintf('  ts = %.4f h  tc = %.4f h  补平段占比 %.4f%%\n', ...
    ts, tc, 100 * (tc - ts) / tc);
end
