# 蒙特卡洛集合独立装置。
#
# 为什么不调用 公共.py 里的 敏感性()：
#   它的 _run_one 与 _push_props 同病 —— 函数体里 reassign 模块级 props/HM/H_Q 却没有
#   global 声明，第一句 orig = props 就读到未绑定的局部名，直接 UnboundLocalError。
#   即：已发表的那 16 次集合目前无法从源码复现。故独立重建，不改被污染的源文件。
#
# 扰动走模块属性赋值（M.props = patched），不需要 global。
#   ⚠️ patched 内必须用默认参数绑住原函数：裸名字会解析到刚被替换掉的那个名字 ⇒ 无限递归。
#
# 抽签流与原实现逐位对齐：
#   原实现按 MC_CASES 顺序先抽满 q3 的全部样本、再抽 q4 的全部样本，故 n=16 时
#   q3 占 SEED 流前 48 抽，q4 从第 49 抽起。本装置沿用这一对齐：
#       q3: default_rng(SEED) 连抽，前 16 组即已发表值
#       q4: default_rng(SEED) 先丢弃 48 抽再连抽，前 16 组即已发表值
#   于是「已发表 16 组」是两个 512 样本流的前缀，门禁与生产共用一条流。
#
# 用法：python mc_ensemble.py [N]          默认 N=512
import csv
import json
import os
import sys
import time
from multiprocessing import Pool

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

# 与 公共.py:1520-1525 同样的理由：单个 worker 内锁死 BLAS 线程数，避免并发加载击穿内存
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np

SEED, LOW, HIGH = 20260912, 0.95, 1.05
NC, DT, CCR, TMAX = 1600, 7.5, 0.15, 4.0e5
NGATE = 16
NPROC = 8

CASES = {"q3": {"case": 3, "shrink": False, "keys": ["D", "hm", "h"]},
         "q4": {"case": 4, "shrink": True, "keys": ["D", "hm", "h", "lam"]}}
# q4 的流要在 q3 的 16 组 × 3 抽之后对齐
Q4_SKIP = NGATE * 3

PUB = os.path.join(ROOT, "data", "processed", "figdata",
                   "mc_sensitivity.csv")


def draw_sets(qn, n):
    """按原实现的抽签顺序生成 qn 配置的前 n 组因子。返回 (groups, 用掉的抽数)。"""
    spec = CASES[qn]
    rng = np.random.default_rng(SEED)
    if qn == "q4":
        rng.uniform(LOW, HIGH, size=Q4_SKIP)
    return [{k: float(rng.uniform(LOW, HIGH)) for k in spec["keys"]}
            for _ in range(n)]


def _solve_one(arg):
    qn, sid, fac = arg
    import 公共 as M
    spec = CASES[qn]
    snap = {k: getattr(M, k) for k in ("props", "HM", "H_Q")}
    if fac.get("D", 1.0) != 1.0:
        base, f = snap["props"], fac["D"]

        def patched(case, C, Tk, _o=base, _f=f):
            rho, cp, kk, D = _o(case, C, Tk)
            return rho, cp, kk, D * _f

        M.props = patched
    if fac.get("hm", 1.0) != 1.0:
        M.HM = snap["HM"] * fac["hm"]
    if fac.get("h", 1.0) != 1.0:
        M.H_Q = snap["H_Q"] * fac["h"]
    try:
        o = M.solve1d(case=spec["case"], Nc=NC, dt=DT, tmax=TMAX,
                      shrink=spec["shrink"], Ccr=CCR, stop_at_hit=True,
                      lam=float(fac.get("lam", 1.0)))
        td = None if o["t_hit_s"] is None else float(o["td_h"])
    finally:
        for k, v in snap.items():
            setattr(M, k, v)
    return qn, sid, dict(fac), td


def run(tasks, nproc=NPROC):
    out = []
    with Pool(nproc) as pool:
        for n, r in enumerate(pool.imap_unordered(_solve_one, tasks), 1):
            out.append(r)
            if n % 64 == 0 or n == len(tasks):
                print("    %4d/%d" % (n, len(tasks)), flush=True)
    out.sort(key=lambda r: (r[0], r[1]))
    return out


def read_published():
    pub = {}
    with open(PUB, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pub[(row["question"], int(row["sample_id"]))] = float(row["td_h"])
    return pub


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 512
    t_start = time.time()
    print("=" * 74)
    print("门禁：独立装置须逐位复现已发表 mc_sensitivity.csv 的 %d×2 个端点" % NGATE)
    print("=" * 74)
    assert n >= NGATE
    gate_tasks = []
    for qn in CASES:
        for sid, fac in enumerate(draw_sets(qn, NGATE)):
            gate_tasks.append((qn, sid, fac))
    t0 = time.time()
    gate_res = run(gate_tasks)
    pub = read_published()
    gate_ok = True
    worst = 0.0
    for qn, sid, fac, td in gate_res:
        want = pub.get((qn, sid))
        if want is None:
            gate_ok = False
            print("  %s/%2d  已发表值缺失" % (qn, sid))
            continue
        if td is None:
            gate_ok = False
            print("  %s/%2d  got None  want %.6f" % (qn, sid, want))
            continue
        d = abs(td - want)
        worst = max(worst, d)
        if d > 5e-4:
            gate_ok = False
            print("  %s/%2d  got %.6f  want %.6f  偏离 %.2e" % (qn, sid, td, want, d))
    print("  最大偏差 %.3e h   用时 %.1f s" % (worst, time.time() - t0))
    if not gate_ok:
        print("\n!! 装置校验未通过：复现不出已发表的集合端点，停止。")
        sys.exit(1)
    print("  装置校验通过 —— 新集合与已发表集合同源")
    print("  注：q3 全部参数生效；q4 另有 λ 经由 solve1d 的显式参数传入")

    print()
    print("=" * 74)
    print("生产：每配置 %d 个成员（原 16 个是它的前缀）" % n)
    print("=" * 74)
    tasks = []
    for qn in CASES:
        for sid, fac in enumerate(draw_sets(qn, n)):
            tasks.append((qn, sid, fac))
    t0 = time.time()
    res = run(tasks)
    print("  用时 %.1f min" % ((time.time() - t0) / 60.0))

    summary = {}
    for qn in CASES:
        v = np.array([r[3] for r in res if r[0] == qn and r[3] is not None])
        miss = sum(1 for r in res if r[0] == qn and r[3] is None)
        qs = np.percentile(v, [2.5, 5, 50, 95, 97.5])
        summary[qn] = {
            "n": int(v.size), "n_missing_endpoint": int(miss),
            "mean_h": round(float(v.mean()), 4),
            "sd_h": round(float(v.std(ddof=1)), 4),
            "median_h": round(float(qs[2]), 4),
            "min_h": round(float(v.min()), 4), "max_h": round(float(v.max()), 4),
            "q025_h": round(float(qs[0]), 4), "q975_h": round(float(qs[4]), 4),
            "q05_h": round(float(qs[1]), 4), "q95_h": round(float(qs[3]), 4),
            "w95_h": round(float(qs[4] - qs[0]), 4),
            "rel_w95_pct": round(float((qs[4] - qs[0]) / qs[2] * 100.0), 4),
        }
        s = summary[qn]
        print()
        print("  %s  N=%d%s" % (qn, s["n"], "" if not miss else "  端点缺失 %d" % miss))
        print("    均值 %.4f h   标准差 %.4f h   中位 %.4f h"
              % (s["mean_h"], s["sd_h"], s["median_h"]))
        print("    2.5–97.5 %% 分位 %.4f–%.4f h   宽 %.4f h (%.2f %%)"
              % (s["q025_h"], s["q975_h"], s["w95_h"], s["rel_w95_pct"]))
        print("    极值 %.4f–%.4f h" % (s["min_h"], s["max_h"]))

    os.makedirs(OUT_DIR, exist_ok=True)
    keys = sorted({k for _q, _s, fac, _t in res for k in fac})
    with open(os.path.join(OUT_DIR, "mc_ensemble.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["question", "sample_id"] + ["f_" + k for k in keys] + ["td_h"])
        for qn, sid, fac, td in res:
            w.writerow([qn, sid] + ["%.6f" % fac[k] if k in fac else ""
                                    for k in keys] + ["" if td is None else "%.6f" % td])
    with open(os.path.join(OUT_DIR, "mc_ensemble_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump({"N": n, "seed": SEED, "dist": "U(%.2f,%.2f)" % (LOW, HIGH),
                   "Nc": NC, "dt": DT, "Ccr": CCR, "params": keys,
                   "gate": {"n": NGATE, "max_dev_h": worst, "passed": bool(gate_ok)},
                   "result": summary}, f, ensure_ascii=False, indent=2)
    print()
    print("写出 %s" % os.path.join(OUT_DIR, "mc_ensemble.csv"))
    print("写出 %s" % os.path.join(OUT_DIR, "mc_ensemble_summary.json"))
    print("总用时 %.1f min" % ((time.time() - t_start) / 60.0))


if __name__ == "__main__":
    main()
