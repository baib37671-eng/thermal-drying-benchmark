# -*- coding: utf-8 -*-
# 问题3：达标烘干时长（附录3，R ≡ 2 cm，判据 max_r C <= 0.15 kg/kg）
#   正式解    表5 + result3.xlsx
#   空间分解  达标时长的空间分解与内部阻力主导（原 专题_空间分解.py，2026-09-13 并入本文件）
# 用法：python 第三问.py            正式解
#       python 第三问.py spacebreak 空间分解
import os
import sys
import csv
import json
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "src"))
os.environ.setdefault("HERB_SRC", os.path.join(_ROOT, "data", "raw"))
import 公共 as common
import 公共 as fvm1d
from 公共 import R0, C0, T0_C, surfC, surfT

CASE, NC, DT, OUT_DT, CCR = 3, 1600, 7.5, 60.0, 0.15
SAMPLE_EVERY = int(round(OUT_DT / DT))
DIST_CM = np.round(np.arange(0.0, 2.0001, 0.1), 1)
DIST_M = DIST_CM / 100.0
TAB_R_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
RES = os.path.join(_ROOT, "results", "q3")


def write_csv(path, mat, header_col, row_names):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([""] + ["%.1f" % x for x in header_col])
        for name, row in zip(row_names, mat):
            w.writerow([name] + ["%.4f" % v for v in row])


def main():
    rows = []
    hour = {}
    xls = os.path.join(RES, "result3.xlsx")
    tmp = common.guard_out(xls)

    def sampler(t, C, T, Rw, Tamb, Cinf):
        rr, Cx, Tx = common.profile_ext(CASE, C, T, NC, Rw, Cinf, Tamb)
        cv = np.interp(DIST_M, rr, Cx)
        rows.append((t, cv))
        k = t / 3600.0
        if k > 0 and abs(k - round(k)) < 1e-9:
            hour[int(round(k))] = cv.copy()
        return None

    out = fvm1d.solve1d(case=CASE, Nc=NC, dt=DT, tmax=4.0e5, shrink=False,
                        Ccr=CCR, sampler=sampler, sample_every=SAMPLE_EVERY,
                        stop_at_hit=True)
    t_hit = out["t_hit_s"]
    Rw = out["Ri"]
    Tamb, Cinf = common.env(t_hit)
    Tamb = float(np.ravel(Tamb)[0])
    Cinf = float(np.ravel(Cinf)[0])
    rr, Cx, Tx = common.profile_ext(CASE, out["C"], out["T"], NC, Rw, Cinf, Tamb)
    cv_hit = np.interp(DIST_M, rr, Cx)
    if abs(rows[-1][0] - t_hit) > 1e-9:
        rows.append((t_hit, cv_hit))

    import xlsxwriter
    wb = xlsxwriter.Workbook(tmp, {"default_format_properties":
                                   {"font_name": "宋体", "font_size": 11}})
    fmt = wb.add_format({"num_format": "0.0000"})
    ws = wb.add_worksheet("Sheet1")
    ws.write(0, 0, "时间\\到药材中心的距离")
    for j, v in enumerate(DIST_CM):
        ws.write_number(0, 1 + j, float(v))
    for i, (t, cv) in enumerate(rows):
        ws.write_number(1 + i, 0, round(float(t), 4))
        for j in range(DIST_CM.size):
            ws.write_number(1 + i, 1 + j, round(float(cv[j]), 4), fmt)
    wb.close()
    common.commit_out(tmp, xls)

    jdx = [int(np.argmin(np.abs(DIST_CM - x))) for x in TAB_R_CM]
    hh = [6 * k for k in range(1, int(t_hit // 3600.0) // 6 + 1)]
    mat = np.array([hour[k][jdx] for k in hh] + [cv_hit[jdx]])
    lbl = ["%d" % k for k in hh] + ["烘干结束时间"]
    write_csv(os.path.join(RES, "表5_水分浓度.csv"), mat, TAB_R_CM, lbl)

    print("问题3  Nc=%d 内步长=%g s 输出间隔=%g s" % (NC, DT, OUT_DT))
    print("烘干结束时间  t_d = %.4f h = %.1f s   (=%.6f h)" % (out["td_h"], t_hit, out["td_h"]))
    print("result3.xlsx 行数 = %d（首行 t=%.1f s，末行 t=%.1f s）" % (len(rows), rows[0][0], rows[-1][0]))
    print("表5《药材烘干过程的水分浓度》kg/kg  列 = 距中心 %s cm"
          % " ".join("%.1f" % v for v in TAB_R_CM))
    for n, r in zip(lbl, mat):
        print("   %-12s " % n + "  ".join("%.4f" % v for v in r))
    with open(os.path.join(RES, "q3_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"Nc": NC, "dt_internal": DT, "dt_output": OUT_DT, "Ccr": CCR,
                   "t_d_h": round(float(out["td_h"]), 6), "t_d_s": round(float(t_hit), 4),
                   "表5_时刻_h": lbl,
                   "表5_水分浓度": [[round(float(v), 4) for v in row] for row in mat],
                   "表_距离_cm": [float(v) for v in TAB_R_CM]}, f, ensure_ascii=False, indent=2)
    return out


def 空间分解():
    """达标时长的空间分解：干透前锋推进 + 内部阻力主导（第7.5节）。"""
    case, nc, dt, ccr = 3, 1600, 7.5, 0.15
    stride, sample_s = 16, 300.0
    out_b = os.path.join(_ROOT, "支撑材料", "figdata")
    nsl = int(round(sample_s / dt))
    xi = (np.arange(nc) + 0.5) / nc
    keep = np.arange(0, nc, stride)
    field, series = [], []

    def sampler(t, C, T, Rw, Tamb, Cinf):
        cs = float(surfC(case, C, T, nc, Rw, Cinf))
        ts = float(surfT(case, C, T, nc, Rw, Tamb)) - 273.15
        rc = xi[keep] * Rw * 100.0
        for i, k in enumerate(keep):
            field.append((t, float(rc[i]), float(C[k]), float(T[k]) - 273.15))
        field.append((t, float(Rw) * 100.0, cs, ts))
        series.append((t, float(C[0]), cs, float(T[0]) - 273.15, ts,
                       float(Rw) * 100.0))
        return None

    out = fvm1d.solve1d(case=case, Nc=nc, dt=dt, tmax=4.0e5, shrink=False, Ccr=ccr,
                        sampler=sampler, sample_every=nsl, stop_at_hit=True)

    nnode = keep.size + 1
    r0 = np.concatenate([xi[keep] * R0 * 100.0, [R0 * 100.0]])
    field = [(0.0, float(rv), float(C0), float(T0_C)) for rv in r0] + field
    series = [(0.0, float(C0), float(C0), float(T0_C), float(T0_C),
               float(R0) * 100.0)] + series

    a = np.asarray(field, float)
    assert a.shape[0] % nnode == 0, "剖面片数不是整数"
    ns = a.shape[0] // nnode
    T = a[:, 0].reshape(ns, nnode)[:, 0]
    R = a[:, 1].reshape(ns, nnode)[0]
    assert np.allclose(a[:, 1].reshape(ns, nnode), R), "固定域下节点半径应逐片相同"
    C = a[:, 2].reshape(ns, nnode)
    tcross = np.full(nnode, np.nan)
    for j in range(nnode):
        col = C[:, j]
        idx = np.nonzero(col <= ccr)[0]
        if idx.size == 0 or idx[0] == 0:
            continue
        i = idx[0]
        w = (col[i - 1] - ccr) / (col[i - 1] - col[i])
        tcross[j] = T[i - 1] + w * (T[i] - T[i - 1])

    td_h = out["td_h"]
    t_surf = float(tcross[-1]) / 3600.0
    t_core = float(tcross[0]) / 3600.0
    span = t_core - t_surf
    print("问题三空间分解（生产格 Nc=%d / dt=%g s）" % (nc, dt))
    print("  剖面片数 %d × 节点 %d = %d 行；t_hit = %.6f h (%.1f s)"
          % (C.shape[0], nnode, len(field), td_h, out["t_hit_s"]))
    print("  表面首越 0.15：t = %.4f h   轴心首越 0.15：t = %.4f h" % (t_surf, t_core))
    print("  补平段 %.4f h，占达标时长 %.4f%%" % (span, span / t_core * 100.0))
    print("  前锋曲线单调性：d t_cross/d r 全为负 = %s"
          % bool(np.all(np.diff(tcross[::-1]) > 0)))

    s = np.asarray(series, float)
    iT = int(np.argmax(np.abs(s[:, 4] - s[:, 3])))
    dT = float(abs(s[iT, 4] - s[iT, 3]))
    t10 = next((float(s[i, 0]) / 3600.0 for i in range(iT, s.shape[0])
                if abs(s[i, 4] - s[i, 3]) < 0.1 * dT), float("nan"))
    sC = s[:, 1] - s[:, 2]
    iC = int(np.argmax(sC))
    print("  热场 |T_surf-T_center| 峰值 %.4f degC @ %.4f h，衰减到峰值 10%% 于 %.4f h"
          % (dT, s[iT, 0] / 3600.0, t10))
    print("  湿场 C_center-C_surf 峰值 %.4f @ %.4f h；末值 %.4f"
          % (sC[iC], s[iC, 0] / 3600.0, sC[-1]))

    p = os.path.join(out_b, "spacebreak_field.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "t_h", "r_cm", "C", "T_C"])
        for (t, r, c, tc) in field:
            w.writerow(["%.1f" % t, "%.6f" % (t / 3600.0), "%.5f" % r,
                        "%.6f" % c, "%.5f" % tc])
    print("  -> %s  (%d 行, %.1f MB)"
          % (os.path.basename(p), len(field), os.path.getsize(p) / 1048576.0))

    p = os.path.join(out_b, "spacebreak_front.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["r_cm", "t_cross_h"])
        for r, t in zip(R, tcross):
            w.writerow(["%.5f" % r, "" if np.isnan(t) else "%.6f" % (t / 3600.0)])
    print("  -> %s" % os.path.basename(p))

    p = os.path.join(out_b, "spacebreak_series.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "t_h", "C_center", "C_surf", "T_center_C", "T_surf_C", "R_cm"])
        for row in series:
            w.writerow(["%.1f" % row[0], "%.6f" % (row[0] / 3600.0)]
                       + ["%.6f" % v for v in row[1:5]] + ["%.5f" % row[5]])
    print("  -> %s  (%d 行)" % (os.path.basename(p), len(series)))

    js = {"case": case, "Nc": nc, "dt": dt, "Ccr": ccr, "sample_s": sample_s,
          "n_slice": int(C.shape[0]), "n_node": nnode,
          "t_hit_s": out["t_hit_s"], "td_h": td_h,
          "t_surf_hit_h": t_surf, "t_core_hit_h": t_core,
          "core_lag_h": span, "core_lag_pct": span / t_core * 100.0,
          "dT_peak_C": dT, "dT_peak_h": float(s[iT, 0]) / 3600.0, "dT_decay10_h": t10,
          "dC_peak": float(sC[iC]), "dC_peak_h": float(s[iC, 0]) / 3600.0,
          "dC_end": float(sC[-1])}
    with open(os.path.join(out_b, "spacebreak_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)
    print("  -> spacebreak_summary.json")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("spacebreak", "空间分解"):
        空间分解()
    else:
        main()
