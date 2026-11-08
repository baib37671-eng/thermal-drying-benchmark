# -*- coding: utf-8 -*-
# 问题4：含收缩的达标时长（附录4，R(t) 取附件2 实测轨迹，判据 max_r C <= 0.15）
#   正式解    表6 + result4.xlsx
#   自洽闭合  收缩由体积守恒解出（原 专题_收缩自洽闭合.py，2026-09-13 并入本文件）
#   本构反演  收缩升格为状态依赖本构（原 专题_收缩本构反演.py，2026-09-13 并入本文件）
# 用法：python 第四问.py             正式解
#       python 第四问.py closed      自洽闭合
#       python 第四问.py shrinklaw   本构反演
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
from scipy.linalg import solve_banded
from 公共 import (L_CYL, R0, T0_C, C0, H_Q, HM, env, props)
from 公共 import make_grid, face_logfac, _assemble, _wall_series

CASE, NC, DT, OUT_DT, CCR = 4, 1600, 7.5, 60.0, 0.15
SAMPLE_EVERY = int(round(OUT_DT / DT))
DIST_CM = np.round(np.arange(0.0, 1.9001, 0.1), 1)   # 固定物理距离列（末列另设"药材表面"）
DIST_M = DIST_CM / 100.0
TAB_R_CM = np.array([0.0, 0.5, 1.0])                 # 表6：„ 省略的中间列中始终在实体内的部分
RES = os.path.join(_ROOT, "results", "q4")


def write_csv(path, header, row_names, mat):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([""] + header)
        for name, row in zip(row_names, mat):
            w.writerow([name] + ["%.4f" % v for v in row])


def main():
    rows = []      # (t, cv 固定距离列, Cs 表面)
    hour = {}
    xls = os.path.join(RES, "result4.xlsx")
    tmp = common.guard_out(xls)

    def sampler(t, C, T, Rw, Tamb, Cinf):
        rr, Cx, Tx = common.profile_ext(CASE, C, T, NC, Rw, Cinf, Tamb)
        cv = np.interp(DIST_M, rr, Cx)
        Cs = float(Cx[-1])
        rows.append((t, cv, Cs, Rw))
        k = t / 3600.0
        if k > 0 and abs(k - round(k)) < 1e-9:
            hour[int(round(k))] = (cv.copy(), Cs)
        return None

    out = fvm1d.solve1d(case=CASE, Nc=NC, dt=DT, tmax=4.0e5, shrink=True,
                        Ccr=CCR, sampler=sampler, sample_every=SAMPLE_EVERY,
                        stop_at_hit=True)
    t_hit = out["t_hit_s"]
    Rw = out["Ri"]
    Tamb, Cinf = common.env(t_hit)
    Tamb = float(np.ravel(Tamb)[0])
    Cinf = float(np.ravel(Cinf)[0])
    rr, Cx, Tx = common.profile_ext(CASE, out["C"], out["T"], NC, Rw, Cinf, Tamb)
    cv_hit = np.interp(DIST_M, rr, Cx)
    Cs_hit = float(Cx[-1])
    if abs(rows[-1][0] - t_hit) > 1e-9:
        rows.append((t_hit, cv_hit, Cs_hit, Rw))

    import xlsxwriter
    wb = xlsxwriter.Workbook(tmp, {"default_format_properties":
                                   {"font_name": "宋体", "font_size": 11}})
    fmt = wb.add_format({"num_format": "0.0000"})
    ws = wb.add_worksheet("Sheet1")
    ws.write(0, 0, "时间\\到药材中心的距离")
    for j, v in enumerate(DIST_CM):
        ws.write_number(0, 1 + j, float(v))
    ws.write(0, 1 + DIST_CM.size, "药材表面")
    nblank = 0
    for i, (t, cv, Cs, Rw_i) in enumerate(rows):
        ws.write_number(1 + i, 0, round(float(t), 4))
        for j in range(DIST_CM.size):
            if DIST_M[j] <= Rw_i + 1e-12:
                ws.write_number(1 + i, 1 + j, round(float(cv[j]), 4), fmt)
            else:
                nblank += 1
        ws.write_number(1 + i, 1 + DIST_CM.size, round(float(Cs), 4), fmt)
    wb.close()
    common.commit_out(tmp, xls)

    jdx = [int(np.argmin(np.abs(DIST_CM - x))) for x in TAB_R_CM]
    hh = [6 * k for k in range(1, int(t_hit // 3600.0) // 6 + 1)]
    mat = np.array([[hour[k][0][j] for j in jdx] + [hour[k][1]] for k in hh]
                   + [[cv_hit[j] for j in jdx] + [Cs_hit]])
    lbl = ["%d" % k for k in hh] + ["烘干结束时间"]
    write_csv(os.path.join(RES, "表6_水分浓度.csv"),
              ["%.1f" % v for v in TAB_R_CM] + ["药材表面"], lbl, mat)

    print("问题4  Nc=%d 内步长=%g s 输出间隔=%g s" % (NC, DT, OUT_DT))
    print("烘干结束时间  t_d = %.4f h = %.1f s   末态 R(t_d) = %.5f cm"
          % (out["td_h"], t_hit, Rw * 100.0))
    print("result4.xlsx 行数=%d，超出 R(t) 留空格数=%d" % (len(rows), nblank))
    print("表6《药材烘干过程的水分浓度》kg/kg  列 = 距中心 %s cm + 药材表面"
          % " ".join("%.1f" % v for v in TAB_R_CM))
    for n, r in zip(lbl, mat):
        print("   %-12s " % n + "  ".join("%.4f" % v for v in r))
    with open(os.path.join(RES, "q4_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"Nc": NC, "dt_internal": DT, "dt_output": OUT_DT, "Ccr": CCR,
                   "t_d_h": round(float(out["td_h"]), 6), "t_d_s": round(float(t_hit), 4),
                   "R_end_cm": round(float(Rw * 100.0), 5),
                   "表6_时刻_h": lbl,
                   "表6_列_cm": [float(v) for v in TAB_R_CM] + ["药材表面"],
                   "表6_水分浓度": [[round(float(v), 4) for v in row] for row in mat]},
                  f, ensure_ascii=False, indent=2)
    return out


def 收缩自洽闭合():
    """R(t) 由体积守恒 R²/R0² = Σ wᵢ v(Cᵢ)/v(C0)、v(C)=(1+C)/rho(C) 逐步刷新，
    替代附件2 实测轨迹；其余网格、面导、壁面串联阻、锁步首值全沿用 fvm1d。"""
    case, nc, dt, ccr = 4, 1600, 7.5, 0.15
    out_b = os.path.join(_ROOT, "支撑材料", "figdata")

    def specvol(C, Tk):
        rho, _, _, _ = props(case, C, Tk)
        return (1.0 + np.asarray(C, float)) / rho

    def step_closed(Cc, T, h, Vsh, logfac, piter, Cinf, Tamb, v0, Rw0):
        Rw = Rw0
        Told = T.copy()
        Cold = Cc.copy()
        ln_wall = np.log(1.0 / (1.0 - 0.5 / nc))
        for _ in range(piter):
            Vi = np.pi * L_CYL * Rw ** 2 * Vsh
            rho, cp, kk, D = props(case, Cc, T)
            Df = np.empty(nc + 1)
            Df[1:nc] = 0.5 * (D[:-1] + D[1:])
            kf = np.empty(nc + 1)
            kf[1:nc] = 0.5 * (kk[:-1] + kk[1:])
            Gc = 2.0 * np.pi * L_CYL * Df * logfac
            Gt = 2.0 * np.pi * L_CYL * kf * logfac
            Gw_c = _wall_series(2.0 * np.pi * L_CYL * D[-1] / ln_wall,
                                2.0 * np.pi * L_CYL * Rw * HM)
            Gw_t = _wall_series(2.0 * np.pi * L_CYL * kk[-1] / ln_wall,
                                2.0 * np.pi * L_CYL * Rw * H_Q)
            abc, rhsc = _assemble(Vi, Gc, (1.0 / h) * np.ones(nc), Gw_c, Cinf, Cold)
            Cc = solve_banded((1, 1), abc, rhsc)
            abt, rhst = _assemble(Vi, Gt, rho * cp / h, Gw_t, Tamb, Told)
            T = solve_banded((1, 1), abt, rhst)
            vbar = float(np.sum(Vsh * specvol(Cc, T)))
            Rw = R0 * np.sqrt(vbar / v0)
        return Cc, T, Rw

    def solve_closed(tmax, piter=3, sampler=None, sample_every=1,
                     stop_at_hit=False):
        xi, Vsh = make_grid(nc)
        logfac = face_logfac(nc)
        Cc = np.full(nc, float(C0))
        T = np.full(nc, float(T0_C) + 273.15)
        v0 = float(specvol(np.array([C0]), np.array([T0_C + 273.15]))[0])
        Rw = R0
        t = 0.0
        hit = None
        prev_max = None
        prev_t = 0.0
        step = 0
        last_sampled = -1.0
        while t < tmax - 1e-9:
            h = min(dt, tmax - t)
            t_new = round(t + h, 6)
            Tamb, Cinf = env(t_new)
            Tamb = float(np.ravel(Tamb)[0])
            Cinf = float(np.ravel(Cinf)[0])
            Cprev, Tprev, Rwprev = Cc, T, Rw
            Cc, T, Rw = step_closed(Cc, T, h, Vsh, logfac, piter, Cinf, Tamb, v0, Rw)
            if hit is None:
                m = float(Cc.max())
                if m <= ccr and prev_max is not None and prev_max > ccr:
                    frac = 0.0 if prev_max <= m else (prev_max - ccr) / (prev_max - m)
                    hit = prev_t + frac * h
                    if stop_at_hit and hit - prev_t > 1e-12:
                        h2 = hit - prev_t
                        Tam2, Cin2 = env(hit)
                        Tam2 = float(np.ravel(Tam2)[0])
                        Cin2 = float(np.ravel(Cin2)[0])
                        Cc, T, Rw = step_closed(Cprev, Tprev, h2, Vsh, logfac,
                                                piter, Cin2, Tam2, v0, Rwprev)
                        Tamb, Cinf, t_new = Tam2, Cin2, hit
                prev_max = m
            step += 1
            if sampler is not None and (step % sample_every == 0
                                        or t_new >= tmax - 1e-9
                                        or (stop_at_hit and hit is not None)):
                if (stop_at_hit and hit is not None) or t_new > last_sampled + 1e-6:
                    sampler(t_new, Cc, T, Rw, Vsh, case)
                    last_sampled = t_new
            prev_t = t_new
            t = t_new
            if stop_at_hit and hit is not None:
                break
        return {"td_h": None if hit is None else hit / 3600.0, "t_hit_s": hit,
                "C": Cc, "T": T, "Ri": Rw}

    rows = []

    def sampler(t, C, T, Rw, Vsh, ca):
        rows.append((t, Rw, float(np.sum(Vsh * C))))

    out = solve_closed(4.0e5, sampler=sampler,
                       sample_every=int(round(300.0 / dt)), stop_at_hit=True)
    td, t_hit = out["td_h"], out["t_hit_s"]

    ta, ra = common.load_att2()
    ts = np.array([r[0] for r in rows])
    rc = np.array([r[1] for r in rows])
    cb = np.array([r[2] for r in rows])
    ra_i = np.interp(np.minimum(ts, ta[-1]), ta, ra) / 100.0
    dev = (ra_i - rc) / ra_i * 100.0

    path = os.path.join(out_b, "shrinkclosed.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "t_h", "R_closed_cm", "R_att2_cm", "dev_pct", "Cbar"])
        for i in range(len(ts)):
            w.writerow(["%.1f" % ts[i], "%.4f" % (ts[i] / 3600.0),
                        "%.5f" % (rc[i] * 100.0), "%.5f" % (ra_i[i] * 100.0),
                        "%.4f" % dev[i], "%.6f" % cb[i]])

    print("闭合收缩（case=4, Nc=%d, dt=%g s）" % (nc, dt))
    print("  t_d              = %.4f h" % td)
    print("  R(t_d) 自洽      = %.5f cm" % (rc[-1] * 100.0))
    print("  R(t_d) 附件2     = %.5f cm" % (ra_i[-1] * 100.0))
    print("  R(t_d) 偏差      = %.2f %%" % dev[-1])
    print("  Cbar(t_d)        = %.5f kg/kg" % cb[-1])
    print("  R(t=0) 自洽      = %.5f cm" % (rc[0] * 100.0))
    print("  偏差范围         = %.2f %% .. %.2f %%" % (dev.min(), dev.max()))
    print("  行数 = %d -> %s" % (len(ts), path))
    with open(os.path.join(out_b, "shrinkclosed_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump({"case": case, "Nc": nc, "dt": dt, "Ccr": ccr,
                   "t_d_h": round(float(td), 6),
                   "t_d_s": round(float(t_hit), 4),
                   "R_closed_end_cm": round(float(rc[-1] * 100.0), 5),
                   "R_att2_end_cm": round(float(ra_i[-1] * 100.0), 5),
                   "dev_end_pct": round(float(dev[-1]), 4),
                   "dev_min_pct": round(float(dev.min()), 4),
                   "dev_max_pct": round(float(dev.max()), 4),
                   "Cbar_end": round(float(cb[-1]), 6)}, f,
                  ensure_ascii=False, indent=2)
    return out


def 收缩本构反演():
    """纯失水律 R_w=R0·√(v̄/v0) / 反演 v_eff(C̄)/v0=(R_att2/R0)² /
    耦合不动点，演示"物性→收缩→时长"链条。C̄ 取体积份额加权。"""
    case, nc, dt, ccr = 4, 1600, 7.5, 0.15
    out_b = os.path.join(_ROOT, "支撑材料", "figdata")
    orig_props = common.props

    def specvol(C):
        rho, _, _, _ = orig_props(case, C, np.full_like(np.asarray(C, float), 301.15))
        return (1.0 + np.asarray(C, float)) / rho

    def run_measured():
        _, Vsh = fvm1d.make_grid(nc)
        v0 = float(specvol(C0))
        rows = []

        def sampler(t, C, T, Rw, Tamb, Cinf):
            vbar = float(np.sum(Vsh * specvol(C)))
            rows.append((t, Rw, R0 * np.sqrt(vbar / v0), float(np.sum(Vsh * C))))
            return None

        out = fvm1d.solve1d(case=case, Nc=nc, dt=dt, tmax=4.0e5, shrink=True,
                            Ccr=ccr, sampler=sampler,
                            sample_every=int(round(300.0 / dt)), stop_at_hit=True)
        return out, rows

    def build_law(rows):
        cb = np.array([C0] + [r[3] for r in rows])
        ve = np.array([1.0] + [(r[1] / R0) ** 2 for r in rows])
        o = np.argsort(cb)
        return cb[o], ve[o]

    def coupled(fac, cb_s, ve_s, niter=4):
        tg = np.linspace(0.0, 4.0e5, 40001)
        law = lambda c: np.interp(np.clip(c, cb_s[0], cb_s[-1]), cb_s, ve_s)
        _, Vsh = fvm1d.make_grid(nc)
        Ri = np.asarray(common.Rof(tg, 1.0), float)
        hist = []
        for it in range(niter):
            fvm1d.Rof = lambda t, lam=1.0, Ri=Ri: np.interp(
                np.minimum(np.asarray(t, float), tg[-1]), tg, Ri)
            fvm1d.props = lambda case, C, T, fac=fac: (
                lambda r: (r[0], r[1], r[2], r[3] * fac))(orig_props(case, C, T))
            cs = []
            res = fvm1d.solve1d(case=case, Nc=nc, dt=dt, tmax=4.0e5, shrink=True,
                                Ccr=ccr,
                                sampler=lambda t, C, T, Rw, Ta, Ci: cs.append(
                                    (t, float(np.sum(Vsh * C)))),
                                sample_every=int(round(300.0 / dt)),
                                stop_at_hit=True)
            tt = np.concatenate([[0.0], [c[0] for c in cs]])
            cc = np.concatenate([[C0], [c[1] for c in cs]])
            newR = np.interp(tg, tt, R0 * np.sqrt(law(cc)))
            dv = float(np.max(np.abs(newR - Ri)) / R0)
            Ri = newR
            hist.append({"iter": it + 1, "max_dR_over_R0": dv,
                         "td_h": res["td_h"], "R_end_cm": float(Ri[-1] * 100.0)})
            if dv < 1e-4:
                break
        fvm1d.Rof = common.Rof
        fvm1d.props = orig_props
        return hist

    out, rows = run_measured()
    print("实测轨迹 t_d = %.4f h   采样点 %d" % (out["td_h"], len(rows)))

    cb_s, ve_s = build_law(rows)
    print("本构 v_eff(Cbar)：Cbar %.4f..%.4f  ->  v_eff/v0 %.5f..%.5f"
          % (cb_s[0], cb_s[-1], ve_s[0], ve_s[-1]))

    v0 = float(specvol(C0))
    v_floor = float(specvol(0.0)) / v0
    print("失水致缩绝对下界 v(0)/v0 = %.5f  ->  R_min = %.4f cm"
          % (v_floor, R0 * 100 * np.sqrt(v_floor)))

    p = os.path.join(out_b, "shrinklaw.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "t_h", "R_water_cm", "R_att2_cm", "gap_pct", "Cbar"])
        for (t, Rw, Rw_, cb) in rows:
            w.writerow(["%.1f" % t, "%.4f" % (t / 3600.0), "%.5f" % (Rw_ * 100),
                        "%.5f" % (Rw * 100), "%.4f" % ((Rw_ - Rw) / Rw * 100),
                        "%.6f" % cb])
    print("  -> %s  (%d 行, 终点 %.4f h)"
          % (os.path.basename(p), len(rows), out["t_hit_s"] / 3600))

    p2 = os.path.join(out_b, "shrinklaw_law.csv")
    with open(p2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Cbar", "v_eff_over_v0", "v_water_over_v0"])
        for c, v in zip(cb_s, ve_s):
            w.writerow(["%.6f" % c, "%.6f" % v, "%.6f" % (specvol(c) / v0)])
    print("  -> %s" % os.path.basename(p2))

    demo = {}
    for fac in (1.0, 1.2, 0.8):
        hist = coupled(fac, cb_s, ve_s)
        demo["D_x%.1f" % fac] = hist
        print("  D x%.1f  收敛 %d 次  max|dR|/R0 = %.2e  t_d = %.4f h"
              % (fac, len(hist), hist[-1]["max_dR_over_R0"], hist[-1]["td_h"]))

    fixed = {}
    for fac in (1.2, 0.8):
        fvm1d.props = lambda case, C, T, fac=fac: (
            lambda r: (r[0], r[1], r[2], r[3] * fac))(orig_props(case, C, T))
        fixed["D_x%.1f" % fac] = fvm1d.solve1d(
            case=case, Nc=nc, dt=dt, tmax=4.0e5, shrink=True, Ccr=ccr,
            stop_at_hit=True)["td_h"]
        fvm1d.props = orig_props
        print("  D x%.1f  R 固定为附件2 : t_d = %.4f h" % (fac, fixed["D_x%.1f" % fac]))

    s = {"baseline_td_h": out["td_h"], "v_floor_over_v0": v_floor,
         "R_min_cm": R0 * 100 * np.sqrt(v_floor),
         "law": [{"Cbar": float(c), "v_eff_over_v0": float(v),
                  "v_water_over_v0": float(specvol(c) / v0)} for c, v in zip(cb_s, ve_s)],
         "coupled": demo, "fixed_R": fixed}
    with open(os.path.join(out_b, "shrinklaw_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print("  -> shrinklaw_summary.json")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg in ("closed", "自洽闭合"):
        收缩自洽闭合()
    elif arg in ("shrinklaw", "本构反演"):
        收缩本构反演()
    else:
        main()
