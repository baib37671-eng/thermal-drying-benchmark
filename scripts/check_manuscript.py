# -*- coding: utf-8 -*-
"""
check_manuscript.py -- 交付一致性核验器（Thermal Science 主稿 main_ts.tex）

对应 vault 卡《交付物一致性总检-同一物理量两条算路与资产编号脱钩》的"资产编号同源"，
以及《概括性断言必须机器重算》的收口动作。九道闸：

  A 资产编号同源   main_ts.aux 的 \\newlabel 真编号 == figure_manifest.csv
  B 资产与生成器   图文件在盘、生成脚本存在且行号落在文件内、正文确实引用
  C 生成器唯一性   同一资产名只能在清单声明的那个生成脚本里写出（多个 = 警告）
  D 表格逐格       四张表的每个数与所在格的行内位置、来源事实逐一比对
  E 正文数值       注册的每个事实必须以某个精度出现在正文里（精度自动反读）
  F 废弃表述       已被取代的旧口径字串不得出现
  G 参考文献       bibitem 数 == bibcite 数 == 被引键数，且首次引用次序 == 条目次序
  H 事实表新鲜度   numeric_facts.json 不得比它引用的本地产物旧
  I 覆盖审计       正文里没有被 A-H 任一规则解释的数字字面量（仅报告，不判死）

A-H 任一失败 -> 退出码 1。用法：

  python build_facts.py
  python check_manuscript.py

E 段的设计：注册表只声明"哪个事实应当出现在正文里"，不写死精度。核验时对每个事实
枚举"×10^k 后取 n 位小数"的全部候选字面量，命中即通过，并把命中的写法记进报告。
这样正文改精度（0.905→0.90）不会误报，而事实表数值一变必然报错。
"""
import csv
import io
import json
import os
import re
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "main_ts.tex")
AUX = os.path.join(HERE, "main_ts.aux")
FACTS = os.path.join(HERE, "data", "numeric_facts.json")
MANIFEST = os.path.join(HERE, "figure_manifest.csv")
SRC_DIRS = [HERE, ROOT, os.path.join(ROOT, "支撑材料"), os.path.join(ROOT, "journal_draft")]

FAILS, WARNS, NOTES = [], [], []


def fail(sec, msg):
    FAILS.append("[%s] %s" % (sec, msg))


def warn(sec, msg):
    WARNS.append("[%s] %s" % (sec, msg))


def note(sec, msg):
    NOTES.append("[%s] %s" % (sec, msg))


# ============================================================================
# 0. 读入
# ============================================================================
def read_text(path):
    with io.open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def find_src(rel):
    for d in SRC_DIRS:
        p = os.path.normpath(os.path.join(d, rel.replace("/", os.sep)))
        if os.path.exists(p):
            return p
    return None


if not os.path.exists(FACTS):
    sys.exit("找不到 %s，先跑 build_facts.py" % FACTS)
if not os.path.exists(TEX):
    sys.exit("找不到 %s" % TEX)

with io.open(FACTS, encoding="utf-8") as fh:
    FACT = json.load(fh)
with io.open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
    MAN = list(csv.DictReader(fh))

RAW = read_text(TEX)
TEXN = unicodedata.normalize("NFKC", RAW)
BODY_ALL = "\n".join(l for l in TEXN.split("\n") if not l.lstrip().startswith("%"))
_cut = BODY_ALL.find("\\begin{thebibliography}")
BODY = BODY_ALL[:_cut] if _cut > 0 else BODY_ALL
BODY_LITS = set(re.findall(r"(?<![\w.])(\d+\.\d+)(?![\w])", BODY))
# 纯整数字面量（行数、t_end、网格数一类），与小数分开收，避免 \d+\.\d+ 的反向污染
BODY_INTS = set(re.findall(r"(?<![\w.])(\d+)(?![\w.])", BODY))


class Missing(object):
    pass


MISSING = Missing()


def val(path):
    """path 形如 'key' 或 'key.sub' 或 'key.3.sub'，逐级取值。"""
    parts = path.split(".")
    cur = FACT.get(parts[0], MISSING)
    if cur is MISSING:
        return MISSING
    cur = cur["value"]
    for p in parts[1:]:
        try:
            cur = cur[int(p)] if isinstance(cur, (list, tuple)) else cur[p]
        except (KeyError, IndexError, TypeError, ValueError):
            return MISSING
    return cur


# ============================================================================
# A. 资产编号同源
# ============================================================================
def section_a():
    if not os.path.exists(AUX):
        fail("A", "缺 %s，先编译一次再核验编号" % os.path.basename(AUX))
        return
    real = {}
    for m in re.finditer(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}\{([^}]*)\}", read_text(AUX)):
        lbl, num, page = m.group(1), m.group(2), m.group(3)
        if lbl.endswith("@cref"):
            continue
        real[lbl] = (num.strip(), page.strip())
    declared = {r["label"]: int(r["in_paper"]) for r in MAN
                if r["kind"] in ("figure", "table", "equation")}
    for lbl, n in sorted(declared.items()):
        if lbl not in real:
            fail("A", "%s 在清单里声明为第 %d 号，但 .aux 里没有这个 label" % (lbl, n))
        elif real[lbl][0] != str(n):
            fail("A", "%s 清单声明 %d，.aux 实际编号 %s（第 %s 页）"
                 % (lbl, n, real[lbl][0], real[lbl][1]))
    for lbl in sorted(real):
        if lbl not in declared:
            note("A", ".aux 里有清单未登记的 label：%s = %s" % (lbl, real[lbl][0]))
    for kind in ("figure", "table", "equation"):
        ns = sorted(int(r["in_paper"]) for r in MAN if r["kind"] == kind)
        if ns and ns != list(range(1, len(ns) + 1)):
            fail("A", "%s 编号不连续：%s" % (kind, ns))
    note("A", "资产编号 %d 个（图 %d / 表 %d / 式 %d）与 .aux 逐一相符"
         % (len(declared), sum(1 for r in MAN if r["kind"] == "figure"),
            sum(1 for r in MAN if r["kind"] == "table"),
            sum(1 for r in MAN if r["kind"] == "equation")))


# ============================================================================
# B / C. 资产与生成器
# ============================================================================
def section_b():
    figs = [r for r in MAN if r["kind"] == "figure" and r["asset"] != "-"]
    used = [u.strip().replace("\\", "/")
            for u in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", TEXN)]
    known = [r["asset"].replace("\\", "/") for r in figs]
    for r in figs:
        asset = r["asset"].replace("\\", "/")
        if asset not in used:
            fail("B", "清单里的 %s（%s）没有被 \\includegraphics 引用" % (asset, r["label"]))
        if not os.path.exists(os.path.join(HERE, asset)):
            fail("B", "图文件不在盘上：%s" % asset)
        gen = r["generator"] or ""
        if gen and gen != "-":
            f, _, ln = gen.rpartition(":")
            gp = os.path.join(HERE, f)
            if not os.path.exists(gp):
                fail("B", "%s 的生成器不存在：%s" % (r["label"], f))
            else:
                n = len(read_text(gp).split("\n"))
                if not ln.isdigit() or int(ln) > n:
                    fail("B", "%s 的生成器行号 %s 超出 %s 的 %d 行" % (r["label"], ln, f, n))
    for u in used:
        if u not in known:
            warn("B", "正文引用了清单未登记的图：%s" % u)


# 真的把图写盘的那些调用。注意 store 判定不能只看"文件名出现过"——把图名当字符串
# 参数传来传去的脚本（比如一个生成出图脚本的元脚本）会被误判成写出者。
WRITE_RE = re.compile(
    r"save_png\s*\(|ggsave2?\s*\(|\bpng\s*\(|\btiff?\s*\(|\bjpeg\s*\(|"
    r"exportgraphics\s*\(|\bsaveas\s*\(|\bimwrite\s*\(|\bprint\s*\(")
ASSIGN_RE = re.compile(r"^\s*[A-Za-z_][\w.]*\s*=[^=]")


def writer_hits(path, base):
    """返回该脚本里"看起来真在写 base 这个文件"的行号列表。

    命中条件（同一行同时满足）：出现该文件名，且该行有写盘调用，或该行是把路径赋给
    某个变量（MATLAB 常见写法：先 png = fullfile(OUT,'x.png'); 再 exportgraphics）。
    """
    out = []
    for i, ln in enumerate(read_text(path).split("\n")):
        if base not in ln:
            continue
        if WRITE_RE.search(ln) or ASSIGN_RE.match(ln):
            out.append(i + 1)
    return out


def section_c():
    """同一资产只能有一个生成器（vault《顺序色阶换色》附则）。"""
    figs = [r for r in MAN if r["kind"] == "figure" and r["asset"] != "-"]
    scripts = [n for n in sorted(os.listdir(HERE))
               if os.path.splitext(n)[1].lower() in (".r", ".m", ".py")]
    for r in figs:
        base = os.path.basename(r["asset"].replace("\\", "/"))
        hitters = {}
        for s in scripts:
            try:
                ln = writer_hits(os.path.join(HERE, s), base)
            except Exception:
                continue
            if ln:
                hitters[s] = ln
        declared = (r["generator"] or "").rpartition(":")[0]
        if declared and declared not in hitters:
            fail("C", "%s 声明的生成器 %s 里找不到写出 %s 的语句"
                 % (r["label"], declared, base))
        if len(hitters) > 1:
            warn("C", "%s 有多个写出者：%s —— 清单声明 %s，另写者会静默覆盖成品"
                 % (base, "；".join("%s:%s" % (k, v) for k, v in sorted(hitters.items())),
                    declared))
        elif declared in hitters:
            # 清单里记的行号必须真的落在写盘语句上，否则脚本被改过而清单没跟
            _, _, ln = (r["generator"] or "").rpartition(":")
            if ln.isdigit() and int(ln) not in hitters[declared]:
                warn("C", "%s 的清单行号 %s 不是 %s 里写出该图的行（实际在 %s）"
                     % (r["label"], ln, declared,
                        ", ".join(str(x) for x in hitters[declared])))


# ============================================================================
# D. 表格逐格
# ============================================================================
MULTICOL = re.compile(r"\\multicolumn\{[^}]*\}\{[^}]*\}")
CMD = re.compile(r"\\[a-zA-Z]+")
NUM = re.compile(r"-?\d+\.\d+|-?\d+")


# 纯分线行：\cmidrule 的前缀是 "cmid" 不是 top|mid|bottom，躲得过上面那条替换；
# \addlinespace 连 "rule" 都没有。两者留在表体里都会被下面的 r.split("\\") 切出
# 一个"只有命令、没有单元格"的伪行，把数据行数撑大而与 facts 对不上。判据用
# "剥掉分线命令后是否为空"，不写死命令名。
RULE_ONLY = re.compile(r"\\(?:top|mid|bottom|cmid)?rule(?:\([^)]*\))?(?:\{[^}]*\})*"
                       r"|\\(?:addlinespace|morecmidrules)(?:\[[^\]]*\])?")


def split_rows(block):
    # 行分隔符是字面量 "\\"（两个反斜杠字符），不是单个反斜杠。写成 split("\\") 是
    # 在一个反斜杠处断行 ⇒ 单元格里的 \lambda / \dgC / \kgkg / \itshape 把一行劈成
    # 两行：前半是"只有标签没有数"的伪行（数值列数偏少），后半以命令残渣当首个单元
    # 格，整表行数与列数双错位，报出来的却是"论文表里数值列数不符"。分线命令
    # （\cmidrule / \addlinespace）本来就独占一行，两种断法在它们身上碰巧等价，所以
    # 这个 bug 只在"单元格里带反斜杠命令"的表上现形。
    block = re.sub(r"\\(top|mid|bottom)(cmid)?rule(\([^)]*\))?(\{[^}]*\})*", "", block)
    rows = []
    for r in re.split(r"\\\\", block):
        r = r.strip()
        if not r:
            continue
        if not RULE_ONLY.sub("", r).strip():
            continue          # 纯分线行（\cmidrule / \addlinespace），不是数据行
        rows.append([c.strip() for c in r.split("&")])
    return rows


def cell_numbers(cell):
    # 表里的区间写成 55.2136--60.0765，NUM 会把第二个连字符读成负号 ⇒ 先把 "--" 拆成
    # 空白，两个数都保住，又不会凭空生成一个负数。
    txt = MULTICOL.sub("", cell).replace("--", " ")
    return NUM.findall(CMD.sub("", txt))


def parse_tables():
    out = {}
    for m in re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", TEXN, re.S):
        blk = m.group(1)
        lm = re.search(r"\\label\{([^}]+)\}", blk)
        tm = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", blk, re.S)
        if lm and tm:
            # \midrule 之上是表头条（表头字符串里也含数字，比如 "C_{cr}" 之类），
            # 只把 \midrule 之下的数据行交给 compare_rows，否则行数与列数都会错位。
            _, sep, body = tm.group(1).partition(r"\midrule")
            out[lm.group(1)] = split_rows(body if sep else tm.group(1))
    return out


def compare_rows(sec, label, exp_rows, got_rows, k, ncols=None):
    """k = 每行左侧若干标签列，不参与比对；ncols = 只比对接下来的几列（None = 全部）。"""
    tag = "%s(%s)" % (sec, label)
    if len(exp_rows) != len(got_rows):
        fail(sec, "%s 数据行数 期望 %d、实际 %d" % (tag, len(exp_rows), len(got_rows)))
        return
    for i, ((ename, evals), cells) in enumerate(zip(exp_rows, got_rows)):
        sel = cells[k:] if ncols is None else cells[k:k + ncols]
        glits = [l for c in sel for l in cell_numbers(c)]
        if len(evals) != len(glits):
            fail(sec, "%s 第 %d 行（%s）数值列数 期望 %d、实际 %d；实际字面量 %s"
                 % (tag, i + 1, ename, len(evals), len(glits), glits))
            continue
        for j, (e, lit) in enumerate(zip(evals, glits)):
            nd = len(lit.split(".")[1]) if "." in lit else 0
            want = "%.*f" % (nd, e)
            if want != lit:
                fail(sec, "%s 第 %d 行（%s）第 %d 个值：表里写 %s，来源给 %.10g（应写 %s）"
                     % (tag, i + 1, ename, j + 1, lit, e, want))


def section_d():
    T = parse_tables()
    for lbl in ("tab:factorial", "tab:criterion", "tab:boundary", "tab:sensitivity"):
        if lbl not in T:
            fail("D", "找不到 %s" % lbl)
    if "tab:factorial" in T:
        # 表 1 表体分两块：上面 2x2 数据（行 = 几何、列 = 物性集 A / B / B/A 比值），
        # 下面 "Derived measures"。跨列标签行本身没有数字（k=1 之后 cells[1:] 为空），
        # 但仍占一行 ⇒ 期望表要对齐这一行。2x2 因子设计的两族比值正交：横着比的
        # $P$ 单占 B/A 列（两行各一个值），竖着比的 $G$ 待在 A/B 两列，故数据行各带
        # 三个数、派生行的 $G$ 带两个数。$G$ 行的 B/A 格是 "---" 占位符（$G$ 不是
        # B/A 量），cell_numbers 取不到数字，正好与期望的两个值对齐。
        compare_rows("D", "tab:factorial",
                     [("Fixed radius", [val("td_A_fixed_h"), val("td_B_fixed_h"),
                                        val("ratio_prop_fixed")]),
                      ("Prescribed shrinkage", [val("td_A_shrinking_h"), val("td_B_shrinking_h"),
                                                val("ratio_prop_shrinking")]),
                      ("Derived-measures 标签行", []),
                      ("Shrinking-to-fixed ratio", [val("ratio_geo_A"), val("ratio_geo_B")]),
                      ("Interaction", [val("interaction_I")])], T["tab:factorial"], 1)
    if "tab:criterion" in T:
        scan = val("threshold_scan")
        rows = T["tab:criterion"]
        compare_rows("D", "tab:criterion",
                     [("%.4g" % s["Ccr"], [s["Ccr"], s["A_fixed_h"], s["B_shrinking_h"]])
                      for s in scan], rows, 0, 3)
        # 末列只写配置代号 A / B（不写 "A earlier by 22 s" 那类把秒差塞进文字格的
        # 写法），该列是文字列、左对齐，比对时取整格字面量而不是在整行里搜 "A earlier"。
        if len(rows) == len(scan):
            for s, cells in zip(scan, rows):
                want = "A" if s["A_fixed_h"] < s["B_shrinking_h"] else "B"
                got = cells[-1].strip() if cells else "?"
                if got != want:
                    fail("D", "tab:criterion 在 C_cr=%.4g 行：Earlier 列写 '%s'，"
                         "而 t_A=%.4f h、t_B=%.4f h ⇒ 应为 %s"
                         % (s["Ccr"], got, s["A_fixed_h"], s["B_shrinking_h"], want))
    if "tab:boundary" in T:
        bs = val("boundary_sensitivity_json")
        res = {r["scenario"]: r for r in bs["results"]}
        w = {r["scenario"]: r for r in val("window_rows")}
        tmap = {r["scenario"]: r for r in val("extrapolation_rows") if r["kind"] == "temperature"}
        compare_rows("D", "tab:boundary", [
            ("Reference", [bs["platform_mean_temperature_C"], val("td_A_fixed_h"),
                           val("td_B_shrinking_h")]),
            ("Mean of final 30 min", [w["窗口·末30min"]["T_plat_C"], w["窗口·末30min"]["A_fixed_h"],
                                      w["窗口·末30min"]["B_shrinking_h"]]),
            ("Mean of final 2 h", [w["窗口·末2h"]["T_plat_C"], w["窗口·末2h"]["A_fixed_h"],
                                   w["窗口·末2h"]["B_shrinking_h"]]),
            ("Mean of final 3 h", [w["窗口·末3h"]["T_plat_C"], w["窗口·末3h"]["A_fixed_h"],
                                   w["窗口·末3h"]["B_shrinking_h"]]),
            ("Final recorded point", [val("T_lastpoint_C"), w["窗口·最后一点"]["A_fixed_h"],
                                      w["窗口·最后一点"]["B_shrinking_h"]]),
            ("Offset -2", [float(tmap["控温-2°C"]["T_plat_C"]),
                           float(tmap["控温-2°C"]["A_fixed_h"]),
                           float(tmap["控温-2°C"]["B_shrinking_h"])]),
            ("Offset -1", [val("T_plat_mean61_C") - 1.0, res["cooler_1C"]["A_fixed_h"],
                           res["cooler_1C"]["B_shrinking_h"]]),
            ("Offset +1", [val("T_plat_mean61_C") + 1.0, res["warmer_1C"]["A_fixed_h"],
                           res["warmer_1C"]["B_shrinking_h"]]),
            ("Offset +2", [float(tmap["控温+2°C"]["T_plat_C"]),
                           float(tmap["控温+2°C"]["A_fixed_h"]),
                           float(tmap["控温+2°C"]["B_shrinking_h"])]),
            ("Moisture -10", [val("T_plat_mean61_C"), res["drier_10pct"]["A_fixed_h"],
                              res["drier_10pct"]["B_shrinking_h"]]),
            ("Moisture +10", [val("T_plat_mean61_C"), res["wetter_10pct"]["A_fixed_h"],
                              res["wetter_10pct"]["B_shrinking_h"]]),
        ], T["tab:boundary"], 2)
    if "tab:sensitivity" in T:
        ps = val("param_sensitivity")
        g = {(r["question"], r["param"]): float(r["S_p"]) for r in ps if r["S_p"] is not None}
        t = {(r["question"], r["param"], r["delta_pct"]): float(r["td_h"]) for r in ps}

        # 表 4 改版后 S_p 有自己的列：每个参数一行，按 A(-5%, +5%, S_p) 再
        # B(-5%, +5%, S_p) 六个数排列。原来 \quad $S_p$ 的悬挂子行已删除。
        def prow(name, key):
            return (name, [t[("q3", key, -5.0)], t[("q3", key, 5.0)], g[("q3", key)],
                           t[("q4", key, -5.0)], t[("q4", key, 5.0)], g[("q4", key)]])

        compare_rows("D", "tab:sensitivity", [
            prow("Diffusivity", "D"),
            prow("Surface mass transfer", "hm"),
            prow("Heat transfer", "h"),
            ("Shrinkage amplitude", [t[("q4", "lam", -5.0)], t[("q4", "lam", 5.0)],
                                     g[("q4", "lam")]]),
            ("Ensemble 标签行", []),
            ("Ensemble mean", [val("ens_q3_mean_h"), val("ens_q4_mean_h")]),
            ("Ensemble sd", [val("ens_q3_sd_h"), val("ens_q4_sd_h")]),
            ("2.5--97.5 quantiles", [val("ens_q3_q025_h"), val("ens_q3_q975_h"),
                                     val("ens_q4_q025_h"), val("ens_q4_q975_h")]),
            ("Quantile range", [val("ens_q3_rel_w95_pct"), val("ens_q4_rel_w95_pct")]),
        ], T["tab:sensitivity"], 1)
    note("D", "四张表逐格比对完成（表内实数全部由 facts 提供，Ordering 列由 t_A/t_B 判）")


# ============================================================================
# E. 正文数值注册表（精度自动反读）
# ============================================================================
#   等级 M = 必须出现在正文里（找不到即失败）；m = 只在报告里提示（多为措辞里写成英文数词）
REG = [
    # --- 记录与题目输入 ---
    ("att1_rows", "M"), ("att1_t_end_h", "m"), ("att1_dt_unique_s.0", "m"),
    ("att2_data_rows", "m"), ("att2_dt_unique_s.0", "m"), ("att2_t_end_h", "M"),
    ("att2_R_first_cm", "m"), ("att2_R_last_cm", "M"), ("att2_R_min_cm", "m"),
    ("R0_cm", "M"), ("C0_kgkg", "M"), ("rho_B_C0", "m"),
    # --- 平台与末一小时 ---
    ("T_plat_mean61_C", "M"), ("C_plat_mean61", "m"), ("T_lastpoint_C", "M"),
    ("C_lastpoint", "m"),
    ("T_band_last1h_C", "M"), ("T_net_last1h_C", "M"), ("T_at_3h_C", "M"),
    ("segment_slope_max_absdiff", "m"),
    # --- 半径与干质量 ---
    ("radius_fit_a_cm", "M"), ("radius_fit_b_cm", "M"), ("radius_fit_tau_s", "m"),
    ("R_bound_cm", "M"), ("R_bound_first_interp_h", "M"), ("R_bound_first_datarow_h", "M"),
    ("att2_below_bound_count", "m"), ("att2_below_bound_first_h", "m"),
    ("m_dry_initial_kg", "M"), ("m_dry_endpoint_kg", "M"), ("m_dry_ratio", "M"),
    ("m_dry_loss_pct", "M"),
    ("v_spec_0_m3kg", "M"), ("v_spec_C0_m3kg", "M"), ("V0_m3", "M"),
    ("Cbar_at_td", "M"), ("R_att2_at_td_cm", "M"),
    ("R_at_hit_A_fixed_cm", "m"), ("R_at_hit_B_shrinking_cm", "m"),
    # --- 冻结 / 状态依赖 ---
    ("cross_dynfrz_surf_h", "M"), ("cross_dynfrz_center_h", "M"),
    ("cross_surf_frz_h", "m"), ("cross_center_frz_h", "M"),
    ("state_3h.T_center_C", "M"), ("state_3h.C_center", "M"), ("state_3h.C_surf", "M"),
    ("frozen_center_3h_kgkg", "M"), ("frozen_center_gap_3h_pct", "M"),
    ("released_frz_3h_pct", "M"), ("released_dyn_3h_pct", "M"), ("released_ratio_3h", "M"),
    ("T_uniformity_3h_maxdiff_C", "M"),
    ("crossing_Ccr", "M"), ("crossing_t_h", "M"),
    # --- 网格与收敛 ---
    ("td_A_fixed_h", "M"), ("td_A_shrinking_h", "M"),
    ("td_B_fixed_h", "M"), ("td_B_shrinking_h", "M"),
    ("delta_bundle_h", "m"), ("delta_bundle_pct", "M"),
    ("ratio_geo_A", "M"), ("ratio_geo_B", "M"),
    ("ratio_prop_fixed", "M"), ("ratio_prop_shrinking", "M"),
    ("interaction_I", "M"),
    ("grid_G_first", "M"), ("grid_G_last", "M"), ("grid_P_first", "M"), ("grid_P_last", "M"),
    ("grid_I_first", "M"), ("grid_I_last", "M"),
    ("scan_vs_production_A_fixed_s", "M"), ("scan_vs_production_B_shrinking_s", "M"),
    ("fem_A_fixed_h", "M"), ("fem_B_shrinking_h", "M"),
    ("fem_gap_A_fixed_s", "M"), ("fem_gap_B_shrinking_s", "M"),
    ("fem_gap_A_fixed_Nc200_s", "M"), ("fem_gap_B_shrinking_Nc200_s", "M"),
    ("order_obs.Q3_FVM", "M"), ("order_obs.Q3_FEM", "M"),
    ("order_obs.Q4_FVM", "M"), ("order_obs.Q4_FEM", "M"),
    ("richardson_fv_h", "M"),
    ("conv_space.0.err", "M"), ("conv_space.4.err", "M"),
    ("floor_fit_p_min", "M"), ("floor_fit_p_max", "M"), ("floor_fit_C_mean", "M"),
    ("floor_fit_C_spread_pct", "M"), ("floor_fit_dt_star_s.3", "M"),
    ("floor_fit_F.0", "M"), ("floor_fit_F.6", "M"), ("floor_fit_F_ratio.0", "M"),
    # --- 事后边界族 ---
    ("window_T_span_C", "M"), ("window_span_A_h", "M"), ("window_span_B_h", "M"),
    ("temp_span_A_h", "M"), ("temp_span_B_h", "M"),
    ("amplifier_A", "M"), ("amplifier_B", "M"),
    ("slope_pm1_A_h_per_C", "M"), ("slope_pm1_B_h_per_C", "M"),
    ("slope_pm2_A_h_per_C", "M"), ("slope_pm2_B_h_per_C", "M"),
    ("curvature_A_pct", "M"), ("curvature_B_pct", "M"),
    ("slope_cold1_A_h_per_C", "M"), ("slope_warm1_A_h_per_C", "M"),
    ("slope_cold2_A_h_per_C", "M"), ("slope_warm2_A_h_per_C", "M"),
    ("slope_cold1_B_h_per_C", "m"), ("slope_warm1_B_h_per_C", "m"),
    ("asym_pm1_A_pct", "M"), ("asym_pm2_A_pct", "M"),
    ("asym_pm1_B_pct", "M"), ("asym_pm2_B_pct", "M"),
    ("span_moisture_pm10pct_A_h", "M"), ("span_moisture_pm10pct_B_h", "M"),
    ("C_plat_minus10pct", "M"), ("C_plat_plus10pct", "M"),
    ("extrapolated_share_A_fixed_pct", "M"), ("extrapolated_share_B_shrinking_pct", "M"),
    ("orders_Tspan2_over_disc", "m"), ("orders_T1deg_over_disc", "m"),
    ("kappa_crit", "M"), ("kappa_td_first_last_h.0", "M"), ("kappa_td_first_last_h.1", "M"),
    # --- Morris ---
    ("morris_A_ref_td_h", "M"), ("morris_B_ref_td_h", "M"),
    ("morris_A_k", "m"), ("morris_B_k", "m"),
    ("morris_A_n_runs", "m"), ("morris_B_n_runs", "m"), ("morris_total_runs", "m"),
    ("morris_max_ratio", "M"), ("morris_band", "m"), ("morris_dt_range_C", "m"),
    ("morris_levels", "m"),
    ("morris_A_D_mu_star", "M"), ("morris_A_hm_mu_star", "M"), ("morris_A_h_mu_star", "M"),
    ("morris_B_D_mu_star", "M"), ("morris_B_lam_mu_star", "M"), ("morris_B_hm_mu_star", "M"),
    ("morris_A_T_mu_star", "M"), ("morris_B_T_mu_star", "M"),
    ("morris_A_D_band_span_h", "M"), ("morris_A_T_band_span_h", "M"),
    ("morris_A_hm_band_span_h", "M"), ("morris_A_C_band_span_h", "M"),
    ("morris_A_h_band_span_h", "M"),
    ("sens_ratio_D_over_h_A", "m"), ("sens_ratio_D_over_h_B", "m"),
    # --- 集合 ---
    ("ens_N", "m"), ("ens_seed", "m"),
    ("ens16_rel_w95_q3_pct", "M"), ("ens16_rel_w95_q4_pct", "M"),
    ("ens_q3_rel_w95_pct", "M"), ("ens_q4_rel_w95_pct", "M"),
    ("ens_q3_q025_h", "M"), ("ens_q3_q975_h", "M"),
    ("ens_q4_q025_h", "M"), ("ens_q4_q975_h", "M"),
    ("ens_q3_mean_h", "M"), ("ens_q4_mean_h", "M"),
    ("ens_q3_sd_h", "M"), ("ens_q4_sd_h", "M"),
    ("ens_q3_w95_h", "M"), ("ens_q4_w95_h", "M"),
    ("ens_rel_w95_widen_factor.q3", "m"), ("ens_rel_w95_widen_factor.q4", "m"),
    # --- 严格闭合 ---
    ("closure_base_td_h", "M"), ("closure_td_strict_h", "M"), ("closure_td_meanv_h", "M"),
    ("closure_shift_strict_pct", "M"), ("closure_shift_strict_h", "M"),
    ("closure_excess_min_strict_pct", "M"), ("closure_excess_max_strict_pct", "M"),
    ("closure_excess_end_strict_pct", "M"), ("closure_eps_m_max_meanv", "M"),
    ("closure_md_initial_kg", "m"), ("closure_case", "m"), ("closure_Nc", "m"),
    ("closure_dt_s", "m"), ("closure_shift_meanv_pct", "m"),
    # --- 其它 ---
    ("cand_surface_n_runs", "m"),
]


def candidates(v):
    """枚举 '×10^k 后取 n 位小数' 的全部候选字面量（含取绝对值与负号两种写法）。"""
    out = []
    if not isinstance(v, (int, float)):
        return out
    v = float(v)
    for k in range(0, 7):
        x = v * 10.0 ** k
        for nd in range(1, 7):
            out.append("%.*f" % (nd, x))
            out.append("%.*f" % (nd, -x))
    return out


def int_candidates(v, pool):
    """整数量（记录行数、t_end、网格数）只在整数池里找，且只认十进制整数写法。

    门槛 |v| >= 10 是为了挡掉 0/1/2 这类几乎必然出现在正文任意位置的小整数——
    它们一旦算命中就是假通过，比漏报更危险。
    """
    out = []
    if not isinstance(v, (int, float)):
        return out
    v = float(v)
    if v != int(v) or abs(v) < 10:
        return out
    for s in ("%d" % int(v), "%d" % -int(v)):
        if s in pool:
            out.append(s)
    return out


def section_e():
    hit, missed_m, missed_may = {}, [], []
    for path, lvl in REG:
        v = val(path)
        if v is MISSING:
            fail("E", "注册表引用了事实表里没有的条目：%s" % path)
            continue
        if not isinstance(v, (int, float)):
            fail("E", "%s 的值不是数值（%r），无法核验" % (path, v))
            continue
        got = None
        for c in candidates(v):
            if c in BODY_LITS:
                got = c
                break
        if got is None:
            ic = int_candidates(v, BODY_INTS)
            if ic:
                got = ic[0]
        if got:
            hit[path] = got
        elif lvl == "M":
            missed_m.append((path, v))
        else:
            missed_may.append((path, v))
    for path, v in missed_m:
        fail("E", "%s = %.10g 在正文里找不到任何精度的写法：事实表改了而论文没跟" % (path, v))
    for path, v in missed_may:
        note("E", "%s = %.10g 未以数字形式出现（多写成数词或只进表，按提示处理）" % (path, v))
    note("E", "注册表 %d 条，正文命中 %d 条" % (len(REG), len(hit)))
    return set(hit.values())


# ============================================================================
# F. 废弃表述
# ============================================================================
DEPRECATED = [
    ("95 \\% interval", "旧的'95% 区间'口径，已改为条件于 ±5% 均匀扰动的 2.5-97.5 分位区间"),
    ("95\\% interval", "同上"),
    ("Monte Carlo mean", "旧措辞，集合量一律写 ensemble"),
    ("Interval width", "旧表头，已改为 Quantile range"),
]


def section_f():
    for s, why in DEPRECATED:
        if s in TEXN:
            fail("F", "正文仍含废弃表述 '%s'（%s）" % (s, why))
    note("F", "废弃表述 %d 条，均未出现" % len(DEPRECATED))


# ============================================================================
# G. 参考文献
# ============================================================================
def section_g():
    items = re.findall(r"\\bibitem\{([^}]+)\}", TEXN)
    dup = sorted({k for k in items if items.count(k) > 1})
    if dup:
        fail("G", "重复的 \\bibitem 键：%s" % dup)
    order, seen = [], set()
    for c in re.findall(r"\\cite\{([^}]+)\}", TEXN):
        for k in c.split(","):
            k = k.strip()
            if k and k not in seen:
                seen.add(k)
                order.append(k)
    if set(items) != seen:
        fail("G", "bibitem 与被引键不一致：只列不引 %s；只引不列 %s"
             % (sorted(set(items) - seen), sorted(seen - set(items))))
    if order != [k for k in items if k in seen]:
        for i, (a, b) in enumerate(zip(order, [k for k in items if k in seen])):
            if a != b:
                fail("G", "首次引用次序与条目次序不符：第 %d 个被引的是 %s，而第 %d 条是 %s"
                     % (i + 1, a, i + 1, b))
                break
    if os.path.exists(AUX):
        bc = re.findall(r"\\bibcite\{([^}]+)\}\{(\d+)\}", read_text(AUX))
        if len(bc) != len(items):
            fail("G", ".aux 的 \\bibcite 有 %d 条，正文 \\bibitem 有 %d 条" % (len(bc), len(items)))
    note("G", "参考文献 %d 条，全部被引，首次引用次序与条目次序一致" % len(items))


# ============================================================================
# H. 事实表新鲜度
# ============================================================================
SKIP_SRC = ("重算", "题给", "同上", "口径", "vs", "插值", "重算 vs 归档")


def section_h():
    ft = os.path.getmtime(FACTS)
    checked, missing = 0, set()
    for k, e in FACT.items():
        s = e.get("source") or ""
        if s in SKIP_SRC:
            continue
        for cand in s.split("+"):
            c = cand.strip()
            if not c or c in SKIP_SRC or " " in c:
                continue
            p = find_src(c)
            if p is None:
                missing.add(c)
                continue
            checked += 1
            if os.path.getmtime(p) > ft + 1.0:
                fail("H", "%s 比它的源 %s 旧 ⇒ 重跑 build_facts.py"
                     % (os.path.basename(FACTS), c))
    note("H", "新鲜度检查覆盖 %d 个本地源文件；无法解析的 source：%s"
         % (checked, ", ".join(sorted(missing)) if missing else "无"))


# ============================================================================
# I. 覆盖审计（仅报告）
# ============================================================================
ALLOWED = {
    "1.05", "0.95", "2.5", "97.5", "0.25", "0.15", "1.0", "0.0", "3.1416",
    "1.5", "2.0", "0.5", "0.9", "0.1",
}


def section_i(reg_lits):
    covered = set(reg_lits)
    for rows in parse_tables().values():
        for cells in rows:
            for c in cells:
                covered.update(cell_numbers(c))
    seen = {}
    for lit in re.findall(r"(?<![\w.])(\d+\.\d+)(?![\w])", BODY):
        if lit not in covered and lit not in ALLOWED:
            seen[lit] = seen.get(lit, 0) + 1
    if seen:
        note("I", "正文里以下 %d 个数字字面量未被注册表或四张表解释，"
             "逐个确认是独立输入还是应补进 build_facts.py：" % len(seen))
        for lit, n in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0])):
            NOTES.append("[I]     %-12s x%d" % (lit, n))
    else:
        note("I", "正文数字全部可回溯到事实表或表内数据")


# ============================================================================
def main():
    section_a()
    section_b()
    section_c()
    section_d()
    reg_lits = section_e()
    section_f()
    section_g()
    section_h()
    section_i(reg_lits)

    line = "-" * 78
    print(line)
    print("check_manuscript.py   main_ts.tex  x  numeric_facts.json(%d 条)  x  figure_manifest.csv(%d 行)"
          % (len(FACT), len(MAN)))
    print(line)
    for s in NOTES:
        print("  " + s)
    if WARNS:
        print(line)
        print("警告 %d 条：" % len(WARNS))
        for s in WARNS:
            print("  " + s)
    print(line)
    if FAILS:
        print("失败 %d 条：" % len(FAILS))
        for s in FAILS:
            print("  " + s)
        print(line)
        print("不合格：论文与事实表 / 清单未锁死。")
        return 1
    print("全部通过：资产编号、生成器、四张表逐格、正文数值注册表、废弃表述、"
          "参考文献、事实表新鲜度均一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
