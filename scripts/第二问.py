# -*- coding: utf-8 -*-
# 问题2 全部计算：整个烘干过程（附录3，R ≡ 2 cm，全程一套物性）
#   正式解    表3/表4（3 h 内每 0.5 h × {0,0.5,1,1.5,2} cm）+ result2.xlsx（1–259200 s，每 1 s × 0.1 cm）
#   受控基线  物性冻结在初值 vs 随状态演变（原 对照_物性冻结基线.py，2026-09-13 并入本文件）
# 用法：python 第二问.py            正式解
#       python 第二问.py baseline   受控基线
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

CASE, NC, DT, OUT_DT, TMAX = 3, 800, 0.5, 1.0, 259200.0
SAMPLE_EVERY = int(round(OUT_DT / DT))
DIST_CM = np.round(np.arange(0.0, 2.0001, 0.1), 1)
DIST_M = DIST_CM / 100.0
TAB_T = np.array([1800.0, 3600.0, 5400.0, 7200.0, 9000.0, 10800.0])
TAB_LBL = ["0.5 h", "1.0 h", "1.5 h", "2.0 h", "2.5 h", "3.0 h"]
TAB_R_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
RES = os.path.join(_ROOT, "results", "q2")


def write_csv(path, mat, header_col, row_names):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([""] + ["%.1f" % x for x in header_col])
        for name, row in zip(row_names, mat):
            w.writerow([name] + ["%.4f" % v for v in row])


def main():
    import xlsxwriter
    xls = os.path.join(RES, "result2.xlsx")
    tmp = common.guard_out(xls)
    wb = xlsxwriter.Workbook(tmp, {"constant_memory": True,
                                   "default_format_properties":
                                       {"font_name": "宋体", "font_size": 11}})
    fmt = wb.add_format({"num_format": "0.0000"})
    wsT = wb.add_worksheet("温度")
    wsC = wb.add_worksheet("水分浓度")
    for ws in (wsT, wsC):
        ws.write(0, 0, "时间\\到药材中心的距离")
        for j, v in enumerate(DIST_CM):
            ws.write_number(0, 1 + j, float(v))

    tab = {}

    def sampler(t, C, T, Rw, Tamb, Cinf):
        rr, Cx, Tx = common.profile_ext(CASE, C, T, NC, Rw, Cinf, Tamb)
        i = int(round(t / OUT_DT))
        cv = np.interp(DIST_M, rr, Cx)
        tv = np.interp(DIST_M, rr, Tx) - 273.15
        wsT.write_number(i, 0, round(float(t), 4))
        wsC.write_number(i, 0, round(float(t), 4))
        wsT.write_row(i, 1, [round(float(v), 4) for v in tv], fmt)
        wsC.write_row(i, 1, [round(float(v), 4) for v in cv], fmt)
        for k, tt in enumerate(TAB_T):
            if abs(t - tt) < 1e-6:
                tab[tt] = (tv.copy(), cv.copy())
        return None

    out = fvm1d.solve1d(case=CASE, Nc=NC, dt=DT, tmax=TMAX, shrink=False,
                        Ccr=-1.0, sampler=sampler, sample_every=SAMPLE_EVERY)
    wb.close()
    common.commit_out(tmp, xls)

    matT = np.array([tab[x][0] for x in TAB_T])
    matC = np.array([tab[x][1] for x in TAB_T])
    jdx = [int(np.argmin(np.abs(DIST_CM - x))) for x in TAB_R_CM]
    matT = matT[:, jdx]
    matC = matC[:, jdx]
    write_csv(os.path.join(RES, "表3_温度.csv"), matT, TAB_R_CM, TAB_LBL)
    write_csv(os.path.join(RES, "表4_水分浓度.csv"), matC, TAB_R_CM, TAB_LBL)

    print("问题2  Nc=%d 内步长=%g s 输出间隔=%g s  tmax=%g s" % (NC, DT, OUT_DT, TMAX))
    print("表3《3 小时内药材的温度》℃  列 = 距中心 %s cm"
          % " ".join("%.1f" % v for v in TAB_R_CM))
    for n, r in zip(TAB_LBL, matT):
        print("   %-6s " % n + "  ".join("%.4f" % v for v in r))
    print("表4《3 小时内药材的水分浓度》kg/kg")
    for n, r in zip(TAB_LBL, matC):
        print("   %-6s " % n + "  ".join("%.4f" % v for v in r))
    with open(os.path.join(RES, "q2_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"Nc": NC, "dt_internal": DT, "dt_output": OUT_DT, "tmax": TMAX,
                   "表3_温度_C": [[round(float(v), 4) for v in row] for row in matT],
                   "表4_水分浓度": [[round(float(v), 4) for v in row] for row in matC],
                   "表_时刻": TAB_LBL, "表_距离_cm": [float(v) for v in TAB_R_CM]},
                  f, ensure_ascii=False, indent=2)
    return matT, matC


def 受控基线():
    """受控基线：同一附录3 参数体系下，"物性冻结在初值" vs "物性随状态演变"。
    目的是把"状态依赖物性到底改变了什么"从叙述变成数字——这是消息级增量，不是重跑同一模型。
    冻结口径：rho/cp/k/D 全部取 (C0=2.55, T0=28℃) 处的值并全程不变；
              边界、网格、时间步、判据全部与正式解相同，差的只有物性是否随状态走。
    产出 支撑材料/figdata/q2_frozen.csv 与 q2_frozen_trace.csv。
    常量为局部量，避免与正式解的 TMAX/RES 撞名。"""
    CASE_B, NC_B, DT_B = 3, 800, 0.5
    TMAX_B = 48 * 3600.0
    SAMPLE_S = 600.0
    OUT_B = os.path.join(_ROOT, "支撑材料", "figdata")

    RHO_F, CP_F, K_F, D_F = [float(v) for v in
                             common.props(CASE_B, np.array([common.C0]),
                                          np.array([common.T0_C]) + 273.15)]

    def surfC_const(Clast, Rw, Cinf, Dc):
        gi = 2.0 * np.pi * common.L_CYL * Dc / np.log(1.0 / (1.0 - 0.5 / NC_B))
        gf = 2.0 * np.pi * common.L_CYL * Rw * common.HM
        return (gi * Clast + gf * Cinf) / (gi + gf)

    def run(tag, freeze):
        orig = fvm1d.props

        def frozen(case, C, T):
            C = np.asarray(C, float)
            return (np.full_like(C, RHO_F), np.full_like(C, CP_F),
                    np.full_like(C, K_F), np.full_like(C, D_F))

        fvm1d.props = frozen if freeze else orig
        try:
            every = max(1, int(round(SAMPLE_S / DT_B)))
            buf = []

            def samp(t_new, Cc, T, Rw, Tamb, Cinf):
                Dc = D_F if freeze else float(common.props(CASE_B, Cc[-1:], T[-1:])[3][0])
                buf.append([t_new, float(Cc[0]), surfC_const(Cc[-1], Rw, Cinf, Dc),
                            float(T[0]) - 273.15, float(Cc.max()),
                            float(T[-1]) - 273.15])
                return buf[-1]

            fvm1d.solve1d(case=CASE_B, Nc=NC_B, dt=DT_B, tmax=TMAX_B, Ccr=-1.0,
                          sampler=samp, sample_every=every)
        finally:
            fvm1d.props = orig
        print("  %s：初值物性 rho=%.2f cp=%.2f k=%.4f D=%.4e" % (tag, RHO_F, CP_F, K_F, D_F))
        return np.array(buf)

    def at(arr, th):
        i = int(np.argmin(np.abs(arr[:, 0] - th * 3600.0)))
        return arr[i]

    print("Q2 受控基线：物性冻结 vs 状态依赖（附录3，Nc=%d，dt=%.1f s）" % (NC_B, DT_B))
    dyn = run("动态物性", False)
    frz = run("冻结物性", True)
    marks = (1.0, 2.0, 3.0, 6.0, 12.0, 24.0, 48.0)
    rows = []
    hdr = ["t_h", "C_center_dyn", "C_center_frz", "dC_center_pct",
           "C_surf_dyn", "C_surf_frz", "T_center_dyn_C", "T_center_frz_C"]
    print("  %-6s %-11s %-11s %-9s %-11s %-11s %-11s"
          % ("t/h", "C心(动态)", "C心(冻结)", "差%", "C表(动态)", "C表(冻结)", "T心(动态)℃"))
    for th in marks:
        a, b = at(dyn, th), at(frz, th)
        dp = 100.0 * (b[1] - a[1]) / a[1]
        rows.append([a[0] / 3600.0, a[1], b[1], dp, a[2], b[2], a[3], b[3]])
        print("  %-6.0f %-11.4f %-11.4f %+8.2f  %-11.4f %-11.4f %-11.3f"
              % (a[0] / 3600.0, a[1], b[1], dp, a[2], b[2], a[3]))
    with open(os.path.join(OUT_B, "q2_frozen.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(rows)
    print("\n-> q2_frozen.csv  %d 行" % len(rows))
    # 把整条 48 h 历程也落盘，供画图用（不截断到 7 个标记点）
    with open(os.path.join(OUT_B, "q2_frozen_trace.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_h", "series", "C_center", "C_surf", "T_center_C", "C_max"])
        for arr, tag in ((dyn, "dyn"), (frz, "frz")):
            for r in arr:
                w.writerow([r[0] / 3600.0, tag, r[1], r[2], r[3], r[4]])
    print("-> q2_frozen_trace.csv")


if __name__ == "__main__":
    # 用法：python 第二问.py            正式解
    #       python 第二问.py baseline   受控基线
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("baseline", "受控基线"):
        受控基线()
    else:
        main()
