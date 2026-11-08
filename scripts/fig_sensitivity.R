# 第 5 条主角图：外推假设的不确定性来源分解（140 mm 落版）。
#
# 2026-09-25 整图重制。旧版三格是"(a) 裸折线 + (b) 裸折线 + (c) 龙卷风图"，
# 按《论文图表铁律》§G.3 属 0 分基础图（裸折线与龙卷风图都被点名禁），故换形。
# 新四格各承接一句结论（2026-09-25 晚：(a)(b) 两块对调过，理由见下）：
#   (a) 参数系综 —— 512 成员的端点分布族（山脊），标出 2.5–97.5 % 区间
#   (b) 窗口取法 —— 五个窗口画成**嵌套时间条**，压在真实 4 h 记录曲线上
#   (c) 量级阶梯 —— 四类来源的跨度同画在一条对数轴上，直接读出数量级差
#   (d) 参数灵敏度 —— Morris 基本效应区间棒 + S_p 点，对数轴对比例参考线
#
# 为什么把"系综山脊"换到左栏、(b) 与 (a) 对调：patchwork 按**列**对齐各面板的
# 绘图区左沿，而一列里"最宽的那套左侧标签"决定整列的左留白。原来左栏是
# (a) 记录曲线（纵轴刻度只占 4 mm）配 (c) 阶梯（分类标签占 28 mm）⇒ (a) 的刻度
# 数字被推到补齐空档的最右端，两者之间空出 **25 mm 纯白**（量自 140×128 mm 成品）。
# 让左栏两块都"左边宽"——系综山脊的纵轴分组名占 18 mm——空档降到 11 mm，并且
# 四块面板宽度从 38.4/38.4/45.2/45.2 变成 43.5/43.6/45.0/45.0，明显更匀。
# 换位只动位置，不动任何数据；两块的 tag 与图注里的 (a)/(b) 同步换过。
#
# 图内不放任何解释性文字：只留"辨认数据记号所必需的短标签"（窗口时长、区间宽度、
# 分组名、参数名）。四行解释性注记已于 2026-09-25 删除，其读数在正文 §5.5 与图注
# 里逐条给出，删掉不丢信息。轴标题同理按下述办法压掉。
#
# 为什么 (b) 必须画成时间条而不是温度带：记录自 28 °C 陡升至 50 °C 后进平台，
# 五个窗口全落在平台段、均值彼此只差 0.504 °C。若按"温度区间"叠画在 22 °C 的
# 量程里，五条带必然完全重合 —— 信息量为零。窗口的本质是**时间区间**，改画成
# 嵌套时间条后，跨度 1 h↔4 h 的差别一眼可辨。选错编码维度会让图"画得认真但
# 什么都没说"。
#
# 为什么 (c) 的横轴是"跨度(h)"而不是 t_d 本身：离散化差 10.4 s（0.0029 h）与
# 控温极差 7.31 h 同画在绝对 t_d 轴上时，前者是一根看不见的发丝。要比较的量级差
# 超过约两个数量级时，必须比较"量本身"而非"它在绝对轴上的位置"。
#
# 配色语义全图统一：蓝=定半径构型(A)，绿=收缩构型(B)；记录曲线与窗口属"供给物
# 与取法"、不属任一构型，故另起紫系（#7D6FA8 / #B39FDB），避开蓝绿语义。
# ⚠️ fig:env 里温度用蓝 —— 本图若也沿用会让"蓝"同时表示温度与定半径，故不沿用。
# ⚠️ 颜色一律用"按行给定的字面量"，不放进 aes()：放进 aes 会走默认离散色盘，
#    实际画出来的颜色与这里写的十六进制无关（且不报错）。
#
# 各格横轴范围留了右侧文字槽（标签高约 7 mm），不这么留会把数值标签裁掉。

# 仓库根目录：按脚本自身位置定位，克隆到任何路径都能运行
.REPO_ROOT <- local({
  a <- commandArgs(trailingOnly = FALSE)
  m <- grep("^--file=", a, value = TRUE)
  if (length(m)) dirname(normalizePath(sub("^--file=", "", m[1]), mustWork = FALSE)) else getwd()
})
.REPO_ROOT <- dirname(.REPO_ROOT)

Sys.setlocale("LC_ALL", "Chinese (Simplified)_China.utf8")
.libPaths(unique(c("D:/claude项目专属/R-library/4.5", "D:/claude项目专属/R-library",
                   .libPaths())))
suppressPackageStartupMessages({
  library(ggplot2); library(patchwork); library(showtext); library(sysfonts)
})

ROOT <- .REPO_ROOT
FIGD <- file.path(ROOT, "data", "processed", "processed", "figdata")
font_add("nsans", regular = "C:/Windows/Fonts/msyh.ttc",
         bold = "C:/Windows/Fonts/msyhbd.ttc")
showtext_auto(); showtext_opts(dpi = 600)

MUT <- c(blue = "#5E84B9", green = "#4F9E67", purple = "#7D6FA8")
LIT <- c(purple = "#B39FDB")
AX <- "#8A8A8A"; TXT <- "#4A4A4A"; TTL <- "#3C3C3C"
CA <- MUT[["blue"]]; CB <- MUT[["green"]]; CP <- MUT[["purple"]]

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
        plot.tag          = element_text(size = 9, colour = TTL, hjust = 0),
        legend.position   = "none",
        plot.margin       = margin(4, 4, 3, 3))

# ---------------- 数据（全部读源文件，图上每个数都能回溯源数据）---------------
env <- read.csv(file.path(FIGD, "env_att1.csv"), fileEncoding = "UTF-8-BOM")
env$h <- env$t_s / 3600
if (nrow(env) != 241) stop("气象记录应为 241 行（4 h @ 1 min）")

be <- read.csv(file.path(ROOT, "data", "processed", "boundary_extrapolation.csv"),
               fileEncoding = "UTF-8-BOM")
dw <- be[be$kind == "window", ]
dt <- be[be$kind == "temperature", ]

mc <- read.csv(file.path(ROOT, "data", "processed", "mc_ensemble.csv"), fileEncoding = "UTF-8-BOM")
mo <- read.csv(file.path(ROOT, "data", "processed", "morris_screen.csv"), fileEncoding = "UTF-8-BOM")
sp <- read.csv(file.path(FIGD, "sensitivity.csv"), fileEncoding = "UTF-8-BOM")

spread <- function(v) max(v) - min(v)
S_WIN <- c(A = spread(dw$A_fixed_h), B = spread(dw$B_shrinking_h))
S_TMP <- c(A = spread(dt$A_fixed_h), B = spread(dt$B_shrinking_h))
# 离散化差（s → h）：正文"数值可复现性"首句给出两实现端点差 10.379 s / 3.147 s
S_DSK <- c(A = 10.379, B = 3.147) / 3600
ENSR <- lapply(c(A = "q3", B = "q4"), function(q) {
  v <- mc$td_h[mc$question == q]
  if (length(v) != 512) stop(sprintf("%s 应有 512 个成员", q))
  list(v = v, q = unname(quantile(v, c(.025, .975))), mean = mean(v))
})
S_ENS <- sapply(ENSR, function(r) diff(r$q))

# ---------------- (b) 窗口取法：真实记录 + 嵌套时间条 ----------------
# 五窗口的时间区间（右端都锚在记录末点 t=4 h）
WSPAN <- data.frame(
  key = c("末3h", "末2h", "末1h", "末30min", "最后一点"),
  # 标签只能写在每根条的左端之前，而最长那根条从 t=1 h 起（左边只剩 9 mm），
  # 写不下"last 3 h"（12.4 mm）。故只留时长，由轴与图注交代"都是取到记录末点"。
  lab = c("3 h", "2 h", "1 h", "30 min", "final sample"),
  x0  = c(1.0, 2.0, 3.0, 3.5, 4.0),
  lvl = c(5, 4, 3, 2, 1),          # 自下而上：最长跨度在底
  stringsAsFactors = FALSE)
WSPAN$x1 <- 4.0
WSPAN$Tp <- dw$T_plat_C[match(WSPAN$key, sub("^窗口·", "", dw$scenario))]
if (anyNA(WSPAN$Tp)) stop("窗口名与源数据对不上")
Y0 <- 27.6; DY <- 1.90               # 时间条带的纵向基线/间距
WSPAN$y <- Y0 + (WSPAN$lvl - 1) * DY
# "最后一点"的条长为零、只余一个菱形点，标签要再退开些才不压到点上
WSPAN$lx <- WSPAN$x0 - ifelse(WSPAN$lvl == 1, 0.20, 0.06)

pa <- ggplot() +
  # 记录曲线：本条数据本身，非任一构型
  geom_line(data = env, aes(h, T_amb_C), colour = CP, linewidth = 0.55) +
  # 嵌套时间条：每窗一条，右端对齐记录末点，左端向右递退成阶梯
  geom_segment(data = WSPAN, aes(x = x0, xend = x1, y = y, yend = y),
               colour = LIT[["purple"]], linewidth = 1.7, lineend = "butt") +
  geom_segment(data = WSPAN[WSPAN$lvl >= 2, ],
               aes(x = x1, xend = x1, y = y - 0.42, yend = y + 0.42),
               colour = CP, linewidth = 0.35) +
  geom_point(data = WSPAN[WSPAN$key == "最后一点", ], aes(x1, y),
             colour = CP, shape = 18, size = 1.9) +
  geom_text(data = WSPAN, aes(x = lx, y = y, label = lab),
            hjust = 1, size = 2.6, colour = CP, family = "nsans") +
  # 面板内不写任何解释性文字（"window means / span 0.50 °C / endpoint spread /
  # 0.9047 / 0.7895 h" 四行 2026-09-25 删除）：图内只留承载数据的记号与
  # 逐条辨认数据记号所必需的短标签，数字与解释一律下移正文。四行原位置
  # 对应的读数在正文 §5.5 与图注里已逐条给出，删掉不丢信息。
  scale_x_continuous(breaks = 0:4, limits = c(0, 4.02), expand = c(0, 0)) +
  # 纵轴不写轴标题、把单位并进最上一个刻度。原因：patchwork 把左列两块面板的
  # 绘图区左沿对齐到 (c) 那条 20 mm 宽的分组标签，于是 (a) 的轴标题被推到补齐
  # 空档的最外侧，标题与轴之间空出约 25 mm（量自 140 × 128 mm 成品 PNG，
  # 标题墨迹止于 10.1 mm、刻度标签起于 35.3 mm）。删掉轴标题后这段空档整体消失，
  # 面板反而宽了 2 mm。单位改由最上一个刻度承担，图注另行点名该面板是温度。
  scale_y_continuous(breaks = seq(30, 50, 10),
                     labels = c("30", "40", "50 °C")) +
  coord_cartesian(ylim = c(26.0, 51.2), expand = FALSE) +
  labs(x = "Time from start of record / h", y = NULL, tag = "(b)") +
  TH

# ---------------- (a) 512 成员参数系综：端点分布族 ----------------
dens01 <- function(v, from, to, base, ht) {
  d <- density(v, from = from, to = to, n = 600)
  data.frame(x = d$x, y = base + ht * d$y / max(d$y))
}
XB0 <- 45.6; XB1 <- 66.0     # 右端留出 9.3 mm 给"4.86 h / 7.86 h"标签
RIDGE <- list(A = list(base = 2.30, ht = 0.60, bar = 2.02),
              B = list(base = 1.16, ht = 0.60, bar = 0.88))
BA <- dens01(ENSR$A$v, XB0, XB1, RIDGE$A$base, RIDGE$A$ht)
BB <- dens01(ENSR$B$v, XB0, XB1, RIDGE$B$base, RIDGE$B$ht)

barrows <- do.call(rbind, lapply(c("A", "B"), function(k) {
  r <- RIDGE[[k]]; q <- ENSR[[k]]$q
  data.frame(x0 = q[1], x1 = q[2], y = r$bar, w = diff(q), pt = ENSR[[k]]$mean)
}))
barrows$col <- c(CA, CB)
barrows$lab <- sprintf("%.2f h", barrows$w)

pb <- ggplot() +
  # 山脊必须用 ribbon(ymin = 各自基线)，不能用 geom_area：area 一律从 y=0 填起，
  # 两条山脊会互相盖住，看着像一整块色斑 —— 且 ggplot 不报任何警告。
  geom_ribbon(data = BA, aes(x, ymin = RIDGE$A$base, ymax = y), fill = CA, alpha = 0.28) +
  geom_line(data = BA, aes(x, y), colour = CA, linewidth = 0.55) +
  geom_ribbon(data = BB, aes(x, ymin = RIDGE$B$base, ymax = y), fill = CB, alpha = 0.28) +
  geom_line(data = BB, aes(x, y), colour = CB, linewidth = 0.55) +
  # 2.5–97.5 % 区间棒：把"点估计"升级成"区间报告"
  geom_segment(data = barrows, aes(x = x0, xend = x1, y = y, yend = y),
               colour = barrows$col, linewidth = 0.5) +
  geom_segment(data = barrows, aes(x = x0, xend = x0, y = y - 0.13, yend = y + 0.13),
               colour = barrows$col, linewidth = 0.5) +
  geom_segment(data = barrows, aes(x = x1, xend = x1, y = y - 0.13, yend = y + 0.13),
               colour = barrows$col, linewidth = 0.5) +
  geom_point(data = barrows, aes(pt, y), colour = barrows$col, shape = 16, size = 1.4) +
  geom_text(data = barrows, aes(x = x1 + 0.28, y = y, label = lab),
            hjust = 0, size = 2.6, colour = barrows$col, family = "nsans") +
  # 族名放在纵轴上、与各自基线齐平：写进图里会横跨整条山脊（山脊横向只占
  # 43 mm，而"B, prescribed shrinkage"占 30 mm），纵轴分组标签是本来的读法。
  scale_x_continuous(breaks = seq(48, 64, 4), limits = c(XB0, XB1), expand = c(0, 0)) +
  scale_y_continuous(breaks = c(RIDGE$A$base, RIDGE$B$base),
                     labels = c("A, fixed\nradius", "B, prescribed\nshrinkage"),
                     limits = c(0.62, 3.05), expand = c(0, 0)) +
  labs(x = expression("Predicted endpoint " * t[d] * " / h"),
       y = NULL, tag = "(a)") +
  TH

# ---------------- (c) 量级阶梯：四类来源的跨度同一条对数轴 ----------------
SRC <- c("Chamber temperature, ±2 °C", "Parameter ensemble, 2.5–97.5 %",
         "Window choice", "Discretization difference")
WID <- c(S_TMP[["A"]], S_TMP[["B"]], S_ENS[["A"]], S_ENS[["B"]],
         S_WIN[["A"]], S_WIN[["B"]], S_DSK[["A"]], S_DSK[["B"]])
# expand.grid 首列变最快：A/B 交替，与 WID 的排列一一对应
LAD <- expand.grid(cfg = c("A", "B"), src = SRC, stringsAsFactors = FALSE)[, c(2, 1)]
LAD$w <- WID
if (anyNA(LAD$w)) stop("阶梯数据缺失")
# 分类轴必须"从下往上"排：让最小的离散化差落在 y=1、最大的控温跨度落在 y=4，
# 阶梯才顺着"量级由小到大"向上长。反转 level 时标签必须同步反转 —— 两处只改一处
# 会让标签与柱子上下颠倒，而 ggplot 不会报错（第一版就是这么错的）。
SLAB <- c("Chamber temperature\n±2 °C", "Parameter ensemble\n2.5–97.5 %",
          "Window choice", "Discretization\ndifference")
LAD$src <- factor(LAD$src, levels = rev(SRC))
LAD$y   <- as.numeric(LAD$src) + ifelse(LAD$cfg == "A", 0.17, -0.17)
LAD$col <- ifelse(LAD$cfg == "A", CA, CB)
LAD$txt <- ifelse(LAD$w < 1 / 60, sprintf("%.1f s", LAD$w * 3600),
                  sprintf("%.2f h", LAD$w))

# 轴量程不是"够放数据"就行，还要给右端的数值列留够位置。全部柱落在
# 8.7e-4 ~ 7.86 h 之间（7 个数量级），若把右端设成 45 h，最长那根柱的标签只剩
# 3.5 mm 而字要 9 mm —— 必被裁。取 5e-4 ~ 300 h（5.78 个数量级 / 43.1 mm
# = 7.5 mm 每数量级），右端就空出 10.8 mm 的数值列，柱身仍占左 73 %。
# 柱的起点必须落在 limits 之内：写成 1e-6（轴外）会让 8 根柱被整片剔除，
# ggplot 只丢一句 "Removed 8 rows" 的 warning，图上是一片空白。
XLOC <- 5.2e-4; XHIC <- 300       # 贴着轴左沿起笔，使四组棒共用同一"零线"
XLAB <- 10.8                       # 数值列：固定在最长柱(7.86 h)右侧，列内对齐
pc <- ggplot(LAD) +
  geom_segment(aes(x = XLOC, xend = w, y = y, yend = y), colour = LAD$col,
               linewidth = 1.5, lineend = "butt") +
  geom_point(aes(w, y), colour = LAD$col, shape = 16, size = 1.7) +
  # 数值列固定在 XLAB 而非贴着柱尾：贴柱尾时窗口那两行的标签会正好压在 1 h
  # 参考虚线上（只差 0.7 mm），且列不齐、读起来不像一张表。
  geom_text(aes(x = XLAB, y = y, label = txt), hjust = 0, size = 2.6,
            colour = LAD$col, family = "nsans") +
  annotate("segment", x = 1, xend = 1, y = 0.45, yend = 4.55,
           colour = AX, linewidth = 0.3, linetype = "dashed") +
  annotate("text", x = 1.06, y = 4.74, hjust = 0, size = 2.6, colour = AX,
           label = "1 h") +
  scale_x_log10(limits = c(5e-4, XHIC),
                breaks = c(1e-3, 1e-2, 1e-1, 1, 10),
                labels = expression(10^-3, 10^-2, 10^-1, 1, 10)) +
  scale_y_continuous(breaks = 1:4, limits = c(0.4, 4.92), labels = rev(SLAB)) +
  labs(x = "Spread in endpoint / h", y = NULL, tag = "(c)") +
  TH + theme(axis.text.y = element_text(size = 7.4, lineheight = 0.92),
             axis.text.x = element_text(size = 7.4))

# ---------------- (d) 参数灵敏度：基本效应区间 + S_p 点 ----------------
# morris_screen.csv 扫了六个量：四个物性参数 D / h_m / h / λ，外加两个边界状态
# C（水分输入）与 T（控温）。后两个不是物性参数，其影响已由 (c) 的"控温 ±2 °C"
# 与表 3 的 Moisture input 族承担；且 sensitivity.csv 不给它们的 S_p。若一并画入，
# 每根区间棒就配不上同名的 S_p 点，且"物性参数"与"假设环境"两类会串台 ——
# 而拆开这两类正是本条目的全部意思。故这里只留四个物性参数。
PLAB <- c(D = "D", hm = "italic(h)[m]", h = "italic(h)", lam = "lambda")
PL   <- unname(PLAB)
mo <- mo[mo$param %in% names(PLAB), ]
mo$plab <- PLAB[mo$param]
if (anyNA(mo$plab)) stop("Morris 参数名与 PLAB 对不上")
mo$yb <- match(mo$plab, PL)
if (anyNA(mo$yb)) stop("参数名与 PL 对不上")
mo$y   <- -mo$yb + ifelse(mo$config == "A", 0.17, -0.17)
mo$col <- ifelse(mo$config == "A", CA, CB)
mo$lo  <- pmin(abs(mo$ee_min), abs(mo$ee_max))
mo$hi  <- pmax(abs(mo$ee_min), abs(mo$ee_max))
mo$Sp  <- NA_real_
for (i in seq_len(nrow(mo))) {
  r <- sp[sp$question == ifelse(mo$config[i] == "A", "q3", "q4") &
            sp$param == mo$param[i], ]
  r <- r[!is.na(r$S_p), ]
  if (nrow(r) == 1) mo$Sp[i] <- abs(r$S_p)
}
if (anyNA(mo$Sp)) stop("有参数查不到 S_p")

pd <- ggplot(mo) +
  geom_segment(aes(x = lo, xend = hi, y = y, yend = y), colour = mo$col,
               linewidth = 1.6, lineend = "butt") +
  geom_segment(aes(x = lo, xend = lo, y = y - 0.11, yend = y + 0.11), colour = mo$col,
               linewidth = 0.45) +
  geom_segment(aes(x = hi, xend = hi, y = y - 0.11, yend = y + 0.11), colour = mo$col,
               linewidth = 0.45) +
  geom_point(aes(Sp, y), colour = mo$col, shape = 16, size = 1.7) +
  annotate("segment", x = 1, xend = 1, y = -4.20, yend = -0.62,
           colour = AX, linewidth = 0.3, linetype = "dashed") +
  annotate("text", x = 0.90, y = -4.58, hjust = 1, size = 2.6, colour = AX,
           label = "proportional") +
  scale_x_log10(limits = c(7e-4, 4.0), breaks = c(1e-3, 1e-2, 1e-1, 1),
                labels = expression(10^-3, 10^-2, 10^-1, 1)) +
  scale_y_continuous(limits = c(-4.95, -0.35), breaks = -c(1, 2, 3, 4),
                     labels = parse(text = PLAB)) +
  labs(x = expression("|" * S[p] * "| and Morris range"), y = NULL, tag = "(d)") +
  TH

# ---------------- 文字越界自检（写在拼装前，供下面的 chk_fit 用）----------------
# 面板绘图区的实际毫米宽，自 140 × 128 mm 成品的 PNG 上量边框得到（不是标称值：
# patchwork 把 140 mm 切成两栏后，还要扣掉轴标题、刻度与轴标签）。
# ⚠️ 改动布局（列宽、字号、轴标题长短）都会改变这四个数，必须重新量并更新。
# 2026-09-25 去掉 (b) 的轴标题与四行注记、并把 (a)(b) 对调后重量的值
# （三轮的旧值依次 36.3/36.4/43.1/43.1、38.3/38.3/45.0/45.1）。
CHW <- 1.55                                    # mm/字符，2.6 mm 字号实测
PW  <- c(a = 43.4, b = 43.4, c = 44.9, d = 44.9)
# 各面板把"数据坐标"换算成"距面板左沿 mm"的函数
XA <- c(0, 4.02)                               # (a) 线性轴
XB <- c(XB0, XB1)                              # (b) 线性轴
XC <- c(5e-4, XHIC); XD <- c(7e-4, 4.0)        # (c)(d) 对数轴
f_lin <- function(x, lim, w) (x - lim[1]) / diff(lim) * w
f_log <- function(x, lim, w) (log10(x) - log10(lim[1])) / diff(log10(lim)) * w

FITS <- list()
note_fit <- function(panel, start_mm, label, where)
  FITS[[length(FITS) + 1]] <<- data.frame(
    panel = panel, start = start_mm, need = nchar(label) * CHW,
    where = where, label = label, stringsAsFactors = FALSE)

for (i in seq_len(nrow(WSPAN))) {              # (b) 窗口名，右对齐于 lx
  note_fit("b", f_lin(WSPAN$lx[i], XA, PW[["b"]]) - nchar(WSPAN$lab[i]) * CHW,
           WSPAN$lab[i], "b 窗口名")
}
for (i in seq_len(nrow(barrows)))              # (a) 区间棒宽度标签
  note_fit("a", f_lin(barrows$x1[i] + 0.28, XB, PW[["a"]]), barrows$lab[i], "a 宽度标签")
for (i in seq_len(nrow(LAD)))                  # (c) 数值列
  note_fit("c", f_log(XLAB, XC, PW[["c"]]), LAD$txt[i], "c 数值列")
note_fit("c", f_log(1.06, XC, PW[["c"]]), "1 h", "c 参考线标注")
note_fit("d", f_log(0.90, XD, PW[["d"]]) - nchar("proportional") * CHW,
         "proportional", "d 参考线标注")

FT <- do.call(rbind, FITS)
FT$end <- FT$start + FT$need
bad <- FT[FT$start < -0.01 | FT$end > PW[FT$panel] + 0.01, ]
if (nrow(bad) > 0) {
  print(bad[, c("panel", "where", "label", "start", "need", "end")])
  stop(sprintf("%d 行文字越出面板边界（面板宽 %s）—— 图上会被静默裁掉",
               nrow(bad), paste(sprintf("%s=%.1f", names(PW), PW), collapse = " ")))
}
cat(sprintf("\n[自检] %d 行图内文字全部落在面板内（最紧一行余 %.1f mm）\n",
            nrow(FT), min(PW[FT$panel] - FT$end)))

# ---------------- 拼装：2×2（左栏放"左边宽"的两块，见文件头说明）----------------
p <- (pb | pa) / (pc | pd)
p <- p + plot_layout(heights = c(1.0, 0.96))

save_png <- function(p, path, w_mm, h_mm) {
  ggsave(path, p, width = w_mm / 25.4, height = h_mm / 25.4,
         dpi = 600, bg = "white", limitsize = FALSE)
  tif <- sub("\\.png$", ".tif", path)
  ggsave(tif, p, width = w_mm / 25.4, height = h_mm / 25.4,
         dpi = 600, bg = "white", limitsize = FALSE,
         device = "tiff", compression = "lzw")
  cat(sprintf("  -> %-28s %7.0f kB\n", basename(path), file.size(path) / 1024))
}

save_png(p, file.path(ROOT, "results", "figures", "fig21_sensitivity.png"), 140, 128)

# ---------------- 自检：图上标出的数必须与源数据一致 ----------------
cat("\n[自检] 图上每个标注值均自源数据重算，与正文/数值总表逐位比对\n")
cat(sprintf("  (b) 窗口温度跨度 %.4f °C   窗口极差 A=%.4f h  B=%.4f h\n",
            spread(dw$T_plat_C), S_WIN[["A"]], S_WIN[["B"]]))
cat(sprintf("  (a) 系综 A n=%d 均值 %.4f h  2.5-97.5%% %.4f-%.4f  宽 %.4f h\n",
            length(ENSR$A$v), ENSR$A$mean, ENSR$A$q[1], ENSR$A$q[2], S_ENS[["A"]]))
cat(sprintf("  (a) 系综 B n=%d 均值 %.4f h  2.5-97.5%% %.4f-%.4f  宽 %.4f h\n",
            length(ENSR$B$v), ENSR$B$mean, ENSR$B$q[1], ENSR$B$q[2], S_ENS[["B"]]))
cat(sprintf("  (c) 阶梯 A：离散 %.4f s  窗口 %.4f h  系综 %.4f h  控温 %.4f h\n",
            S_DSK[["A"]] * 3600, S_WIN[["A"]], S_ENS[["A"]], S_TMP[["A"]]))
cat(sprintf("      最大/最小 = %.0f 倍  （%.1f s 对 %.2f h）\n",
            max(S_TMP[["A"]], S_ENS[["A"]]) / S_DSK[["A"]],
            S_DSK[["A"]] * 3600, max(S_TMP[["A"]], S_ENS[["A"]])))
cat("  (d) Morris 基本效应极差（区间棒）与 S_p（点）配对核验：\n")
print(data.frame(param = mo$plab, cfg = mo$config,
                 ee_range = sprintf("%.4f-%.4f", mo$lo, mo$hi),
                 Sp = sprintf("%.4f", mo$Sp)))
