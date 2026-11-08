# -*- coding: utf-8 -*-
"""
build_facts.py -- 数值事实表生成器（Thermal Science 主稿用）

依据 vault 卡《概括性断言必须机器重算》：正文里凡出现"种数/换算/配对/端点/趋势/覆盖率"
的数字，一律由本脚本从源数据重算并落进 data/numeric_facts.json，散文只从表里抄。

同时执行《交付物一致性总检》的"同量一算路"：每个量只认一个来源文件，
并在表里写明 source 与 method，供 check_manuscript.py 三方配对回查。

运行：python build_facts.py
"""
import csv
import json
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGD = os.path.join(ROOT, "data", "processed", "figdata")
JD = os.path.join(ROOT, "data", "processed")
TS_DATA = os.path.join(ROOT, "data", "processed")

L_CYL = 0.25          # m, 题给长度
R0_CM = 2.0           # cm, 题给初始半径
C0 = 2.55             # kg/kg, 题给初始干基含水率
T0_C = 28.0
CCR = 0.15            # 判据
H = 25.0              # W m-2 K-1
HM = 8.0e-7           # m s-1

FACTS = {}


def put(name, value, unit, source, method):
    FACTS[name] = {"value": value, "unit": unit, "source": source, "method": method}


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def fnum(row, key):
    v = row.get(key, "")
    return None if v in ("", None) else float(v)


def td_from_series(t, c, ccr):
    """首次 max C <= ccr 的时刻，样本间线性插值。返回 (t_s, 是否命中)。"""
    for i in range(1, len(t)):
        if c[i] <= ccr:
            if c[i - 1] == c[i]:
                return t[i], True
            return t[i - 1] + (t[i] - t[i - 1]) * (c[i - 1] - ccr) / (c[i - 1] - c[i]), True
    return None, False


def _floor_fit(dts, errs, lo=0.2, hi=2.5, n=6000):
    """err = F + C*dt^p 的最小二乘拟合。对 p 作一维扫描，内层 (F, C) 是线性参数、
    用闭式正规方程精确求解；两轮扫描（粗扫 + 在最优 p 附近细化）定位 p。
    只用内建数学函数，不引 numpy/scipy ⇒ 换机器换实现也复现同一组数。
    返回 (F, C, p, sse)。"""
    def inner(p):
        x = [d ** p for d in dts]
        m = len(errs)
        Sx = sum(x)
        Sxx = sum(v * v for v in x)
        Sy = sum(errs)
        Sxy = sum(x[i] * errs[i] for i in range(m))
        det = m * Sxx - Sx * Sx
        if abs(det) < 1e-300:
            return None
        F = (Sy * Sxx - Sx * Sxy) / det
        C = (m * Sxy - Sx * Sy) / det
        sse = sum((errs[i] - (F + C * x[i])) ** 2 for i in range(m))
        return (F, C, p, sse)

    def sweep(a, b, m):
        best = None
        for k in range(m + 1):
            p = a + (b - a) * k / m
            r = inner(p)
            if r is not None and (best is None or r[3] < best[3]):
                best = r
        return best

    b1 = sweep(lo, hi, n)
    w = (hi - lo) / n * 10.0
    b2 = sweep(b1[2] - w, b1[2] + w, n)
    return b2 if b2[3] <= b1[3] else b1


def main():
    # ---------------- 1. 题给输入序列（附件1 / 附件2 的抽出品） ----------------
    env = read_csv(os.path.join(FIGD, "env_att1.csv"))
    t_env = [fnum(r, "t_s") for r in env]
    T_env = [fnum(r, "T_amb_C") for r in env]
    C_env = [fnum(r, "C_amb_kgkg") for r in env]
    put("att1_rows", len(env), "count", "figdata/env_att1.csv", "len(rows)")
    dt1 = sorted({round(t_env[i + 1] - t_env[i], 9) for i in range(len(t_env) - 1)})
    put("att1_dt_unique_s", dt1, "s", "figdata/env_att1.csv", "set(diff(t))")
    put("att1_t_end_s", t_env[-1], "s", "figdata/env_att1.csv", "t[-1]")
    put("att1_t_end_h", t_env[-1] / 3600.0, "h", "figdata/env_att1.csv", "t[-1]/3600")

    rad = read_csv(os.path.join(FIGD, "radius_att2.csv"))
    rad_d = [(fnum(r, "t_s"), fnum(r, "R_data_cm")) for r in rad if fnum(r, "R_data_cm") is not None]
    put("att2_file_rows", len(rad), "count", "figdata/radius_att2.csv", "len(rows) 含拟合插值行")
    put("att2_data_rows", len(rad_d), "count", "figdata/radius_att2.csv", "R_data_cm 非空计数")
    dtr = sorted({round(rad_d[i + 1][0] - rad_d[i][0], 9) for i in range(len(rad_d) - 1)})
    put("att2_dt_unique_s", dtr, "s", "figdata/radius_att2.csv", "set(diff(t)) on data rows")
    put("att2_t_end_s", rad_d[-1][0], "s", "figdata/radius_att2.csv", "t[-1] of data rows")
    put("att2_t_end_h", rad_d[-1][0] / 3600.0, "h", "figdata/radius_att2.csv", "/3600")
    put("att2_R_first_cm", rad_d[0][1], "cm", "figdata/radius_att2.csv", "R_data[0]")
    put("att2_R_last_cm", rad_d[-1][1], "cm", "figdata/radius_att2.csv", "R_data[-1]")
    rd = [x[1] for x in rad_d]
    put("att2_R_min_cm", min(rd), "cm", "figdata/radius_att2.csv", "min")
    put("att2_R_max_cm", max(rd), "cm", "figdata/radius_att2.csv", "max")
    dr = [rd[i + 1] - rd[i] for i in range(len(rd) - 1)]
    put("att2_R_diff_down", sum(1 for x in dr if x < 0), "count", "figdata/radius_att2.csv", "diff<0")
    put("att2_R_diff_flat", sum(1 for x in dr if x == 0), "count", "figdata/radius_att2.csv", "diff==0")
    put("att2_R_diff_up", sum(1 for x in dr if x > 0), "count", "figdata/radius_att2.csv", "diff>0")

    # ---------------- 2. 平台值（末 61 点均值）与末点 ----------------
    n61 = 61
    T_plat = sum(T_env[-n61:]) / n61
    C_plat = sum(C_env[-n61:]) / n61
    put("T_plat_mean61_C", T_plat, "degC", "figdata/env_att1.csv", "mean(T[-61:])")
    put("C_plat_mean61", C_plat, "kg/kg", "figdata/env_att1.csv", "mean(C[-61:])")
    put("T_lastpoint_C", T_env[-1], "degC", "figdata/env_att1.csv", "T[-1]")
    put("C_lastpoint", C_env[-1], "kg/kg", "figdata/env_att1.csv", "C[-1]")
    put("n_plat_window", n61, "count", "boundary_sensitivity.py 口径", "末 1 h = 61 点（含端点）")

    # ---------------- 3. 记录内分段斜率（重算并与 boundary_trend.csv 对照） ----------------
    seg = []
    for k in range(4):
        lo, hi = k * 3600.0, (k + 1) * 3600.0
        pts = [(t_env[i], T_env[i]) for i in range(len(t_env)) if lo <= t_env[i] <= hi]
        n = len(pts)
        xs = [p[0] / 3600.0 for p in pts]
        ys = [p[1] for p in pts]
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
        slope = sxy / sxx
        resid = [ys[i] - (my + slope * (xs[i] - mx)) for i in range(n)]
        sd_fit = math.sqrt(sum(r * r for r in resid) / (n - 2))          # 拟合残差标准误
        sd_raw = math.sqrt(sum((y - my) ** 2 for y in ys) / (n - 1))     # 段内标准差 ddof=1
        sd_pop = math.sqrt(sum((y - my) ** 2 for y in ys) / n)           # 段内标准差 ddof=0
        rng = max(ys) - min(ys)
        seg.append({"bin": k + 1, "n": n, "slope_C_per_h": slope,
                    "sd_within_ddof0_C": sd_pop, "sd_within_ddof1_C": sd_raw,
                    "sd_fitresid_C": sd_fit, "range_C": rng,
                    "T_first_C": ys[0], "T_last_C": ys[-1]})
    put("segment_slopes", seg, "degC/h", "figdata/env_att1.csv", "每段独立最小二乘，n=61")
    trend = read_csv(os.path.join(TS_DATA, "boundary_trend.csv"))
    put("segment_slopes_archived", [
        {"bin": int(r["hour_bin"]), "slope_C_per_h": float(r["dT_dt_C_per_h"]),
         "sd_C": float(r["sd_C"]), "n": int(r["n"])} for r in trend],
        "degC/h", "thermal_science/data/boundary_trend.csv", "已归档值，用于对照")
    put("segment_slope_max_absdiff",
        max(abs(seg[i]["slope_C_per_h"] - float(trend[i]["dT_dt_C_per_h"])) for i in range(4)),
        "degC/h", "重算 vs 归档", "斜率 max|diff| 应为 0 量级")
    # 归档 sd_C 的口径判定：ddof=0 段内标准差 / ddof=1 / 拟合残差标准误，谁与归档一致？
    d_pop = max(abs(seg[i]["sd_within_ddof0_C"] - float(trend[i]["sd_C"])) for i in range(4))
    d_raw = max(abs(seg[i]["sd_within_ddof1_C"] - float(trend[i]["sd_C"])) for i in range(4))
    d_fit = max(abs(seg[i]["sd_fitresid_C"] - float(trend[i]["sd_C"])) for i in range(4))
    put("segment_sd_archived_kouji", "ddof=0 段内标准差" if d_pop < min(d_raw, d_fit) else "未定",
        "degC", "重算 vs 归档", "三种口径逐一比对，取 max|diff| 最小者")
    put("segment_sd_maxdiff_ddof0", d_pop, "degC", "重算 vs 归档", "应 <1e-5")
    put("segment_sd_maxdiff_ddof1", d_raw, "degC", "重算 vs 归档", "对照")
    put("segment_sd_maxdiff_fitresid", d_fit, "degC", "重算 vs 归档", "对照")
    assert d_pop < 1e-5, "归档 sd_C 口径未复现：%r" % d_pop
    assert max(abs(seg[i]["slope_C_per_h"] - float(trend[i]["dT_dt_C_per_h"])) for i in range(4)) < 1e-5

    # ---------------- 4. 四格因子端点（生产算例） ----------------
    abl = read_json(os.path.join(FIGD, "ablation.json"))
    a3f, a3s = abl["a3_fix"]["td_h"], abl["a3_shr"]["td_h"]
    a4f, a4s = abl["a4_fix"]["td_h"], abl["a4_shr"]["td_h"]
    for k, v in (("A_fixed", a3f), ("A_shrinking", a3s), ("B_fixed", a4f), ("B_shrinking", a4s)):
        put("td_%s_h" % k, v, "h", "figdata/ablation.json", "生产算例 Nc=1600 dt=7.5")
        put("td_%s_s" % k, v * 3600.0, "s", "figdata/ablation.json", "td_h*3600")
    put("td_hit_A_fixed_s", abl["a3_fix"]["t_hit_s"], "s", "figdata/ablation.json", "t_hit_s")
    put("td_hit_B_shrinking_s", abl["a4_shr"]["t_hit_s"], "s", "figdata/ablation.json", "t_hit_s")
    put("R_at_hit_A_fixed_cm", abl["a3_fix"]["Ri_cm"], "cm", "figdata/ablation.json", "Ri_cm")
    put("R_at_hit_A_shrinking_cm", abl["a3_shr"]["Ri_cm"], "cm", "figdata/ablation.json", "Ri_cm")
    put("R_at_hit_B_shrinking_cm", abl["a4_shr"]["Ri_cm"], "cm", "figdata/ablation.json", "Ri_cm")

    put("delta_bundle_h", a3f - a4s, "h", "ablation.json", "A_fixed - B_shrinking")
    put("delta_bundle_pct", 100.0 * (a3f - a4s) / a3f, "%", "ablation.json", "相对 A_fixed")
    put("ratio_geo_A", a3s / a3f, "-", "ablation.json", "A_shr/A_fix")
    put("ratio_geo_B", a4s / a4f, "-", "ablation.json", "B_shr/B_fix")
    put("ratio_prop_fixed", a4f / a3f, "-", "ablation.json", "B_fix/A_fix")
    put("ratio_prop_shrinking", a4s / a3s, "-", "ablation.json", "B_shr/A_shr")
    put("interaction_I", (a3f * a4s) / (a3s * a4f), "-", "ablation.json",
        "t_Af*t_Bs/(t_As*t_Bf)；对称口径下为恒等式，仅作交叉比读数")

    grid = read_csv(os.path.join(FIGD, "ablation_grid.csv"))
    put("ablation_grid", [{k: (float(v) if k != "Nc" else int(float(v))) for k, v in r.items()}
                          for r in grid], "h / -", "figdata/ablation_grid.csv", "网格依赖四格表")

    # ---------------- 5. FEM 交叉核验 ----------------
    fem = read_csv(os.path.join(FIGD, "fem_crosscheck.csv"))
    def pick(kind, q, meth, nc):
        for r in fem:
            if (r["kind"] == kind and r["question"] == q and r["method"] == meth
                    and int(float(r["Nc"])) == nc):
                return float(r["value"])
        return None
    for q, tag in (("Q3", "A_fixed"), ("Q4", "B_shrinking")):
        fv, fe = pick("cross", q, "FVM", 1600), pick("cross", q, "FEM", 1600)
        put("fem_%s_h" % tag, fe, "h", "figdata/fem_crosscheck.csv", "Nc=1600 FEM")
        put("fem_gap_%s_s" % tag, (fe - fv) * 3600.0, "s", "figdata/fem_crosscheck.csv",
            "(FEM-FVM)*3600")
        put("fem_gaprow_%s_s" % tag, pick("gap", q, "FEM-FVM", 1600), "s",
            "figdata/fem_crosscheck.csv", "文件内 gap 行，用于对照")
        for nc in (200, 400, 800, 1600):
            put("fem_gap_%s_Nc%d_s" % (tag, nc), pick("gap", q, "FEM-FVM", nc), "s",
                "figdata/fem_crosscheck.csv", "gap 行")
    put("order_obs", {r["question"] + "_" + r["method"]: float(r["value"])
                      for r in fem if r["kind"] == "order_obs_nc"}, "order",
        "figdata/fem_crosscheck.csv", "order_obs_nc 行")
    # Richardson：必须取文件里的 extrap_p2 行（全精度），不能由 ablation_grid.csv 的
    # 4 位小数圆整值反推——后者给出 57.4787，与正文的 57.4786 差在末位，也会把
    # "within 1 s" 顶成 1.08 s（同量一算路）。
    ext = [r for r in fem if r["kind"] == "extrap_p2" and r["question"] == "Q3"
           and r["method"] == "FVM"]
    put("richardson_fv_h", float(ext[0]["value"]), "h", "figdata/fem_crosscheck.csv",
        "extrap_p2 行（p=2 的 Richardson 外推）")

    conv = read_csv(os.path.join(FIGD, "convergence.csv"))
    sp = [(float(r["x"]), float(r["err"])) for r in conv if r["kind"] == "space"]
    tm = [(float(r["x"]), float(r["err"])) for r in conv if r["kind"] == "time"]
    put("conv_space", [{"Nc": x, "err": e} for x, e in sp], "-", "figdata/convergence.csv", "原样")
    put("conv_space_orders", [math.log(sp[i][1] / sp[i + 1][1]) / math.log(sp[i + 1][0] / sp[i][0])
                              for i in range(len(sp) - 1)], "order",
        "figdata/convergence.csv", "相邻比值 log2 阶（解析基准）")
    put("conv_time", [{"dt": x, "err": e} for x, e in tm], "-", "figdata/convergence.csv", "原样")
    put("conv_time_orders", [math.log(tm[i][1] / tm[i + 1][1]) / math.log(tm[i][0] / tm[i + 1][0])
                             for i in range(len(tm) - 1)], "order",
        "figdata/convergence.csv", "相邻比值阶（含空间误差地板，仅作对照）")

    # ---------------- 6. 判据扫描：t_d(Ccr) 与两配置交叉 ----------------
    q3 = read_csv(os.path.join(FIGD, "q3_maxC.csv"))
    q4 = read_csv(os.path.join(FIGD, "q4_maxC.csv"))
    t3 = [float(r["t_s"]) for r in q3]
    c3 = [float(r["C_max"]) for r in q3]
    t4 = [float(r["t_s"]) for r in q4]
    c4 = [float(r["C_max"]) for r in q4]
    put("maxC_series_rows", {"A_fixed": len(t3), "B_shrinking": len(t4)}, "count",
        "figdata/q3_maxC.csv, q4_maxC.csv", "len")
    put("maxC_series_dt_s", {"A_fixed": sorted({round(t3[i+1]-t3[i], 6) for i in range(len(t3)-1)})[:3],
                             "B_shrinking": sorted({round(t4[i+1]-t4[i], 6) for i in range(len(t4)-1)})[:3]},
        "s", "figdata/q3_maxC.csv, q4_maxC.csv", "set(diff) 前 3 个")
    scan = []
    for ccr in [0.15, 0.16, 0.17, 0.1737, 0.18, 0.19, 0.20]:
        ta, oka = td_from_series(t3, c3, ccr)
        tb, okb = td_from_series(t4, c4, ccr)
        scan.append({"Ccr": ccr, "A_fixed_h": (ta / 3600.0 if oka else None),
                     "B_shrinking_h": (tb / 3600.0 if okb else None)})
    put("threshold_scan", scan, "h", "figdata/q3_maxC.csv, q4_maxC.csv",
        "首次 C_max<=Ccr，300 s 样本间线性插值")

    def gap(ccr):
        ta, _ = td_from_series(t3, c3, ccr)
        tb, _ = td_from_series(t4, c4, ccr)
        return (ta - tb) / 3600.0
    lo, hi = 0.15, 0.18
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if gap(lo) * gap(mid) <= 0:
            hi = mid
        else:
            lo = mid
    ccr_star = 0.5 * (lo + hi)
    ta_star, _ = td_from_series(t3, c3, ccr_star)
    put("crossing_Ccr", ccr_star, "kg/kg", "q3_maxC.csv, q4_maxC.csv", "二分法解 t_A(Ccr)=t_B(Ccr)")
    put("crossing_t_h", ta_star / 3600.0, "h", "q3_maxC.csv, q4_maxC.csv", "对应时刻")
    put("scan_vs_production_A_fixed_s",
        td_from_series(t3, c3, 0.15)[0] - abl["a3_fix"]["t_hit_s"], "s",
        "q3_maxC.csv vs ablation.json", "扫描口径与生产口径之差（应 <300 s 采样粒度）")
    put("scan_vs_production_B_shrinking_s",
        td_from_series(t4, c4, 0.15)[0] - abl["a4_shr"]["t_hit_s"], "s",
        "q4_maxC.csv vs ablation.json", "同上")

    # ---------------- 7. 冻结物性 vs 状态依赖：穿越时刻 ----------------
    tr = read_csv(os.path.join(FIGD, "q2_frozen_trace.csv"))
    dyn = [r for r in tr if r["series"] == "dyn"]
    frz = [r for r in tr if r["series"] == "frz"]
    tt = [float(r["t_h"]) for r in dyn]
    cs = [float(r["C_surf"]) for r in dyn]
    cc = [float(r["C_center"]) for r in dyn]
    put("frozen_trace_rows", {"dyn": len(dyn), "frz": len(frz)}, "count",
        "figdata/q2_frozen_trace.csv", "len by series")
    put("frozen_trace_dt_h", sorted({round(tt[i+1]-tt[i], 9) for i in range(len(tt)-1)})[:3], "h",
        "figdata/q2_frozen_trace.csv", "set(diff)")
    put("cross_surf_dyn_h", td_from_series(tt, cs, CCR)[0], "h",
        "figdata/q2_frozen_trace.csv", "dyn 序列首次 C_surf<=0.15，线性插值")
    put("cross_center_dyn_h", td_from_series(tt, cc, CCR)[0], "h",
        "figdata/q2_frozen_trace.csv", "dyn 序列首次 C_center<=0.15，线性插值")
    put("cross_surf_frz_h", td_from_series([float(r["t_h"]) for r in frz],
                                           [float(r["C_surf"]) for r in frz], CCR)[0], "h",
        "figdata/q2_frozen_trace.csv", "frz 序列首次 C_surf<=0.15")
    put("cross_center_frz_h", td_from_series([float(r["t_h"]) for r in frz],
                                             [float(r["C_center"]) for r in frz], CCR)[0], "h",
        "figdata/q2_frozen_trace.csv", "frz 序列首次 C_center<=0.15")

    # ---------------- 8. 3 h 状态点 ----------------
    i3 = min(range(len(tt)), key=lambda i: abs(tt[i] - 3.0))
    put("state_3h", {"t_h": tt[i3], "T_center_C": float(dyn[i3]["T_center_C"]),
                     "C_center": float(dyn[i3]["C_center"]), "C_surf": float(dyn[i3]["C_surf"])},
        "-", "figdata/q2_frozen_trace.csv", "t 最接近 3 h 的行")
    fd = read_json(os.path.join(FIGD, "figdata_summary.json"))
    put("state_3h_archived", {"T_center_C": fd["q2"]["T_3h_C"][0], "T_surf_C": fd["q2"]["T_3h_C"][-1],
                              "C_center": fd["q2"]["C_3h"][0], "C_surf": fd["q2"]["C_3h"][-1],
                              "n_nodes": len(fd["q2"]["C_3h"])},
        "-", "figdata/figdata_summary.json", "q2 3h 剖面首末节点")
    put("T_uniformity_3h_maxdiff_C", max(fd["q2"]["T_3h_C"]) - min(fd["q2"]["T_3h_C"]), "degC",
        "figdata/figdata_summary.json", "3 h 剖面 T 极差")

    # ---------------- 9. 外推边界：窗口侧 vs 控温侧 ----------------
    bs = read_json(os.path.join(JD, "boundary_sensitivity.json"))
    put("boundary_sensitivity_json", bs, "-", "journal_draft/boundary_sensitivity.json", "原样")
    bx = read_csv(os.path.join(TS_DATA, "boundary_extrapolation.csv"))
    win = [r for r in bx if r["kind"] == "window"]
    tmp = [r for r in bx if r["kind"] == "temperature"]
    def col(rows, key):
        return [float(r[key]) for r in rows]
    wA, wB = col(win, "A_fixed_h"), col(win, "B_shrinking_h")
    tA, tB = col(tmp, "A_fixed_h"), col(tmp, "B_shrinking_h")
    put("extrapolation_rows", bx, "-", "thermal_science/data/boundary_extrapolation.csv", "原样 10 行")
    put("window_span_A_h", max(wA) - min(wA), "h", "boundary_extrapolation.csv", "max-min（5 窗口）")
    put("window_span_B_h", max(wB) - min(wB), "h", "boundary_extrapolation.csv", "max-min")
    put("temp_span_A_h", max(tA) - min(tA), "h", "boundary_extrapolation.csv", "max-min（-2..+2 degC）")
    put("temp_span_B_h", max(tB) - min(tB), "h", "boundary_extrapolation.csv", "max-min")
    put("amplifier_A", (max(tA) - min(tA)) / (max(wA) - min(wA)), "-", "boundary_extrapolation.csv",
        "控温侧极差 / 窗口侧极差")
    put("amplifier_B", (max(tB) - min(tB)) / (max(wB) - min(wB)), "-", "boundary_extrapolation.csv",
        "同上，B")
    put("window_span_A_pct_of_base", 100.0 * (max(wA) - min(wA)) / a3f, "%", "boundary_extrapolation.csv",
        "相对 A_fixed 基准")
    # 斜率：±1 degC 段与 ±2 degC 段
    # CSV 里的 T_plat_C 是 6 位小数落盘值，与重算的 T_plat 差 ~4e-7，故 key 必须圆整
    tmap = {round(float(r["T_plat_C"]) - T_plat, 6): (float(r["A_fixed_h"]), float(r["B_shrinking_h"]))
            for r in tmp}
    put("tmap_keys", sorted(tmap), "degC", "boundary_extrapolation.csv", "圆整后的偏移键")
    d1A = (tmap[1.0][0] - tmap[-1.0][0]) / -2.0
    d1B = (tmap[1.0][1] - tmap[-1.0][1]) / -2.0
    d2A = (tmap[2.0][0] - tmap[-2.0][0]) / -4.0
    d2B = (tmap[2.0][1] - tmap[-2.0][1]) / -4.0
    put("slope_pm1_A_h_per_C", d1A, "h/degC", "boundary_extrapolation.csv", "-1..+1 段中心差分（取正）")
    put("slope_pm1_B_h_per_C", d1B, "h/degC", "boundary_extrapolation.csv", "同上")
    put("slope_pm2_A_h_per_C", d2A, "h/degC", "boundary_extrapolation.csv", "-2..+2 段中心差分")
    put("slope_pm2_B_h_per_C", d2B, "h/degC", "boundary_extrapolation.csv", "同上")
    put("curvature_A_pct", 100.0 * (d2A - d1A) / d1A, "%", "boundary_extrapolation.csv",
        "(slope_pm2-slope_pm1)/slope_pm1；中心差分口径下曲率极小")
    put("curvature_B_pct", 100.0 * (d2B - d1B) / d1B, "%", "boundary_extrapolation.csv", "同上")
    # 单边斜率与冷/暖侧不对称（memory 旧记的"1.75/1.53、8% 曲率"实为此处暖侧单边值）
    for tag, idx in (("A", 0), ("B", 1)):
        c1 = (tmap[-1.0][idx] - tmap[-0.0][idx]) / 1.0      # 冷侧 ±1
        w1 = (tmap[-0.0][idx] - tmap[1.0][idx]) / 1.0       # 暖侧 ±1
        c2 = (tmap[-2.0][idx] - tmap[-0.0][idx]) / 2.0      # 冷侧 ±2
        w2 = (tmap[-0.0][idx] - tmap[2.0][idx]) / 2.0       # 暖侧 ±2
        put("slope_cold1_%s_h_per_C" % tag, c1, "h/degC", "boundary_extrapolation.csv", "0->-1 单边")
        put("slope_warm1_%s_h_per_C" % tag, w1, "h/degC", "boundary_extrapolation.csv", "0->+1 单边")
        put("slope_cold2_%s_h_per_C" % tag, c2, "h/degC", "boundary_extrapolation.csv", "0->-2 单边")
        put("slope_warm2_%s_h_per_C" % tag, w2, "h/degC", "boundary_extrapolation.csv", "0->+2 单边")
        put("asym_pm1_%s_pct" % tag, 100.0 * (c1 - w1) / c1, "%", "boundary_extrapolation.csv",
            "(冷侧-暖侧)/冷侧，±1 degC")
        put("asym_pm2_%s_pct" % tag, 100.0 * (c2 - w2) / c2, "%", "boundary_extrapolation.csv",
            "(冷侧-暖侧)/冷侧，±2 degC")

    # 表 2 需要 ±10% 湿度情景对应的 C_plat 值（同量一算路：由 C_plat 直接算，不手打）
    put("C_plat_minus10pct", C_plat * 0.9, "kg/kg", "figdata/env_att1.csv", "C_plat*0.9")
    put("C_plat_plus10pct", C_plat * 1.1, "kg/kg", "figdata/env_att1.csv", "C_plat*1.1")
    put("span_moisture_pm10pct_A_h",
        abs(float([r for r in bs["results"] if r["scenario"] == "wetter_10pct"][0]["A_fixed_h"])
            - float([r for r in bs["results"] if r["scenario"] == "drier_10pct"][0]["A_fixed_h"])),
        "h", "journal_draft/boundary_sensitivity.json", "wetter-drier 极差，A")
    put("span_moisture_pm10pct_B_h",
        abs(float([r for r in bs["results"] if r["scenario"] == "wetter_10pct"][0]["B_shrinking_h"])
            - float([r for r in bs["results"] if r["scenario"] == "drier_10pct"][0]["B_shrinking_h"])),
        "h", "journal_draft/boundary_sensitivity.json", "wetter-drier 极差，B")
    put("window_rows", [{"scenario": r["scenario"], "T_plat_C": float(r["T_plat_C"]),
                         "C_plat": float(r["C_plat_kgkg"]), "A_fixed_h": float(r["A_fixed_h"]),
                         "B_shrinking_h": float(r["B_shrinking_h"])} for r in win],
        "-", "boundary_extrapolation.csv", "窗口侧 5 行（表 2 用）")
    put("temperature_rows", [{"scenario": r["scenario"], "T_plat_C": float(r["T_plat_C"]),
                              "C_plat": float(r["C_plat_kgkg"]), "A_fixed_h": float(r["A_fixed_h"]),
                              "B_shrinking_h": float(r["B_shrinking_h"])} for r in tmp],
        "-", "boundary_extrapolation.csv", "控温侧 5 行（表 2 用）")

    # ---------------- 10. 记录覆盖率（外推占比） ----------------
    put("record_coverage_A_fixed_pct", 100.0 * 4.0 / a3f, "%", "att1 + ablation.json",
        "4 h 记录 / A_fixed 端点")
    put("record_coverage_B_shrinking_pct", 100.0 * 4.0 / a4s, "%", "att1 + ablation.json",
        "4 h 记录 / B_shrinking 端点")
    put("extrapolated_share_A_fixed_pct", 100.0 - 100.0 * 4.0 / a3f, "%", "att1 + ablation.json",
        "1 - 覆盖率")
    put("extrapolated_share_B_shrinking_pct", 100.0 - 100.0 * 4.0 / a4s, "%", "att1 + ablation.json",
        "1 - 覆盖率")

    # ---------------- 11. 干固体口径诊断（纯失水律） ----------------
    def v_spec(c):
        return (1.0 + c) / (760.0 + 90.0 * c)
    R_bound_cm = R0_CM * math.sqrt(v_spec(0.0) / v_spec(C0))
    put("v_spec_0_m3kg", v_spec(0.0), "m3/kg", "physical_consistency.md 口径", "v(0)=1/760")
    put("v_spec_C0_m3kg", v_spec(C0), "m3/kg", "同上", "(1+2.55)/(760+90*2.55)")
    put("rho_B_C0", 760.0 + 90.0 * C0, "kg/m3", "题给附录4", "760+90C")
    put("R_bound_cm", R_bound_cm, "cm", "重算", "R0*sqrt(v(0)/v(C0))")
    below = [x for x in rad_d if x[1] < R_bound_cm]
    put("att2_below_bound_count", len(below), "count", "figdata/radius_att2.csv + 重算",
        "R_data < R_bound 计数")
    put("att2_below_bound_first_h", (below[0][0] / 3600.0) if below else None, "h",
        "figdata/radius_att2.csv", "首次越界时刻")
    V0 = math.pi * (R0_CM / 100.0) ** 2 * L_CYL
    m_d0 = (760.0 + 90.0 * C0) * V0 / (1.0 + C0)
    put("V0_m3", V0, "m3", "重算", "pi*R0^2*L")
    put("m_dry_initial_kg", m_d0, "kg", "重算", "rho_B(C0)*V0/(1+C0)")
    sl = read_csv(os.path.join(FIGD, "shrinklaw.csv"))
    last = sl[-1]
    Cbar_end = float(last["Cbar"])
    R_end_cm = float(last["R_att2_cm"])
    t_end_s = float(last["t_s"])
    Ve = math.pi * (R_end_cm / 100.0) ** 2 * L_CYL
    m_de = (760.0 + 90.0 * Cbar_end) * Ve / (1.0 + Cbar_end)
    put("shrinklaw_last_t_s", t_end_s, "s", "figdata/shrinklaw.csv", "末行 t")
    put("Cbar_at_td", Cbar_end, "kg/kg", "figdata/shrinklaw.csv", "末行 Cbar（体积平均口径）")
    put("R_att2_at_td_cm", R_end_cm, "cm", "figdata/shrinklaw.csv", "末行 R_att2_cm")
    put("m_dry_endpoint_kg", m_de, "kg", "重算", "rho_B(Cbar)*pi*R^2*L/(1+Cbar)")
    put("m_dry_ratio", m_de / m_d0, "-", "重算", "端点/初始")
    put("m_dry_loss_pct", 100.0 * (1.0 - m_de / m_d0), "%", "重算", "1-ratio")

    # ---- 11b. 半径下穿 R_bound 的首次时刻：两种口径（数据行 vs 分段线性插值） ----
    put("R_bound_first_datarow_h", (below[0][0] / 3600.0) if below else None, "h",
        "figdata/radius_att2.csv", "首个 R_data < R_bound 的数据行时刻")
    tcross = None
    for i in range(1, len(rad_d)):
        r0, r1 = rad_d[i - 1][1], rad_d[i][1]
        if r0 >= R_bound_cm > r1:
            frac = (r0 - R_bound_cm) / (r0 - r1)
            tcross = (rad_d[i - 1][0] + frac * (rad_d[i][0] - rad_d[i - 1][0])) / 3600.0
            break
    put("R_bound_first_interp_h", tcross, "h",
        "figdata/radius_att2.csv", "分段线性插值下穿时刻（= 求解器实际用的口径）")

    # ---- 11c. 状态依赖(dyn) vs 冻结物性(frz) 两条轨迹的交叉时刻 ----
    #      草稿里的 "surface crossing 5.70 h / center crossing 15.88 h" 指的是这个，
    #      不是达阈时刻。达阈时刻另存 cross_surf_dyn_h / cross_center_dyn_h。
    dmap = {round(float(r["t_h"]), 9): r for r in dyn}
    fmap = {round(float(r["t_h"]), 9): r for r in frz}
    common = sorted(set(dmap) & set(fmap))
    put("dynfrz_common_rows", len(common), "count", "figdata/q2_frozen_trace.csv",
        "dyn/frz 共同时刻行数")

    def first_sign_change(field):
        prev_t, prev_d = None, None
        for t in common:
            dd = float(dmap[t][field]) - float(fmap[t][field])
            if prev_d is not None and prev_d * dd < 0:
                frac = prev_d / (prev_d - dd)
                return prev_t + frac * (t - prev_t), prev_d, dd
            prev_t, prev_d = t, dd
        return None, prev_d, None
    cs_t, _, _ = first_sign_change("C_surf")
    cc_t, _, _ = first_sign_change("C_center")
    put("cross_dynfrz_surf_h", cs_t, "h", "figdata/q2_frozen_trace.csv",
        "C_surf(dyn)-C_surf(frz) 首次变号，线性插值")
    put("cross_dynfrz_center_h", cc_t, "h", "figdata/q2_frozen_trace.csv",
        "C_center(dyn)-C_center(frz) 首次变号，线性插值")
    put("dynfrz_trace_span_h", [common[0], common[-1]], "h", "figdata/q2_frozen_trace.csv",
        "轨迹时间跨度")
    put("dynfrz_dCcenter_pct_at", [
        {"t_h": float(r["t_h"]), "C_center_dyn": float(r["C_center"]),
         "C_center_frz": float(fmap[round(float(r["t_h"]), 9)]["C_center"]),
         "dC_pct": 100.0 * (float(fmap[round(float(r["t_h"]), 9)]["C_center"])
                            - float(r["C_center"])) / float(r["C_center"])}
        for r in dyn if float(r["t_h"]) in (1.0, 3.0, 6.0, 12.0, 24.0, 48.0)],
        "%", "figdata/q2_frozen_trace.csv", "(frz-dyn)/dyn*100，用于与 q2_frozen.csv 对照")
    q2f = read_csv(os.path.join(FIGD, "q2_frozen.csv"))
    put("q2_frozen_archived", [{k: float(v) for k, v in r.items()} for r in q2f],
        "-", "figdata/q2_frozen.csv", "归档粗表，用于对照")

    # ---------------- 12. 自洽闭合 vs 实测轨迹 ----------------
    sc = read_json(os.path.join(FIGD, "shrinkclosed_summary.json"))
    put("selfclosed", sc, "-", "figdata/shrinkclosed_summary.json", "原样")
    put("selfclosed_vs_att2_end_pct", sc["dev_end_pct"], "%", "shrinkclosed_summary.json", "dev_end_pct")
    # 逐行复核 shrinkclosed.csv：末行口径 + 偏差极值（区分"72 h 末行 1.198"与"t_d 处 1.199"）
    scl = read_csv(os.path.join(FIGD, "shrinkclosed.csv"))
    devs = [float(r["dev_pct"]) for r in scl]
    lastc = scl[-1]
    put("shrinkclosed_rows", len(scl), "count", "figdata/shrinkclosed.csv", "len")
    put("shrinkclosed_last", {k: float(v) for k, v in lastc.items()}, "-",
        "figdata/shrinkclosed.csv", "末行（= 自洽闭合端点）")
    put("shrinkclosed_dev_min_pct", min(devs), "%", "figdata/shrinkclosed.csv", "min(dev_pct)")
    put("shrinkclosed_dev_max_pct", max(devs), "%", "figdata/shrinkclosed.csv", "max(dev_pct)")
    put("shrinkclosed_dev_span_pct", max(devs) - min(devs), "%", "figdata/shrinkclosed.csv", "极差")
    # 附件2 半径在自洽端点时刻的取值（插值），核 1.199 的口径
    t_end_closed = float(lastc["t_s"])
    r_at = None
    for i in range(1, len(rad_d)):
        if rad_d[i - 1][0] <= t_end_closed <= rad_d[i][0]:
            f = ((t_end_closed - rad_d[i - 1][0]) / (rad_d[i][0] - rad_d[i - 1][0])
                 if rad_d[i][0] != rad_d[i - 1][0] else 0.0)
            r_at = rad_d[i - 1][1] + f * (rad_d[i][1] - rad_d[i - 1][1])
            break
    put("R_att2_at_selfclosed_td_cm", r_at, "cm", "figdata/radius_att2.csv 插值",
        "在 t=%.4f h 处插值" % (t_end_closed / 3600.0))
    rf = read_json(os.path.join(FIGD, "radius_fit.json"))
    put("radius_fit", rf, "-", "figdata/radius_fit.json", "原样")

    # ---------------- 13. 参数灵敏度与蒙特卡洛 ----------------
    sens = read_csv(os.path.join(FIGD, "sensitivity.csv"))
    put("param_sensitivity", [{k: (v if k in ("question", "param") else
                                   (None if v == "" else float(v))) for k, v in r.items()}
                              for r in sens], "h / -", "figdata/sensitivity.csv", "原样")
    mc = read_json(os.path.join(FIGD, "mc_sensitivity_summary.json"))
    put("monte_carlo", mc, "-", "figdata/mc_sensitivity_summary.json", "原样")
    put("kappa_crit", fd["kap"]["kappa_crit"], "-", "figdata/figdata_summary.json", "kap.kappa_crit")
    put("kappa_td_first_last_h", [fd["kap"]["kappa_td_h"][0], fd["kap"]["kappa_td_h"][-1]], "h",
        "figdata/figdata_summary.json", "kappa=0 与 kappa=2.995")

    # ---------------- 14. 网格口径 ----------------
    for q in (1, 2, 3, 4):
        s = read_json(os.path.join(ROOT, "data", "processed", "results", "q%d_summary.json" % q))
        put("grid_q%d" % q, {k: s[k] for k in ("Nc", "dt_internal", "Ccr") if k in s} |
            {"t_d_h": s.get("t_d_h"), "t_d_s": s.get("t_d_s"), "R_end_cm": s.get("R_end_cm")},
            "-", "问题%d/results/q%d_summary.json" % (q, q), "原样键")

    # ---------------- 15. 双向离散的地板拟合（误差曲面 7x6） ----------------
    # 固定 Nc 加密 dt 时，空间误差形成地板，表观时间阶被顶住（Nc=200 上伪阶 0.54..0.13）。
    # 把地板显式写进拟合式 err = F(Nc) + C*dt^p，才能还原真实的时间阶。
    surf_rows = read_csv(os.path.join(FIGD, "cand_surface.csv"))
    bync = {}
    for r in surf_rows:
        bync.setdefault(int(float(r["Nc"])), []).append((float(r["dt"]), float(r["err"])))
    ncs = sorted(bync)
    fits = {}
    for nc in ncs:
        pair = sorted(bync[nc])
        fits[nc] = _floor_fit([q[0] for q in pair], [q[1] for q in pair])
    ps = [fits[nc][2] for nc in ncs]
    cs = [fits[nc][1] for nc in ncs]
    fs = [fits[nc][0] for nc in ncs]
    put("floor_fit_nc", ncs, "-", "figdata/cand_surface.csv", "曲面网格的空间档")
    put("floor_fit_p", ps, "-", "figdata/cand_surface.csv",
        "err=F+C*dt^p：p 一维扫描 + 内层 (F,C) 闭式最小二乘（_floor_fit）")
    put("floor_fit_p_min", min(ps), "-", "figdata/cand_surface.csv", "min(p)")
    put("floor_fit_p_max", max(ps), "-", "figdata/cand_surface.csv", "max(p)")
    put("floor_fit_C_mean", sum(cs) / len(cs), "kg/kg", "figdata/cand_surface.csv", "mean(C)")
    put("floor_fit_C_spread_pct",
        100.0 * (max(cs) - min(cs)) / (sum(cs) / len(cs)), "%",
        "figdata/cand_surface.csv", "(max(C)-min(C))/mean(C)")
    put("floor_fit_F", fs, "kg/kg", "figdata/cand_surface.csv", "各 Nc 的地板")
    put("floor_fit_F_ratio", [fs[i] / fs[i + 1] for i in range(len(fs) - 1)], "-",
        "figdata/cand_surface.csv", "逐次 F(Nc)/F(2Nc)，空间二阶应趋 4")
    put("floor_fit_dt_star_s",
        [(fs[i] / cs[i]) ** (1.0 / ps[i]) for i in range(len(ncs))], "s",
        "figdata/cand_surface.csv", "(F/C)^(1/p)：时间误差与空间地板相等处")

    # ---------------- 16. 干质量闭合：均值口径 vs 严格全场积分口径 ----------------
    #  产物出自独立装置 strict_closure.py，该装置自带门禁（先逐位复现已发表的均值
    #  口径端点）。原先散落在本文件里的 61.4016 / -6.09 / 20.2 等手算条目改由此处
    #  统一供给，使两种口径同出一源、可逐项对照，也避免"自洽半径超出量"与
    #  "端点位移"两个同为百分数的量在表里串位。
    cl = read_json(os.path.join(TS_DATA, "strict_closure_summary.json"))
    assert cl["gate"]["passed"], "strict_closure 装置门禁未通过"
    put("closure_gate_passed", bool(cl["gate"]["passed"]), "bool",
        "thermal_science/data/strict_closure_summary.json", "装置自校验（须 True）")
    put("closure_case", cl["case"], "-", "strict_closure_summary.json", "原样")
    put("closure_Nc", cl["Nc"], "-", "strict_closure_summary.json", "原样")
    put("closure_dt_s", cl["dt"], "s", "strict_closure_summary.json", "原样")
    put("closure_piter", cl["piter"], "-", "strict_closure_summary.json", "半径-场不动点迭代次数")
    put("closure_v0_m3kg", cl["v0"], "m3/kg", "strict_closure_summary.json", "v(C0)=(1+C0)/rho_B(C0)")
    for tag, sub in (("meanv", "mean_v"), ("strict", "strict")):
        d = cl[sub]
        put("closure_td_%s_h" % tag, d["t_d_h"], "h", "strict_closure_summary.json",
            "mean_v: R=R0*sqrt(<v>/v0)；strict: R=R0/sqrt(v0*sum(w_i/v_i))")
        put("closure_td_%s_s" % tag, d["t_d_s"], "s", "strict_closure_summary.json", "原样")
        put("closure_dev_end_%s_pct" % tag, d["dev_end_pct"], "%", "strict_closure_summary.json",
            "(R_att2-R_closed)/R_att2*100，负号表示自洽半径大于制表值")
        put("closure_dev_min_%s_pct" % tag, d["dev_min_pct"], "%", "strict_closure_summary.json",
            "min(dev_pct)")
        put("closure_dev_max_%s_pct" % tag, d["dev_max_pct"], "%", "strict_closure_summary.json",
            "max(dev_pct)")
        # 正文用的是"超出"口径（正数）：对 dev_pct 取负号换向，符号约定在此一次性固定
        put("closure_excess_min_%s_pct" % tag, -d["dev_max_pct"], "%",
            "strict_closure_summary.json", "-dev_max_pct（自洽半径超出制表值的下界）")
        put("closure_excess_max_%s_pct" % tag, -d["dev_min_pct"], "%",
            "strict_closure_summary.json", "-dev_min_pct（超出量的上界）")
        put("closure_excess_end_%s_pct" % tag, -d["dev_end_pct"], "%",
            "strict_closure_summary.json", "-dev_end_pct（端点处超出量）")
        put("closure_Cbar_end_%s" % tag, d["Cbar_end"], "kg/kg", "strict_closure_summary.json",
            "端点体积平均含水率")
        put("closure_R_closed_end_%s_cm" % tag, d["R_closed_end_cm"], "cm",
            "strict_closure_summary.json", "自洽半径在端点的值")
        put("closure_eps_m_max_%s" % tag, d["eps_m_max"], "-", "strict_closure_summary.json",
            "干质量漂移 max|m_d(t)/m_d(0)-1|")
    put("closure_delta_td_h", cl["delta_td_h"], "h", "strict_closure_summary.json",
        "strict - mean_v")
    put("closure_delta_td_pct", cl["delta_td_pct"], "%", "strict_closure_summary.json",
        "(strict/mean_v - 1)*100：两口径之间的差")
    # 端点位移：相对"规定收缩"基准（B_shrinking），与上面的两口径之差是两个不同的量
    put("closure_base_td_h", a4s, "h", "figdata/ablation.json", "B_shrinking 规定收缩端点，位移基准")
    put("closure_shift_meanv_h", cl["mean_v"]["t_d_h"] - a4s, "h",
        "重算 vs ablation.json", "mean_v 端点 - 基准")
    put("closure_shift_meanv_pct", 100.0 * (cl["mean_v"]["t_d_h"] - a4s) / a4s, "%",
        "重算 vs ablation.json", "相对基准；勿与 closure_excess_* 混用")
    put("closure_shift_strict_h", cl["strict"]["t_d_h"] - a4s, "h",
        "重算 vs ablation.json", "strict 端点 - 基准")
    put("closure_shift_strict_pct", 100.0 * (cl["strict"]["t_d_h"] - a4s) / a4s, "%",
        "重算 vs ablation.json", "相对基准")
    # 式(8) 的半径下界、初始干质量，与上面的自洽闭合共用同一套物性
    put("closure_md_initial_kg", m_d0, "kg", "重算", "rho_B(C0)*pi*R0^2*L/(1+C0)")

    # ---------------- 17. 扰动集合：512 次（原 16 次为其随机流前缀） ----------------
    e5 = read_json(os.path.join(TS_DATA, "mc_ensemble_summary.json"))
    assert e5["gate"]["passed"], "mc_ensemble 装置门禁未通过"
    put("ens_gate_passed", bool(e5["gate"]["passed"]), "bool",
        "thermal_science/data/mc_ensemble_summary.json", "装置自校验（须 True）")
    put("ens_N", e5["N"], "count", "mc_ensemble_summary.json", "每配置成员数")
    put("ens_seed", e5["seed"], "-", "mc_ensemble_summary.json", "原样")
    put("ens_dist", e5["dist"], "-", "mc_ensemble_summary.json", "均匀分布，人为扰动带")
    put("ens_gate_n", e5["gate"]["n"], "count", "mc_ensemble_summary.json",
        "门禁样本数（= 已发表的 16 成员）")
    put("ens_gate_maxdev_h", e5["gate"]["max_dev_h"], "h", "mc_ensemble_summary.json",
        "前缀逐位复现已发表值的最大偏差")
    for q in ("q3", "q4"):
        for k in ("mean_h", "sd_h", "median_h", "min_h", "max_h", "q025_h", "q975_h",
                  "q05_h", "q95_h", "w95_h", "rel_w95_pct"):
            put("ens_%s_%s" % (q, k), e5["result"][q][k],
                "h" if k.endswith("_h") else "%", "mc_ensemble_summary.json", "原样")
    put("ens_n_missing_endpoint", {"q3": e5["result"]["q3"]["n_missing_endpoint"],
                                   "q4": e5["result"]["q4"]["n_missing_endpoint"]},
        "count", "mc_ensemble_summary.json", "未达阈的成员数，须为 0")
    # 16 成员版本（已发表），用于正文那句"更早的版本把同样两个相对宽度放在 7.21/12.10"
    mc16 = read_json(os.path.join(FIGD, "mc_sensitivity_summary.json"))
    put("ens16_rel_w95_q3_pct", mc16["result"]["q3"]["rel_w95_pct"], "%",
        "figdata/mc_sensitivity_summary.json", "原样")
    put("ens16_rel_w95_q4_pct", mc16["result"]["q4"]["rel_w95_pct"], "%",
        "figdata/mc_sensitivity_summary.json", "原样")
    put("ens_rel_w95_widen_factor", {"q3": e5["result"]["q3"]["rel_w95_pct"] / mc16["result"]["q3"]["rel_w95_pct"],
                                     "q4": e5["result"]["q4"]["rel_w95_pct"] / mc16["result"]["q4"]["rel_w95_pct"]},
        "-", "重算", "512 成员相对宽度 / 16 成员相对宽度")

    # ---------------- 18. Morris 全局筛选 ----------------
    ms = read_json(os.path.join(TS_DATA, "morris_screen_summary.json"))
    put("morris_levels", ms["levels"], "-", "thermal_science/data/morris_screen_summary.json", "原样")
    put("morris_trajectories", ms["trajectories"], "count", "morris_screen_summary.json", "每配置轨迹数")
    put("morris_band", ms["band"], "-", "morris_screen_summary.json", "乘性参数的相对半宽")
    put("morris_dt_range_C", ms["dt_range_C"], "degC", "morris_screen_summary.json",
        "T∞ 的绝对半宽（不能乘性缩放：env 里是开尔文）")
    put("morris_seed", ms["seed"], "-", "morris_screen_summary.json", "原样")
    put("morris_step_rel", 2.0 * ms["band"] * ms["levels"] / (2.0 * (ms["levels"] - 1.0)), "-",
        "morris_screen.py 口径", "乘性参数的单个基本步长 Δp/p")
    ratio_max = 0.0
    for cfg in ("A", "B"):
        r = ms["results"][cfg]
        put("morris_%s_k" % cfg, r["k"], "count", "morris_screen_summary.json", "该配置参数个数")
        put("morris_%s_n_runs" % cfg, r["n_runs"], "count", "morris_screen_summary.json",
            "trajectories*(k+1)")
        put("morris_%s_ref_td_h" % cfg, r["ref_td_h"], "h", "morris_screen_summary.json",
            "该配置的参考端点（未扰动）")
        for p, d in sorted(r["params"].items()):
            put("morris_%s_%s_mu_star" % (cfg, p), d["mu_star"], "-" if p != "T" else "h/degC",
                "morris_screen_summary.json", "|EE| 均值；乘性参数为 S 等效量")
            put("morris_%s_%s_sigma" % (cfg, p), d["sigma"], "-", "morris_screen_summary.json",
                "EE 标准差 ddof=1")
            put("morris_%s_%s_ratio" % (cfg, p), d["ratio"], "-", "morris_screen_summary.json",
                "sigma/mu_star")
            ratio_max = max(ratio_max, abs(d["ratio"]))
    put("morris_total_runs", ms["results"]["A"]["n_runs"] + ms["results"]["B"]["n_runs"], "count",
        "重算", "n_runs_A + n_runs_B，正文的 130")
    put("morris_max_ratio", ratio_max, "-", "重算",
        "max(sigma/mu_star)；正文的'不超过 7.7%'")
    # 每个参数在其扰动带内把端点推动多少：Δln t = mu_star * Δln p（乘性），
    # T 为绝对量 Δt = mu_star * 2*dt_range_C。与 S_p 同一量级，但口径必须写明。
    dlnp = math.log(1.0 + ms["band"]) - math.log(1.0 - ms["band"])
    for cfg in ("A", "B"):
        r = ms["results"][cfg]
        for p, d in sorted(r["params"].items()):
            if p == "T":
                span = d["mu_star"] * 2.0 * ms["dt_range_C"]      # h/degC * 全幅 2 degC
                how = "mu_star*2*dT_range"
            else:
                span = d["mu_star"] * dlnp * r["ref_td_h"]        # S 等效量 * 全幅 ln(1.05/0.95)
                how = "mu_star*ln(1.05/0.95)*ref_td_h"
            put("morris_%s_%s_band_span_h" % (cfg, p), span, "h", "重算", how)

    # ---------------- 19. 题给常量、半径拟合、网格稳定性、冻结对照 ----------------
    #  正文散落的小字面量在此之前没有单一来源，这里一次性把它们接到产物上。
    for name, val, unit, src, mth in (
            ("T0_C", 28.0, "degC", "题给", "初始温度"),
            ("C0_kgkg", C0, "kg/kg", "题给", "初始干基含水率"),
            ("R0_cm", R0_CM, "cm", "题给", "初始半径"),
            ("L_m", L_CYL, "m", "题给", "圆柱长度"),
            ("h_W_m2K", H, "W/m2/K", "题给", "表面对流传热系数，两套物性共用"),
            ("hm_m_s", HM, "m/s", "题给", "表面传质系数，两套物性共用")):
        put(name, val, unit, src, mth)

    rfit = read_json(os.path.join(FIGD, "radius_fit.json"))
    put("radius_fit_a_cm", rfit["a"], "cm", "figdata/radius_fit.json", "R=a+b*exp(-t/tau)")
    put("radius_fit_b_cm", rfit["b"], "cm", "figdata/radius_fit.json", "同上")
    put("radius_fit_tau_s", rfit["tau_s"], "s", "figdata/radius_fit.json", "同上")
    put("radius_fit_sd_cm", rfit["sd"][:2], "cm", "figdata/radius_fit.json", "a、b 的标准误")
    put("radius_fit_sd_tau_s", rfit["sd"][2], "s", "figdata/radius_fit.json", "tau 的标准误")

    for tag, k in (("G", "G_geo"), ("P", "P_prop"), ("I", "I_int")):
        put("grid_%s_first" % tag, float(grid[0][k]), "-", "figdata/ablation_grid.csv",
            "Nc=%d" % int(float(grid[0]["Nc"])))
        put("grid_%s_last" % tag, float(grid[-1][k]), "-", "figdata/ablation_grid.csv",
            "Nc=%d" % int(float(grid[-1]["Nc"])))

    # 五窗口 T_plat 的极差：正文"窗口只worth 0.504 degC"
    put("window_T_span_C", max(float(r["T_plat_C"]) for r in win) - min(float(r["T_plat_C"]) for r in win),
        "degC", "boundary_extrapolation.csv", "5 个窗口 T_plat 的 max-min")
    put("cand_surface_n_runs", len(surf_rows), "count", "figdata/cand_surface.csv",
        "双向加密算例数，正文的 42")

    # 表 2 在 Ccr=0.1737 处谁更早、差多少秒（标签是手写的，这里给出机器判据）
    g1737 = [s for s in scan if abs(s["Ccr"] - 0.1737) < 1e-12][0]
    d1737 = (g1737["B_shrinking_h"] - g1737["A_fixed_h"]) * 3600.0
    put("cross_gap_at_01737_s", abs(d1737), "s", "重算",
        "|B-A|*3600，由 threshold_scan 同一对值算出")
    put("cross_gap_at_01737_earlier", "A" if d1737 > 0 else "B", "-", "重算",
        "t_A<t_B 则 A 更早；正文表 2 的 Ordering 列须与此一致")

    # 冻结/状态依赖在 3 h 的对照（正文 §3.1）
    row3 = None
    for r in q2f:
        if abs(float(r["t_h"]) - 3.0) < 1e-9:
            row3 = r
    cfr, cdy = float(row3["C_center_frz"]), float(row3["C_center_dyn"])
    put("frozen_center_3h_kgkg", cfr, "kg/kg", "figdata/q2_frozen.csv", "t=3 h 行的 C_center_frz")
    put("frozen_center_gap_3h_pct", 100.0 * (cfr - cdy) / cdy, "%", "重算", "(frz-dyn)/dyn")
    put("released_frz_3h_pct", 100.0 * (C0 - cfr) / C0, "%", "重算", "(C0-C_frz)/C0")
    put("released_dyn_3h_pct", 100.0 * (C0 - cdy) / C0, "%", "重算", "(C0-C_dyn)/C0")
    put("released_ratio_3h", (C0 - cdy) / (C0 - cfr), "-", "重算", "已释放量之比（正文的 2.03）")

    # ---------------- 20. 平台段"多久算平"的机器判据 + 量级比 ----------------
    #  正文原写"末三小时总变幅小于 0.5 degC"，而 0.479 属于**末一小时**；末三小时实测跨度
    #  2.761 degC。这里把三个窗口的跨度同时登记，散文只能引用其中一个，避免范围漏缺。
    def T_range(a_h, b_h):
        seg_t = [T_env[i] for i in range(len(t_env)) if a_h * 3600.0 - 1e-9 <= t_env[i] <= b_h * 3600.0 + 1e-9]
        return max(seg_t) - min(seg_t)
    put("T_band_last1h_C", T_range(3.0, 4.0), "degC", "figdata/env_att1.csv", "t in [3,4] h 的 max-min")
    put("T_band_last2h_C", T_range(2.0, 4.0), "degC", "figdata/env_att1.csv", "t in [2,4] h 的 max-min")
    put("T_band_last3h_C", T_range(1.0, 4.0), "degC", "figdata/env_att1.csv", "t in [1,4] h 的 max-min")
    put("T_net_last1h_C", seg[3]["T_last_C"] - seg[3]["T_first_C"], "degC",
        "figdata/env_att1.csv", "T(4 h)-T(3 h)，含符号")
    put("T_at_3h_C", seg[3]["T_first_C"], "degC", "figdata/env_att1.csv", "t=3 h 的 T")

    # 量级比：S_p(D) / S_p(h)，正文用"三个数量级"描述，这里给真值供四舍五入
    for cfg, tag in (("q3", "A"), ("q4", "B")):
        got = {}
        for r in sens:
            if r["question"] == cfg and r["S_p"] not in ("", None):
                got[r["param"]] = float(r["S_p"])
        r_ratio = got["D"] / got["h"]
        put("sens_ratio_D_over_h_%s" % tag, r_ratio, "-", "figdata/sensitivity.csv", "S_p(D)/S_p(h)")
        put("sens_orders_D_over_h_%s" % tag, math.log10(r_ratio), "order", "重算", "log10 比值")
    # 两处"三个数量级"的真值：±2 degC 极差版 3.40（够 3），±1 degC 斜率版 2.80（只能说"近三"）
    disc_h = FACTS["fem_gap_A_fixed_s"]["value"] / 3600.0
    put("orders_Tspan2_over_disc",
        math.log10(FACTS["temp_span_A_h"]["value"] / disc_h), "order", "重算",
        "log10(±2 degC 极差 / 生产网格差)")
    put("orders_T1deg_over_disc",
        math.log10(FACTS["slope_pm1_A_h_per_C"]["value"] / disc_h), "order", "重算",
        "log10(±1 degC 斜率 / 生产网格差)")

    # ---------------- 落盘 ----------------
    os.makedirs(TS_DATA, exist_ok=True)
    out = os.path.join(TS_DATA, "numeric_facts.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(FACTS, fh, ensure_ascii=False, indent=1, default=str)
    print("written:", out, "entries:", len(FACTS))

    def show(name):
        e = FACTS[name]
        v = e["value"]
        if isinstance(v, float):
            v = round(v, 10)
        print("%-34s %s  [%s]  <- %s" % (name, v, e["unit"], e["source"]))

    keys = ["att1_rows", "att1_dt_unique_s", "att1_t_end_h", "att2_data_rows", "att2_dt_unique_s",
            "att2_t_end_h", "att2_R_first_cm", "att2_R_last_cm", "att2_R_min_cm",
            "att2_R_diff_down", "att2_R_diff_flat", "att2_R_diff_up",
            "T_plat_mean61_C", "C_plat_mean61", "T_lastpoint_C", "C_lastpoint",
            "segment_slope_max_absdiff", "td_A_fixed_h", "td_A_shrinking_h", "td_B_fixed_h",
            "td_B_shrinking_h", "delta_bundle_h", "delta_bundle_pct", "ratio_geo_A", "ratio_geo_B",
            "ratio_prop_fixed", "interaction_I", "fem_A_fixed_h", "fem_gap_A_fixed_s",
            "fem_B_shrinking_h", "fem_gap_B_shrinking_s", "conv_space_orders", "conv_time_orders",
            "crossing_Ccr", "crossing_t_h", "scan_vs_production_A_fixed_s",
            "scan_vs_production_B_shrinking_s", "cross_surf_dyn_h", "cross_center_dyn_h",
            "cross_surf_frz_h", "cross_center_frz_h", "state_3h", "state_3h_archived",
            "T_uniformity_3h_maxdiff_C", "window_span_A_h", "window_span_B_h", "temp_span_A_h",
            "temp_span_B_h", "amplifier_A", "amplifier_B", "window_span_A_pct_of_base",
            "slope_pm1_A_h_per_C", "slope_pm1_B_h_per_C", "slope_pm2_A_h_per_C",
            "slope_pm2_B_h_per_C", "curvature_A_pct", "curvature_B_pct",
            "record_coverage_A_fixed_pct", "extrapolated_share_A_fixed_pct",
            "extrapolated_share_B_shrinking_pct", "R_bound_cm", "att2_below_bound_count",
            "att2_below_bound_first_h", "m_dry_initial_kg", "Cbar_at_td", "R_att2_at_td_cm",
            "m_dry_endpoint_kg", "m_dry_ratio", "m_dry_loss_pct", "selfclosed_vs_att2_end_pct",
            "kappa_crit", "R_bound_first_datarow_h", "R_bound_first_interp_h",
            "cross_dynfrz_surf_h", "cross_dynfrz_center_h", "dynfrz_common_rows",
            "dynfrz_trace_span_h", "shrinkclosed_rows", "shrinkclosed_last",
            "shrinkclosed_dev_min_pct", "shrinkclosed_dev_max_pct", "shrinkclosed_dev_span_pct",
            "R_att2_at_selfclosed_td_cm", "tmap_keys", "att2_file_rows",
            "slope_cold1_A_h_per_C", "slope_warm1_A_h_per_C", "slope_cold2_A_h_per_C",
            "slope_warm2_A_h_per_C", "asym_pm1_A_pct", "asym_pm2_A_pct",
            "slope_cold1_B_h_per_C", "slope_warm1_B_h_per_C", "slope_cold2_B_h_per_C",
            "slope_warm2_B_h_per_C", "asym_pm1_B_pct", "asym_pm2_B_pct"]
    print("-" * 78)
    for k in keys:
        show(k)
    print("-" * 78)
    print("segment_slopes:")
    for s in FACTS["segment_slopes"]["value"]:
        print("   ", s)
    print("threshold_scan:")
    for s in FACTS["threshold_scan"]["value"]:
        print("   ", s)
    print("order_obs:", FACTS["order_obs"]["value"])


if __name__ == "__main__":
    main()
