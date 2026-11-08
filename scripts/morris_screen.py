# Morris 全局筛选：把 §3.5 的"联合区间有多宽"升级成"这宽度里谁占多少"。
#
# 动机：现稿 §3.5 的一参数系数 S_p 与 16 次蒙特卡洛都用**一律 ±5%** 的扰动带。
# 那个排序里有多少是模型真实性质、有多少是"一律 ±5%"这个口径造出来的，现有结果答不了。
# Morris 的基本效应 μ*（|EE| 均值）与 σ（EE 标准差）能回答两件事：
#   μ* 与同带内的 S_p 一致 ⇒ 响应在带内近似线性，一参数排序即是全局排序（口径没问题）；
#   σ/μ* 不小 ⇒ 存在交互/非线性，一参数排序不可外推到联合扰动。
#
# 关键：**不用源文件里的 _push_props**（该函数缺 global 声明，已不可用，会抛
# UnboundLocalError）。这里改成对模块属性直接赋值 props / HM / H_Q / env，
# 并在 finally 里还原；开始处先用已发表的 S_p 端点做逐位校验，校验不过就退出。
#
# 参数带：D / h_m / h / λ（仅收缩）/ C∞ 取乘性 ±BAND，T∞ 取绝对 ±1.0 °C
# （T∞ 不能乘性缩放——它在 env 里是开尔文温度，±5% 会是 ±16 K）。
# 用法：python morris_screen.py [band] [trajectories]

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

_old_iter = worksheet.Worksheet.iter_rows
if "values_only" not in inspect.signature(_old_iter).parameters:
    worksheet.Worksheet.iter_rows = lambda self, **kw: (
        tuple(c.value for c in row) for row in _old_iter(self, **kw)
    )

sys.path.insert(0, SOURCE_CODE)
import 公共 as M

BAND = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
R_TRAJ = int(sys.argv[2]) if len(sys.argv) > 2 else 10
P_LEVELS = 8
DT_RANGE = 1.0                      # T∞ 绝对半宽 [°C]

SOLVE = dict(Nc=1600, dt=7.5, tmax=4.0e5, Ccr=0.15, stop_at_hit=True)
CASES = {"A": (3, False, ["D", "hm", "h", "C", "T"]),
         "B": (4, True, ["D", "hm", "h", "lam", "C", "T"])}
BASE_TD = {"A": 57.475473, "B": 51.095835}

T0 = float(M.T1_END)
PLAT_T = float(M.TA_PLAT)
PLAT_C = float(M.CA_PLAT)
BASE_ENV = M.env
ENV_KEYS = ("props", "HM", "H_Q", "env")


def make_env(dT, fC):
    """记录期内原样；记录期后平台温度平移 dT °C、平台含湿量乘 fC。"""
    def env(t, kappa=1.0):
        T, C = BASE_ENV(t, kappa)
        tt = np.asarray(t, float)
        return (np.where(tt <= T0, T, PLAT_T + dT + 273.15),
                np.where(tt <= T0, C, PLAT_C * fC * kappa))
    return env


def apply_params(v):
    """按参数字典把缩放施加到模块全局；返回还原用的快照。"""
    snap = {k: getattr(M, k) for k in ENV_KEYS}
    if v.get("D", 1.0) != 1.0:
        base_props, f = M.props, v["D"]

        def patched(case, C, Tk, _o=base_props, _f=f):
            rho, cp, kk, D = _o(case, C, Tk)
            return rho, cp, kk, D * _f

        M.props = patched
    if v.get("hm", 1.0) != 1.0:
        M.HM = snap["HM"] * v["hm"]
    if v.get("h", 1.0) != 1.0:
        M.H_Q = snap["H_Q"] * v["h"]
    if v.get("T", 0.0) != 0.0 or v.get("C", 1.0) != 1.0:
        M.env = make_env(v.get("T", 0.0), v.get("C", 1.0))
    return snap


def restore(snap):
    for k, val in snap.items():
        setattr(M, k, val)


def td_once(case, shrink, v):
    snap = apply_params(v)
    try:
        return float(M.solve1d(case=case, shrink=shrink,
                               lam=v.get("lam", 1.0), **SOLVE)["td_h"])
    finally:
        restore(snap)


# ---------------- 0. 装置校验：必须复现已发表的 S_p 端点 ----------------
print("=" * 74)
print("装置校验（±5%%，须与 sensitivity.csv 逐位一致）")
print("=" * 74)
CHECKS = [
    ("A", {}, 57.475473, "base"),
    ("A", {"D": 1.05}, 55.0598, "D +5%"),
    ("A", {"D": 0.95}, 60.1518, "D -5%"),
    ("A", {"hm": 1.05}, 57.1699, "hm +5%"),
    ("A", {"h": 1.05}, 57.4717, "h +5%"),
    ("B", {}, 51.095835, "base"),
    ("B", {"D": 1.05}, 48.9575, "D +5%"),
    ("B", {"lam": 1.05}, 48.2638, "lam +5%"),
    ("B", {"hm": 1.05}, 50.9781, "hm +5%"),
]
ok = True
for cfg, v, want, label in CHECKS:
    case, shrink, _ = CASES[cfg]
    got = td_once(case, shrink, v)
    same = abs(got - want) < 5e-4
    ok = ok and same
    print("  %s %-8s  got %10.4f  want %10.4f  %s"
          % (cfg, label, got, want, "OK" if same else "MISMATCH"))
if not ok:
    print("\n装置校验未通过——不往下跑。")
    sys.exit(1)
print("  装置校验通过\n")


# ---------------- 1. Morris 轨迹 ----------------
def trajectories(k, r, rng):
    delta = P_LEVELS / (2.0 * (P_LEVELS - 1.0))
    grid = np.arange(0.0, 1.0 + 1e-12, 1.0 / (P_LEVELS - 1.0))
    starts = grid[grid <= 1.0 - delta + 1e-12]
    out = []
    for _ in range(r):
        x = np.array([rng.choice(starts) for _ in range(k)])
        order = rng.permutation(k)
        pts, cur = [x.copy()], x.copy()
        for i in order:
            nxt = cur.copy()
            nxt[i] = nxt[i] + delta
            pts.append(nxt)
            cur = nxt
        out.append((np.array(pts), order, delta))
    return out


def decode(names, x, band):
    """[0,1] 归一化坐标 → 实际参数值。乘性参数走 1±band，T 走绝对 ±DT_RANGE。"""
    v = {}
    for n, xi in zip(names, x):
        if n == "T":
            v[n] = (2.0 * xi - 1.0) * DT_RANGE
        else:
            v[n] = 1.0 + (2.0 * xi - 1.0) * band
    return v


# ---------------- 2. 逐配置跑 Morris ----------------
rng = np.random.default_rng(20260921)
rows, summary = [], {}
t_start = time.time()

for cfg, (case, shrink, names) in CASES.items():
    k = len(names)
    ref = td_once(case, shrink, {})
    trajs = trajectories(k, R_TRAJ, rng)
    n_runs = R_TRAJ * (k + 1)
    print("-" * 74)
    print("配置 %s（k=%d，%d 条轨迹，%d 次求解，参考 t_d=%.6f h）"
          % (cfg, k, R_TRAJ, n_runs, ref))
    print("-" * 74)
    effects = {n: [] for n in names}
    done = 0
    t_cfg = time.time()
    for ti, (pts, order, delta) in enumerate(trajs):
        ys = []
        for x in pts:
            ys.append(td_once(case, shrink, decode(names, x, BAND)))
            done += 1
        for j, i in enumerate(order):
            n = names[i]
            if n == "T":
                # 绝对步长：ΔT = 2*DT_RANGE*delta
                ee = (ys[j + 1] - ys[j]) / (2.0 * DT_RANGE * delta)
            else:
                # S 等效量：(Δy/y_ref)/(Δp/p_ref)，p_ref=1，Δp = 2*BAND*delta
                ee = ((ys[j + 1] - ys[j]) / ref) / (2.0 * BAND * delta)
            effects[n].append(ee)
        print("    轨迹 %2d/%d  用时 %5.0f s  累计 %5.0f s"
              % (ti + 1, R_TRAJ, time.time() - t_cfg, time.time() - t_start))

    cfg_sum = {}
    for n in names:
        e = np.array(effects[n])
        mu, mus, sd = float(e.mean()), float(np.abs(e).mean()), float(e.std(ddof=1))
        cfg_sum[n] = {"mu": mu, "mu_star": mus, "sigma": sd,
                      "ratio": abs(sd / mus) if mus else float("nan"),
                      "lo": float(e.min()), "hi": float(e.max())}
        rows.append([cfg, n, "%.6f" % mu, "%.6f" % mus, "%.6f" % sd,
                     "%.4f" % (sd / mus if mus else float("nan")),
                     "%.6f" % e.min(), "%.6f" % e.max()])
    summary[cfg] = {"ref_td_h": ref, "k": k, "n_runs": n_runs,
                    "band": BAND, "dt_range_C": DT_RANGE, "params": cfg_sum}

    print("\n  %s 基本效应（乘性参数为 S 等效量，T 为 h/°C）" % cfg)
    print("  %-5s %10s %10s %10s %8s" % ("参数", "mu", "mu*", "sigma", "sigma/mu*"))
    for n in sorted(names, key=lambda z: -abs(cfg_sum[z]["mu_star"])):
        s = cfg_sum[n]
        print("  %-5s %10.4f %10.4f %10.4f %8.3f"
              % (n, s["mu"], s["mu_star"], s["sigma"], s["ratio"]))
    print()

os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "morris_screen.csv")
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["config", "param", "mu", "mu_star", "sigma", "sigma_over_mu_star",
                "ee_min", "ee_max"])
    w.writerows(rows)

import json
js = os.path.join(OUT_DIR, "morris_screen_summary.json")
with open(js, "w", encoding="utf-8") as f:
    json.dump({"band": BAND, "dt_range_C": DT_RANGE, "levels": P_LEVELS,
               "trajectories": R_TRAJ, "seed": 20260921,
               "Nc": SOLVE["Nc"], "dt": SOLVE["dt"], "Ccr": SOLVE["Ccr"],
               "results": summary}, f, indent=2, ensure_ascii=False)

print("写出", out)
print("写出", js)
print("总用时 %.0f s" % (time.time() - t_start))
