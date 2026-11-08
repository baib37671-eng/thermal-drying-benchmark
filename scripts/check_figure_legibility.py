# -*- coding: utf-8 -*-
"""
check_figure_legibility.py -- 图内文字印刷字号核验（vault《图内文字放大与静默丢字》）

  printed_pt = 源字号 × 落版宽 / 图自身物理宽

落版宽从 main_ts.tex 的 \\includegraphics[width=NNNmm] 反读；图自身物理宽从 PNG
反算（px / dpi × 25.4），不用 figure('Position') 标称的 cm —— exportgraphics 会裁到
内容框，标称宽与实出宽不是一回事（fig18 标称 140 mm，实出 129.7 mm）。

源字号必须逐条锚定到生成脚本里的原文，锚点找不到就报错：这样脚本改了字号而本表
没跟会被抓住，而不是让本表悄悄给出一个过期数字（"注释里写的一致"不是一致）。

判据两条：落版宽 <= 140 mm；印刷最小字 >= 6.5 pt（该刊图内文字下限 2 mm ≈ 5.67 pt，
6.5 pt 是本项目自设的更高目标）。
"""
import io
import os
import re
import sys

from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "main_ts.tex")
FIGDIR = os.path.join(HERE, "figures")
LIMIT_MM = 140.0
FLOOR_PT = 5.67     # 该刊图内文字下限 2 mm —— 低于此判失败
TARGET_PT = 6.5     # 本项目自设目标（Nature/Cell 区间的下沿）—— 低于此仅提示
DPI = {"fig18_crosscheck": 600.0}    # MATLAB exportgraphics Resolution
DPI_DEFAULT = 600.0                  # R ggsave dpi

# 每张图的"最小源字号"及其锚点：(pt, 生成脚本, 锚点原文, 说明)
# 键用不带扩展名的完整文件名，不能用 "figNN" 前缀：本文保留了历史文件名，
# fig02 与 fig07 各有两张（env_radius/method、baseline_trace/closure），按前缀
# 取键会让后一张静默顶掉前一张，并把锚点配到不属于它的文件上。
SRC_PT = {
    "fig02_env_radius": (8.0, "figures_ts.R",
                         "axis.text         = element_text(colour = TXT, size = 8)",
                         "TH 的 axis.text / legend.text"),
    "fig07_baseline_trace": (8.5, "figures_ts.R",
                             "legend.text = element_text(size = 8.5, colour = TXT)",
                             "THB 的 legend.text"),
    "fig13_ablation_field": (8.0, "figures_ts.R",
                             "strip.text = element_text(size = 8, colour = TTL)",
                             "该块的 strip.text"),
    "fig18_crosscheck": (6.5, "fig18_ts.m",
                         "'FontSize', 6.5,",
                         "面板 (b)(c)(d) 的图例、构型名与 inset 注记；标题轴标为 FS=7"),
    "fig21_sensitivity": (7.4, "fig_sensitivity.R",
                          'size = 2.6, colour',
                          "annotate() 的 size 单位是 mm ⇒ 2.6 mm = 7.37 pt"),
}

tex = io.open(TEX, encoding="utf-8").read()
placed = {}
for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}", tex):
    name = m.group(1)
    stem = os.path.splitext(name)[0]
    w = re.search(r"width\s*=\s*([\d.]+)\s*mm", m.group(0))
    if not w:
        sys.exit("!! %s 没有固定 width（单位为 mm）——印刷字号无法确定" % name)
    placed[stem] = (name, float(w.group(1)))

fails = []
rows = []
skipped = []
for stem in sorted(placed):
    name, lay_mm = placed[stem]
    p = os.path.join(FIGDIR, name)
    if not os.path.exists(p):
        fails.append("%s 不在盘上" % name)
        continue
    # 示意类图（fig01/fig02_method/fig07_closure，由 prepare_three_schematics.py 画）
    # 的字号写在图内布局里、不由数据图脚本的 'FontSize' 参数统一控制，本表不锚定。
    # 这里显式列出而不静默跳过：漏掉谁要看得见。
    if stem not in SRC_PT:
        skipped.append(name)
        continue
    img = Image.open(p)
    px_w = img.width
    img.close()
    dpi = DPI.get(stem, DPI_DEFAULT)
    own_mm = px_w / dpi * 25.4
    scale = lay_mm / own_mm
    pt, gen, anchor, why = SRC_PT[stem]
    gp = os.path.join(HERE, gen)
    src = io.open(gp, encoding="utf-8").read()
    if anchor not in src:
        fails.append("%s 的源字号锚点在 %s 里找不到（脚本改过而本表没跟）：%r"
                     % (stem, gen, anchor))
        continue
    rows.append((name, px_w, own_mm, lay_mm, scale, pt, pt * scale, why))

print("{:<28} {:>7} {:>8} {:>8} {:>7} {:>7} {:>11}".format(
    "文件", "px宽", "图宽mm", "落版mm", "缩放", "源字号", "印刷最小字"))
for name, px_w, own_mm, lay_mm, scale, pt, printed, why in rows:
    flag = ""
    if lay_mm > LIMIT_MM + 0.05:
        flag += "  << 超 %.0fmm" % LIMIT_MM
        fails.append("%s 落版宽 %.1f mm 超过 %.0f mm" % (name, lay_mm, LIMIT_MM))
    if printed < FLOOR_PT:
        flag += "  << 低于该刊下限 %.2fpt" % FLOOR_PT
        fails.append("%s 印刷最小字 %.2f pt 低于该刊下限 %.2f pt" % (name, printed, FLOOR_PT))
    elif printed < TARGET_PT:
        flag += "  -- 低于自设目标 %.1fpt，仍高于该刊下限" % TARGET_PT
    print("{:<28} {:>7} {:>8.1f} {:>8.1f} {:>7.3f} {:>7.1f} {:>10.2f}pt{}".format(
        name, px_w, own_mm, lay_mm, scale, pt, printed, flag))
    print("{:<28} 源字号依据：{}".format("", why))

print()
if skipped:
    print("未收录（示意类，字号不由数据图脚本的 'FontSize' 控制，本表不锚定）：")
    for s in skipped:
        print("  - " + s)
    print()
print("判据：落版宽 <= %.0f mm；印刷最小字 >= %.2f pt（该刊下限），目标 >= %.1f pt"
      % (LIMIT_MM, FLOOR_PT, TARGET_PT))
if fails:
    print()
    for s in fails:
        print("失败：" + s)
    sys.exit(1)
print("源字号锚点 %d 条全部命中生成脚本。" % len(SRC_PT))
