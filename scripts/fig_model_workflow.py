"""Colour schematic for the drying model and analysis flow.

The palette matches figures_ts.R. Run with D:\\daima\\python.exe.
"""

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
BASE = OUT / "fig01_model_workflow"
BLUE, RED, GREEN, PURPLE = "#5E84B9", "#C27472", "#4F9E67", "#7D6FA8"
PALE = {BLUE: "#EAF1FA", RED: "#FAEDEC", GREEN: "#EAF5ED", PURPLE: "#F1EDF8"}
TEXT, GREY = "#3C3C3C", "#8A8A8A"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5,
                     "pdf.fonttype": 42, "ps.fonttype": 42})
fig = plt.figure(figsize=(5.51, 2.8), facecolor="white")  # 140 mm wide
left = fig.add_axes((0.015, 0.035, 0.49, 0.93))
right = fig.add_axes((0.55, 0.035, 0.435, 0.93))
for ax in (left, right):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
left.set_aspect("equal", adjustable="box")

def txt(ax, x, y, s, **kw):
    kw.setdefault("color", TEXT)
    ax.text(x, y, s, va="center", **kw)

def arr(ax, start, end, color, lw=1.3, ms=9):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                 mutation_scale=ms, lw=lw, color=color,
                 shrinkA=0, shrinkB=0))

txt(left, 0.02, 0.955, "(a) Radial model", fontsize=8.5,
    fontweight="bold", ha="left")
cx, cy = 0.43, 0.53
left.add_patch(Circle((cx, cy), 0.305, fill=False, ec=GREY,
                      lw=1.0, ls=(0, (4, 3))))
left.add_patch(Circle((cx, cy), 0.255, fc="#F9F9F9", ec=PURPLE, lw=2.0))
left.plot(cx, cy, "o", color=TEXT, ms=3)
arr(left, (cx, cy), (0.635, cy), PURPLE, lw=1.0, ms=7)
txt(left, 0.43, 0.44, r"$r=0$", fontsize=7, ha="center")
txt(left, 0.55, 0.57, r"$r$", fontsize=8, ha="center")
txt(left, 0.075, 0.78, r"$R_\lambda(t)$", fontsize=7.3,
    ha="left", color=PURPLE)
txt(left, 0.08, 0.18, r"$R_0$", fontsize=7.3, ha="left")
arr(left, (0.89, 0.805), (0.635, 0.68), BLUE)
txt(left, 0.83, 0.88, "heat in", fontsize=7.3, ha="center", color=BLUE)
arr(left, (0.665, 0.385), (0.89, 0.29), RED)
txt(left, 0.80, 0.205, "moisture out", fontsize=7.3,
    ha="center", color=RED)
txt(left, 0.44, 0.08, r"$t_d$: max $C\leq C_{cr}$", fontsize=7.2,
    ha="center")

txt(right, 0.02, 0.955, "(b) Analysis workflow", fontsize=8.5,
    fontweight="bold", ha="left")

def box(y, title, subtitle, color):
    right.add_patch(FancyBboxPatch((0.055, y), 0.89, 0.15,
                    boxstyle="round,pad=0.005,rounding_size=0.014",
                    ec=color, fc=PALE[color], lw=1.1))
    txt(right, 0.085, y + 0.105, title, fontsize=7.7,
        fontweight="bold", ha="left")
    txt(right, 0.085, y + 0.045, subtitle, fontsize=7.0, ha="left")

box(0.745, "Prescribed inputs", "air + radius + A/B properties", BLUE)
box(0.53, r"$2\times2$ model runs", "A/B  ×  fixed/shrinking", PURPLE)
box(0.315, "Numerical checks", "FEM + analytic + refinement", GREEN)
box(0.10, "Conditional results", "uncertainty + dry-mass test", RED)
for y0, y1 in ((0.74, 0.695), (0.525, 0.48), (0.31, 0.265)):
    arr(right, (0.50, y0), (0.50, y1), GREY, lw=1.0, ms=7)

pdf_path = OUT / "fig01_model_workflow.pdf"
fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.025)
fig.savefig(BASE.with_suffix(".png"), dpi=600,
            bbox_inches="tight", pad_inches=0.025)
fig.savefig(BASE.with_suffix(".tif"), dpi=600,
            bbox_inches="tight", pad_inches=0.025,
            pil_kwargs={"compression": "tiff_lzw"})
plt.close(fig)
print(BASE)
