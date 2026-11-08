function fig18_ts()
% ------------------------------------------------------------------------
% Thermal Science，Fig. 6：数值校核 + 二维收敛联合视图（140 mm 落版，2 行布局）
%   上排通栏  (a) 误差曲面 (Nc, dt) -> log10 max|C - C_ana|      —— 一字未动
%   下排三格  (b) 阈值时间 vs Nc：两构型 FVM↔FEM 之间填淡彩色带，
%                 构型名放面板中部空白，面板内再嵌一个放大 inset
%             (c) 两种离散之差（秒，log 纵轴），带 -2 斜率参考线
%             (d) 解析基准上轴/内部/壁面三处偏差 vs Nc，带 -2 斜率参考线
%
% (b)(c)(d) 于 2026-09-25 重绘，三处改动各有据：
%   ① 原 (c)/(d) 的图例摆在坐标区 southwest，而两条/三条曲线都是单调下降的
%      斜线族、恰好穿过左下角 ⇒ 图例的示例线段与真实数据线重合，读者分不清
%      哪条是图例哪条是数据。现移到 northeast（该处三条线均已降到低量级，
%      是唯一真正空白的角），并锁 'AutoUpdate','off' 防后续 plot 追加条目。
%   ② 原 (b) 的 y 轴跨 7.3 h，而固定半径构型组内只变 0.092 h、收缩构型只变
%      0.036 h ⇒ 两条线被压成水平直线，"收敛"完全读不出来。现主图保留绝对
%      量纲与两端绝对读数，把收敛证据移进面板内闲置的中部空白（y∈[51.2,57.3]
%      内无任何数据）里嵌的 inset；inset 里标的 57.4786 h 与 p=1.33/1.53
%      均为正文已报道、且可在 fem_crosscheck.csv 的 extrap_p2 / order_obs_nc
%      行逐位复算的量（图上不出正文没有的数）。
%   ③ 斜率参考线原为灰色，踩"图内数据元素与标注线禁红黑灰"红线。改淡黄深档
%      #C7B84C：(d) 里蓝/绿/紫已被轴心/内部/壁面三处占用，同图一色只能有
%      一个语义，故不能就近取紫。
%   ④ (b) 的构型名原贴在数据带同一高度、紧邻末点右侧，文字左缘与末点右缘只
%      隔 9 px（≈0.4 mm 印刷宽），印出来与线段黏成一条；面板纵向在带外只剩
%      0.22 h / 0.17 h，放不下一行字 ⇒ 改放两带之间的空档，各留 0.15 h 净空。
%   ⑤ (b) inset 的纵轴上限 57.494 容不下 57.4786 那行注记（文字高 0.019 h），
%      注记顶部比上框高出 17 px、露在框外 ⇒ 上限抬到 57.512，注记与虚线留
%      0.006 h 净空。
%   ⑥ (d) 图例四条在 3.9 个数量级的窄面板里排不下（单列高占 40% 而东北角净空
%      41%，两列宽占 88% 必压纵轴）⇒ 图例只留三条位置线，黄金虚线与 (c) 同源
%      不重复列出；示例线段由默认 30 pt 收到 12 pt，宽占比 58%→44%。
%   ⑦ (c) 纵轴上限原为 3e2，只比数据最大点 118.25 高 0.4 个数量级 ⇒ 数据顶端
%      离轴顶仅 18.7% 轴高，容不下任何图例（三行 40%、两行 28.7%）⇒ 上限提到
%      1e3，数据顶端离轴顶 34.4%。随之 (c) 的图例也只留两条数据线，黄金虚线
%      在整图由 (d)/(c) 同色同型的同一条线，语义并入图注。
%
% (a) 段代码与其 axes Position 一字未动；最外内容边界（左 0.095 / 右 0.905 /
% 上 / 下）在三格重排后保持不变，故 exportgraphics 的裁切框不变、(a) 逐位不变。
%
% 只读 figdata 的 CSV，不改写任何既有文件（含 figs_matlab.m / figures_ts.R）。
% 公用 helper（warm_anchors / ramp_from / seq_cmap / style_ax）与
% 新建文件夹\代码\figs_matlab.m 逐位一致；R 侧 figures_ts.R 的 WARM() 必须同锚点。
%
% 字号：画布 14.0 cm 宽，落版 width=140mm。exportgraphics 裁到内容框，故"图自身
%       物理宽"必须从 PNG 像素反算（px / 600 dpi × 25.4），不能用 figure('Position')
%       标称的 cm。最小源字号 6.5 pt（图例与 inset 注记），该刊图内文字下限
%       2 mm ≈ 5.67 pt。落版后印刷字号由 check_figure_legibility.py 复核。
% ------------------------------------------------------------------------
HERE = fileparts(mfilename('fullpath'));
ROOT = fileparts(HERE);
FD  = fullfile(ROOT, 'data', 'processed', 'figdata');
OUT = fullfile(ROOT, 'results', 'figures');

C_ = struct();
C_.blue   = [0.3686 0.5176 0.7255];   % #5E84B9
C_.red    = [0.7608 0.4549 0.4471];   % #C27472
C_.green  = [0.3098 0.6196 0.4039];   % #4F9E67
C_.purple = [0.4902 0.4353 0.6588];   % #7D6FA8
C_.gold   = [0.7804 0.7216 0.2980];   % #C7B84C 淡黄 muted 深档：斜率参考线
C_.lilac  = [0.7020 0.6235 0.8588];   % #B39FDB 淡紫原色：inset 的锥形引线
FS = 7;

% 色阶自检：亮度必须逐档严格递减，否则产生假边界；首档不得近白（库卡《顺序色阶换色》）
cmap = seq_cmap();
bri  = 255 * (0.2126 * cmap(:, 1) + 0.7152 * cmap(:, 2) + 0.0722 * cmap(:, 3));
assert(all(diff(bri) < 0), '色阶亮度非严格递减');
assert(bri(1) < 250, '色阶首档近白，会糊进白底');
fprintf('  色阶自检：%d 行，亮度 %.1f -> %.1f 严格递减，首档 %.1f 不近白\n', ...
        numel(bri), bri(1), bri(end), bri(1));

fh = figure('Units', 'centimeters', 'Position', [2 2 14.0 12.5], 'Color', 'w');

% ======================= (a) 误差曲面 ==============================
S = readmatrix(fullfile(FD, 'cand_surface.csv'), 'NumHeaderLines', 1);   % [Nc dt err]
Ncv = unique(S(:, 1));  dtv = unique(S(:, 2));
Z = nan(numel(dtv), numel(Ncv));
for k = 1:size(S, 1)
    i = find(dtv == S(k, 2), 1);  j = find(Ncv == S(k, 1), 1);
    Z(i, j) = log10(S(k, 3));
end
Xv = log2(Ncv);  Yv = log2(dtv);
[Xg, Yg] = meshgrid(Xv, Yv);

axA = axes('Position', [0.105 0.480 0.750 0.455]);
surf(axA, Xg, Yg, Z, Z, 'EdgeColor', [0.45 0.45 0.45], 'FaceColor', 'flat', ...
     'LineWidth', 0.3);
% 色标窗口按数据的真实跨度取（42 点的 log10 err ∈ [-5.269, -2.514]）：
% 若留到 -6.2，色阶底部约 15% 永不出现，整条色阶的可用分辨率被白白丢掉
colormap(axA, cmap);  clim(axA, [-5.5 -2.4]);
hold(axA, 'on');

% 42 个真实采样点：不插值、不平滑，读者看得到采样密度
plot3(axA, Xg(:), Yg(:), Z(:), '.', 'Color', [0.25 0.25 0.25], 'MarkerSize', 5);

% 带地板的双参数拟合 err = F + C*dt^p（fminsearch，多起点取最小残差）
Fv = nan(numel(Ncv), 1);  Cv = Fv;  Pv = Fv;
for j = 1:numel(Ncv)
    m = S(:, 1) == Ncv(j);  dd = S(m, 2);  ee = S(m, 3);
    obj = @(q) sum((ee - (q(1) + q(2) * dd .^ q(3))) .^ 2);
    best = [];  bv = inf;
    for p0 = [1e-6 1.87e-5 1.0; 1e-6 1.87e-5 2.0; 1e-7 1.0e-5 0.5; ...
              1e-6 1.87e-5 0.8; 1e-6 1.87e-5 0.3]
        [q, fv] = fminsearch(obj, p0, optimset('MaxFunEvals', 4e4, ...
            'MaxIter', 4e4, 'Display', 'off', 'TolX', 1e-12, 'TolFun', 1e-18));
        if fv < bv, bv = fv;  best = q;  end
    end
    Fv(j) = best(1);  Cv(j) = best(2);  Pv(j) = best(3);
end
fprintf('  地板拟合 p ='); fprintf(' %.4f', Pv); fprintf('\n');
fprintf('  p 范围 = [%.4f, %.4f]\n', min(Pv), max(Pv));
fprintf('  C = %.4e，相对散布 (max-min)/mean = %.3f %%\n', mean(Cv), ...
        100 * (max(Cv) - min(Cv)) / mean(Cv));
rt = Fv(1:end-1) ./ Fv(2:end);
fprintf('  地板逐次比值 ='); fprintf(' %.3f', rt); fprintf('\n');

% 时间已收敛端 dt = 0.25 s：绿色实线 + 实心点
[~, i025] = min(abs(dtv - 0.25));
plot3(axA, Xv, Yv(i025) * ones(size(Xv)), Z(i025, :), '-o', 'Color', C_.green, ...
      'MarkerFaceColor', C_.green, 'MarkerEdgeColor', 'w', 'MarkerSize', 4, ...
      'LineWidth', 1.0);

% 生产用点 (Nc=1600, dt=7.5 s)
Pp = readmatrix(fullfile(FD, 'cand_surface_prod.csv'), 'NumHeaderLines', 1);
xp = log2(Pp(1));  yp = log2(Pp(2));  zp = log10(Pp(3));
plot3(axA, xp, yp, zp, 's', 'MarkerSize', 7, 'MarkerFaceColor', C_.purple, ...
      'MarkerEdgeColor', 'w', 'LineWidth', 0.6);

% 时间/空间两误差相等处：dt* = (F/C)^(1/p)，该处 err = 2F（故标记落在 2F 高度上）
dtstar = (Fv ./ Cv) .^ (1 ./ Pv);
Ystar  = log2(dtstar);
on = Ystar >= Yv(1) & Ystar <= Yv(end);
if any(on)
    Xs = Xv(on);  Ys = Ystar(on);  Zs = log10(2 * Fv(on));
    [Xs, ix] = sort(Xs);  Ys = Ys(ix);  Zs = Zs(ix);
    plot3(axA, Xs, Ys, Zs, '--o', 'Color', [0.15 0.15 0.15], 'MarkerSize', 4.5, ...
          'MarkerFaceColor', 'w', 'LineWidth', 1.0);
end

xlabel(axA, 'log_2 N_c');
ylabel(axA, 'log_2 (\Deltat / s)');
title(axA, '(a) joint view of the two discretization directions', ...
      'FontWeight', 'normal', 'HorizontalAlignment', 'left');
set(axA, 'XTick', Xv, 'XTickLabel', compose('%d', Ncv), ...
         'YTick', Yv, 'YTickLabel', {'0.25','0.5','1','2','4','8'}, ...
         'ZTick', -5:1:-3, 'View', [-38 20], 'BoxStyle', 'full');
% z 轴与色标共用同一窗口：两者刻度对齐，读者能直接由高度读色
zlim(axA, [-5.5 -2.4]);
style_ax(axA, FS);  box(axA, 'on');
% z 轴不另加标签（zlabel 会外溢到下面板标题区），量纲由色标承担
cb = colorbar(axA, 'Position', [0.870 0.480 0.017 0.455]);
set(cb, 'FontName', 'Microsoft YaHei', 'FontSize', FS, ...
        'Color', [0.29 0.29 0.29], 'LineWidth', 0.4, 'TickDir', 'in');
ylabel(cb, 'log_1_0 error');

% ======================= 读互校表 ==================================
T  = readtable(fullfile(FD, 'fem_crosscheck.csv'));
cr = T(strcmp(T.kind, 'cross'), :);
gp = T(strcmp(T.kind, 'gap'), :);
gn = {'Q3','Q4'};  gc = {C_.blue, C_.red};

% ======================= (b) 阈值时间 ==============================
% 纵轴跨 6.85 h，而每个构型组内只变 0.09 / 0.04 h：同一根轴同时装"两构型之差"
% 与"组内收敛"必然把后者压平。故主图只给全貌与绝对读数，收敛证据交给面板内
% 闲置的中部空白（y∈[51.2, 57.3] 无任何数据）里嵌的 inset。
axB = axes('Position', [0.095 0.075 0.270 0.245]);
hold(axB, 'on');
xlim(axB, [7.0 12.1]);  ylim(axB, [50.85 57.70]);
set(axB, 'XTick', log2([200 800 1600]), 'XTickLabel', {'200','800','1600'}, ...
         'YTick', 51:2:57);

NB = cell(1, 2);  VB = cell(1, 2);  NC = cell(1, 2);  VC = cell(1, 2);
for c = 1:2
    for mth = {'FVM', 'FEM'}
        m = strcmp(cr.question, gn{c}) & strcmp(cr.method, mth{1});
        nc = cr.Nc(m);  vv = cr.value(m);
        [nc, ix] = sort(nc);  vv = vv(ix);
        if strcmp(mth{1}, 'FVM')
            NB{c} = nc;  VB{c} = vv;
        else
            NC{c} = nc;  VC{c} = vv;
        end
    end
end
% 色带 = 两实现之间的分歧：淡彩原色填充，线条取其 muted 深档（同色相两档）
bandc = {[0.6314 0.7882 0.9569], [1.0000 0.6235 0.6078]};   % #A1C9F4 / #FF9F9B
for c = 1:2
    fill(axB, [log2(NB{c}); flipud(log2(NC{c}))], [VB{c}; flipud(VC{c})], ...
         bandc{c}, 'EdgeColor', 'none', 'FaceAlpha', 0.55, 'HandleVisibility', 'off');
end
% 实线圆点 = 有限体积，虚线三角 = 有限元（线型含义下沉图注）
for c = 1:2
    plot(axB, log2(NB{c}), VB{c}, '-o', 'Color', gc{c}, 'LineWidth', 1.0, ...
         'MarkerSize', 3.4, 'MarkerFaceColor', 'w', 'HandleVisibility', 'off');
    plot(axB, log2(NC{c}), VC{c}, '--^', 'Color', gc{c}, 'LineWidth', 0.85, ...
         'MarkerSize', 3.4, 'MarkerFaceColor', 'w', 'HandleVisibility', 'off');
end
% 生产网格 = Nc 1600（正文"Numerical repeatability"首句：该网格上 FEM 给
% 57.4784 h、与 FVM 相差 10.379 s / 3.147 s，两数都只在 1600 行成立）。
% 原 (b) 只在末点画标记，"空心标记即生产网格"的指认即由此而来；重绘后每点都
% 带标记，该指认失效 ⇒ 把末点填实，指认保留。两实现的末点相差不到 0.003 h、
% 落在同一像素，故每个构型只补一个实心点。
for c = 1:2
    plot(axB, log2(NB{c}(end)), VB{c}(end), 'o', 'Color', gc{c}, 'LineWidth', 0.8, ...
         'MarkerSize', 3.4, 'MarkerFaceColor', gc{c}, 'HandleVisibility', 'off');
end
% 构型名不用图例框：两条数据带分居上下两端，坐标区任何一角都会压上其一，
% 而面板中部要留给 inset。
% 位置约束（实测）：面板纵向在带上沿之下只多 0.22 h、带下沿之上只多 0.17 h，
% 都放不下一行 6.5 pt 文字；而原先贴在带高、紧邻末点右侧时，文字左缘与末点
% 右缘只隔 9 px（≈0.4 mm 印刷宽），印刷后与线段黏成一条。故改放到两带之间
% 的空档，各留 0.15 h（≈20 px）净空，并横向退到 inset 物理边界（x=10.61）之外。
text(axB, 10.85, 57.236, 'fixed', 'FontSize', 6.5, 'Color', C_.blue, ...
     'VerticalAlignment', 'top');
text(axB, 10.85, 51.170, 'shrinking', 'FontSize', 6.5, 'Color', C_.red, ...
     'VerticalAlignment', 'bottom');
xlabel(axB, 'N_c');  ylabel(axB, 't_d / h');
title(axB, '(b) endpoint', 'FontWeight', 'normal', 'HorizontalAlignment', 'left');
style_ax(axB, FS);

% ---- (b) 的 inset：固定半径构型的纵向放大（正文对它报了外推值与观测阶）----
% 只放大固定半径构型：两个构型相差 6.38 h，不能同轴放大，而正文的 Richardson
% 外推与观测阶正是对这个构型报的。
% 位置取面板中部偏右：贴 y 轴会让 inset 的纵轴刻度与主图刻度并成一列、读成同一
% 根轴（第一版即栽在此）；过右又会撞数据带右端的构型名。
axIn = axes('Position', [0.178 0.150 0.108 0.108]);
hold(axIn, 'on');
% 上限由 57.494 放到 57.512：原上限容不下 57.4786 那行注记（文字高 0.019 h，
% 底部在 57.481 时顶到 57.500，比 inset 上框高出 17 px、露在框外）。
xlim(axIn, [7.45 10.85]);  ylim(axIn, [57.372 57.512]);
c = 1;
fill(axIn, [log2(NB{c}); flipud(log2(NC{c}))], [VB{c}; flipud(VC{c})], ...
     bandc{c}, 'EdgeColor', 'none', 'FaceAlpha', 0.55);
plot(axIn, log2(NB{c}), VB{c}, '-o', 'Color', C_.blue, 'LineWidth', 0.9, ...
     'MarkerSize', 2.6, 'MarkerFaceColor', 'w');
plot(axIn, log2(NC{c}), VC{c}, '--^', 'Color', C_.blue, 'LineWidth', 0.8, ...
     'MarkerSize', 2.6, 'MarkerFaceColor', 'w');
% Richardson 外推极限（extrap_p2 行，p = 2）：正文已报 57.4786 h
exh = T(strcmp(T.kind, 'extrap_p2') & strcmp(T.question, gn{1}) & ...
        strcmp(T.method, 'FVM'), :).value;
plot(axIn, [7.45 10.85], [exh exh], ':', 'Color', C_.gold, 'LineWidth', 0.9);
% 与虚线留 0.006 h（≈13 px）净空：原 0.0025 h 只有 6 px，数字下缘几乎擦到虚线
text(axIn, 10.78, exh + 0.006, sprintf('%.4f', exh), 'FontSize', 6.5, ...
     'Color', C_.gold, 'HorizontalAlignment', 'right', 'VerticalAlignment', 'bottom');
% x 刻度只留刻度线、不留标签：inset 的横轴与主图同源（源框与引线已指明对应
% 区间），重复标注只会让 MATLAB 把三个标签旋转 45°，比主图刻度还抢眼
set(axIn, 'XTick', log2([200 800 1600]), 'XTickLabel', {}, ...
          'YTick', [57.40 57.45], 'YTickLabel', {'57.40','57.45'});
style_ax(axIn, 6.5);

% 源框取固定半径带的真实纵向边界，两条锥形引线接到 inset 的上边两角
% （接 inset 下两角会横穿 inset 内容）
pB  = get(axB,  'Position');
pIn = get(axIn, 'Position');
gxB = @(xd) pB(1) + pB(3) * (xd - 7.0) / (12.1 - 7.0);
gyB = @(yd) pB(2) + pB(4) * (yd - 50.85) / (57.70 - 50.85);
sy0 = min([min(VB{1}) min(VC{1})]);
sy1 = max([max(VB{1}) max(VC{1})]);
sx0 = min(log2(NB{1}));  sx1 = max(log2(NB{1}));
plot(axB, [sx0 sx1 sx1 sx0 sx0], [sy0 sy0 sy1 sy1 sy0], '-', ...
     'Color', C_.lilac, 'LineWidth', 0.6, 'HandleVisibility', 'off');
annotation(fh, 'line', [gxB(sx0) pIn(1)], [gyB(sy0) pIn(2) + pIn(4)], ...
           'Color', C_.lilac, 'LineWidth', 0.5);
annotation(fh, 'line', [gxB(sx1) pIn(1) + pIn(3)], [gyB(sy0) pIn(2) + pIn(4)], ...
           'Color', C_.lilac, 'LineWidth', 0.5);

% ======================= (c) 两离散之差 ============================
axC = axes('Position', [0.4325 0.075 0.195 0.245]);
hold(axC, 'on');
set(axC, 'YScale', 'log');
hc = gobjects(0);
for c = 1:2
    m = strcmp(gp.question, gn{c});
    nc = gp.Nc(m);  vv = gp.value(m);
    [nc, ix] = sort(nc);  vv = vv(ix);
    hc(end + 1) = plot(axC, log2(nc), vv, '-o', 'Color', gc{c}, 'LineWidth', 0.85, ...
         'MarkerSize', 3.6, 'MarkerFaceColor', 'w');
end
% 单条 -2 斜率参考线，锚在 Q3 序列首点。原为灰色 [0.6 0.6 0.6]，踩"图内数据
% 元素与标注线禁红黑灰"红线；改淡黄深档（本面板蓝/红已被两构型占用）
m = strcmp(gp.question, gn{1});
nc = gp.Nc(m);  vv = gp.value(m);
[nc, ix] = sort(nc);  vv = vv(ix);
hgC = plot(axC, log2(nc), vv(1) .* 2 .^ (-2 * (log2(nc) - log2(nc(1)))), '--', ...
     'Color', C_.gold, 'LineWidth', 0.8);
% 纵轴上限由 3e2 提到 1e3：原上限只比数据最大点 118.25 高 0.4 个数量级，即
% 数据顶端离轴顶只有 18.7% 轴高，而三行图例高占 40%、两行占 28.7% ⇒ 图例下沿
% 必然压上 fixed 曲线（第一版即如此）。提到 1e3 后数据顶端离轴顶 34.4%，两行
% 图例净空 5.7% 轴高。代价是数据占轴高的比例由 72% 降到 58%，收敛斜率略平。
xlim(axC, [7.2 10.9]);  ylim(axC, [2 1e3]);
set(axC, 'XTick', log2([200 800 1600]), 'XTickLabel', {'200','800','1600'}, ...
         'YTick', [3 30 300 1000]);
xlabel(axC, 'N_c');  ylabel(axC, 'FVM - FEM / s');
title(axC, '(c) scheme gap', 'FontWeight', 'normal', 'HorizontalAlignment', 'left');
% 图例从 southwest 移到 northeast：两条线都是单调下降斜线，正好穿过左下角，
% 原位置使图例的示例线段与真实数据线重合。northeast 处两序列都已降到低量级，
% 是唯一真空白角；再锁 AutoUpdate，防后续 plot/fill 自动追加入图例。
% 只列两条数据线：本面板的黄金虚线是与 (d) 同一条二阶斜率参考线，两条都容
% 不下第三个条目，故统一交给图注交代（一个参考线语义只在图注说一次）。
lgC = legend(axC, hc, {'fixed', 'shrinking'}, 'Location', 'northeast', ...
             'FontSize', 6.5, 'Box', 'off', 'Color', 'none');
lgC.AutoUpdate = 'off';
% 与 (d) 用同一个示例线段长度，两格图例的长宽比才一致
lgC.ItemTokenSize = [12 6];
style_ax(axC, FS);

% ======================= (d) 解析基准三处偏差 ======================
axD = axes('Position', [0.695 0.075 0.210 0.245]);
hold(axD, 'on');
set(axD, 'YScale', 'log');
% 三处位置用蓝/绿/紫，不用红色：红在本图 (b)(c) 里已约定为 shrinking 配置，
% 同一张图内一个颜色只能有一个语义（否则读者要靠图例反复切换解码规则）
srs = {'order_fem_axis', C_.blue, 'axis'; ...
       'order_fem_interior', C_.green, 'interior'; ...
       'order_fem_wall', C_.purple, 'wall'};
hd = gobjects(0);
for s = 1:3
    m = strcmp(T.kind, srs{s, 1});
    nc = T.Nc(m);  vv = T.value(m);
    [nc, ix] = sort(nc);  vv = vv(ix);
    hd(end + 1) = plot(axD, log2(nc), vv, '-o', 'Color', srs{s, 2}, 'LineWidth', 0.85, ...
         'MarkerSize', 3.6, 'MarkerFaceColor', 'w');
end
% 单条 -2 斜率参考线，锚在 axis 序列首点
m = strcmp(T.kind, srs{1, 1});
nc = T.Nc(m);  vv = T.value(m);
[nc, ix] = sort(nc);  vv = vv(ix);
hgD = plot(axD, log2(nc), vv(1) .* 2 .^ (-2 * (log2(nc) - log2(nc(1)))), '--', ...
     'Color', C_.gold, 'LineWidth', 0.8);
xlim(axD, [4.2 8.9]);  ylim(axD, [5e-7 4e-3]);
set(axD, 'XTick', log2([25 100 400]), 'XTickLabel', {'25','100','400'}, ...
         'YTick', [1e-6 1e-4]);
xlabel(axD, 'N_c');  ylabel(axD, 'max|C - C_a_n_a|');
title(axD, '(d) analytic error', 'FontWeight', 'normal', 'HorizontalAlignment', 'left');
% 同 (c)：原 southwest 图例的三条示例线段与三条数据线在同一像素带重合，移到
% northeast。本条目的四条一次排不下：两条数据带之外本面板只剩 3.9 个数量级的
% 动态范围，四行单列图例高占面板 40%、而东北角在该宽度处的净空只有 41%；
% 两列则宽占 88%，必压上左侧纵轴刻度。
% 故图例只留三条位置线：本面板的黄金虚线与 (c) 是同一条参考线、同色同型，
% 图例已在 (c) 出面，此处重复不增加信息。示例线段再由默认 30 pt 收到 12 pt，
% 把图例宽从 58% 压到 44%，在东北角取得余量。
lgD = legend(axD, hd, {'axis', 'interior', 'wall'}, 'Location', 'northeast', ...
             'FontSize', 6.5, 'Box', 'off', 'Color', 'none');
lgD.AutoUpdate = 'off';
lgD.ItemTokenSize = [12 6];
style_ax(axD, FS);

% ======================= 落盘 ======================================
png = fullfile(OUT, 'fig18_crosscheck.png');
tif = fullfile(OUT, 'fig18_crosscheck.tif');
exportgraphics(fh, png, 'Resolution', 600, 'BackgroundColor', 'white');
exportgraphics(fh, tif, 'Resolution', 600, 'BackgroundColor', 'white');
d = dir(png);  e = dir(tif);
fprintf('  -> %-28s %7.0f kB\n', d.name, d.bytes / 1024);
fprintf('  -> %-28s %7.0f kB\n', e.name, e.bytes / 1024);
close(fh);
end

% ---------------- 公用（与 figs_matlab.m 逐位一致） ----------------
function A = warm_anchors()
A = [0.980 0.941 0.651;      % 浅黄 #FAF0A6
     1.000 0.780 0.714;      % 粉的浅档 #FFC7B6
     1.000 0.624 0.608;      % 粉   #FF9F9B
     0.702 0.624 0.859;      % 淡紫 #B39FDB
     0.490 0.435 0.659];     % 深紫 #7D6FA8
end

function c = ramp_from(A, n)
q = linspace(0, 1, n).';  x = linspace(0, 1, size(A, 1));
c = [interp1(x, A(:, 1), q), interp1(x, A(:, 2), q), interp1(x, A(:, 3), q)];
end

function c = seq_cmap()
c = ramp_from(warm_anchors(), 220);
end

function style_ax(ax, fs)
if nargin < 2 || isempty(fs), fs = 7; end
set(ax, 'FontName', 'Microsoft YaHei', 'FontSize', fs, 'LineWidth', 0.4, ...
    'TickDir', 'in', 'TickLength', [0.012 0.012], 'XColor', [0.29 0.29 0.29], ...
    'YColor', [0.29 0.29 0.29], 'ZColor', [0.29 0.29 0.29], 'GridLineStyle', 'none');
grid(ax, 'off');
end
