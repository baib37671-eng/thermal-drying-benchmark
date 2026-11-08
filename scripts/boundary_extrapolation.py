# 第 5 条：把"4 h 后按平台延拓"这条外推假设的不确定性拆开量化。
#
# 要回答两个分开的问题：
#   ① 平台窗口怎么取（末 30 min / 末 1 h / 末 2 h / 末 3 h / 最后一点）—— 这是"策略"侧
#   ② 烘房控温偏多少（-2…+2 °C）—— 这是"物理"侧
# 两者都只用附件1 的记录，不引入题面之外的新物理项。求解器不改，只在进程内换 env。

import csv
import inspect
import os
import sys
import time

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OUT_DIR = os.path.join(ROOT, "results", "tables")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE_CODE = os.path.join(ROOT, "src")
os.environ["HERB_SRC"] = os.path.join(ROOT, "data", "raw")

import openpyxl.worksheet.worksheet as worksheet
old_iter_rows = worksheet.Worksheet.iter_rows
if "values_only" not in inspect.signature(old_iter_rows).parameters:
    worksheet.Worksheet.iter_rows = lambda self, **kwargs: (
        tuple(cell.value for cell in row) for row in old_iter_rows(self)
    )

sys.path.insert(0, SOURCE_CODE)
import 公共 as model

BASE_ENV = model.env
T0 = float(model.T1_END)          # 附件1 记录跨度 14400 s
PLAT_T = float(model.TA_PLAT)     # 末 1 h 平台均值
PLAT_C = float(model.CA_PLAT)

CASES = (("A_fixed", 3, False), ("B_shrinking", 4, True))
SOLVE = dict(Nc=1600, dt=7.5, tmax=4.0e5, Ccr=0.15, stop_at_hit=True)

WINDOWS = [
    ("末30min", 0.5),
    ("末1h", 1.0),          # 现状基准，须与 57.475473 / 51.095835 对上
    ("末2h", 2.0),
    ("末3h", 3.0),
    ("最后一点", 0.0),       # 0 = 只取记录最后一个采样点
]
DTEMP = [-2.0, -1.0, 0.0, 1.0, 2.0]


def window_stats(hours):
    """返回该窗口内 T∞/C∞ 的均值；hours=0 表示只取最后一个采样点。"""
    t = np.asarray(model._T1, float)
    Ta = np.asarray(model._Ta, float)
    Ca = np.asarray(model._Ca, float)
    if hours == 0:
        return float(Ta[-1]), float(Ca[-1]), 1
    m = t >= (T0 - hours * 3600.0)
    return float(Ta[m].mean()), float(Ca[m].mean()), int(m.sum())


def make_env(plat_t, plat_c):
    def env(t, kappa=1.0):
        T, C = BASE_ENV(t, kappa)
        tt = np.asarray(t, float)
        return (np.where(tt <= T0, T, plat_t + 273.15),
                np.where(tt <= T0, C, plat_c * kappa))
    return env


def run(label, plat_t, plat_c):
    model.env = make_env(plat_t, plat_c)
    row = {"scenario": label, "T_plat_C": plat_t, "C_plat": plat_c}
    t0 = time.time()
    for name, case, shrink in CASES:
        row[name] = float(model.solve1d(case=case, shrink=shrink, **SOLVE)["td_h"])
    model.env = BASE_ENV
    row["d_pct"] = 100.0 * (row["B_shrinking"] - row["A_fixed"]) / row["A_fixed"]
    print("%-14s T=%8.4f  A=%10.6f  B=%10.6f  Δ=%6.2f%%  (%.0f s)" % (
        label, plat_t, row["A_fixed"], row["B_shrinking"], row["d_pct"],
        time.time() - t0))
    return row


print("平台窗口端点温度（附件1 记录内实测均值）")
rows = []
for wname, wh in WINDOWS:
    pt, pc, n = window_stats(wh)
    print("  %-8s  T=%8.4f °C  C=%.8f kg/kg  n=%d" % (wname, pt, pc, n))
    rows.append(run("窗口·" + wname, pt, pc))

print("\n控温偏差（平台温度整体平移，窗口固定为末 1 h）")
for dt in DTEMP:
    rows.append(run("控温%+.0f°C" % dt, PLAT_T + dt, PLAT_C))

# ---- 记录内趋势：逐小时分段线性斜率，用于说明"4 h 内是否已达稳态" ----
t = np.asarray(model._T1, float)
Ta = np.asarray(model._Ta, float)
slopes = []
for k in range(4):
    m = (t >= k * 3600.0) & (t <= (k + 1) * 3600.0)
    s = float(np.polyfit(t[m] / 3600.0, Ta[m], 1)[0])
    slopes.append((k + 1, s, float(Ta[m].std()), int(m.sum())))

print("\n附件1 逐小时分段线性斜率")
for h, s, sd, n in slopes:
    print("  %d–%d h  dT/dt = %+9.4f °C/h   sd=%6.4f  n=%d" % (h - 1, h, s, sd, n))

os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "boundary_extrapolation.csv")
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["scenario", "kind", "T_plat_C", "C_plat_kgkg",
                "A_fixed_h", "B_shrinking_h", "B_minus_A_pct"])
    for r in rows:
        w.writerow([r["scenario"],
                    "window" if r["scenario"].startswith("窗口") else "temperature",
                    "%.6f" % r["T_plat_C"], "%.8f" % r["C_plat"],
                    "%.6f" % r["A_fixed"], "%.6f" % r["B_shrinking"],
                    "%.4f" % r["d_pct"]])
print("\n写出", out)

side = os.path.join(OUT_DIR, "boundary_trend.csv")
with open(side, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["hour_bin", "dT_dt_C_per_h", "sd_C", "n"])
    for h, s, sd, n in slopes:
        w.writerow([h, "%.6f" % s, "%.6f" % sd, n])
print("写出", side)
