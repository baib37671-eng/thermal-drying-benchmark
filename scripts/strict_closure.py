# 严格干质量闭合装置。
#
# 为什么不直接用 第四问.py 的 收缩自洽闭合()：
#   该函数本身是干净的（不 reassign 模块级 props/HM/H_Q，故不触发 UnboundLocalError），
#   但它把结果写到 _ROOT/支撑材料/figdata，而 新建文件夹 下没有该目录，跑到写盘点就断；
#   且它只有"均值近似"一种口径，没有严格口径、没有干质量漂移监控、没有均匀场单测。
#   故在此独立重建，不改任何被污染的源文件。
#
# 两种口径：
#   v(C) = (1+C)/rho_B(C) 是"单位干物质所占的体积"，局部干物质密度 = 1/v(C)，故
#       m_d = ∫_V dV/v(C) = 2πL R² ∫₀¹ ξ/v(C(ξ,t)) dξ  ≈  πL R² Σ_i Vsh_i/v_i,  ΣVsh_i = 1
#   mean_v（旧口径，用于门禁）：R = R₀ √( ⟨v⟩ / v₀ )，⟨v⟩ = Σ Vsh_i v_i
#       —— 这是"体积÷平均比容"的均值近似，只有 v 全场均匀时才等于干质量守恒
#   strict（严格口径）        ：R = R₀ / √( v₀ Σ_i Vsh_i/v_i )
#       —— 由 m_d 守恒直接解出；因 v(C) 随 C 单调增，式 (8) 的半径下界两种口径下逐字相同
#
# 用法：python strict_closure.py          门禁 + 两口径 + 单测
import csv
import json
import os
import sys
import time

import numpy as np
from scipy.linalg import solve_banded

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE_CODE = os.path.join(ROOT, "src")
OUT_DIR = os.path.join(ROOT, "results", "tables")
os.environ["HERB_SRC"] = os.path.join(ROOT, "data", "raw")
sys.path.insert(0, SOURCE_CODE)

from 公共 import (L_CYL, R0, T0_C, C0, H_Q, HM, env, props, load_att2,
                  make_grid, face_logfac, _assemble, _wall_series)

CASE, NC, DT, CCR, TMAX = 4, 1600, 7.5, 0.15, 4.0e5
PITER = 3
SAMPLE_S = 300.0

# 已发表值（支撑材料/figdata/shrinkclosed_summary.json），门禁用
GATE = {"t_d_h": 61.401643, "dev_end_pct": -6.0869, "dev_min_pct": -23.5279,
        "dev_max_pct": -0.6103, "Cbar_end": 0.118394, "R_closed_end_cm": 1.27198}


def specvol(C, Tk):
    rho, _, _, _ = props(CASE, C, Tk)
    return (1.0 + np.asarray(C, float)) / rho


def radius_from_field(mode, C, T, Vsh, v0):
    """由当前场与固定的干质量 m_d,0 解出半径。两种口径唯一的分歧就在这一行。"""
    v = specvol(C, T)
    if mode == "mean_v":
        return R0 * np.sqrt(float(np.sum(Vsh * v)) / v0)
    if mode == "strict":
        return R0 / np.sqrt(v0 * float(np.sum(Vsh / v)))
    raise ValueError(mode)


def make_step(mode, v0):
    def step_closed(Cc, T, h, Vsh, logfac, piter, Cinf, Tamb, Rw0):
        Rw = Rw0
        Told = T.copy()
        Cold = Cc.copy()
        ln_wall = np.log(1.0 / (1.0 - 0.5 / NC))
        for _ in range(piter):
            Vi = np.pi * L_CYL * Rw ** 2 * Vsh
            rho, cp, kk, D = props(CASE, Cc, T)
            Df = np.empty(NC + 1)
            Df[1:NC] = 0.5 * (D[:-1] + D[1:])
            kf = np.empty(NC + 1)
            kf[1:NC] = 0.5 * (kk[:-1] + kk[1:])
            Gc = 2.0 * np.pi * L_CYL * Df * logfac
            Gt = 2.0 * np.pi * L_CYL * kf * logfac
            Gw_c = _wall_series(2.0 * np.pi * L_CYL * D[-1] / ln_wall,
                                2.0 * np.pi * L_CYL * Rw * HM)
            Gw_t = _wall_series(2.0 * np.pi * L_CYL * kk[-1] / ln_wall,
                                2.0 * np.pi * L_CYL * Rw * H_Q)
            abc, rhsc = _assemble(Vi, Gc, (1.0 / h) * np.ones(NC), Gw_c, Cinf, Cold)
            Cc = solve_banded((1, 1), abc, rhsc)
            abt, rhst = _assemble(Vi, Gt, rho * cp / h, Gw_t, Tamb, Told)
            T = solve_banded((1, 1), abt, rhst)
            Rw = radius_from_field(mode, Cc, T, Vsh, v0)
        return Cc, T, Rw
    return step_closed


def solve_closed(mode, v0):
    step_closed = make_step(mode, v0)
    xi, Vsh = make_grid(NC)
    logfac = face_logfac(NC)
    Cc = np.full(NC, float(C0))
    T = np.full(NC, float(T0_C) + 273.15)
    Rw = R0
    md0 = np.pi * L_CYL * R0 ** 2 * float(np.sum(Vsh / specvol(np.full(NC, C0), T)))
    rows = []
    t, hit, prev_max, prev_t, step = 0.0, None, None, 0.0, 0
    last_sampled = -1.0
    while t < TMAX - 1e-9:
        h = min(DT, TMAX - t)
        t_new = round(t + h, 6)
        Tamb, Cinf = env(t_new)
        Tamb = float(np.ravel(Tamb)[0])
        Cinf = float(np.ravel(Cinf)[0])
        Cprev, Tprev, Rwprev = Cc, T, Rw
        Cc, T, Rw = step_closed(Cc, T, h, Vsh, logfac, PITER, Cinf, Tamb, Rw)
        if hit is None:
            m = float(Cc.max())
            if m <= CCR and prev_max is not None and prev_max > CCR:
                frac = 0.0 if prev_max <= m else (prev_max - CCR) / (prev_max - m)
                hit = prev_t + frac * h
                if hit - prev_t > 1e-12:
                    h2 = hit - prev_t
                    Tam2, Cin2 = env(hit)
                    Tam2 = float(np.ravel(Tam2)[0])
                    Cin2 = float(np.ravel(Cin2)[0])
                    Cc, T, Rw = step_closed(Cprev, Tprev, h2, Vsh, logfac,
                                            PITER, Cin2, Tam2, Rwprev)
                    Tamb, Cinf, t_new = Tam2, Cin2, hit
            prev_max = m
        step += 1
        if (step % int(round(SAMPLE_S / DT)) == 0 or hit is not None):
            if hit is not None or t_new > last_sampled + 1e-6:
                md = np.pi * L_CYL * Rw ** 2 * float(np.sum(Vsh / specvol(Cc, T)))
                rows.append((t_new, Rw, float(np.sum(Vsh * Cc)), md))
                last_sampled = t_new
        prev_t = t_new
        t = t_new
        if hit is not None:
            break
    return {"t_d_h": hit / 3600.0, "t_hit_s": hit, "rows": rows, "md0": md0,
            "R_end_m": Rw, "eps_m_end": rows[-1][3] / md0 - 1.0,
            "eps_m_max": max(abs(r[3] / md0 - 1.0) for r in rows)}


def radius_test():
    """两种口径的退化与分裂。

    ① 均匀场：C 全场等于 C、T 全场等于 T0 时，两种口径都必须退化为
       R = R0*sqrt(v(C)/v(C0)) —— 这是式 (8) 的下界在均匀态取等号的那一支。
    ② 两区场：一半 C0 一半 0.3 时两种口径必须分开，且 strict < mean_v
       （Jensen：<v> >= 1/<1/v>），即均值近似系统性地高估半径。
    """
    xi, Vsh = make_grid(NC)
    T0k = float(T0_C) + 273.15
    v0 = float(specvol(np.array([C0]), np.array([T0k]))[0])
    half = NC // 2
    out = []
    for Ctest in (C0, 0.30):
        v = float(specvol(np.array([Ctest]), np.array([T0k]))[0])
        want = R0 * np.sqrt(v / v0)
        got = {}
        for mode in ("mean_v", "strict"):
            got[mode] = float(radius_from_field(mode, np.full(NC, Ctest),
                                                np.full(NC, T0k), Vsh, v0))
        out.append((Ctest, want, got))
    split = {}
    Csplit = np.concatenate([np.full(half, C0), np.full(NC - half, 0.30)])
    for mode in ("mean_v", "strict"):
        split[mode] = float(radius_from_field(mode, Csplit, np.full(NC, T0k), Vsh, v0))
    return out, split


def main():
    v0 = float(specvol(np.array([C0]), np.array([T0_C + 273.15]))[0])
    _xi, Vsh = make_grid(NC)
    print("=" * 74)
    print("装置自检")
    print("=" * 74)
    print("  网格数 Nc=%d，Σ Vsh = %.12f（须=1）" % (NC, float(np.sum(Vsh))))
    with np.errstate(divide="ignore", invalid="ignore"):
        rho_C0, _, _, _ = props(CASE, np.array([C0]), np.array([T0_C + 273.15]))
        rho_0, _, _, _ = props(CASE, np.array([0.0]), np.array([T0_C + 273.15]))
    print("  ρ_B(C0=%.4f) = %.4f   ρ_B(0) = %.4f" % (C0, float(rho_C0[0]), float(rho_0[0])))
    print("  v0 = v(C0) = %.8e m³/kg    v(0) = %.8e" % (v0, float(specvol(np.array([0.0]), np.array([T0_C + 273.15]))[0])))
    print("  R0 = %.6f m, L = %.6f m" % (R0, L_CYL))

    print()
    print("=" * 74)
    print("单测① 均匀场：两种口径都必须退化为 R = R0·sqrt(v(C)/v(C0))")
    print("=" * 74)
    uni, split = radius_test()
    ut_ok = True
    for Ctest, want, got in uni:
        for mode in ("mean_v", "strict"):
            rel = abs(got[mode] - want) / want
            ut_ok = ut_ok and rel < 1e-12
            print("  C=%.4f  %-7s R=%.12e  期望 %.12e  相对偏差 %.2e  %s"
                  % (Ctest, mode, got[mode], want, rel, "OK" if rel < 1e-12 else "FAIL"))
    print("  单测① %s" % ("通过" if ut_ok else "未通过"))

    print()
    print("=" * 74)
    print("单测② 两区场（一半 C0 一半 0.3）：两种口径必须分开，且 strict < mean_v")
    print("=" * 74)
    gap = (split["mean_v"] - split["strict"]) / split["strict"] * 100.0
    split_ok = split["strict"] < split["mean_v"]
    print("  mean_v R = %.12e m" % split["mean_v"])
    print("  strict R = %.12e m" % split["strict"])
    print("  mean_v 比 strict 高 %.4f %%  —— Jensen 间隙，均值近似高估半径" % gap)
    print("  单测② %s" % ("通过" if split_ok else "未通过"))
    if not (ut_ok and split_ok):
        print("\n!! 半径更新函数未通过退化/分裂单测，停止。")
        sys.exit(1)

    print()
    print("=" * 74)
    print("门禁：mean_v 口径须逐位复现已发表的自洽闭合端点")
    print("=" * 74)
    t0 = time.time()
    res_mean = solve_closed("mean_v", v0)
    ta, ra = load_att2()
    ts = np.array([r[0] for r in res_mean["rows"]])
    rc = np.array([r[1] for r in res_mean["rows"]])
    cb = np.array([r[2] for r in res_mean["rows"]])
    ra_i = np.interp(np.minimum(ts, ta[-1]), ta, ra) / 100.0
    dev = (ra_i - rc) / ra_i * 100.0
    got = {"t_d_h": res_mean["t_d_h"], "dev_end_pct": float(dev[-1]),
           "dev_min_pct": float(dev.min()), "dev_max_pct": float(dev.max()),
           "Cbar_end": res_mean["rows"][-1][2], "R_closed_end_cm": res_mean["R_end_m"] * 100.0}
    gate_ok = True
    for k, want in GATE.items():
        tol = 1e-4 if k == "t_d_h" else (1e-2 if k.endswith("_cm") else 5e-3)
        hit = abs(got[k] - want) <= tol
        gate_ok = gate_ok and hit
        print("  %-16s got %12.6f   want %12.6f   %s"
              % (k, got[k], want, "OK" if hit else "FAIL(%.2e)" % abs(got[k] - want)))
    print("  用时 %.1f s" % (time.time() - t0))
    if not gate_ok:
        print("\n!! 装置校验未通过：mean_v 口径复现不出已发表的自洽闭合端点，停止。")
        sys.exit(1)
    print("  装置校验通过 —— strict 口径与已发表口径同源")

    print()
    print("=" * 74)
    print("strict 口径（R = R0/sqrt(v0·Σ Vsh/v)）")
    print("=" * 74)
    t0 = time.time()
    res_strict = solve_closed("strict", v0)
    ts2 = np.array([r[0] for r in res_strict["rows"]])
    rc2 = np.array([r[1] for r in res_strict["rows"]])
    cb2 = np.array([r[2] for r in res_strict["rows"]])
    ra_i2 = np.interp(np.minimum(ts2, ta[-1]), ta, ra) / 100.0
    dev2 = (ra_i2 - rc2) / ra_i2 * 100.0
    print("  t_d              = %.6f h" % res_strict["t_d_h"])
    print("  R(t_d) 严格闭合  = %.5f cm" % (rc2[-1] * 100.0))
    print("  R(t_d) 附件2     = %.5f cm" % (ra_i2[-1] * 100.0))
    print("  R(t_d) 偏差      = %.2f %%" % dev2[-1])
    print("  Cbar(t_d)        = %.6f kg/kg" % cb2[-1])
    print("  偏差范围         = %.2f %% .. %.2f %%" % (dev2.min(), dev2.max()))
    print("  用时 %.1f s" % (time.time() - t0))

    print()
    print("=" * 74)
    print("端点位移")
    print("=" * 74)
    print("  mean_v : %.6f h   (已发表 61.401643)" % res_mean["t_d_h"])
    print("  strict : %.6f h" % res_strict["t_d_h"])
    print("  Δ      = %+.6f h  (%+.3f %%)" % (res_strict["t_d_h"] - res_mean["t_d_h"],
                                             (res_strict["t_d_h"] / res_mean["t_d_h"] - 1) * 100.0))
    print()
    print("  干质量漂移 ε_m = m_d(t)/m_d(0) - 1")
    print("    mean_v（均值近似）max|ε_m| = %.4e  末端 %+.4e" % (res_mean["eps_m_max"], res_mean["eps_m_end"]))
    print("    strict（严格积分）max|ε_m| = %.4e  末端 %+.4e" % (res_strict["eps_m_max"], res_strict["eps_m_end"]))
    print("    （strict 的残差 = 每步 piter=%d 的迭代滞后，不是模型误差）" % PITER)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "strict_closure.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["mode", "t_s", "t_h", "R_cm", "R_att2_cm", "dev_pct", "Cbar", "md_kg"])
        for mode, res in (("mean_v", res_mean), ("strict", res_strict)):
            for r in res["rows"]:
                t_s = r[0]
                r_att = float(np.interp(min(t_s, ta[-1]), ta, ra)) / 100.0
                w.writerow([mode, "%.1f" % t_s, "%.4f" % (t_s / 3600.0),
                            "%.5f" % (r[1] * 100.0), "%.5f" % (r_att * 100.0),
                            "%.4f" % ((r_att - r[1]) / r_att * 100.0),
                            "%.6f" % r[2], "%.8f" % r[3]])
    summary = {
        "case": CASE, "Nc": NC, "dt": DT, "Ccr": CCR, "piter": PITER,
        "v0": v0, "R0": R0, "L": L_CYL,
        "gate": {"want": GATE, "got": got, "passed": bool(gate_ok)},
        "mean_v": {"t_d_h": res_mean["t_d_h"], "t_d_s": res_mean["t_hit_s"],
                   "dev_end_pct": float(dev[-1]), "dev_min_pct": float(dev.min()),
                   "dev_max_pct": float(dev.max()), "Cbar_end": res_mean["rows"][-1][2],
                   "R_closed_end_cm": res_mean["R_end_m"] * 100.0,
                   "eps_m_max": res_mean["eps_m_max"], "eps_m_end": res_mean["eps_m_end"]},
        "strict": {"t_d_h": res_strict["t_d_h"], "t_d_s": res_strict["t_hit_s"],
                   "dev_end_pct": float(dev2[-1]), "dev_min_pct": float(dev2.min()),
                   "dev_max_pct": float(dev2.max()), "Cbar_end": res_strict["rows"][-1][2],
                   "R_closed_end_cm": res_strict["R_end_m"] * 100.0,
                   "eps_m_max": res_strict["eps_m_max"], "eps_m_end": res_strict["eps_m_end"]},
        "delta_td_h": res_strict["t_d_h"] - res_mean["t_d_h"],
        "delta_td_pct": (res_strict["t_d_h"] / res_mean["t_d_h"] - 1.0) * 100.0,
    }
    with open(os.path.join(OUT_DIR, "strict_closure_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print()
    print("写出 %s" % os.path.join(OUT_DIR, "strict_closure.csv"))
    print("写出 %s" % os.path.join(OUT_DIR, "strict_closure_summary.json"))


if __name__ == "__main__":
    main()
