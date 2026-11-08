# -*- coding: utf-8 -*-
# 问题1 驱动：预热平衡阶段（附录2 固定物性，R ≡ 2 cm），0–1800 s
# 输出：表1/表2（论文表，7 个时刻 × {0,0.5,1,1.5,2} cm）+ result1.xlsx（每 1 s × 0.1 cm）
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

CASE, NC, DT, OUT_DT, TMAX = 2, 800, 0.05, 1.0, 1800.0
SAMPLE_EVERY = int(round(OUT_DT / DT))
DIST_CM = np.round(np.arange(0.0, 2.0001, 0.1), 1)
DIST_M = DIST_CM / 100.0
TAB_T = np.array([100.0, 300.0, 600.0, 900.0, 1200.0, 1500.0, 1800.0])
TAB_R_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
RES = os.path.join(_ROOT, "results", "q1")


def run():
    nrow = int(round(TMAX / OUT_DT))
    Ctab = np.empty((nrow, DIST_CM.size))
    Ttab = np.empty((nrow, DIST_CM.size))
    ttab = np.empty(nrow)

    def sampler(t, C, T, Rw, Tamb, Cinf):
        rr, Cx, Tx = common.profile_ext(CASE, C, T, NC, Rw, Cinf, Tamb)
        i = int(round(t / OUT_DT)) - 1
        ttab[i] = t
        Ctab[i] = np.interp(DIST_M, rr, Cx)
        Ttab[i] = np.interp(DIST_M, rr, Tx)
        return None

    out = fvm1d.solve1d(case=CASE, Nc=NC, dt=DT, tmax=TMAX, shrink=False,
                        Ccr=-1.0, sampler=sampler, sample_every=SAMPLE_EVERY)
    return out, ttab, Ttab, Ctab


def table_rows(ttab, arr):
    idx = [int(np.argmin(np.abs(ttab - x))) for x in TAB_T]
    jdx = [int(np.argmin(np.abs(DIST_CM - x))) for x in TAB_R_CM]
    return arr[np.ix_(idx, jdx)]


def write_csv(path, mat, header_col, row_names):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([""] + ["%.1f" % x for x in header_col])
        for name, row in zip(row_names, mat):
            w.writerow([name] + ["%.4f" % v for v in row])


def write_xlsx(tmp_path, final_path, ttab, Ttab, Ctab):
    import xlsxwriter
    wb = xlsxwriter.Workbook(tmp_path, {"default_format_properties":
                                        {"font_name": "宋体", "font_size": 11}})
    fmt = wb.add_format({"num_format": "0.0000"})
    for name, arr in (("温度", Ttab), ("水分浓度", Ctab)):
        ws = wb.add_worksheet(name)
        ws.write(0, 0, "时间\\到药材中心的距离")
        for j, v in enumerate(DIST_CM):
            ws.write_number(0, 1 + j, float(v))
        for i in range(arr.shape[0]):
            ws.write_number(1 + i, 0, round(float(ttab[i]), 4))
            for j in range(arr.shape[1]):
                ws.write_number(1 + i, 1 + j, round(float(arr[i, j]), 4), fmt)
    wb.close()
    common.commit_out(tmp_path, final_path)


def main():
    xls = os.path.join(RES, "result1.xlsx")
    tmp = common.guard_out(xls)
    out, ttab, Ttab, Ctab = run()
    TtabC = Ttab - 273.15
    matT = table_rows(ttab, TtabC)
    matC = table_rows(ttab, Ctab)
    names = ["%.0f s" % x for x in TAB_T]
    write_csv(os.path.join(RES, "表1_温度.csv"), matT, TAB_R_CM, names)
    write_csv(os.path.join(RES, "表2_水分浓度.csv"), matC, TAB_R_CM, names)
    write_xlsx(tmp, xls, ttab, TtabC, Ctab)

    print("问题1  Nc=%d 内步长=%g s 输出间隔=%g s  末态中心 T=%.4f ℃ C=%.4f  表面 T=%.4f ℃ C=%.4f"
          % (NC, DT, OUT_DT, TtabC[-1, 0], Ctab[-1, 0], TtabC[-1, -1], Ctab[-1, -1]))
    print("表1《30 分钟内药材的温度》℃  列 = 距中心 %s cm"
          % " ".join("%.1f" % v for v in TAB_R_CM))
    for n, r in zip(names, matT):
        print("   %-7s " % n + "  ".join("%.4f" % v for v in r))
    print("表2《30 分钟内药材的水分浓度》kg/kg")
    for n, r in zip(names, matC):
        print("   %-7s " % n + "  ".join("%.4f" % v for v in r))
    with open(os.path.join(RES, "q1_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"Nc": NC, "dt_internal": DT, "dt_output": OUT_DT, "tmax": TMAX,
                   "T_end_C": [round(float(v), 6) for v in TtabC[-1]],
                   "C_end": [round(float(v), 6) for v in Ctab[-1]],
                   "dist_cm": [float(v) for v in DIST_CM],
                   "表1_温度_C": [[round(float(v), 4) for v in row] for row in matT],
                   "表2_水分浓度": [[round(float(v), 4) for v in row] for row in matC],
                   "表1_时刻_s": [float(v) for v in TAB_T],
                   "表_距离_cm": [float(v) for v in TAB_R_CM]}, f, ensure_ascii=False, indent=2)
    return matT, matC


if __name__ == "__main__":
    main()
