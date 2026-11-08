# -*- coding: utf-8 -*-
# 用法：Rscript 出图_R绘制.R  [图名...]   不传参 = 全画
# Rscript 子进程默认只看得到系统库，须显式补上 D 盘用户库，否则 showtext/Rcpp 等“装了却找不到”
# 仓库根目录：按脚本自身位置定位，克隆到任何路径都能运行
.REPO_ROOT <- local({
  a <- commandArgs(trailingOnly = FALSE)
  m <- grep("^--file=", a, value = TRUE)
  if (length(m)) dirname(normalizePath(sub("^--file=", "", m[1]), mustWork = FALSE)) else getwd()
})
.REPO_ROOT <- dirname(.REPO_ROOT)

.libPaths(unique(c("D:/claude项目专属/R-library/4.5", "D:/claude项目专属/R-library",
                   .libPaths())))
suppressPackageStartupMessages({
  library(ggplot2); library(patchwork); library(scales); library(ggdist)
  library(ggridges); library(showtext); library(sysfonts)
})
FD   <- file.path(.REPO_ROOT, "data", "processed", "figdata")
ROOT <- .REPO_ROOT
# 中文字体改回 Microsoft YaHei（库卡 EDA 样张 §1 定稿骨架原方）。原用 NotoSansSC-VF.ttf
# 是可变字体、fvar 默认实例 wght=100(Thin)，showtext 取默认实例 ⇒ 全部图文字笔画过细；
# 文字像素核心仍是规范的 #4A4A4A，"浅"来自字重而非颜色。
font_add("nsans",
         regular = "C:/Windows/Fonts/msyh.ttc",
         bold    = "C:/Windows/Fonts/msyhbd.ttc")
showtext_auto(); showtext_opts(dpi = 600)

LIT <- c(blue = "#A1C9F4", red = "#FF9F9B", yellow = "#FAF0A6",
         green = "#8DE5A1", purple = "#B39FDB")
MUT <- c(blue = "#5E84B9", red = "#C27472", yellow = "#C7B84C",
         green = "#4F9E67", purple = "#7D6FA8")

# 轴系三色（EDA 样张 §1 定稿：框浅灰、刻度中灰、格头略深，一律不加粗）
AX  <- "#8A8A8A"   # 全框 / 轴线 / 刻度线
TXT <- "#4A4A4A"   # 刻度数字 / 轴标题
TTL <- "#3C3C3C"   # 面板标题 / 格头

# 浅灰全框（EDA 样张 L4：多面板需格子边界）+ 白底显式声明（防 grey92 灰底）
TH <- theme_bw(base_family = "nsans", base_size = 9) +
  theme(panel.grid        = element_blank(),
        panel.border      = element_rect(colour = AX, fill = NA, linewidth = 0.38),
        panel.background  = element_rect(fill = "white", colour = NA),
        plot.background   = element_rect(fill = "white", colour = NA),
        axis.line         = element_blank(),
        axis.ticks        = element_line(colour = AX, linewidth = 0.38),
        axis.ticks.length = unit(-1.6, "pt"),
        axis.text         = element_text(colour = TXT, size = 8),
        axis.title        = element_text(colour = TXT, size = 9),
        legend.key        = element_blank(),
        legend.background = element_blank(),
        legend.title      = element_text(size = 8.5, colour = TXT),
        legend.text       = element_text(size = 8, colour = TXT),
        legend.margin     = margin(0, 0, 0, 0),
        plot.title        = element_text(size = 9, colour = TTL, hjust = 0, margin = margin(b = 3)),
        plot.margin       = margin(4, 4, 3, 3))

save_png <- function(p, path, w_mm, h_mm) {
  ggsave(path, p, width = w_mm / 25.4, height = h_mm / 25.4,
         dpi = 600, bg = "white", limitsize = FALSE)
  cat(sprintf("  -> %-26s %7.0f kB\n", basename(path), file.size(path) / 1024))
}

# 含水率 C 的顺序色阶：锚点全部取自图14 那套五色淡彩板（浅黄/粉/紫三支），
# 路径 近白 → 浅黄 → 粉浅 → 粉 → 淡紫 → 深紫，亮度单调递减 ⇒ 不产生假边界。
# 锚点与 MATLAB 侧 figs_matlab.m 的 warm_anchors() 逐位一致（R/MATLAB 两路出图必须同色）。
WARM <- function(n = 8, lo = "#FDFBE9")
  colorRampPalette(c(lo, "#FAF0A6", "#FFC7B6", "#FF9F9B", "#B39FDB", "#7D6FA8"))(n)

# 顺序型填充色：跨图统一（浅→深）
SEQ <- function(n = 8) WARM(n)

# 离散场填充的公共标度（两处时空场共用，保证跨图配色一致）
# labels 默认 waiver() = 显示分档区间；显式传 NULL 会把全部键名静默清空（色阶失去标度），勿用。
fill_field <- function(n = 8, labels = waiver()) {
  scale_fill_manual(values = SEQ(n), drop = FALSE, name = "C / (kg/kg)",
                    labels = labels,
                    guide = guide_legend(reverse = TRUE, keyheight = unit(5, "pt"),
                                         keywidth = unit(7, "pt")))
}

# 时间语义色阶（绿支）：四锚点亮度 236→205→137→92 严格递减，
# 顺序色阶的合法性判据是"亮度逐档递减"而非色相数（vault 顺序色阶换色卡）。
TGRN <- function(n = 64)
  colorRampPalette(c("#D8F3DF", LIT[["green"]], MUT[["green"]], "#2F6B47"))(n)

# 五色谱（全色相顺序色阶）：淡彩板五个色相各占一站，按**亮度降序**排成
#   浅黄236.8 → 淡绿205.4 → 淡蓝195.6 → 淡粉179.1 → 淡紫167.6 → 深紫118.1
# 库卡判据只要求"亮度逐档严格递减"，色相数不限 —— 故五色相仍合法（不是彩虹色阶：
# 彩虹色阶的毛病是亮度非单调，这里逐档都在降、无反弹、无假边界）。
FIVE <- function(n = 64)
  colorRampPalette(c("#FDFBE9", "#FAF0A6", "#8DE5A1", "#A1C9F4",
                     "#FF9F9B", "#B39FDB", "#7D6FA8"))(n)

# 出样张前量亮度并断言单调，肉眼"看着舒服"不能代替这一步。
# col2rgb 已是 0–255，不再乘 255（多乘一次只是把数字放大 255 倍，判据不变但打印值失真）。
chk_ramp <- function(cols, tag) {
  m <- col2rgb(cols)
  lv <- 0.2126 * m[1, ] + 0.7152 * m[2, ] + 0.0722 * m[3, ]
  stopifnot(all(diff(lv) < 0))
  cat(sprintf("  [%s] 亮度 %s 单调递减\n", tag, paste(round(lv), collapse = "→")))
}

# D(C) 镜像：与 公共内核/common.py 的 props(case=2) 逐字一致（问题一=附录2 固定物性）
# D = 7.0e-9 * exp(max(-0.89/C, -700))  [m^2/s]；用于由图5 存储剖面反算失水通量。
D_OF_C <- function(C) 7.0e-9 * exp(pmax(-0.89 / C, -700))

FIG <- list()

# ---------------- 图2 环境工况的云雨图（建模动机证据） ----------------
# 形式（2026-09-13 用户选定）：单张云雨图。每组左侧抖动原始点、中间窄箱线、右侧半小提琴，
# 把 241 个环境采样按 1 h 切成四段。要看的不是均值也不是极值，而是**组内变异的塌缩**：
# 爬升段组内剧烈上行（很散），平台段整组缩成一束。变异塌缩本身就是"平台段可用作稳态
# 外推"的视觉证据 —— 这和"看一条折线爬到顶"是不同的信息。
# 配色按物理量分派（库卡《顺序色阶换色》§2）：T∞ 走蓝支、C∞ 走粉支；两行用 facet 分栏，
# 栏头即变量名，故不再另设图例（图例会与栏头重复）。
FIG$env_radius <- function() {
  e <- read.csv(file.path(FD, "env_att1.csv"))
  e$g <- cut(e$t_s, breaks = c(-1, 3600, 7200, 10800, 14400),
             labels = c("0–1", "1–2", "2–3", "3–4"))

  # 每组变异指标机器重算（概括性断言必须重算，不靠肉眼估）
  st <- function(x) c(n = length(x), sd = sd(x), cv = sd(x) / mean(x))
  cat("  [工况] 逐时段 T∞  (n, sd, CV):\n"); print(round(do.call(rbind, tapply(e$T_amb_C, e$g, st)), 6))
  cat("  [工况] 逐时段 C∞  (n, sd, CV):\n"); print(round(do.call(rbind, tapply(e$C_amb_kgkg, e$g, st)), 8))

  qT <- "环境温度 T∞ / °C"; qC <- "环境含湿量 C∞ / (kg/kg)"
  lg <- rbind(data.frame(g = e$g, v = e$T_amb_C, q = qT),
              data.frame(g = e$g, v = e$C_amb_kgkg, q = qC))
  # 分组轴必须是**离散**的：x、y 都连续时 ggplot 推不出哪根是分组轴，会静默把 y
  # 当分组、把 x 当数值画成一根横贯全宽的箱体（与 geom_col 那个坑同源）。
  # 两处水平也都显式定序 —— facet/轴默认按字符串排，"含"会排到"温"前面。
  lg$q <- factor(lg$q, levels = c(qT, qC))
  lg$g <- factor(lg$g, levels = c("0–1", "1–2", "2–3", "3–4"))
  # 手动标度的 names 必须逐字等于数据里的因子水平（= qT/qC 原串）——名字对不上时
  # ggplot 只报一句 "No shared levels found"，然后静默把整层涂成默认灰/丢掉。
  cmap <- setNames(c(unname(MUT[["blue"]]), unname(MUT[["red"]])), c(qT, qC))
  fmap <- setNames(c(unname(LIT[["blue"]]), unname(LIT[["red"]])), c(qT, qC))

  # 三件套横向排开互不遮挡：抖点居左（贴组心）、窄箱右移 0.20、半小提琴再右移到 0.32。
  # 离散轴上 position_nudge 仍按数值偏移生效，故不必退回连续轴。
  p <- ggplot(lg, aes(g, v)) +
    geom_point(aes(colour = q), size = 0.32, alpha = 0.55,
               position = position_jitter(width = 0.13, height = 0, seed = 1)) +
    geom_boxplot(aes(colour = q), width = 0.07, linewidth = 0.3,
                 outlier.shape = NA, fill = "white",
                 position = position_nudge(x = 0.20)) +
    stat_halfeye(aes(fill = q), side = "right", width = 0.62,
                 colour = NA, alpha = 0.85,
                 position = position_nudge(x = 0.30)) +
    scale_colour_manual(values = cmap, name = NULL) +
    scale_fill_manual(values = fmap, name = NULL) +
    scale_x_discrete(name = "采样时段 t / h",
                     expand = expansion(add = c(0.45, 0.85))) +
    facet_wrap(~q, ncol = 1, scales = "free_y") +
    labs(y = NULL) + TH +
    theme(legend.position = "none",
          panel.spacing.y = unit(7, "pt"),
          strip.background = element_blank(),
          strip.text = element_text(colour = TTL, size = 8.5, hjust = 0,
                                    margin = margin(b = 2.5)))

  save_png(p, file.path(ROOT, "results", "figures", "fig02_env_radius.png"), 152, 88)
  invisible(list(
    n_win = as.integer(table(e$g)),
    cv_T = as.numeric(tapply(e$T_amb_C, e$g, function(x) sd(x) / mean(x))),
    cv_C = as.numeric(tapply(e$C_amb_kgkg, e$g, function(x) sd(x) / mean(x))),
    sd_T = as.numeric(tapply(e$T_amb_C, e$g, sd)),
    sd_C = as.numeric(tapply(e$C_amb_kgkg, e$g, sd))))
}

# ---------------- 图20 κ 情景扫描：语义分区 + 两端渐近锚点 ----------------
# 设计（2026-09-11 用户拍板）：弱驱动区(κ<1,淡蓝) / 强驱动区(1<κ<κ_crit,淡红) 分带着色；
#   κ=0 有限端点与 κ=1 基准用锚点标死；κ_crit 画竖向渐近线并标注该处达标不可实现；
#   右轴叠放大倍数 t_d/t_d(κ=1)。信息密度最高，一眼讲清"两端形态不同"。
FIG$kappa <- function() {
  k  <- read.csv(file.path(FD, "kappa_scan.csv"))
  # ⚠️ 必须用未四舍五入的平台均值：0.15/0.04999 = 3.0006（错），0.15/0.04998754 = 3.0007477（对）
  cplat <- jsonlite::fromJSON(file.path(FD, "radius_fit.json"))$C_plat_kgkg
  kc <- 0.15 / cplat                       # 平台含湿量本身越过达标线之处，可解析算出
  d  <- k[!is.na(k$td_h) & k$censored == 0, ]
  t0 <- d$td_h[d$kappa == 0]               # 左端有限端点
  t1 <- d$td_h[d$kappa == 1]               # 基准（生产口径）
  ymax <- max(d$td_h)
  xmax <- kc + 0.34

  p <- ggplot(d, aes(kappa, td_h)) +
    # —— 语义分区：弱驱动 / 强驱动（淡彩，不压曲线）——
    annotate("rect", xmin = -Inf, xmax = 1, ymin = -Inf, ymax = Inf,
             fill = LIT[["blue"]], alpha = 0.28) +
    annotate("rect", xmin = 1, xmax = kc, ymin = -Inf, ymax = Inf,
             fill = LIT[["red"]], alpha = 0.26) +
    # —— 两条渐近参照 ——
    geom_hline(yintercept = t0, linetype = "22",
               colour = MUT[["blue"]], linewidth = 0.4) +
    geom_vline(xintercept = kc, linetype = "22",
               colour = MUT[["red"]], linewidth = 0.45) +
    # —— 主曲线 ——
    geom_line(colour = MUT[["blue"]], linewidth = 0.6) +
    geom_point(colour = MUT[["blue"]], size = 0.85) +
    # —— 两个锚点：κ=0 有限端点（实心）· κ=1 基准（空心）——
    geom_point(data = d[d$kappa == 0, ], colour = MUT[["blue"]],
               size = 1.7, shape = 16) +
    geom_point(data = d[d$kappa == 1, ], shape = 21, fill = "white",
               colour = MUT[["red"]], size = 1.7, stroke = 0.5) +
    # —— 右端发散箭头 ——
    annotate("segment", x = kc - 0.13, xend = kc - 0.02,
             y = t1 * 1.55, yend = t1 * 2.4,
             arrow = arrow(length = unit(1.6, "pt"), type = "closed"),
             colour = MUT[["red"]], linewidth = 0.4) +
    scale_x_continuous(limits = c(-0.06, xmax), breaks = c(0, 0.5, 1, 1.5, 2, 2.5, 3)) +
    scale_y_continuous(limits = c(0, ymax * 1.16),
                       sec.axis = sec_axis(~ . / t1, name = "放大倍数  t_d / t_d(κ=1)",
                                           breaks = c(1, 2, 3))) +
    labs(x = "环境含湿量缩放 κ（无量纲）", y = "达标时长 t_d / h") +
    TH + theme(axis.title.y.right = element_text(size = 8.5, colour = TXT))
  save_png(p, file.path(ROOT, "results", "figures", "fig20_kappa_scan.png"), 108, 74)
  invisible(list(kappa_crit = kc, td_kappa0 = t0, td_kappa1 = t1, td_max = ymax))
}

# ---------------- 图10 自创指标：Γ_* 与 Ψ_* 各沿自己的口径 ----------------
# Γ_* = α/D 描述烘干过程本身 ⇒ 问题三正式解（附录3、固定域），几何因子恒为 1；
# Ψ_* = (R/R0)^2 · D3/D4 描述问题三→问题四的竞争 ⇒ 问题四收缩域轨迹。
# 两条轨迹状态不同，故不画相图（相图会强行把两个口径配对），改为各画各的演化。
FIG$phase <- function() {
  g3 <- read.csv(file.path(FD, "gammapsi_q3.csv"))
  g3$t_h <- g3$t_s / 3600
  g4 <- read.csv(file.path(FD, "gammapsi_q4.csv"))
  g4$t_h <- g4$t_s / 3600
  td3 <- g3$t_h[nrow(g3)]
  td4 <- g4$t_h[nrow(g4)]
  iv  <- which.min(g3$Gamma_star); tv <- g3$t_h[iv]; gv <- g3$Gamma_star[iv]
  ic  <- which(diff(sign(g4$Psi_star - 1)) != 0)[1]
  tc  <- g4$t_h[ic] + (1 - g4$Psi_star[ic]) /
         (g4$Psi_star[ic + 1] - g4$Psi_star[ic]) * (g4$t_h[ic + 1] - g4$t_h[ic])

  # 把两条一维时间序列改画成"机制空间里的路径"：色场=指标本身的分档等值，
  # 轨迹颜色=时间，形状=状态点。色场分档只覆盖轨迹自身的取值域，否则档界全落在轨迹外。
  Tg <- function(C, Tc) {
    Tk <- Tc + 273.15
    rho <- 650 + 128 * C; cp <- 1450 + 2736 * C / (C + 1); kk <- 0.21 + 0.38 * C / (C + 1)
    Dv <- exp(pmax(log(2.4e-3) - 0.45 / C - 3850 / Tk, -700))
    (kk / (rho * cp)) / Dv
  }
  # 判据场（Γ*、Ψ*）走紫支顺序阶：与全篇"判据 = 紫"同一绑定，锚点取自图14 五色淡彩板
  FILL <- colorRampPalette(c("#F7F4FC", "#E2D9F2", "#CBBDE6", "#B39FDB",
                             "#9A8AC8", "#7D6FA8"))(8)
  # 轨迹颜色编码时间，走绿支；GRN 取色板深档，与轨迹末端同色（与原设定一致）
  PATH <- c("#DDF3E2", "#8DE5A1", "#6BC285", "#4F9E67")
  GRN  <- "#4F9E67"; PUR <- MUT[["purple"]]; YEL <- LIT[["yellow"]]
  segd <- function(x, y, tt) data.frame(x = head(x, -1), y = head(y, -1),
                                        xe = tail(x, -1), ye = tail(y, -1),
                                        t = head(tt, -1))
  mkat <- function(d, ss) d[vapply(ss, function(v) which.min(abs(d$t_h - v)), 1L),
                            , drop = FALSE]
  fill_leg <- function(nm, n) scale_fill_manual(
    values = FILL[seq_len(n)], name = nm,
    guide = guide_legend(reverse = TRUE, nrow = 1, byrow = TRUE,
                         title.position = "left", keywidth = unit(0.30, "cm"),
                         keyheight = unit(0.24, "cm")))
  time_leg <- scale_colour_gradientn(
    colours = PATH, limits = c(0, td3), breaks = c(0, 12, 24, 36, 48), name = "t / h",
    guide = guide_colourbar(direction = "horizontal", title.position = "left",
                            barwidth = unit(2.0, "cm"), barheight = unit(0.22, "cm")))

  ga <- expand.grid(C = seq(0.15, 3.20, length.out = 220),
                    T_C = seq(20.0, 60.0, length.out = 220))
  ga$logG <- log10(Tg(ga$C, ga$T_C))
  brk_a <- seq(0.8, 3.0, by = 0.35)
  sa <- segd(g3$C_star, g3$T_star_C, g3$t_h)
  pa <- ggplot(ga, aes(C, T_C)) +
    geom_contour_filled(aes(z = logG), breaks = brk_a) +
    geom_contour(aes(z = logG), breaks = brk_a, colour = "white", linewidth = 0.20) +
    geom_segment(data = sa, aes(x = x, y = y, xend = xe, yend = ye, colour = t),
                 linewidth = 0.9, lineend = "round") +
    geom_segment(data = sa[12, , drop = FALSE], aes(x = x, y = y, xend = xe, yend = ye),
                 inherit.aes = FALSE, linewidth = 0.9, colour = GRN,
                 arrow = arrow(length = unit(1.7, "mm"), type = "closed")) +
    geom_segment(data = sa[150, , drop = FALSE], aes(x = x, y = y, xend = xe, yend = ye),
                 inherit.aes = FALSE, linewidth = 0.9, colour = GRN,
                 arrow = arrow(length = unit(1.7, "mm"), type = "closed")) +
    geom_point(data = mkat(g3, c(6, 24)), aes(C_star, T_star_C),
               shape = 21, size = 1.5, stroke = 0.3, fill = YEL, colour = GRN) +
    geom_point(data = g3[1, , drop = FALSE], aes(C_star, T_star_C),
               shape = 22, size = 1.5, stroke = 0.3, fill = YEL, colour = GRN) +
    geom_point(data = g3[iv, , drop = FALSE], aes(C_star, T_star_C),
               shape = 21, size = 2.6, stroke = 0.55, fill = "white", colour = GRN) +
    fill_leg(expression(log[10] * Gamma["*"]), length(brk_a) - 1) + time_leg +
    scale_x_continuous(limits = c(0.05, 3.20),
                       breaks = c(0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)) +
    scale_y_continuous(limits = c(20, 60), breaks = c(25, 30, 35, 40, 45, 50, 55)) +
    labs(x = expression("C / (kg kg"^-1 * ")"), y = expression("T / " * degree * C)) + TH

  g4$G <- (g4$R_cm / 2.0)^2
  g4$P <- g4$D3_over_D4
  ip <- which.min(abs(g4$Psi_star - 1))
  gb <- expand.grid(G = seq(0.26, 1.12, length.out = 180),
                    P = seq(1.40, 6.60, length.out = 180))
  gb$logP <- log10(gb$G) + log10(gb$P)
  brk_b <- seq(-0.5, 1.0, by = 0.3)
  sb <- segd(g4$G, g4$P, g4$t_h)
  pb <- ggplot(gb, aes(G, P)) +
    geom_contour_filled(aes(z = logP), breaks = brk_b) +
    geom_contour(aes(z = logP), breaks = brk_b, colour = "white", linewidth = 0.20) +
    geom_contour(aes(z = logP), breaks = 0, colour = PUR, linewidth = 0.85) +
    geom_segment(data = sb, aes(x = x, y = y, xend = xe, yend = ye, colour = t),
                 linewidth = 0.9, lineend = "round") +
    geom_segment(data = sb[40, , drop = FALSE], aes(x = x, y = y, xend = xe, yend = ye),
                 inherit.aes = FALSE, linewidth = 0.9, colour = GRN,
                 arrow = arrow(length = unit(1.7, "mm"), type = "closed")) +
    geom_segment(data = sb[400, , drop = FALSE], aes(x = x, y = y, xend = xe, yend = ye),
                 inherit.aes = FALSE, linewidth = 0.9, colour = GRN,
                 arrow = arrow(length = unit(1.7, "mm"), type = "closed")) +
    geom_point(data = mkat(g4, c(6, 24, 48)), aes(G, P),
               shape = 21, size = 1.5, stroke = 0.3, fill = YEL, colour = GRN) +
    geom_point(data = g4[1, , drop = FALSE], aes(G, P),
               shape = 22, size = 1.5, stroke = 0.3, fill = YEL, colour = GRN) +
    geom_point(data = g4[ip, , drop = FALSE], aes(G, P),
               shape = 21, size = 2.6, stroke = 0.55, fill = "white", colour = GRN) +
    fill_leg(expression(log[10] * Psi["*"]), length(brk_b) - 1) + time_leg +
    scale_x_continuous(limits = c(0.26, 1.12), breaks = c(0.4, 0.6, 0.8, 1.0)) +
    scale_y_continuous(limits = c(1.4, 6.6), breaks = c(2, 3, 4, 5, 6)) +
    labs(x = expression("G = (R/R"[0] * ")"^2),
         y = expression("P = D"[3] * "/D"[4])) + TH

  p <- (pa | pb) + plot_layout(guides = "collect")  &
    theme(legend.position = "bottom", legend.box = "vertical",
          legend.box.just = "center", legend.spacing.y = unit(0.5, "pt"))
  save_png(p, file.path(ROOT, "results", "figures", "fig10_indicator_phase.png"), 172, 92)
  invisible(list(Gamma0 = g3$Gamma_star[1], t_valley_h = tv, Gamma_valley = gv,
                 Gamma_end = g3$Gamma_star[nrow(g3)],
                 Gamma_end_over_start = g3$Gamma_star[nrow(g3)] / g3$Gamma_star[1],
                 Gamma_end_over_valley = g3$Gamma_star[nrow(g3)] / gv,
                 td_q3_h = td3,
                 Psi0 = g4$Psi_star[1],
                 Psi_24h = g4$Psi_star[which.min(abs(g4$t_h - 24))],
                 t_cross_h = tc, Psi_end = g4$Psi_star[nrow(g4)], td_q4_h = td4))
}

# ---------------- 辅助图（不入正文）灵敏度：参数不确定度的输出分布族（蒙特卡洛） ----------------
# 只画 MC 样本的分布形态；中位数与 95% 区间宽由本函数回传，供正文/图注引用，
# 不写进图内（库卡「图例文字不入图」）。确定性 ±5% 扫描只留下三个标量诊断：
# ① S_p 口径自校 ② 幂律一阶近似的最大相对偏差 ③ MC 回归弹性 vs 表内 S_p。
FIG$sens <- function() {
  s <- read.csv(file.path(FD, "sensitivity.csv"))
  base0 <- setNames(s$td_h[s$param == "base"], s$question[s$param == "base"])
  m <- read.csv(file.path(FD, "mc_sensitivity.csv"))
  m$td0 <- base0[m$question]
  m$rel <- (m$td_h - m$td0) / m$td0 * 100
  m$qlab <- factor(c(q3 = "问题三（固定域）", q4 = "问题四（收缩域）")[m$question],
                   c("问题四（收缩域）", "问题三（固定域）"))

  spv <- s[!is.na(s$S_p), c("question", "param", "S_p")]   # S_p 只写在 +5% 行
  lo <- s[s$param != "base" & s$delta_pct < 0, c("question", "param", "td_h")]
  hi <- s[s$param != "base" & s$delta_pct > 0,
          c("question", "param", "delta_pct", "td_h")]
  names(lo)[names(lo) == "td_h"] <- "td_lo"
  names(hi)[names(hi) == "td_h"] <- "td_hi"
  e <- merge(merge(merge(lo, hi, by = c("question", "param")), spv,
                   by = c("question", "param")),
             data.frame(question = names(base0), td0 = as.numeric(base0)),
             by = "question")
  # ① S_p 应对称地由 ±5% 这一对对数差分算出；② 幂律 t_d ∝ p^S_p 在该区间内的适用边界
  dev_sp <- max(abs(log(e$td_hi / e$td_lo) / log(1.05 / 0.95) - e$S_p))
  dev_pl <- max(abs(e$td0 * (1 + e$delta_pct / 100)^e$S_p / e$td_h - 1)) * 100
  # ③ 独立口径互证：MC 样本上 log t_d 对 log f_p 的回归斜率（含交互的平均弹性）
  mcS <- do.call(rbind, lapply(c("q3", "q4"), function(q) {
    d <- m[m$question == q, ]
    ks <- if (q == "q4") c("D", "hm", "h", "lam") else c("D", "hm", "h")
    b <- qr.solve(cbind(1, as.matrix(log(d[paste0("f_", ks)]))), log(d$td_h))
    data.frame(question = q, param = ks, S_mc = as.numeric(b[-1]), n = nrow(d))
  }))
  mcS <- merge(mcS, spv, by = c("question", "param"))
  dev_mc <- max(abs(mcS$S_mc - mcS$S_p))
  st <- do.call(rbind, lapply(split(m, m$question), function(d) {
    q <- quantile(d$rel, c(0.025, 0.975))
    data.frame(question = d$question[1], n = nrow(d), median_h = median(d$td_h),
               w95_h = (q[2] - q[1]) / 100 * d$td0[1],
               rel_pct = (q[2] - q[1]) / (1 + median(d$rel) / 100))
  }))

  p <- ggplot(m, aes(rel, qlab, fill = qlab, colour = qlab)) +
    stat_halfeye(side = "top", justification = -0.22, scale = 0.6, slab_alpha = 0.55,
                 .width = 0.95, point_interval = median_qi,
                 interval_size_range = c(0.4, 0.65), point_size = 1.35,
                 show.legend = FALSE) +
    stat_dots(side = "bottom", justification = 0.90, dotsize = 0.30,
              quantiles = 110, alpha = 0.45, show.legend = FALSE) +
    geom_vline(xintercept = 0, linetype = "22", colour = "grey35", linewidth = 0.4) +
    facet_wrap(~qlab, ncol = 1, scales = "free_y") +
    scale_fill_manual(values = c("问题三（固定域）" = LIT[["blue"]],
                                 "问题四（收缩域）" = LIT[["red"]])) +
    scale_colour_manual(values = c("问题三（固定域）" = MUT[["blue"]],
                                   "问题四（收缩域）" = MUT[["red"]])) +
    scale_x_continuous(breaks = c(-5, 0, 5), limits = c(-8.4, 8.4), expand = c(0, 0)) +
    scale_y_discrete(expand = expansion(add = 0.26)) +
    labs(x = expression("达标时长 " * t[d] * " 相对生产口径基准的偏差 / %"),
         y = NULL) +
    TH + theme(strip.text = element_blank(), panel.spacing = unit(3.6, "pt"),
               legend.position = "none")

  save_png(p, file.path(ROOT, "results", "figures", "aux_mcdist_sens.png"), 84, 49)
  invisible(list(max_sp_check = dev_sp, max_pl_vs_calc_pct = dev_pl,
                 max_mc_vs_det = dev_mc, mc_elasticity = mcS, dist_stats = st))
}

# ---------------- 图17 收敛性：空间阶 + 时间阶（双对数） ----------------
FIG$conv <- function() {
  cv <- read.csv(file.path(FD, "convergence.csv"))
  ds <- cv[cv$kind == "space", ]; ds <- ds[order(ds$x), ]
  dt <- cv[cv$kind == "time",  ]; dt <- dt[order(dt$x), ]
  # 时间序固定在单网格，被该网格的空间误差地板支配；拟合 err = A*h^p + E 后画去地板残差
  ft <- nls(err ~ A * x^p + E, data = dt,
            start = list(A = 1.9e-5, p = 1, E = 4.5e-5))
  cf <- coef(ft)
  dt$err <- dt$err - cf[["E"]]

  panel <- function(d, xlab, ylab, ref) {
    xr <- range(d$x)
    rl <- data.frame(x = 10^seq(log10(xr[1]), log10(xr[2]), length.out = 60))
    rl$y <- d$err[1] * (rl$x / d$x[1])^(-ref)
    ggplot(d, aes(x, err)) +
      geom_line(data = rl, aes(x, y), linetype = "22",
                colour = "grey55", linewidth = 0.4) +
      geom_line(colour = MUT[["blue"]], linewidth = 0.5) +
      geom_point(colour = MUT[["blue"]], size = 1.2) +
      scale_x_log10() + scale_y_log10() +
      labs(x = xlab, y = ylab) + TH
  }

  p_obs <- mean(-diff(log(ds$err)) / diff(log(ds$x)))
  pa <- panel(ds, expression(N[c] * "（径向单元数）"),
              expression(max * "|" * C[num] - C[ana] * "|"), 2)
  pb <- panel(dt, expression(Delta * t * " / s"),
              expression("残差（已扣地板 E）"), 1)
  p <- pa | pb
  save_png(p, file.path(ROOT, "results", "figures", "fig17_convergence.png"), 170, 70)
  invisible(list(p_space = p_obs, p_time = cf[["p"]], E = cf[["E"]]))
}

# ---------------- 图14 格式精度的逐点剖面：节点误差山脊 + 分布迁移 ----------------
# 数据源 cand_errprof.csv：独立 P1-FEM 的精确时刻节点解与解析解在同一批节点上逐点相减
# （同网格对位，不做插值），故不引入参考栅格自身的 O(h²) 污染。
# 山脊高度按 log10(max|err|/|err|) 记账——越高表示该处越准，ξ≈0.73 的误差过零点即体现为尖峰。
# 右栏是同一批节点误差的分布随网格加密的迁移，空心圈标出轴心节点（各档分布的右端离群点）。
FIG$errprof <- function() {
  d    <- read.csv(file.path(FD, "cand_errprof.csv"))
  lvl  <- c(25, 50, 100, 200, 400)
  d$Nc <- factor(d$Nc, levels = lvl)
  d$l  <- log10(d$err)
  d$h  <- log10(max(d$err) / d$err)
  # 浅层做面、同相深档做线：面用淡彩、描边用 muted，跨图与其它图保持同一套淡彩板
  sfl <- c("25" = "#FF9F9B", "50" = "#B39FDB", "100" = "#F5E97F",
           "200" = "#A1C9F4", "400" = "#8DE5A1")
  sln <- c("25" = "#C27472", "50" = "#7D6FA8", "100" = "#C7B84C",
           "200" = "#5E84B9", "400" = "#4F9E67")

  pa <- ggplot(d, aes(x = xi, y = Nc, group = Nc, height = h, fill = Nc, colour = Nc)) +
    geom_ridgeline(alpha = 0.9, linewidth = 0.45, scale = 0.95, show.legend = FALSE) +
    scale_fill_manual(values = sfl) + scale_colour_manual(values = sln) +
    scale_y_discrete(expand = expansion(mult = c(0.02, 0.18))) +
    scale_x_continuous(breaks = seq(0, 1, 0.25)) +
    labs(x = "无量纲半径  xi = r/R", y = "径向分段数  Nc") + TH

  ax <- d[d$xi < 1e-9, ]
  pb <- ggplot(d, aes(x = l, y = Nc, fill = Nc, colour = Nc)) +
    stat_halfeye(.width = 0, point_interval = NULL, justification = -0.10,
                 slab_alpha = 0.95, slab_linewidth = 0.45, show.legend = FALSE) +
    geom_point(data = ax, size = 1.7, shape = 21, stroke = 0.6, fill = "white",
               show.legend = FALSE) +
    scale_fill_manual(values = sfl) + scale_colour_manual(values = sln) +
    scale_x_continuous(breaks = -7:-2,
                       labels = function(b) parse(text = paste0("10^", b))) +
    scale_y_discrete(expand = expansion(mult = c(0.02, 0.18))) +
    labs(x = "节点误差  |数值 - 解析|", y = "径向分段数  Nc") + TH

  save_png(pa | pb,
           file.path(ROOT, "results", "figures", "fig14_errprofile_ridgeline.png"), 183, 72)
  invisible(list(med = tapply(d$l, d$Nc, median), n_axis = nrow(ax)))
}

# ---------------- 候选 图13-A 消融归因的网格无关性（三倍数随 Nc） ----------------
# 三条曲线各自贴住自己的水平虚线＝该倍数在生产格上的取值：贴得住，归因就是模型的性质。
# 右栏把偏差放大：纵轴是相对生产格的相对差，虚线为 −1 参考斜率（一阶）。
FIG$ablgrid <- function() {
  d   <- read.csv(file.path(FD, "ablation_grid.csv"), fileEncoding = "UTF-8-BOM")
  d   <- d[order(d$Nc), ]
  nm  <- c("几何倍数", "物性倍数", "交互因子")
  key <- c("G_geo", "P_prop", "I_int")
  LGL <- c("几何倍数" = "#8DE5A1", "物性倍数" = "#B39FDB", "交互因子" = "#A1C9F4")
  DKL <- c("几何倍数" = "#4F9E67", "物性倍数" = "#7D6FA8", "交互因子" = "#5E84B9")
  lg  <- do.call(rbind, lapply(seq_along(nm), function(i)
    data.frame(Nc = d$Nc, f = d[[key[i]]], s = nm[i])))
  lg$s <- factor(lg$s, levels = nm)
  rf   <- data.frame(y = vapply(key, function(k) d[[k]][nrow(d)], 0.0),
                     s = factor(nm, levels = nm))
  fine <- max(d$Nc)
  dv   <- do.call(rbind, lapply(seq_along(nm), function(i) {
    f <- d[[key[i]]]; data.frame(Nc = d$Nc[d$Nc < fine],
                                 rel = abs(f[d$Nc < fine] - f[d$Nc == fine]) / f[d$Nc == fine],
                                 s = nm[i])
  }))
  dv$s <- factor(dv$s, levels = nm)
  b8   <- min(dv$rel[dv$Nc == 800])
  ref  <- data.frame(Nc = c(200, 800), rel = b8 * (c(200, 800) / 800)^(-1))

  pa <- ggplot(lg, aes(Nc, f, colour = s)) +
    geom_hline(data = rf, aes(yintercept = y, colour = s), linetype = "22",
               linewidth = 0.35, alpha = 0.9) +
    geom_line(linewidth = 0.55) +
    geom_point(aes(fill = s), shape = 21, size = 1.7, stroke = 0.45, show.legend = FALSE) +
    scale_fill_manual(values = LGL) + scale_colour_manual(values = DKL, name = NULL) +
    scale_x_log10(breaks = c(200, 400, 800, 1600)) +
    scale_y_log10(breaks = c(0.4, 0.5, 0.7, 1, 1.5, 2)) +
    labs(x = expression(N[c]), y = "倍数（对数轴）") + TH +
    theme(legend.position = c(0.03, 0.90), legend.justification = c(0, 1),
          legend.key.height = unit(7, "pt"), legend.spacing.y = unit(0.6, "pt"))

  pb <- ggplot(dv, aes(Nc, rel, colour = s)) +
    geom_line(data = ref, aes(Nc, rel), inherit.aes = FALSE, linetype = "22",
              colour = "grey55", linewidth = 0.4) +
    geom_line(linewidth = 0.55) +
    geom_point(aes(fill = s), shape = 21, size = 1.7, stroke = 0.45, show.legend = FALSE) +
    scale_fill_manual(values = LGL) + scale_colour_manual(values = DKL, name = NULL) +
    scale_x_log10(breaks = c(200, 400, 800)) +
    scale_y_log10(limits = c(3e-5, 1.2e-3), breaks = c(5e-5, 1e-4, 2e-4, 5e-4, 1e-3)) +
    labs(x = expression(N[c]), y = "与生产格的相对差") + TH + theme(legend.position = "none")

  save_png(pa | pb, file.path(ROOT, "results", "figures", "cand_abl_grid.png"), 183, 72)
  invisible(list(G = rf$y[1], P = rf$y[2], I = rf$y[3]))
}

# ---------------- 候选 图13-B 交互的机理：剖面束 + 内部降幅占比 ----------------
# 剖面束取自"轴心含水率同为 1.0"的共同状态（同一状态才可比，不按同一钟表时间比）；
# 横轴按各自当时的 R(λ) 无量纲化，故五条曲线的右端点齐在 ξ=1，表面值随 λ 上抬＝内部降幅收窄。
# 右栏 φ=(C_core−C_surf)/(C_core−C_inf) 即内部降幅占总降幅的比重，两物性各一条。
FIG$ablprof <- function() {
  d  <- read.csv(file.path(FD, "ablation_profile.csv"), fileEncoding = "UTF-8-BOM")
  NN <- 41; xi <- seq(0, 1, length.out = NN); cn <- sprintf("C%02d", 0:(NN - 1))
  lam <- sort(unique(d$lam))
  RAMP <- c("#C6DCF2", "#A1C9F4", "#7FA8D8", "#5E84B9", "#3A5680")
  names(RAMP) <- as.character(lam)
  cf <- d[d$case == 4, ]
  pf <- do.call(rbind, lapply(seq_len(nrow(d)), function(i) {
    data.frame(xi = xi, C = as.numeric(d[i, cn]),
               lam = factor(d$lam[i], levels = lam),
               mt = factor(as.character(d$case[i]), levels = c("3", "4")))
  }))
  MT <- c("3" = "附录3 物性", "4" = "附录4 物性")
  cv <- d
  cv$q <- factor(as.character(cv$lam), levels = lam)

  pa <- ggplot(pf, aes(xi, C, colour = lam)) +
    geom_line(linewidth = 0.6) +
    geom_hline(yintercept = 0.15, linetype = "22", colour = "grey45", linewidth = 0.4) +
    facet_wrap(~ mt, ncol = 1, labeller = labeller(mt = MT)) +
    scale_colour_manual(values = RAMP, name = expression(lambda)) +
    scale_x_continuous(breaks = seq(0, 1, 0.25)) +
    scale_y_continuous(limits = c(0, 1.05), expand = c(0, 0)) +
    labs(x = expression(xi == r / R), y = "含水率 C / (kg/kg)") + TH +
    theme(legend.position = "bottom", legend.margin = margin(0, 0, 0, 0),
          legend.key.width = unit(15, "pt"), legend.title.position = "left",
          strip.background = element_blank(),
          strip.text = element_text(size = 8.5, colour = TTL),
          panel.spacing.x = unit(5, "pt")) +
    guides(colour = guide_legend(nrow = 1, title.position = "left"))

  MAT <- c("3" = "#5E84B9", "4" = "#7D6FA8")
  cv$mt <- factor(as.character(cv$case), levels = c("3", "4"))
  pb <- ggplot(cv, aes(lam, phi, colour = mt)) +
    geom_line(linewidth = 0.6) +
    geom_point(aes(fill = mt), shape = 21, size = 2.0, stroke = 0.5) +
    scale_fill_manual(values = c("3" = "#A1C9F4", "4" = "#B39FDB"), labels = MT, name = NULL) +
    scale_colour_manual(values = MAT, labels = MT, name = NULL) +
    scale_x_continuous(breaks = lam) +
    scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    labs(x = expression("收缩幅度 " * lambda), y = expression(phi == (C[c] - C[s]) / (C[c] - C[inf]))) + TH +
    theme(legend.position = c(0.02, 0.03), legend.justification = c(0, 0),
          legend.key.height = unit(7.5, "pt"), legend.spacing.y = unit(0.6, "pt"))

  save_png(pa | pb, file.path(ROOT, "results", "figures", "cand_abl_prof.png"), 183, 84)
  invisible(cv[, c("case", "lam", "phi", "C_surf")])
}

# ---------------- 候选 图13-C 消融四格时空场（几何效应 = 随 τ 加宽的空楔形） ----------------
# 四格共用同一半径轴与同一填充标度：固定域两格铺满整块，收缩域两格的 r > R(t) 记空，
# 于是"收缩缩短了扩散路程"这件事表现为右侧空楔形，不需要任何图内文字；
# 楔形边缘另用 ablation_field_edge.csv 的逐帧实测 R(τ) 描一条细线（白描边保证深底上可辨）。
FBR <- c(0.05, 0.15, 0.35, 0.75, 1.40, 2.00, 2.60)   # 与图15(spacefront)同一套分箱，同一物理量跨图配色一致
FLB <- sprintf("%.2f–%.2f", FBR[-length(FBR)], FBR[-1])

FIG$ablfield <- function() {
  d  <- read.csv(file.path(FD, "ablation_field.csv"), fileEncoding = "UTF-8-BOM")
  EG <- read.csv(file.path(FD, "ablation_field_edge.csv"), fileEncoding = "UTF-8-BOM")
  lab <- c(a3fix = "附录3 物性 · 固定域", a3shr = "附录3 物性 · 收缩域",
           a4fix = "附录4 物性 · 固定域", a4shr = "附录4 物性 · 收缩域")
  d$tg  <- factor(lab[d$tag], levels = lab)
  EG    <- EG[EG$shrink == 1, ]
  EG$tg <- factor(lab[EG$tag], levels = lab)

  p <- ggplot(d, aes(r_cm, tau)) +
    geom_contour_filled(aes(z = C), breaks = FBR) +
    fill_field(length(FBR) - 1, FLB) +
    geom_contour(aes(z = C), breaks = 0.15, colour = MUT[["red"]], linewidth = 0.5) +
    geom_path(data = EG, aes(Rw_cm, tau), inherit.aes = FALSE,
              colour = "white", linewidth = 1.5) +
    geom_path(data = EG, aes(Rw_cm, tau), inherit.aes = FALSE,
              colour = "grey20", linewidth = 0.45) +
    facet_wrap(~ tg, nrow = 2) +
    scale_x_continuous(breaks = c(0, 0.5, 1, 1.5, 2)) +
    scale_y_continuous(breaks = seq(0, 1, 0.25), expand = c(0, 0)) +
    labs(x = "半径 r / cm", y = expression(tau == t / t[d])) + TH +
    guides(fill = guide_legend(reverse = TRUE, nrow = 2, byrow = TRUE,
                               keyheight = unit(4, "pt"), keywidth = unit(9, "pt"))) +
    theme(strip.background = element_blank(),
          strip.text = element_text(size = 8, colour = TTL),
          panel.spacing = unit(5, "pt"),
          legend.position = "bottom", legend.key.width = unit(16, "pt"),
          legend.title.position = "left")

  save_png(p, file.path(ROOT, "results", "figures", "cand_abl_field.png"), 168, 108)
  invisible(dim(d))
}

# ---------------- 图13 消融四格时空场（极坐标：半径 = r，极角 = 归一化时间 τ = t/t_d） ----------------
# 四格共用同一半径轴、同一分箱、同一色标。固定域两格铺满整块；收缩域两格 r > R(t) 记空，
# 外缘用逐帧实测 R(τ) 描细线（白描边保证深底可辨），于是"收缩缩短了扩散路程"只靠几何表达。
# 极角取归一化时间后四格同轴，所以格里看得见的差异不是达标时长之差，而是过程结构的差异。
FIG$ablpolar <- function() {
  da <- read.csv(file.path(FD, "ablation_field.csv"), fileEncoding = "UTF-8-BOM")
  da <- da[!is.na(da$C), ]        # 域外点(空值)不参与绘制，否则 geom_tile 会按 NA 涂灰
  EG <- read.csv(file.path(FD, "ablation_field_edge.csv"), fileEncoding = "UTF-8-BOM")
  lab <- c(a3fix = "附录3 物性 · 固定域", a3shr = "附录3 物性 · 收缩域",
           a4fix = "附录4 物性 · 固定域", a4shr = "附录4 物性 · 收缩域")
  da$th  <- 2 * pi * da$tau
  da$Cb  <- cut(da$C, breaks = FBR, include.lowest = TRUE, right = FALSE)
  da$tg  <- factor(lab[da$tag], levels = lab)
  ts <- sort(unique(da$t_s))
  d  <- da[da$t_s %in% ts[seq(1, length(ts), by = 2)], ]
  EG <- EG[EG$shrink == 1, ]
  EG$th <- 2 * pi * EG$tau
  EG$tg <- factor(lab[EG$tag], levels = lab)

  p <- ggplot(d, aes(th, r_cm, fill = Cb)) +
    geom_tile() +
    geom_contour(data = da, aes(th, r_cm, z = C), inherit.aes = FALSE,
                 breaks = 0.15, colour = MUT[["purple"]], linewidth = 0.45) +
    geom_path(data = EG, aes(th, Rw_cm), inherit.aes = FALSE,
              colour = "white", linewidth = 1.5) +
    geom_path(data = EG, aes(th, Rw_cm), inherit.aes = FALSE,
              colour = MUT[["green"]], linewidth = 0.45) +
    fill_field(length(FBR) - 1, FLB) +
    guides(fill = guide_legend(reverse = TRUE, nrow = 2, byrow = TRUE,
                               keyheight = unit(4, "pt"), keywidth = unit(9, "pt"))) +
    facet_wrap(~ tg, nrow = 1) +
    coord_polar(start = -pi / 2, direction = 1) +
    scale_x_continuous(breaks = c(0, pi / 2, pi, 3 * pi / 2),
                       labels = c("0", "0.25", "0.5", "0.75")) +
    scale_y_continuous(breaks = c(0.5, 1, 1.5, 2)) +
    labs(x = expression(tau == t / t[d] * "   （极角）"), y = "半径 r / cm") + TH +
    theme(strip.background = element_blank(),
          strip.text = element_text(size = 8, colour = TTL),
          axis.ticks.x = element_blank(),
          legend.position = "bottom", legend.key.width = unit(16, "pt"),
          legend.title.position = "left")

  save_png(p, file.path(ROOT, "results", "figures", "fig13_ablation_field.png"), 160, 74)
  invisible(dim(d))
}

# ---------------- 候选 图13-E 固定域成本景观 t_d(R, Ccr) + 真实半径扫描段 ----------------
# 两物性各一张景观：横轴半径（反向，让"由 2.0 缩到 1.20 cm"与时间同向），纵轴判据；
# 底部那一段实线即真实收缩过程所在的扫描线，两端就是两个收缩域格达标时的实测半径。
FIG$ablland <- function() {
  d  <- read.csv(file.path(FD, "ablation_landscape.csv"), fileEncoding = "UTF-8-BOM")
  d$mt <- factor(ifelse(d$case == 3, "附录3 物性", "附录4 物性"),
                 levels = c("附录3 物性", "附录4 物性"))
  xb <- sort(unique(d$R_cm)); yb <- sort(unique(d$Ccr))
  rm <- min(xb); dx <- diff(xb)[1]; dy <- diff(yb)[1]
  BL <- c(0, 10, 20, 30, 45, 60, 90, 120, 140)          # t_d 分箱：低值段加密
  d$tb <- cut(d$td_h, breaks = BL, include.lowest = TRUE, right = FALSE)
  lb <- attr(d$tb, "levels")
  lb <- sub("^\\[([0-9.]+),([0-9.]+)\\)$", "\\1–\\2", lb)

  p <- ggplot(d, aes(R_cm, Ccr, fill = tb)) +
    geom_tile(width = dx, height = dy, colour = "grey88", linewidth = 0.15) +
    scale_fill_manual(values = SEQ(length(BL) - 1), drop = FALSE,
                      name = expression(t[d] / h), labels = lb,
                      guide = guide_legend(reverse = TRUE,
                                           keyheight = unit(5, "pt"),
                                           keywidth = unit(7, "pt"))) +
    annotate("segment", x = rm, xend = max(xb), y = 0.15, yend = 0.15,
             colour = "grey15", linewidth = 0.8) +
    facet_wrap(~ mt, nrow = 1) +
    scale_x_reverse(breaks = rev(xb),
                    limits = c(min(xb) - dx / 2, max(xb) + dx / 2),
                    expand = c(0, 0)) +
    scale_y_continuous(breaks = yb, expand = c(0, 0)) +
    labs(x = "固定域半径 R / cm（由右向左＝由初始缩到最小）",
         y = expression("达标判据 " * C[cr] * " / (kg/kg)")) + TH +
    theme(strip.background = element_blank(),
          strip.text = element_text(size = 8, colour = TTL),
          panel.spacing = unit(5, "pt"),
          legend.position = "right", legend.key.height = unit(6.5, "pt"))

  save_png(p, file.path(ROOT, "results", "figures", "cand_abl_land.png"), 168, 82)
  invisible(d[d$Ccr == 0.15, ])
}

# ---------------- 候选 图13-F 乘法分解的支路对照（带宽 = 该支路的对数倍数） ----------------
# 两条路线各由一个几何支路与一个物性支路串成：走收缩域与走固定域，同一支路的带宽不同，
# 带宽差就是不可分离性。带宽按 |log10 倍数| 取，带宽相等即两因子可乘。
FIG$ablflow <- function() {
  d <- read.csv(file.path(FD, "ablation_grid.csv"), fileEncoding = "UTF-8-BOM")
  r <- d[d$Nc == max(d$Nc), ]
  A <- r$td_a3fix; B <- r$td_a3shr; Cn <- r$td_a4fix; D <- r$td_a4shr
  leg <- function(x0, t0, x1, t1, g) {
    hw <- 0.18 * abs(log10(t1 / t0))
    data.frame(x = c(x0, x1, x1, x0),
               y = c(t0 * 10^(-hw), t1 * 10^(-hw), t1 * 10^(hw), t0 * 10^(hw)),
               grp = g)
  }
  rb <- rbind(
    leg(1, A, 2, B,  "几何 · 走收缩域"),
    leg(2, B, 3, D,  "物性 · 走收缩域"),
    leg(1, A, 2, Cn, "物性 · 走固定域"),
    leg(2, Cn, 3, D, "几何 · 走固定域"))
  rb$grp <- factor(rb$grp, levels = c("几何 · 走收缩域", "几何 · 走固定域",
                                      "物性 · 走收缩域", "物性 · 走固定域"))
  FL <- c("几何 · 走收缩域" = "#8DE5A1", "几何 · 走固定域" = "#C6EECB",
          "物性 · 走收缩域" = "#B39FDB", "物性 · 走固定域" = "#D7CCEC")
  nd <- data.frame(x = c(1, 2, 2, 3), y = c(A, B, Cn, D))

  p <- ggplot() +
    geom_polygon(data = rb, aes(x, y, fill = grp), alpha = 0.95, colour = NA) +
    geom_point(data = nd, aes(x, y), shape = 21, size = 1.9, stroke = 0.5,
               fill = "white", colour = "grey20") +
    scale_fill_manual(values = FL, name = NULL) +
    scale_x_continuous(breaks = c(1, 2, 3),
                       labels = c("基线", "加入一个因子", "两个因子"),
                       limits = c(0.9, 3.1)) +
    scale_y_log10(breaks = c(20, 30, 50, 70, 100, 130)) +
    labs(x = NULL, y = expression("达标时长 " * t[d] * " / h")) + TH +
    theme(legend.position = "right", legend.key.height = unit(8, "pt"),
          legend.spacing.y = unit(1.2, "pt"), panel.grid = element_blank())

  save_png(p, file.path(ROOT, "results", "figures", "cand_abl_flow.png"), 168, 78)
  invisible(c(A = A, B = B, Cn = Cn, D = D))
}

# ---------------- 图5 问题一：固定域短时热–湿响应（0–1800 s） ----------------
# 形式（2026-09-13 用户选定：换形式、不与既有图重复）：
#   左 = 失水通量矢量场 J = -D(C)·dC/dr（由 30 s 存储剖面一阶差商反算，不另跑求解器），
#   右 = 径向含水率剖面族。
#   配色（用户 2026-09-13 纠正）：走全篇统一的**多色系**顺序色阶 SEQ = 图14 那套浅黄→粉→紫
#   五支，且颜色重新绑回物理量**含水率 C**（与图13/图14 同义：紫=高含湿、黄=已烘干）。
#   上一版把时间映射到单色绿支，与全篇色阶脱钩 —— 颜色一旦不绑定物理量，跨图就不可比。
#   两面板同为这 8 个时刻、共用同一条 C 色阶条（左第 k 行箭头 ⇔ 右第 k 条剖面，图注写明）：
#   颜色恒定读"此处多湿"，左图箭头**长度**读 log10(J)、右图**纵坐标**读 C —— 一条通道一个量。
#   箭头方向在轴对称下恒指向表面（水分只外迁），方向不含信息、信息全在长度；J 在域内跨
#   数个数量级，故长度按 log10(J) 归一（图注须写明该缩放），否则内部箭头被表面通量压平。
FIG$q1 <- function() {
  M <- read.csv(file.path(FD, "q1_profiles.csv")); M$t_h <- M$t_s / 3600
  S <- read.csv(file.path(FD, "q1_series.csv"));   S$t_h <- S$t_s / 3600
  e <- S[nrow(S), ]

  chk_ramp(FIVE(9), "C-five")

  tt <- sort(unique(M$t_s)); rr <- sort(unique(M$r_cm))
  stopifnot(nrow(M) == length(tt) * length(rr))
  Cm <- matrix(M$C, nrow = length(tt), ncol = length(rr), byrow = TRUE)
  dr <- diff(rr / 100)
  Jm <- t(apply(Cm, 1, function(cc) -D_OF_C(cc) * c(0, diff(cc) / dr)))   # J(0)=0（轴心对称）

  # 两面板共用这 8 个时刻（左第 k 行箭头 ⇔ 右第 k 条剖面）
  ts <- seq(240, 1800, by = 240)
  stopifnot(!anyNA(match(ts, tt)))

  # 两面板同一条色阶：全域 C 的 [min, max]，与图13/图14 同族同标题
  CLIM <- c(1.50, 2.56)
  gscale <- scale_colour_gradientn(
    colours = FIVE(64), name = "C / (kg/kg)", limits = CLIM,
    breaks = seq(1.6, 2.4, 0.2),
    guide = guide_colourbar(barwidth = unit(38, "mm"), barheight = unit(3.0, "mm"),
                            title.position = "left"))

  # --- 左：失水通量矢量场（箭头终点落在采样半径上，长度向左生长 ⇒ 相邻箭头不重叠）---
  rs <- round(seq(0.2, 2.0, by = 0.15), 4)       # 13 列（轴心 J≡0，不画）
  # ⚠️ 必须 round：seq 的浮点尾巴（0.1*3 = 0.30000000000000004）匹配不上 CSV 里的 0.3，
  # match 全返回 NA 而 stopifnot 才报错；整数列（t_s）没有这个坑。
  A <- expand.grid(t_s = ts, r_cm = rs)
  A$J <- Jm[cbind(match(A$t_s, tt), match(A$r_cm, rr))]
  A$C <- Cm[cbind(match(A$t_s, tt), match(A$r_cm, rr))]
  stopifnot(!anyNA(A$J), !anyNA(A$C))
  hi <- max(A$J); lo <- hi / 1e3                 # 只映射 3 个数量级
  cat(sprintf("  [J] 峰值 %.2e；箭头长度映射窗 [%.2e, %.2e]（3 个数量级）\n", hi, lo, hi))
  A$s <- pmin(pmax((log10(pmax(A$J, lo)) - log10(lo)) / 3, 0), 1)
  A$len <- 0.008 + 0.117 * A$s                   # 数据单位 cm，上限 < 列距 0.15
  A$t_h <- A$t_s / 3600

  pa <- ggplot(A) +
    geom_segment(aes(x = r_cm - len, xend = r_cm, y = t_h, yend = t_h, colour = C),
                 arrow = arrow(ends = "last", length = unit(1.4, "pt"), type = "open"),
                 linewidth = 0.38) +
    gscale +
    scale_x_continuous(limits = c(0, 2.0), breaks = c(0, 0.5, 1.0, 1.5, 2.0),
                       expand = expansion(add = c(0.04, 0.04))) +
    scale_y_continuous(limits = c(0, 0.5), breaks = seq(0, 0.5, 0.1),
                       expand = expansion(add = c(0.012, 0.012))) +
    labs(x = "半径 r / cm", y = "时间 t / h") + TH

  # --- 右：径向剖面族（同一 C 色阶；每条曲线按自身含水率上色 ⇒ 表面黄、轴心紫的丝带族）---
  P <- do.call(rbind, lapply(ts, function(k) {
    i <- match(k, tt)
    data.frame(r_cm = rr, C = Cm[i, ], t_s = k)
  }))

  pb <- ggplot(P, aes(r_cm, C)) +
    geom_line(aes(colour = C, group = t_s), linewidth = 0.5) +
    gscale +
    scale_x_continuous(limits = c(0, 2.0), breaks = c(0, 0.5, 1.0, 1.5, 2.0),
                       expand = expansion(add = c(0.04, 0.04))) +
    scale_y_continuous(limits = CLIM, breaks = seq(1.6, 2.4, 0.2),
                       expand = expansion(add = c(0.012, 0.012))) +
    labs(x = "半径 r / cm", y = "含水率 C / (kg/kg)") + TH

  p <- (pa | pb) + plot_layout(widths = c(1.05, 1), guides = "collect") &
    theme(legend.position = "bottom", legend.box.just = "center")
  save_png(p, file.path(ROOT, "results", "figures", "fig05_q1_window.png"), 170, 74)
  invisible(list(C_surf_end = e$C_surf, C_center_end = e$C_center,
                 C_center_drop_rel = 1 - e$C_center / S$C_center[1],
                 dT_end = e$T_surf_C - e$T_center_C,
                 J_max = hi, J_lo = lo,
                 J_surf_1800 = Jm[match(1800, tt), length(rr)]))
}

# ---------------- 图9 问题三：全域阈值事件（首次达标） ----------------
# 主视觉是余量场 log10(C/C_cr)：0 等值线就是判据本身，它自表面处张开、收到轴心，
# 两个端点即两个事件。原版画 C 的等距八档，0.15 不是档界（53% 的格点落在第一档内），
# 判据只能另画一条线，事件被埋在一片平涂里。
# 面板(b) 只画两条真实不同的曲线：C_max ≡ C_center（690/690 时刻逐点相等），
# 重画一次是把恒等式冒充成信息；纵轴同样取对数余量，0.15 不再贴在轴底 6% 处。
FIG$q3 <- function() {
  M <- read.csv(file.path(FD, "q3_profiles_6h.csv")); M$t_h <- M$t_s / 3600
  X <- read.csv(file.path(FD, "q3_maxC.csv"));        X$t_h <- X$t_s / 3600
  Ccr <- 0.15; td <- max(X$t_h)
  d <- max(abs(X$C_max - X$C_center))
  if (d > 1e-9) warning(sprintf("max|C_max-C_center| = %.2e：图9(b) 两曲线的前提失效", d))
  M$mrg <- log10(M$C / Ccr)

  # 档界压在值域 [-0.455, 0.831] 上、0 必为档界；达标侧只留两档，
  # 色差信息集中在尚未达标的一侧
  brk <- c(-0.50, -0.25, 0, 0.10, 0.20, 0.35, 0.55, 0.70, 0.90)
  lb  <- c("≤ 0.084", "0.084–0.15", "0.15–0.19", "0.19–0.24",
           "0.24–0.34", "0.34–0.53", "0.53–0.75", "≥ 0.75")
  # 本图专色阶：同一条含水率色阶，但最浅档抬到浅黄，否则"已达标区"与白底同色、在图上被画丢
  SF9 <- WARM(length(brk) - 1, lo = "#FAF0A6")

  # 0 等值线的两个端点：表面首次触及判据、轴心（即全域）达标
  xr <- function(v) {
    o <- order(X$t_h); tt <- X$t_h[o]; vv <- v[o]; k <- which(vv <= Ccr)[1]
    tt[k - 1] + (Ccr - vv[k - 1]) / (vv[k] - vv[k - 1]) * (tt[k] - tt[k - 1])
  }

  pa <- ggplot(M, aes(r_cm, t_h, z = mrg)) +
    geom_contour_filled(breaks = brk) +
    scale_fill_manual(values = SF9, drop = FALSE,
                      name = expression(log[10]*"("*C*"/"*C[cr]*")"), labels = lb,
                      guide = guide_legend(reverse = TRUE, keyheight = unit(4.6, "pt"),
                                           keywidth = unit(7, "pt"))) +
    geom_contour(breaks = brk, colour = "white", linewidth = 0.16) +
    geom_contour(breaks = 0, colour = MUT[["purple"]], linewidth = 0.7) +
    annotate("point", x = 2.0, y = xr(X$C_surf), shape = 21, size = 1.9,
             stroke = 0.55, fill = "white", colour = MUT[["blue"]]) +
    annotate("point", x = 0, y = xr(X$C_center), shape = 21, size = 1.9,
             stroke = 0.55, fill = "white", colour = MUT[["green"]]) +
    scale_x_continuous(breaks = c(0, 0.5, 1.0, 1.5, 2.0), limits = c(0, 2.0),
                       expand = expansion(add = c(0.05, 0.05))) +
    scale_y_continuous(breaks = c(6, 12, 24, 36, 48, td),
                       labels = c("6", "12", "24", "36", "48", "57.5"),
                       limits = c(6, td), expand = expansion(add = c(1.2, 1.2))) +
    labs(x = "半径 r / cm", y = "时间 t / h") + TH

  lg <- rbind(data.frame(t_h = X$t_h, mrg = log10(X$C_surf / Ccr),   idx = "表面 C(R, t)"),
              data.frame(t_h = X$t_h, mrg = log10(X$C_center / Ccr), idx = "中心 C(0, t) = 全域最大"))
  lg$idx <- factor(lg$idx, levels = c("表面 C(R, t)", "中心 C(0, t) = 全域最大"))
  pb <- ggplot(lg, aes(t_h, mrg, colour = idx)) +
    geom_hline(yintercept = 0, linetype = "22", colour = MUT[["purple"]], linewidth = 0.5) +
    geom_line(linewidth = 0.6) +
    annotate("point", x = xr(X$C_center), y = 0, shape = 21, size = 2.0,
             stroke = 0.55, fill = "white", colour = MUT[["green"]]) +
    scale_colour_manual(values = c(MUT[["blue"]], MUT[["green"]]), name = NULL) +
    scale_x_continuous(breaks = c(0, 12, 24, 36, 48, td),
                       labels = c("0", "12", "24", "36", "48", "57.5"),
                       limits = c(0, td), expand = expansion(mult = 0.012)) +
    scale_y_continuous(breaks = c(-0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2)) +
    labs(x = "时间 t / h", y = expression(log[10]*"("*C*"/"*C[cr]*")")) +
    TH + theme(legend.position = "top", legend.text = element_text(size = 7.4))

  p <- pa | pb
  save_png(p, file.path(ROOT, "results", "figures", "fig09_q3_event.png"), 170, 70)
  invisible(list(td_h = td, t_surf_h = xr(X$C_surf), C_surf_end = X$C_surf[nrow(X)]))
}

# ---------------- 图18 跨离散方法核验：FVM 与独立 P1-FEM ----------------
FIG$cross <- function() {
  z  <- read.csv(file.path(FD, "fem_crosscheck.csv"))
  cr <- z[z$kind == "cross", ]; gp <- z[z$kind == "gap", ]
  qn <- c(Q3 = "问题3（固定域）", Q4 = "问题4（收缩域）")
  cr$q <- qn[cr$question]; gp$q <- qn[gp$question]
  prod <- cr[cr$Nc == max(cr$Nc), ]
  # 生产格上的实现间相对差（机器重算，不手打）
  rel <- sapply(c("Q3", "Q4"), function(k) {
    d <- prod[prod$question == k, ]
    abs(diff(d$value)) / d$value[d$method == "FVM"] * 100
  })

  pa <- ggplot(cr, aes(Nc, value, colour = q, linetype = method)) +
    geom_line(linewidth = 0.5) + geom_point(size = 0.85) +
    geom_point(data = prod, size = 1.7, shape = 21, fill = "white", stroke = 0.5) +
    scale_x_log10(breaks = c(200, 400, 800, 1600)) +
    scale_colour_manual(values = c(MUT[["red"]], MUT[["blue"]]), name = NULL) +
    scale_linetype_manual(values = c(FVM = "solid", FEM = "22"), name = NULL) +
    labs(x = expression(N[c] * "（径向单元数）"), y = "达标时长 t_d / h") +
    TH + theme(legend.position = "top", legend.box = "horizontal",
               legend.margin = margin(0, 0, 0, 0), legend.spacing.x = unit(5, "pt"))

  pb <- ggplot(gp, aes(Nc, value, colour = q)) +
    geom_line(linewidth = 0.5) + geom_point(size = 0.95) +
    scale_x_log10(breaks = c(200, 400, 800, 1600)) + scale_y_log10() +
    scale_colour_manual(values = c(MUT[["red"]], MUT[["blue"]]), name = NULL) +
    labs(x = expression(N[c]), y = "|t_d(FEM) − t_d(FVM)| / s") +
    TH + theme(legend.position = "none")

  ob <- z[grepl("^order_fem_", z$kind), ]
  ob$loc <- c(order_fem_interior = "内点", order_fem_wall = "壁面",
              order_fem_axis = "轴心")[ob$kind]
  ob <- ob[order(ob$kind, ob$Nc), ]
  po <- sapply(split(ob, ob$kind), function(d) {
    -diff(log(d$value)) / diff(log(d$Nc)) -> p; mean(p)
  })
  xr <- range(ob$Nc)
  rf <- data.frame(Nc = 10^seq(log10(xr[1]), log10(xr[2]), length.out = 30))
  rf$err <- ob$value[ob$kind == "order_fem_interior" & ob$Nc == xr[1]] *
            (rf$Nc / xr[1])^(-2)

  pc <- ggplot(ob, aes(Nc, value, colour = loc)) +
    geom_line(data = rf, aes(Nc, err), inherit.aes = FALSE, linetype = "22",
              colour = "grey55", linewidth = 0.4) +
    geom_line(linewidth = 0.5) + geom_point(size = 0.9) +
    scale_x_log10() + scale_y_log10() +
    scale_colour_manual(values = c(MUT[["blue"]], MUT[["red"]], MUT[["purple"]]),
                        name = NULL) +
    labs(x = expression(N[c]), y = expression(max * "|" * C[num] - C[ana] * "|")) +
    TH + theme(legend.position = "top", legend.margin = margin(0, 0, 0, 0))

  p <- pa / (pb | pc) + plot_layout(heights = c(1.12, 1))
  save_png(p, file.path(ROOT, "results", "figures", "fig18_crosscheck.png"), 170, 88)
  invisible(list(rel_pct_q3 = rel[["Q3"]], rel_pct_q4 = rel[["Q4"]],
                 gap_q3_s = gp$value[gp$question == "Q3"][which.max(gp$Nc[gp$question == "Q3"])],
                 orders = po))
}

# ---------------- 图19 一维降阶的模型形式检验：端面效应（2D 轴对称） ----------------
FIG$endface <- function() {
  e <- read.csv(file.path(FD, "endface_2d.csv"))
  a <- e[e$kind == "endface", ]; b <- e[e$kind == "limit", ]
  a <- a[order(a$Nr), ]; b <- b[order(b$Nz), ]

  pa <- ggplot(a, aes(Nr, delta_pct)) +
    geom_hline(yintercept = 0, colour = "grey70", linewidth = 0.35) +
    geom_line(colour = MUT[["blue"]], linewidth = 0.5) +
    geom_point(colour = MUT[["blue"]], size = 1.4) +
    labs(x = expression(N[r] * "（径向单元数）"),
         y = expression(Delta * t[d] * " / %")) +
    TH + theme(axis.title.y = element_text(size = 8.5))

  b$mult <- b$Nz / min(b$Nz)
  pb <- ggplot(b, aes(mult, abs(delta_pct))) +
    geom_line(colour = MUT[["red"]], linewidth = 0.5) +
    geom_point(colour = MUT[["red"]], size = 1.5) +
    annotate("segment", x = max(b$mult) * 0.78, xend = max(b$mult) * 1.25,
             y = min(abs(b$delta_pct)) * 1.4, yend = min(abs(b$delta_pct)) * 0.75,
             arrow = arrow(length = unit(1.6, "pt"), type = "closed"),
             colour = MUT[["red"]], linewidth = 0.4) +
    scale_x_continuous(breaks = b$mult) + scale_y_log10() +
    labs(x = "圆柱半长倍数（Δz 不变）",
         y = expression("|" * Delta * t[d] * "| / %")) +
    TH + theme(axis.title.y = element_text(size = 8.5))

  # 机制判据：轴向扩散特征长度 √(D(t)·t) 与圆柱半长 L/2 的对比
  # ⚠️ 该量随 t 非单调：先因升温/高含水率下 D 大而增长，10 h 前后达峰，
  #    之后随含水率下降、D = exp(ln2.4e-3 − 0.45/C − 3850/T) 崩塌而回落。
  g <- read.csv(file.path(FD, "gammapsi_q3.csv"))
  Ld <- sqrt(g$D1e9 * 1e-9 * g$t_s) * 1000            # mm
  Lhalf <- 250 / 2                                     # 圆柱半长 mm（题目 L=25 cm）
  imx <- which.max(Ld)
  d3 <- data.frame(t_h = g$t_s / 3600, L = Ld)
  pc <- ggplot(d3, aes(t_h, L)) +
    geom_hline(yintercept = Lhalf, linetype = "22", colour = MUT[["purple"]],
               linewidth = 0.45) +
    geom_line(colour = MUT[["blue"]], linewidth = 0.5) +
    geom_point(data = d3[imx, ], colour = MUT[["red"]], size = 1.5) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.12))) +
    labs(x = "时间 t / h", y = "轴向扩散特征长度 / mm") +
    TH + theme(axis.title.y = element_text(size = 8.5))

  p <- (pa | pb | pc)
  save_png(p, file.path(ROOT, "results", "figures", "fig19_endface.png"), 170, 66)
  invisible(list(delta_min = min(a$delta_pct), delta_max = max(a$delta_pct),
                 delta_spread_pct = 100 * diff(range(abs(a$delta_pct))) / mean(abs(a$delta_pct)),
                 delta_s_span_s = diff(range(abs(a$delta_s))),
                 mult_max = max(b$mult), limit_final = min(abs(b$delta_pct)),
                 Ld_max_mm = max(Ld), t_at_max_h = d3$t_h[imx],
                 Ld_at_td_mm = Ld[length(Ld)], Lhalf_mm = Lhalf,
                 ratio_at_peak = Lhalf / Ld[imx], ratio_peak = Lhalf / max(Ld)))
}

# ---------------- 图7 Q2 基线→进阶：冻结初始物性的受控反事实（过程感图） ----------------
# 面板 a 给两档物性的中心含水率全程对照；面板 b 把"差多少"与"谁高"拆成相对差曲线，
# 两条零交叉（表层 5.70 h、中心 15.88 h）由数据现算，不写死。
FIG$baseline <- function() {
  d <- read.csv(file.path(FD, "q2_frozen_trace.csv"))
  m <- merge(d[d$series == "dyn", c("t_h", "C_center", "C_surf")],
             d[d$series == "frz", c("t_h", "C_center", "C_surf")],
             by = "t_h", suffixes = c("_dyn", "_frz"))
  m <- m[order(m$t_h), ]
  m$d_c <- 100 * (m$C_center_frz - m$C_center_dyn) / m$C_center_dyn
  m$d_s <- 100 * (m$C_surf_frz   - m$C_surf_dyn)   / m$C_surf_dyn

  xcross <- function(t, y) {                     # 线性插值定位 y 的首次零穿越
    s <- which(diff(sign(y)) != 0)[1]
    t[s] + (0 - y[s]) * (t[s + 1] - t[s]) / (y[s + 1] - y[s])
  }
  tc <- xcross(m$t_h, m$d_c)
  ts <- xcross(m$t_h, m$d_s)
  ts2 <- xcross(m$t_h[m$t_h > ts + 1], m$d_s[m$t_h > ts + 1])   # 表层第二次反向
  i5 <- which(abs(m$d_c) > 5)[1]                 # 首次越出 ±5% 的时刻
  t5 <- m$t_h[i5]
  dmax <- max(m$d_c); tmax <- m$t_h[which.max(m$d_c)]
  dmin <- min(m$d_c)

  # 本图配色（只上色、不换形态）：数据两支改蓝/深绿；一切"判据/参考线"用全文判据色深紫，
  # 容带改淡紫。原图的红虚线(基线)、黑竖线(交叉时刻)、灰达标线、灰容带四类都踩"图内禁红黑白灰"。
  GRN <- "#4F9E67"                  # 数据第二支：基线 / 表层（原文 MUT[["red"]] 红）
  PUR <- "#7D6FA8"                  # 判据 / 参考线（原文 黑 TXT、灰 AX）
  LAV <- "#B39FDB"                  # ±5% 容带填充（原文 grey82 灰块）
  # 本图专用大字号主题：TH 的绝对字号在本图统一上调（不动 TH 本体 ⇒ 其余图逐位不变）
  THB <- TH + theme(axis.text   = element_text(colour = TXT, size = 12),
                    axis.title  = element_text(colour = TXT, size = 12.5),
                    legend.text = element_text(size = 11.5, colour = TXT))

  pa <- ggplot(m, aes(t_h)) +
    geom_hline(yintercept = 0.15, linetype = "13", colour = PUR, linewidth = 0.35) +
    geom_vline(xintercept = tc, linetype = "22", colour = PUR, linewidth = 0.4) +
    geom_line(aes(y = C_center_dyn, colour = "状态依赖物性（正式解）"), linewidth = 0.55) +
    geom_line(aes(y = C_center_frz, colour = "冻结初始物性（基线）"),
              linewidth = 0.55, linetype = "22") +
    scale_colour_manual(values = c("状态依赖物性（正式解）" = MUT[["blue"]],
                                   "冻结初始物性（基线）" = GRN),
                        name = NULL, guide = guide_legend(keywidth = unit(9, "pt"))) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.06))) +
    labs(x = "时间 t / h", y = "中心含水率 / (kg/kg)") +
    THB + theme(legend.position = c(0.795, 0.86), legend.direction = "vertical")

  pb <- ggplot(m, aes(t_h)) +
    annotate("rect", xmin = -Inf, xmax = Inf, ymin = -5, ymax = 5,
             fill = LAV, alpha = 0.40) +
    geom_hline(yintercept = 0, colour = PUR, linewidth = 0.4) +
    geom_vline(xintercept = c(ts, tc, ts2), linetype = "22", colour = PUR, linewidth = 0.4) +
    geom_line(aes(y = d_c, colour = "中心"), linewidth = 0.55) +
    geom_line(aes(y = d_s, colour = "表层"), linewidth = 0.55, linetype = "42") +
    scale_colour_manual(values = c("中心" = MUT[["blue"]], "表层" = GRN),
                        name = NULL, guide = guide_legend(keywidth = unit(9, "pt"))) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.06))) +
    labs(x = "时间 t / h", y = "相对差 δ / %") +
    THB + theme(legend.position = c(0.86, 0.24), legend.direction = "vertical")

  p <- pa / pb + plot_layout(heights = c(1.18, 1))
  save_png(p, file.path(ROOT, "results", "figures", "fig07_baseline_trace.png"), 170, 98)
  invisible(list(t_cross_center_h = tc, t_cross_surf_h = ts, t_cross_surf2_h = ts2,
                 t_first_5pct_h = t5,
                 d_center_max_pct = dmax, t_at_max_h = tmax,
                 d_surf_max_pct = max(m$d_s), t_at_dsurf_max_h = m$t_h[which.max(m$d_s)],
                 d_center_min_pct = dmin, t_at_min_h = m$t_h[which.min(m$d_c)],
                 d_center_48h_pct = m$d_c[nrow(m)]))
}

# ---------------- 候选① §7.5 达标时长的空间分解：干透前锋推进 ----------------
# 数据全来自 公共内核/spacebreak.py 的一次运行（同一算路）：
#   spacebreak_field.csv  (t,r) 温湿场   spacebreak_front.csv  干透前锋 C=C_cr
#   spacebreak_series.csv 同工况(Q3)轴心/表面序列； 热场对照取 q2_series.csv(Q2)
FIG$spacefront <- function() {
  F  <- read.csv(file.path(FD, "spacebreak_field.csv")); F$t_h  <- F$t_s / 3600
  FR <- read.csv(file.path(FD, "spacebreak_front.csv"))
  X  <- read.csv(file.path(FD, "spacebreak_series.csv")); X$t_h <- X$t_s / 3600
  Y  <- read.csv(file.path(FD, "q2_series.csv"));         Y$t_h <- Y$t_s / 3600

  ts <- min(FR$t_cross_h, na.rm = TRUE)    # 表面首越 C_cr
  tc <- max(FR$t_cross_h, na.rm = TRUE)    # 轴心首越 C_cr = 达标时刻
  # 把 0.15 摆成一条分箱边界，干透壳与未干区才会落在不同色块上
  BR <- c(0.05, 0.15, 0.35, 0.75, 1.40, 2.00, 2.60)

  pa <- ggplot(F, aes(r_cm, t_h, z = C)) +
    geom_contour_filled(breaks = BR) + fill_field(length(BR) - 1) +
    geom_path(data = FR, aes(r_cm, t_cross_h), inherit.aes = FALSE,
              colour = MUT[["red"]], linewidth = 0.7) +
    annotate("segment", x = 0, xend = 2, y = tc, yend = tc,
             colour = "grey35", linetype = "22", linewidth = 0.35) +
    annotate("point", x = 2.0, y = ts, colour = MUT[["red"]], size = 1.6, shape = 16) +
    annotate("point", x = 0.0, y = tc, colour = MUT[["red"]], size = 1.6, shape = 16) +
    annotate("text", x = 1.94, y = ts + 4.2, hjust = 1, size = 2.0,
             colour = MUT[["red"]], label = sprintf("表面达标 %.4f h", ts)) +
    annotate("text", x = 0.08, y = tc - 5.5, hjust = 0, size = 2.0,
             colour = MUT[["red"]], label = sprintf("轴心达标 %.4f h", tc)) +
    annotate("text", x = 1.32, y = 33.0, hjust = 0.5, size = 2.0, colour = TXT,
             lineheight = 0.95,
             label = sprintf("干透前锋 C = 0.15\n自表面向内推进")) +
    guides(fill = guide_legend(reverse = TRUE, nrow = 2, byrow = TRUE,
                               keyheight = unit(4, "pt"), keywidth = unit(9, "pt"))) +
    labs(x = "半径 r / cm", y = "时间 t / h") +
    TH + theme(legend.position = "bottom")

  nC <- (X$C_center - X$C_surf); nC <- nC / max(nC)
  nT <- abs(Y$T_surf_C - Y$T_center_C); nT <- nT / max(nT)
  # t=0 处两侧温差本就为零，不能直接取"首次 <0.1"；须自峰值之后首次跌破
  iT <- which.max(nT)
  tT <- Y$t_h[iT - 1 + which(nT[iT:length(nT)] < 0.1)[1]]
  G <- rbind(data.frame(t_h = X$t_h, v = nC, idx = "含水率差（问题三）"),
             data.frame(t_h = Y$t_h, v = nT, idx = "温差（问题二）"))

  pb <- ggplot(G, aes(t_h, v, colour = idx)) +
    geom_hline(yintercept = 0.1, linetype = "22", colour = "grey55", linewidth = 0.4) +
    geom_line(linewidth = 0.6) +
    annotate("text", x = 30, y = 0.165, hjust = 0.5, size = 1.85, colour = "grey40",
             label = "峰值的 10%") +
    annotate("text", x = 63, y = 0.87, hjust = 1, size = 1.95, colour = MUT[["purple"]],
             label = sprintf("温差：%.2f h 落到 10%%", tT)) +
    annotate("text", x = 63, y = 0.67, hjust = 1, size = 1.95, colour = MUT[["red"]],
             label = sprintf("含水率差：收工时仍余 %.1f%%", 100 * nC[length(nC)])) +
    scale_colour_manual(values = c(MUT[["red"]], MUT[["purple"]]), name = NULL) +
    scale_x_continuous(limits = c(0, 72), expand = c(0, 0)) +
    labs(x = "时间 t / h", y = "空间差异（各自按峰值归一）") +
    TH + theme(legend.position = "top", plot.margin = margin(0, 4, 3, 3))

  # 分解条与下面的曲线共用同一条 t 轴，两段的长度才与时间刻度对得上
  pc <- ggplot(data.frame(a = 1)) +
    geom_rect(aes(xmin = 0, xmax = ts, ymin = 0, ymax = 1),
              fill = LIT[["blue"]], colour = "white", linewidth = 0.4) +
    geom_rect(aes(xmin = ts, xmax = tc, ymin = 0, ymax = 1),
              fill = LIT[["red"]], colour = "white", linewidth = 0.4) +
    annotate("text", x = ts / 2, y = 0.5, size = 1.95, colour = "#3C3C3C",
             label = sprintf("%.2f%%", 100 * ts / tc)) +
    annotate("text", x = (ts + tc) / 2, y = 0.5, size = 1.95, colour = "#3C3C3C",
             label = sprintf("%.2f%%", 100 * (tc - ts) / tc)) +
    annotate("text", x = 0.4, y = 1.78, hjust = 0, size = 1.95, colour = "#3C3C3C",
             label = sprintf("表面达标段  %.4f h", ts)) +
    annotate("text", x = 71.6, y = 1.78, hjust = 1, size = 1.95, colour = "#3C3C3C",
             label = sprintf("轴心补平段  %.4f h", tc - ts)) +
    scale_x_continuous(limits = c(0, 72), expand = c(0, 0)) +
    scale_y_continuous(limits = c(0, 2.05), expand = c(0, 0)) +
    labs(x = NULL, y = NULL) +
    TH + theme(axis.text = element_blank(), axis.ticks = element_blank(),
               plot.margin = margin(4, 4, 0, 3))

  p <- pa | (pc / pb) ; p <- p + plot_layout(widths = c(1.12, 1), heights = c(1, 3.1))
  save_png(p, file.path(ROOT, "results", "figures", "cand1_front.png"), 170, 78)
  invisible(list(t_surf = ts, t_core = tc, t_thermal_10 = tT))
}

# ---------------- 备选② §7.5 剖面山脊图：干透壳如何自外向内吃进来 ----------------
# 每条山脊 = 一个时刻的 C(r) 剖面，脊基线落在它自己的时刻上（故 y 轴仍可读作时间）；
# 脊的"下半截"（C<=0.15）涂淡红 = 已干透，"上半截"涂淡蓝 = 未干透。
# 同一份 spacebreak_field.csv / spacebreak_front.csv，与候选①同算路。
FIG$ridge <- function() {
  F  <- read.csv(file.path(FD, "spacebreak_field.csv")); F$t_h <- F$t_s / 3600
  FR <- read.csv(file.path(FD, "spacebreak_front.csv"))
  CCR <- 0.15
  ns  <- length(unique(F$t_s)); nn <- nrow(F) / ns
  th  <- F$t_h[seq(1, nrow(F), by = nn)]
  rr  <- F$r_cm[1:nn]
  Z   <- matrix(F$C, nrow = ns, ncol = nn, byrow = TRUE)
  ts  <- min(FR$t_cross_h, na.rm = TRUE); tc <- max(FR$t_cross_h, na.rm = TRUE)

  nsel <- 21
  sel  <- unique(round(seq(1, ns, length.out = nsel))); sel[length(sel)] <- ns
  dy   <- (th[ns] - th[1]) / (length(sel) - 1)
  k    <- 0.72 * dy / max(Z[1, ])          # 脊高 = 0.72 倍脊距，留出上叠的层次

  G <- do.call(rbind, lapply(sel, function(s) {
    cv <- Z[s, ]
    data.frame(t_h = th[s], r_cm = rr,
               y0  = th[s],
               ylo = th[s] + pmin(cv, CCR) * k,      # 已干透段的顶
               y15 = th[s] + CCR * k,                # 0.15 等值高
               yhi = th[s] + pmax(cv, CCR) * k,      # 未干透段的顶（0.15 以上）
               ytop = th[s] + cv * k)                # 剖面轮廓
  }))

  FRo <- FR[order(FR$r_cm), ]
  FRo <- FRo[!is.na(FRo$t_cross_h), ]
  FRT <- do.call(rbind, lapply(sel, function(s) {
    tt <- th[s]
    ok <- FRo$t_cross_h <= tt
    data.frame(t_h = tt,
               r_cm = if (any(ok)) max(FRo$r_cm[ok]) else NA_real_,
               y = tt + CCR * k)
  }))

  p <- ggplot(G, aes(r_cm)) +
    geom_ribbon(aes(ymin = y0, ymax = ylo, group = t_h), fill = LIT[["red"]], colour = NA) +
    geom_ribbon(aes(ymin = y15, ymax = yhi, group = t_h), fill = LIT[["blue"]], colour = NA) +
    geom_line(aes(y = y0, group = t_h), colour = "grey62", linewidth = 0.22) +
    geom_line(aes(y = ytop, group = t_h), colour = MUT[["blue"]], linewidth = 0.32) +
    geom_path(data = FRT[!is.na(FRT$r_cm), ], aes(r_cm, y),
              colour = MUT[["red"]], linewidth = 0.7) +
    annotate("point", x = 2.0, y = ts + CCR * k, colour = MUT[["red"]], size = 1.7) +
    annotate("point", x = 0.0, y = tc + CCR * k, colour = MUT[["red"]], size = 1.7) +
    annotate("text", x = 1.55, y = ts - 3.4, hjust = 0.5, size = 2.0,
             colour = MUT[["red"]], label = sprintf("表面首越 0.15：%.4f h", ts)) +
    annotate("text", x = 0.30, y = tc + 2.2, hjust = 0, size = 2.0,
             colour = MUT[["red"]], label = sprintf("轴心首越 0.15：%.4f h", tc)) +
    annotate("text", x = 1.62, y = 34.0, hjust = 0, size = 2.0, colour = TXT,
             lineheight = 0.95,
             label = "淡红 = 已干透壳 C ≤ 0.15\n淡蓝 = 未干透\n红线 = 干透前锋沿脊爬行") +
    scale_x_continuous(limits = c(0, 2.0), expand = c(0.01, 0)) +
    scale_y_continuous(limits = c(-1.6, 62), expand = c(0, 0)) +
    labs(x = "半径 r / cm", y = "时间 t / h",
         subtitle = "每条山脊为一个时刻的含水率剖面 C(r)，脊高即 C（0 至 2.55 kg/kg）；脊基线落在该时刻上") +
    TH + theme(plot.subtitle = element_text(size = 6.0, colour = "grey38"),
               plot.margin = margin(3, 5, 3, 3))
  save_png(p, file.path(ROOT, "results", "figures", "cand_ridge.png"), 118, 82)
  invisible(list(n_ridge = length(sel), t_surf = ts, t_core = tc))
}

# ---------------- 备选②' §7.5 湿—热相轨迹：过程如何离开温差维 ----------------
# 山脊图是走不通的：C(r) 剖面的极差从 2.55 塌到 0.0974（仅 C0 的 3.8%），
# 线性高度的脊必然全成平线；非线性高度会破坏"脊下面积=水量"的语义。
# 改把两个空间差异量当坐标轴，时间只做配色 => 相轨迹图，全文无此型。
# 湿场与热场都取 spacebreak_series.csv（问题三自身同一次运行），不跨问混口径。
# 注：本函数原名 FIG$phase，与上方图10 的 FIG$phase 撞名（R 后定义者覆盖前者），
# 结果图10 的产出函数永远不会被驱动执行；二者本是两张不同的图，故此处改名。输出文件不变。
FIG$cand_phase <- function() {
  X  <- read.csv(file.path(FD, "spacebreak_series.csv")); X$t_h <- X$t_s / 3600
  dC <- X$C_center - X$C_surf
  dT <- abs(X$T_surf_C - X$T_center_C)
  nC <- dC / max(dC); nT <- dT / max(dT)
  iC <- which.max(dC); iT <- which.max(dT)
  tT <- X$t_h[iT - 1 + which(nT[iT:length(nT)] < 0.1)[1]]
  D  <- data.frame(t_h = X$t_h, x = nT, y = nC)

  # 箭头必须按弧长布点：轨迹前 2 h 走得极快、后 55 h 几乎不动，按序号取点会横切轨迹
  s  <- cumsum(sqrt(c(0, diff(D$x))^2 + c(0, diff(D$y))^2))
  u  <- seq(0.07, 0.93, length.out = 8) * s[length(s)]
  i1 <- vapply(u, function(v) which.min(abs(s - v)), 1L)
  i2 <- vapply(u + 0.016 * s[length(s)], function(v) which.min(abs(s - v)), 1L)
  A  <- data.frame(x = D$x[i1], y = D$y[i1], xe = D$x[i2], ye = D$y[i2])
  A  <- A[abs(A$xe - A$x) + abs(A$ye - A$y) > 0.02, ]

  p <- ggplot(D, aes(x, y)) +
    geom_vline(xintercept = 0.1, linetype = "22", colour = "grey72", linewidth = 0.3) +
    geom_hline(yintercept = 0.1, linetype = "22", colour = "grey72", linewidth = 0.3) +
    geom_path(colour = "grey55", linewidth = 0.35) +
    geom_point(aes(colour = t_h), size = 0.9) +
    geom_segment(data = A, aes(x = x, y = y, xend = xe, yend = ye), inherit.aes = FALSE,
                 colour = "grey30", linewidth = 0.32,
                 arrow = arrow(length = unit(1.5, "mm"), type = "open")) +
    annotate("point", x = nT[iT], y = nC[iT], colour = MUT[["purple"]], size = 1.9) +
    annotate("point", x = nT[iC], y = nC[iC], colour = MUT[["red"]], size = 1.9) +
    annotate("text", x = nT[iT] + 0.035, y = nC[iT] - 0.085, hjust = 1, size = 1.95,
             colour = MUT[["purple"]],
             label = sprintf("温差见顶 %.2f h（%.2f ℃）", X$t_h[iT], max(dT))) +
    annotate("text", x = nT[iC] - 0.03, y = nC[iC] + 0.055, hjust = 1, size = 1.95,
             colour = MUT[["red"]],
             label = sprintf("湿差见顶 %.2f h（%.2f kg/kg）", X$t_h[iC], max(dC))) +
    annotate("text", x = 0.075, y = 0.028, hjust = 0, size = 1.95, colour = "grey35",
             label = "起点 t = 0") +
    annotate("text", x = 0.17, y = 0.66, hjust = 0, size = 1.95, colour = "grey30",
             label = sprintf("温差 %.2f h 即落到峰值 10%%", tT)) +
    annotate("text", x = 0.055, y = 0.42, hjust = 0, size = 1.95, colour = "grey30",
             lineheight = 0.95,
             label = sprintf("此后 %.1f h\n沿湿差轴单向爬行", X$t_h[length(X$t_h)] - tT)) +
    annotate("text", x = 0.985, y = 0.075, hjust = 1, size = 1.95, colour = MUT[["red"]],
             label = sprintf("收工：湿差仍余 %.1f%%", 100 * nC[length(nC)])) +
    scale_colour_gradientn("时间 t / h（对数刻度）",
                           colours = c("#CFE0F7", "#8FB6E0", "#5E84B9", "#37527D"),
                           trans = "log1p", breaks = c(0, 0.5, 2, 8, 30),
                           labels = c("0", "0.5", "2", "8", "30"),
                           guide = guide_colourbar(barwidth = unit(46, "mm"),
                                                   barheight = unit(2.6, "pt"),
                                                   ticks.colour = "grey40")) +
    scale_x_continuous(limits = c(-0.02, 1.06), expand = c(0, 0)) +
    scale_y_continuous(limits = c(-0.02, 1.12), expand = c(0, 0)) +
    labs(x = expression("温差 " * Delta * "T / 峰值（无量纲）"),
         y = expression("湿差 " * Delta * "C / 峰值（无量纲）")) +
    TH + theme(legend.position = "top", legend.direction = "horizontal",
               legend.margin = margin(0, 0, 1, 0),
               plot.margin = margin(3, 5, 3, 3))
  save_png(p, file.path(ROOT, "results", "figures", "cand_phase.png"), 118, 84)
  invisible(list(t_thermal10 = tT, t_dC_peak = X$t_h[iC], t_dT_peak = X$t_h[iT],
                 nC_end = nC[length(nC)]))
}

# ---------------- 候选④ §7.5 湿分剖面的分布演化 + 轴心/表面包络 ----------------
# 高度语义与"剖面山脊"完全不同：山脊的高度是 C 本身，剖面变平就塌成直线；
# 这里每条的高度是各时刻自归一的核密度——分布收缩只会变窄变尖，不会消失。
# 图内不放背景色块、不放说明文字（本项目的全局约定）：分段时长等数字一律留给正文图注。
# 每条小提琴按局部密度做纵向渐变（芯深尾淡），并叠 25%~75% 竖向区间条与中位点。
# y 轴可选线性/√/log：C 的剖面跨度从 2.55 缩到 0.0974（25 倍），线性刻度下末段全挤在下沿；
# 换成压缩型刻度只改"显示"，不改任何数值——数据、包络、判据线的真实间距与顺序都不变。
viol_body <- function(ytr = "lin", out = "cand_violin.png") {
  F  <- read.csv(file.path(FD, "spacebreak_field.csv"))
  FR <- read.csv(file.path(FD, "spacebreak_front.csv"))
  ts <- min(FR$t_cross_h, na.rm = TRUE)    # 表面首越 C_cr
  tc <- max(FR$t_cross_h, na.rm = TRUE)    # 轴心首越 C_cr = 达标时刻
  th <- sort(unique(F$t_s)); nn <- length(unique(F$r_cm))
  Cm <- matrix(F$C, nrow = length(th), ncol = nn, byrow = TRUE)

  # 节点按 r 升序落列 ⇒ 第 1 列是轴心、第 nn 列是表面；两条包络与空间分解同一算路
  CV <- rbind(data.frame(t_h = th / 3600, C = Cm[, 1],  series = "轴心（决定达标）"),
              data.frame(t_h = th / 3600, C = Cm[, nn], series = "表面"))

  tsel <- c(1, 2.5, 5, 8, 10.5, ts, 15, 19, 24, 30, 36, 42, 48, 53, tc)
  ii   <- unique(vapply(tsel * 3600, function(v) which.min(abs(th - v)), 1L))
  HW   <- 1.62; NG <- 150
  LO0  <- if (is.character(ytr) && ytr == "log10") 0.05 else 0  # log 下 y=0 → -Inf，栅格下沿须离零
  REC <- NULL; OUT <- NULL; sk <- numeric(0)
  for (k in ii) {
    cv <- Cm[k, ]
    if (sd(cv) < 1e-4) { sk <- c(sk, th[k] / 3600); next }
    de <- density(cv, n = 320, adjust = 0.85, from = 0, to = 2.62)
    # y 栅格跟着本条的有效支撑走：否则支撑之外的段全是零宽矩形，会被渲染成贯穿全高的竖线。
    # 支撑取本条剖面的数据范围本身（与 geom_violin 的口径一致）——若沿用核密度的
    # 1e-3 阈值外延，带宽尾部会拖出一条细针，在压缩刻度下被放大成假形态。
    yg  <- seq(max(LO0, min(cv)), min(2.62, max(cv)), length.out = NG + 1)
    ym  <- (yg[-1] + yg[-(NG + 1)]) / 2
    dv  <- approx(de$x, de$y, xout = ym, rule = 1)$y
    dv[is.na(dv)] <- 0
    dv <- dv / max(dv)                     # 每条各按自身峰值归一，宽度口径与常规小提琴一致
    x0 <- th[k] / 3600
    # 逐薄条渲染：横向半宽给形状，填充色给时间，透明度只在小范围里给密度（实体感 + 一点芯深尾淡）
    REC <- rbind(REC, data.frame(xmin = x0 - dv * HW, xmax = x0 + dv * HW,
                                 ymin = yg[-(NG + 1)], ymax = yg[-1],
                                 dens = dv, t_h = x0, g = k))
    OUT <- rbind(OUT, data.frame(x = c(x0 - dv * HW, rev(x0 + dv * HW)),
                                 C = c(ym, rev(ym)), g = k))
  }
  cat("  小提琴带: 条数", length(unique(REC$g)), " 分布坍缩被跳过",
      if (length(sk)) sprintf("%.2f h", sk) else "无",
      " 薄条", nrow(REC), " 补平段",
      sprintf("%.4f h = %.2f%%", tc - ts, 100 * (tc - ts) / tc), "\n")

  # 幂刻度 y'=C^p（p<1）：压顶扩底——顶端 C≈2.55 被压缩、底端 0.05~0.35 被放大。
  # 这正是"上包络右端抬起来、下包络仍旧贴着底"的几何来源，且不改变任何 C 的真实取值。
  PT <- function(p) scales::trans_new(sprintf("pow%.3f", p),
                                      transform = function(x) x^p,
                                      inverse   = function(x) x^(1 / p))
  BRK <- c(0, 0.15, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5)
  SY <- if (is.numeric(ytr)) {
    scale_y_continuous(trans = PT(ytr), limits = c(0, 2.70), expand = c(0, 0), breaks = BRK)
  } else switch(ytr,
    sqrt  = scale_y_sqrt(limits = c(0, 2.70), expand = c(0, 0), breaks = BRK),
    log10 = scale_y_log10(limits = c(0.05, 2.70), expand = c(0, 0),
                          breaks = c(0.05, 0.1, 0.2, 0.5, 1, 2)),
    scale_y_continuous(limits = c(0, 2.70), expand = c(0, 0)))
  SUF <- if (is.numeric(ytr)) "（纵轴压缩刻度）" else
         switch(ytr, sqrt = "（√ 刻度）", log10 = "（对数刻度）", "")

  p <- ggplot() +
    geom_rect(data = REC, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax,
                              fill = t_h, alpha = dens), colour = NA) +
    geom_path(data = OUT, aes(x, C, group = g), colour = "#4A6A96", linewidth = 0.22) +
    geom_line(data = CV, aes(t_h, C, colour = series), linewidth = 0.55) +
    geom_hline(yintercept = 0.15, linetype = "22", colour = "grey45", linewidth = 0.45) +
    scale_fill_gradientn(name = "时间 t / h",
                         colours = c("#A1C9F4", "#7FA8D8", "#5E84B9", "#37527D"),
                         limits = c(0, tc), breaks = c(0, ts, 30, tc),
                         labels = c("0", "12.55", "30", "57.48"),
                         guide = guide_colourbar(barwidth = unit(38, "mm"),
                                                 barheight = unit(2.6, "pt"),
                                                 title.position = "top",
                                                 ticks.colour = AX)) +
    scale_alpha_continuous(range = c(0.42, 1), guide = "none") +
    scale_colour_manual(values = c("轴心（决定达标）" = MUT[["purple"]],
                                   "表面" = MUT[["red"]]), name = NULL) +
    scale_x_continuous(limits = c(-2.6, 60.0), expand = c(0, 0)) +
    SY +
    labs(x = "时间 t / h", y = paste0("含水率 C / (kg/kg)", SUF)) +
    TH + theme(legend.position = c(0.962, 0.985),
               legend.justification = c(1, 1),
               legend.box = "vertical", legend.box.just = "right",
               legend.direction = "horizontal",
               legend.background = element_blank(), legend.key = element_blank(),
               legend.margin = margin(0, 0, 0, 0), legend.spacing.y = unit(0.8, "pt"),
               plot.margin = margin(3, 4, 2, 3))
  save_png(p, file.path(ROOT, "results", "figures", out), 132, 92)
  invisible(list(t_surf = ts, t_core = tc, lag_h = tc - ts,
                 lag_pct = 100 * (tc - ts) / tc, ytr = ytr,
                 n = length(unique(REC$g)), skipped = sk))
}

FIG$violin      <- function() viol_body("lin",   "fig15_spacebreak.png")
# 备选纵向刻度（用户 2026-09-12 裁定用线性原稿，故默认不注册；如需重出，临时解注一行即可）
# FIG$violin_sqrt <- function() viol_body("sqrt",  "cand_violin_sqrt.png")
# FIG$violin_log  <- function() viol_body("log10", "cand_violin_log.png")
# FIG$violin_p35  <- function() viol_body(0.35,    "cand_violin_p35.png")
# FIG$violin_p28  <- function() viol_body(0.28,    "cand_violin_p28.png")

# ---------------- 候选⑤ §7.5 分位扇形带：分布随时间的连续演化 ----------------
# 与离散小提琴不同：691 个时刻全用上，每时刻按 101 个径向节点取一组分位带，
# 由宽到窄依序叠加——被最多层覆盖的芯部最深，只有一两层覆盖的尾部最淡，
# 于是"沿时间整体下移、末段贴在判定线上"以连续渐变的方式呈现，不需要任何色块背景。
FIG$fan <- function() {
  F  <- read.csv(file.path(FD, "spacebreak_field.csv"))
  FR <- read.csv(file.path(FD, "spacebreak_front.csv"))
  ts <- min(FR$t_cross_h, na.rm = TRUE)
  tc <- max(FR$t_cross_h, na.rm = TRUE)
  th <- sort(unique(F$t_s)); nn <- length(unique(F$r_cm))
  Cm <- matrix(F$C, nrow = length(th), ncol = nn, byrow = TRUE)
  t_h <- th / 3600

  NL <- 33
  pw <- seq(0.03, 0.98, length.out = NL)          # 各层分位带宽度，0.98 层≈极值
  LO <- t(apply(Cm, 1, quantile, probs = 0.5 - pw / 2, names = FALSE))
  HI <- t(apply(Cm, 1, quantile, probs = 0.5 + pw / 2, names = FALSE))
  # 由宽到窄入栈：窄层压在宽层之上，芯部被覆盖的层数最多，叠加后自然最深
  RB <- do.call(rbind, lapply(order(pw, decreasing = TRUE), function(j)
    data.frame(t_h = t_h, lo = LO[, j], hi = HI[, j], w = pw[j])))
  MD <- data.frame(t_h = t_h, C = apply(Cm, 1, median))

  p <- ggplot() +
    geom_ribbon(data = RB, aes(t_h, ymin = lo, ymax = hi, group = w),
                fill = "#2F4E7A", colour = NA, alpha = 0.095) +
    geom_line(data = MD, aes(t_h, C), colour = "grey15", linewidth = 0.4) +
    geom_hline(yintercept = 0.15, linetype = "22", colour = "grey45", linewidth = 0.45) +
    scale_x_continuous(limits = c(0, 58.5), expand = c(0.008, 0)) +
    scale_y_continuous(limits = c(0, 2.70), expand = c(0, 0)) +
    labs(x = "时间 t / h", y = "含水率 C / (kg/kg)") +
    TH + theme(legend.position = "none", plot.margin = margin(3, 4, 2, 3))
  save_png(p, file.path(ROOT, "results", "figures", "cand_fan.png"), 132, 88)
  invisible(list(n_width = NL, n_t = length(t_h), t_surf = ts, t_core = tc,
                 q_lo = LO[, 1], q_hi = HI[, NL]))
}

SEL <- commandArgs(trailingOnly = TRUE)
if (length(SEL) == 0) SEL <- names(FIG)
for (k in SEL) if (!is.null(FIG[[k]])) { cat("[", k, "]\n", sep = ""); print(FIG[[k]]()) }
