# 探针：确认求解器可用，并逐位复现基准两个端点（57.475473 / 51.095835 h）。
# 跑不通就别往下批量算 —— 30 次算例白跑的时间成本远高于这一次验证。

import inspect
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE_CODE = os.path.join(ROOT, "src")
os.environ["HERB_SRC"] = os.path.join(ROOT, "data", "raw")

# 本机 Anaconda 的 openpyxl 偏旧，iter_rows 不吃 values_only；只在进程内打补丁，不改源文件
import openpyxl.worksheet.worksheet as worksheet
old_iter_rows = worksheet.Worksheet.iter_rows
if "values_only" not in inspect.signature(old_iter_rows).parameters:
    worksheet.Worksheet.iter_rows = lambda self, **kwargs: (
        tuple(cell.value for cell in row) for row in old_iter_rows(self)
    )

sys.path.insert(0, SOURCE_CODE)
import 公共 as model

print("T∞ 平台均值 = %.6f °C" % float(model.TA_PLAT))
print("C∞ 平台均值 = %.8f kg/kg" % float(model.CA_PLAT))
print("附件1 末时刻 = %.1f s，采样 %d 点" % (float(model._T1[-1]), len(model._T1)))
print()

BASE = {("A", 3, False): 57.475473, ("B", 4, True): 51.095835}
ok = True
for name, case, shrink in (("A", 3, False), ("B", 4, True)):
    t0 = time.time()
    r = model.solve1d(case=case, Nc=1600, dt=7.5, tmax=4.0e5,
                      shrink=shrink, Ccr=0.15, stop_at_hit=True)
    got = float(r["td_h"])
    want = BASE[(name, case, shrink)]
    hit = abs(got - want) < 5e-7
    ok = ok and hit
    print("%s-%-10s t_d = %.6f h  (基准 %.6f, %s)  用时 %.1f s" % (
        name, "shrinking" if shrink else "fixed", got, want,
        "逐位复现" if hit else "偏离 %+.6f" % (got - want), time.time() - t0))

print("\n" + ("探针通过" if ok else "!! 探针未通过，不要继续批量算例"))
