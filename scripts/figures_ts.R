# Thermal Science 版出图脚本（由 _superseded/make_figures_ts_legacy.py 从 journal_draft 原稿派生）
# 与原稿差异仅两处：ROOT 指向本目录；画布压到 140 mm 宽并等比调高。
# 本脚本只产出图1/图2/图3（fig02/fig13/fig07）。图4 见 fig18_ts.m，图5 见
# fig_sensitivity.R —— 图4 的 R 版块已于 2026-09-21 删除（其 v1 成品归档为
# figures/fig18_crosscheck_v1_prev.png），以免重跑本脚本静默覆盖 MATLAB 版成品。
# 配色、字号、图型定义逐字继承原稿，不降格。

# 仓库根目录：按脚本自身位置定位，克隆到任何路径都能运行
.REPO_ROOT <- local({
  a <- commandArgs(trailingOnly = FALSE)
  m <- grep("^--file=", a, value = TRUE)
  if (length(m)) dirname(normalizePath(sub("^--file=", "", m[1]), mustWork = FALSE)) else getwd()
})
.REPO_ROOT <- dirname(.REPO_ROOT)

Sys.setlocale("LC_ALL", "Chinese (Simplified)_China.utf8")
# -*- coding: utf-8 -*-
# 用法：Rscript 出图_R绘制.R  [图名...]   不传参 = 全画
# Rscript 子进程默认只看得到系统库，须显式补上 D 盘用户库，否则 showtext/Rcpp 等“装了却找不到”
.libPaths(unique(c("D:/claude项目专属/R-library/4.5", "D:/claude项目专属/R-library",
                   .libPaths())))
suppressPackageStartupMessages({
  library(ggplot2); library(patchwork); library(scales); library(ggdist)
  library(ggridges); library(showtext); library(sysfonts)
})
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
  tif <- sub("\\.png$", ".tif", path)
  ggsave(tif, p, width = w_mm / 25.4, height = h_mm / 25.4,
         dpi = 600, bg = "white", limitsize = FALSE,
         device = "tiff", compression = "lzw")
  cat(sprintf("  -> %-26s %7.0f kB\\n", basename(path), file.size(path) / 1024))
}

# 顺序色阶的合法性判据是"亮度逐档严格递减"、且首档不得近白（首档糊进白底=最低档不画，
# 是信息丢失而非难看）。col2rgb() 已返回 0-255，勿再乘 255（会让打印的自检数失真）。
luma <- function(col)
  as.numeric(c(0.2126, 0.7152, 0.0722) %*% col2rgb(col))

check_seq <- function(col, what = "sequential scale") {
  b <- luma(col)
  stopifnot(all(diff(b) < 0))       # 非严格递减 ⇒ 相邻两档之间出假边界
  stopifnot(b[1] < 250)             # 首档近白 ⇒ 落在白底上等于不画
  cat(sprintf("  [%s] %d bands, luma %.1f -> %.1f strictly decreasing, first %.1f\n",
              what, length(b), b[1], b[length(b)], b[1]))
  invisible(b)
}

# 含水率 C 的顺序色阶：五个锚点全部取自淡彩板（浅黄/粉/紫三支），
# 路径 浅黄 → 粉浅 → 粉 → 淡紫 → 深紫，亮度单调递减 ⇒ 不产生假边界。
# 首档一律不得取近白 #FDFBE9：C 场最低档占图面四成，落在纯白底上等于不画。
# 锚点与 MATLAB 侧 figs_matlab.m 的 warm_anchors() 逐位一致（R/MATLAB 两路出图必须同色）。
WARM_ANCHORS <- c("#FAF0A6", "#FFC7B6", "#FF9F9B", "#B39FDB", "#7D6FA8")

WARM <- function(n = 8) colorRampPalette(WARM_ANCHORS)(n)

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

FD   <- file.path(ROOT, "data", "processed", "figdata")
ROOT <- .REPO_ROOT
LIT <- c(blue = "#A1C9F4", red = "#FF9F9B", yellow = "#FAF0A6",
         green = "#8DE5A1", purple = "#B39FDB")
MUT <- c(blue = "#5E84B9", red = "#C27472", yellow = "#C7B84C",
         green = "#4F9E67", purple = "#7D6FA8")
AX  <- "#8A8A8A"   # 全框 / 轴线 / 刻度线
TXT <- "#4A4A4A"   # 刻度数字 / 轴标题
TTL <- "#3C3C3C"   # 面板标题 / 格头
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
FIG$env_radius <- function() {
  e <- read.csv(file.path(FD, "env_att1.csv"))
  e$g <- cut(e$t_s, breaks = c(-1, 3600, 7200, 10800, 14400),
             labels = c("0–1", "1–2", "2–3", "3–4"))

  # 每组变异指标机器重算（概括性断言必须重算，不靠肉眼估）
  st <- function(x) c(n = length(x), sd = sd(x), cv = sd(x) / mean(x))
  cat("  [工况] 逐时段 T∞  (n, sd, CV):\n"); print(round(do.call(rbind, tapply(e$T_amb_C, e$g, st)), 6))
  cat("  [工况] 逐时段 C∞  (n, sd, CV):\n"); print(round(do.call(rbind, tapply(e$C_amb_kgkg, e$g, st)), 8))

  qT <- "Air temperature T∞ / °C"; qC <- "Air-side input C∞ / (kg/kg)"
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
    scale_x_discrete(name = "Sampling interval t / h",
                     expand = expansion(add = c(0.45, 0.85))) +
    facet_wrap(~q, ncol = 1, scales = "free_y") +
    labs(y = NULL) + TH +
    theme(legend.position = "none",
          panel.spacing.y = unit(7, "pt"),
          strip.background = element_blank(),
          strip.text = element_text(colour = TTL, size = 8.5, hjust = 0,
                                    margin = margin(b = 2.5)))

  save_png(p, file.path(ROOT, "results", "figures", "fig02_env_radius.png"), 140, 81)
  invisible(list(
    n_win = as.integer(table(e$g)),
    cv_T = as.numeric(tapply(e$T_amb_C, e$g, function(x) sd(x) / mean(x))),
    cv_C = as.numeric(tapply(e$C_amb_kgkg, e$g, function(x) sd(x) / mean(x))),
    sd_T = as.numeric(tapply(e$T_amb_C, e$g, sd)),
    sd_C = as.numeric(tapply(e$C_amb_kgkg, e$g, sd))))
}

FD   <- file.path(ROOT, "data", "processed", "figdata")
ROOT <- .REPO_ROOT
LIT <- c(blue = "#A1C9F4", red = "#FF9F9B", yellow = "#FAF0A6",
         green = "#8DE5A1", purple = "#B39FDB")
MUT <- c(blue = "#5E84B9", red = "#C27472", yellow = "#C7B84C",
         green = "#4F9E67", purple = "#7D6FA8")
AX  <- "#8A8A8A"   # 全框 / 轴线 / 刻度线
TXT <- "#4A4A4A"   # 刻度数字 / 轴标题
TTL <- "#3C3C3C"   # 面板标题 / 格头
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
FBR <- c(0.05, 0.15, 0.35, 0.75, 1.40, 2.00, 2.60)   # 与图15(spacefront)同一套分箱，同一物理量跨图配色一致
FLB <- sprintf("%.2f–%.2f", FBR[-length(FBR)], FBR[-1])
FIG$ablpolar <- function() {
  check_seq(SEQ(length(FBR) - 1), "fig13 C field")
  da <- read.csv(file.path(FD, "ablation_field.csv"), fileEncoding = "UTF-8-BOM")
  da <- da[!is.na(da$C), ]        # 域外点(空值)不参与绘制，否则 geom_tile 会按 NA 涂灰
  EG <- read.csv(file.path(FD, "ablation_field_edge.csv"), fileEncoding = "UTF-8-BOM")
  lab <- c(a3fix = "A · fixed", a3shr = "A · shrinking",
           a4fix = "B · fixed", a4shr = "B · shrinking")
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
    labs(x = expression(tau == t / t[d] * "    (angle)"), y = "Radius r / cm") + TH +
    theme(strip.background = element_blank(),
          strip.text = element_text(size = 8, colour = TTL),
          axis.ticks.x = element_blank(),
          legend.position = "bottom", legend.key.width = unit(16, "pt"),
          legend.title.position = "left")

  save_png(p, file.path(ROOT, "results", "figures", "fig13_ablation_field.png"), 140, 65)
  invisible(dim(d))
}


FD   <- file.path(ROOT, "data", "processed", "figdata")
ROOT <- .REPO_ROOT
LIT <- c(blue = "#A1C9F4", red = "#FF9F9B", yellow = "#FAF0A6",
         green = "#8DE5A1", purple = "#B39FDB")
MUT <- c(blue = "#5E84B9", red = "#C27472", yellow = "#C7B84C",
         green = "#4F9E67", purple = "#7D6FA8")
AX  <- "#8A8A8A"   # 全框 / 轴线 / 刻度线
TXT <- "#4A4A4A"   # 刻度数字 / 轴标题
TTL <- "#3C3C3C"   # 面板标题 / 格头
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
FBR <- c(0.05, 0.15, 0.35, 0.75, 1.40, 2.00, 2.60)   # 与图15(spacefront)同一套分箱，同一物理量跨图配色一致
FLB <- sprintf("%.2f–%.2f", FBR[-length(FBR)], FBR[-1])
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
  THB <- TH + theme(axis.text   = element_text(colour = TXT, size = 9),
                    axis.title  = element_text(colour = TXT, size = 9),
                    legend.text = element_text(size = 8.5, colour = TXT))

  pa <- ggplot(m, aes(t_h)) +
    geom_hline(yintercept = 0.15, linetype = "13", colour = PUR, linewidth = 0.35) +
    geom_vline(xintercept = tc, linetype = "22", colour = PUR, linewidth = 0.4) +
    geom_line(aes(y = C_center_dyn, colour = "State-dependent properties"), linewidth = 0.55) +
    geom_line(aes(y = C_center_frz, colour = "Frozen initial properties"),
              linewidth = 0.55, linetype = "22") +
    scale_colour_manual(values = c("State-dependent properties" = MUT[["blue"]],
                                   "Frozen initial properties" = GRN),
                        name = NULL, guide = guide_legend(keywidth = unit(9, "pt"))) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.06))) +
    labs(x = "Time t / h", y = "Center C / (kg/kg)") +
    THB + theme(legend.position = c(0.795, 0.86), legend.direction = "vertical")

  pb <- ggplot(m, aes(t_h)) +
    annotate("rect", xmin = -Inf, xmax = Inf, ymin = -5, ymax = 5,
             fill = LAV, alpha = 0.40) +
    geom_hline(yintercept = 0, colour = PUR, linewidth = 0.4) +
    geom_vline(xintercept = c(ts, tc, ts2), linetype = "22", colour = PUR, linewidth = 0.4) +
    geom_line(aes(y = d_c, colour = "Center"), linewidth = 0.55) +
    geom_line(aes(y = d_s, colour = "Surface"), linewidth = 0.55, linetype = "42") +
    scale_colour_manual(values = c("Center" = MUT[["blue"]], "Surface" = GRN),
                        name = NULL, guide = guide_legend(keywidth = unit(9, "pt"))) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.06))) +
    labs(x = "Time t / h", y = "Difference δ / %") +
    THB + theme(legend.position = c(0.86, 0.24), legend.direction = "vertical")

  p <- pa / pb + plot_layout(heights = c(1.18, 1))
  save_png(p, file.path(ROOT, "results", "figures", "fig07_baseline_trace.png"), 140, 81)
  invisible(list(t_cross_center_h = tc, t_cross_surf_h = ts, t_cross_surf2_h = ts2,
                 t_first_5pct_h = t5,
                 d_center_max_pct = dmax, t_at_max_h = tmax,
                 d_surf_max_pct = max(m$d_s), t_at_dsurf_max_h = m$t_h[which.max(m$d_s)],
                 d_center_min_pct = dmin, t_at_min_h = m$t_h[which.min(m$d_c)],
                 d_center_48h_pct = m$d_c[nrow(m)]))
}

# -------- 只出本脚本负责的 3 张（图4 见 fig18_ts.m，图5 见 fig_sensitivity.R） --------
requested <- commandArgs(trailingOnly = TRUE)
if (!length(requested) || "env_radius" %in% requested) FIG$env_radius()
if (!length(requested) || "ablpolar" %in% requested) FIG$ablpolar()
