# -*- coding: utf-8 -*-
# ====================================================================
# 来自 公共_物性与边界.py
# ====================================================================
# 公共内核：附录2/3/4 物性、边界环境、几何与附件读取
# 题目：2026 CUMCM A 题《药材的烘干问题》
import os
import numpy as np
from openpyxl import load_workbook

# ---------- 几何与固定参数（全部来自题目正文与附录） ----------
L_CYL = 0.25          # 圆柱长度 m
R0    = 0.02          # 初始半径 m
T0_C  = 28.0          # 初温 ℃
C0    = 2.55          # 初含水率 kg/kg(干基)
H_Q   = 25.0          # 对流换热系数 W/(m2·K)   [附录2]
HM    = 8.0e-7        # 对流传质系数 m/s        [附录2]
EXP_FLOOR = -700.0    # 仅对"指数"做下限保护，绝不截断物理量本身

# 附件路径：默认取交付目录下的 题目文件/
_HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.environ.get("HERB_SRC", os.path.join(_HERE, "..", "data", "raw"))


def load_att1(path=None):
    """附件1 -> t[s], T_amb[℃], C_amb[kg/kg]"""
    path = path or os.path.join(SRC_DIR, "附件1.xlsx")
    ws = load_workbook(path, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(values_only=True):
        try:
            v = [float(r[0]), float(r[1]), float(r[2])]
        except (TypeError, ValueError, IndexError):
            continue
        rows.append(v)
    a = np.array(rows)
    return a[:, 0], a[:, 1], a[:, 2]


def load_att2(path=None):
    """附件2 -> t[s], R[cm]"""
    path = path or os.path.join(SRC_DIR, "附件2.xlsx")
    ws = load_workbook(path, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(values_only=True):
        try:
            v = [float(r[0]), float(r[1])]
        except (TypeError, ValueError, IndexError):
            continue
        rows.append(v)
    a = np.array(rows)
    return a[:, 0], a[:, 1]


_T1, _Ta, _Ca = load_att1()
_T2, _R2 = load_att2()
TA_PLAT = float(np.mean(_Ta[-61:]))      # 恒温段环境温度 ℃
CA_PLAT = float(np.mean(_Ca[-61:]))      # 恒温段环境含湿量 kg/kg
T1_END  = float(_T1[-1])                 # 14400 s
T2_END  = float(_T2[-1])                 # 259200 s


def env(t, kappa=1.0):
    """环境边界：附件1 线性插值至 14400 s，其后取恒温段平台。kappa 为环境含湿量缩放因子。"""
    tt = np.asarray(t, float)
    T = np.where(tt <= T1_END, np.interp(np.minimum(tt, T1_END), _T1, _Ta), TA_PLAT)
    C = np.where(tt <= T1_END, np.interp(np.minimum(tt, T1_END), _T1, _Ca), CA_PLAT)
    return T + 273.15, C * kappa


def Rof(t, lam=1.0):
    """半径轨迹：R_lam(t) = R0 + lam*[R_att2(t) - R0]，lam=1 为附件2真实轨迹。单位 m。"""
    tt = np.minimum(np.asarray(t, float), T2_END)
    r_att2 = np.interp(tt, _T2, _R2) / 100.0
    return R0 + lam * (r_att2 - R0)


def props(case, C, Tk):
    """按题号返回 rho, cp, k, D。case=2/3/4 对应附录2/3/4。仅对指数做下限保护。"""
    C = np.asarray(C, float)
    Tk = np.asarray(Tk, float)
    if case == 2:
        rho = np.full_like(C, 820.0)
        cp = np.full_like(C, 2600.0)
        kk = np.full_like(C, 0.36)
        D = 7.0e-9 * np.exp(np.maximum(-0.89 / C, EXP_FLOOR))
    elif case == 3:
        rho = 650.0 + 128.0 * C
        cp = 1450.0 + 2736.0 * C / (C + 1.0)
        kk = 0.21 + 0.38 * C / (C + 1.0)
        e = np.log(2.4e-3) - 0.45 / C - 3850.0 / Tk
        D = np.exp(np.maximum(e, EXP_FLOOR))
    elif case == 4:
        rho = 760.0 + 90.0 * C
        cp = 1850.0 + 2150.0 * C / (C + 1.0)
        kk = 0.12 + 0.20 * C / (C + 1.0)
        e = np.log(4.2e-4) - 0.30 / C - 3850.0 / Tk
        D = np.exp(np.maximum(e, EXP_FLOOR))
    else:
        raise ValueError("case 必须是 2/3/4")
    return rho, cp, kk, D


def surfC(case, C, T, Nc, Rw, Cinf):
    """壁面串联传质阻反解表面含水率（末单元中心 != 表面）"""
    _, _, _, D = props(case, C, T)
    Gint = 2.0 * np.pi * L_CYL * D[-1] / np.log(1.0 / (1.0 - 0.5 / Nc))
    Gfilm = 2.0 * np.pi * L_CYL * Rw * HM
    return (Gint * C[-1] + Gfilm * Cinf) / (Gint + Gfilm)


def surfT(case, C, T, Nc, Rw, Tamb):
    """壁面串联换热阻反解表面温度"""
    _, _, kk, _ = props(case, C, T)
    Gint = 2.0 * np.pi * L_CYL * kk[-1] / np.log(1.0 / (1.0 - 0.5 / Nc))
    Gfilm = 2.0 * np.pi * L_CYL * Rw * H_Q
    return (Gint * T[-1] + Gfilm * Tamb) / (Gint + Gfilm)


def guard_out(path):
    """长计算前预检目标可写；返回临时路径 path+'.part'，算完再 commit_out 原子替换。
    xlsxwriter 是到最后 close() 才组装 zip 写盘，若那时目标被 Excel/WPS 锁住，
    几百秒的计算会全部作废——所以在开算之前就把这个坑探掉。"""
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        raise RuntimeError("结果目录不存在：%s" % d)
    try:
        with open(path, "a"):
            pass
    except OSError as e:
        raise RuntimeError(
            "目标文件正被其它程序占用，无法写入：\n  %s\n"
            "请先关闭打开它的 Excel / WPS 窗口再重跑。系统提示：%s" % (path, e))
    return path + ".part"


def commit_out(tmp, path):
    """把临时产物原子替换到目标位置；失败时 tmp 仍完整保留，不丢计算结果。"""
    try:
        os.replace(tmp, path)
    except OSError as e:
        raise RuntimeError(
            "写入目标失败，但完整结果已保留在：\n  %s\n"
            "关闭占用它的程序后把它改名为 %s 即可。系统提示：%s"
            % (tmp, os.path.basename(path), e))


def cell_r(Nc, Rw):
    """单元中心物理半径 r_i = xi_i * R(t)，单位 m（xi_i=(i+0.5)/Nc）。"""
    return ((np.arange(Nc) + 0.5) / Nc) * Rw


def profile_ext(case, C, T, Nc, Rw, Cinf, Tamb):
    """把单元中心剖面扩成 Nc+1 个节点：末节点 r=R 用壁面串联阻反解补上。
    否则 np.interp 在 r 接近 R 的一段会退化为端点外推（末单元中心 ≠ 表面）。
    返回 (r_nodes, Cx, Tx)。"""
    r_nodes = np.empty(Nc + 1)
    r_nodes[:Nc] = cell_r(Nc, Rw)
    r_nodes[Nc] = Rw
    Cx = np.empty(Nc + 1)
    Cx[:Nc] = C
    Cx[Nc] = surfC(case, C, T, Nc, Rw, Cinf)
    Tx = np.empty(Nc + 1)
    Tx[:Nc] = T
    Tx[Nc] = surfT(case, C, T, Nc, Rw, Tamb)
    return r_nodes, Cx, Tx


# ====================================================================
# 来自 求解_一维有限体积.py
# ====================================================================
# 一维径向有限体积求解器（拉格朗日 xi = r/R(t) 坐标，单元中心型 FVM）
# 关键纪律：backward Euler + Picard，RHS 一律锁定步首值 Told/Cold，迭代内只刷新系数
import numpy as np
from scipy.linalg import solve_banded


def make_grid(Nc):
    """单元中心 xi_i=(i+0.5)/Nc；体积份额 Vsh_i=(xi_{i+1})^2-(xi_i)^2（xi 为单元边界 i/Nc）。"""
    xi = (np.arange(Nc) + 0.5) / Nc
    lo = np.arange(Nc) / Nc
    hi = (np.arange(Nc) + 1) / Nc
    return xi, hi ** 2 - lo ** 2


def face_logfac(Nc):
    """面几何因子 1/ln(xi_{i+1}/xi_i)（单元中心之比）。
    返回长度 Nc+1 的数组，索引 i+1 对应"单元 i 与 i+1 之间的面"；索引 0 与 Nc 置 0（不使用）。"""
    xi = (np.arange(Nc) + 0.5) / Nc
    g = np.zeros(Nc + 1)
    for i in range(Nc - 1):
        g[i + 1] = 1.0 / np.log(xi[i + 1] / xi[i])
    return g


def _assemble(Vi, Gfaces, cap, Gw, Cinf, Cold):
    """三对角装配：diag = cap + 左/右/壁面导；RHS = cap*Cold (+ 壁面源 wall*Cinf)。"""
    Nc = Vi.size
    left = np.zeros(Nc)
    left[1:] = Gfaces[1:Nc] / Vi[1:]
    right = np.zeros(Nc)
    right[:-1] = Gfaces[1:Nc] / Vi[:-1]
    wall = np.zeros(Nc)
    wall[-1] = Gw / Vi[-1]
    diag = cap + left + right + wall
    ab = np.zeros((3, Nc))
    ab[1, :] = diag
    ab[2, :-1] = -left[1:]
    ab[0, 1:] = -right[:-1]
    rhs = cap * Cold
    rhs[-1] += wall[-1] * Cinf
    return ab, rhs


def _wall_series(Gint, Gfilm):
    return 1.0 / (1.0 / Gint + 1.0 / Gfilm)


def _step(Cc, T, t_new, dt, case, Nc, shrink, Vsh, logfac, piter, Cinf, Tamb, lam=1.0):
    """单个 backward Euler 步；R(t) 取步末（隐式）。lam 为半径轨迹缩放（仅 shrink=True 时生效）。"""
    Rw = float(Rof(t_new, lam)) if shrink else R0
    Vi = np.pi * L_CYL * Rw ** 2 * Vsh
    Told = T.copy()
    Cold = Cc.copy()
    xiN = 1.0 - 0.5 / Nc
    ln_wall = np.log(1.0 / xiN)
    for _ in range(piter):
        rho, cp, kk, D = props(case, Cc, T)
        Df = np.empty(Nc + 1)
        Df[1:Nc] = 0.5 * (D[:-1] + D[1:])
        kf = np.empty(Nc + 1)
        kf[1:Nc] = 0.5 * (kk[:-1] + kk[1:])
        Gc = 2.0 * np.pi * L_CYL * Df * logfac
        Gt = 2.0 * np.pi * L_CYL * kf * logfac
        Gw_c = _wall_series(2.0 * np.pi * L_CYL * D[-1] / ln_wall,
                            2.0 * np.pi * L_CYL * Rw * HM)
        Gw_t = _wall_series(2.0 * np.pi * L_CYL * kk[-1] / ln_wall,
                            2.0 * np.pi * L_CYL * Rw * H_Q)
        abc, rhsc = _assemble(Vi, Gc, (1.0 / dt) * np.ones(Nc), Gw_c, Cinf, Cold)
        Cc = solve_banded((1, 1), abc, rhsc)
        abt, rhst = _assemble(Vi, Gt, rho * cp / dt, Gw_t, Tamb, Told)
        T = solve_banded((1, 1), abt, rhst)
    return Cc, T


def solve1d(case, Nc, dt, tmax, kappa=1.0, shrink=False, Ccr=0.15,
            T0=T0_C, C0=C0, piter=3, sampler=None, sample_every=1,
            stop_at_hit=False, lam=1.0):
    """积分至 tmax；stop_at_hit=True 时提前停在首次 max_r C <= Ccr（步内线性插值定位）。
    内部步长 dt 与输出网格解耦：sampler 每 sample_every 步调用一次，终点/达标点必调一次。
    stop_at_hit 时用 h2=t_hit-t_prev 从步首状态重走最后一段，使返回的 C/T 恰好落在 t_hit。
    lam 为半径轨迹缩放 R_lam(t)=R0+lam*[R_att2(t)-R0]，仅 shrink=True 时生效（灵敏度 S_lam 用）。
    返回 dict(td_h, t_hit_s, C, T, r, Ri, rows)。"""
    xi, Vsh = make_grid(Nc)
    logfac = face_logfac(Nc)
    Cc = np.full(Nc, float(C0))
    T = np.full(Nc, float(T0) + 273.15)
    t = 0.0
    tmax = float(tmax)
    hit = None
    prev_max = None
    prev_t = 0.0
    rows = []
    Rw = R0
    step = 0
    last_sampled = -1.0
    while t < tmax - 1e-9:
        h = min(dt, tmax - t)
        # 把时间钉在 1e-6 s 栅格上：否则 t += h 的浮点漂移会让 36000 步后落在
        # 1799.9999999989107，循环多走一步，末点重复落盘（详见下方采样去重注释）。
        # 本工程所有 dt（0.05/0.5/7.5/30）都是 1e-6 的整数倍 ⇒ 该取整不引入任何失真。
        t_new = round(t + h, 6)
        Tamb, Cinf = env(t_new, kappa)
        Tamb = float(np.ravel(Tamb)[0])
        Cinf = float(np.ravel(Cinf)[0])
        Cprev, Tprev = Cc, T
        Cc, T = _step(Cc, T, t_new, h, case, Nc, shrink, Vsh, logfac, piter, Cinf, Tamb, lam)
        Rw = float(Rof(t_new, lam)) if shrink else R0
        if hit is None:
            m = float(Cc.max())
            if m <= Ccr and prev_max is not None and prev_max > Ccr:
                frac = 0.0 if prev_max <= m else (prev_max - Ccr) / (prev_max - m)
                hit = prev_t + frac * h
                if stop_at_hit and hit - prev_t > 1e-12:
                    h2 = hit - prev_t
                    Tam2, Cin2 = env(hit, kappa)
                    Tam2 = float(np.ravel(Tam2)[0])
                    Cin2 = float(np.ravel(Cin2)[0])
                    Cc, T = _step(Cprev, Tprev, hit, h2, case, Nc, shrink, Vsh,
                                  logfac, piter, Cin2, Tam2, lam)
                    Rw = float(Rof(hit, lam)) if shrink else R0
                    Tamb, Cinf, t_new = Tam2, Cin2, hit
            prev_max = m
        step += 1
        if sampler is not None and (step % sample_every == 0
                                    or t_new >= tmax - 1e-9
                                    or (stop_at_hit and hit is not None)):
            # 浮点累加 t += h 有系统漂移：dt=0.05 累到 1800 s 时，样本落在
            # 1799.9999999989107，再补一步才到 1800.0（漂移约 1.1e-9 s）。
            # 两个采样在 %.6g 下**同写成 "1800"** ⇒ 落盘成重复时间块，
            # 令任何 reshape/pivot 直接报错。故按单调时间去重，容差 1e-6 s
            # （远大于 1.1e-9 漂移，远小于最小输出间隔 0.05 s）。
            # 达标点（hit）必须保留，不受此去重影响。
            if (stop_at_hit and hit is not None) or t_new > last_sampled + 1e-6:
                rows.append(sampler(t_new, Cc, T, Rw, Tamb, Cinf))
                last_sampled = t_new
        prev_t = t_new
        t = t_new
        if stop_at_hit and hit is not None:
            break
    return {"td_h": None if hit is None else hit / 3600.0, "t_hit_s": hit,
            "C": Cc, "T": T, "r": xi * Rw, "Ri": Rw, "rows": rows}


# ====================================================================
# 来自 求解_二维轴对称.py
# ====================================================================
# 二维轴对称有限体积（r-z，单元中心型）：量化"端面效应按单位长度归一（一维径向降阶）"
# 这条假设的**形式误差**——题面没给依据，此前它只是假设，不是计算。
# 计算域取半个圆柱 z∈[0,L/2]：z=0 为对称面（中截面），z=L/2 为端面。
# 降维一致性核验：endface='adiabatic' 时解必须 z 向均匀 ⇒ 精确退化为 fvm1d（径向离散逐项照抄：
#   面导对数精确、面积用单元边界、对数里用单元中心、壁面串联阻）。已验证 max|ΔC|=3.3e-15。
#   ⚠️ 该测试**只覆盖轴向不活跃的分支**，不能证明 Robin 端面实现正确——端面导纳被乘 0，
#      分支写错也照样通过。Robin 分支的检验只能靠：几何上确证串联形式 + 有限长→无穷长极限回退 1D。
# 端面导纳（与径向侧壁同为"内部半格阻 + 膜阻"串联，只是半格阻的形式不同）：
#   径向侧壁内部半格 = 圆柱对数阻 ln(R/r_last)/(2πL·k) ；
#   轴向端面内部半格 = 平板阻 Δz/(2·k·A_z) —— 末单元中心在 z=L/2−Δz/2，端面在 L/2，中间隔着半格。
import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

DR = None
DZ = None


def geo(Nr, Nz, L2=None):
    """单元边界 re、单元中心 rc、单元体积 Vi[Nr]、环面积 Az[Nr]、
    径向面导几何因子 grf[Nr-1]、壁面串联阻几何因子 (gint_g, gfilm_g)。
    L2 = 半长（默认 L_CYL/2）；做"有限长→无穷长回退 1D"极限检验时改大它。"""
    if L2 is None:
        L2 = L_CYL / 2.0
    dr = R0 / Nr
    dz = L2 / Nz
    re = np.arange(Nr + 1) * dr
    rc = (np.arange(Nr) + 0.5) * dr
    Vi = np.pi * (re[1:] ** 2 - re[:-1] ** 2) * dz
    Az = np.pi * (re[1:] ** 2 - re[:-1] ** 2)
    grf = 2.0 * np.pi * dz / np.log(rc[1:] / rc[:-1])      # 长度 Nr-1
    gint_g = 2.0 * np.pi * dz / np.log(R0 / rc[-1])
    gfilm_g = 2.0 * np.pi * R0 * dz
    return dr, dz, rc, Vi, Az, grf, gint_g, gfilm_g


def _build(gr_f, gz_f, sink, cap, Vi, Nr, Nz):
    """gr_f：径向面导（长度 Nn-Nz，按 i 主序展平）；gz_f：轴向面导（长度 Nn-1，j=Nz-1 处为 0）；
    sink：各单元汇导（长度 Nn）。返回 A，供 cap*Cold + 源项 求解。"""
    Nn = Nr * Nz
    V = np.repeat(Vi, Nz)
    fs = np.zeros(Nn)
    fs[:Nn - Nz] += gr_f
    fs[Nz:] += gr_f
    fs[:Nn - 1] += gz_f
    fs[1:] += gz_f
    diag = cap + (fs + sink) / V
    A = diags([-gz_f / V[1:], -gr_f / V[Nz:], diag,
               -gr_f / V[:Nn - Nz], -gz_f / V[:Nn - 1]],
              [-1, -Nz, 0, Nz, 1], format="csc")
    return A


def _faces(Dm, Az, grf, dz, Nr, Nz):
    """由逐格系数场 Dm(Nr,Nz) 构造径向/轴向面导（相邻单元中心均值）。"""
    gr = (0.5 * (Dm[:-1, :] + Dm[1:, :]) * grf[:, None]).ravel()
    gz = np.zeros((Nr, Nz))
    gz[:, :-1] = 0.5 * (Dm[:, :-1] + Dm[:, 1:]) * (Az / dz)[:, None]
    return gr, gz.ravel()[:-1]


def _step2d(Cc, T, dt, case, Nr, Nz, Vi, Az, grf, gint_g, gfilm_g, dz, endface,
          piter, Cinf, Tamb):
    Nn = Nr * Nz
    Told = T.copy()
    Cold = Cc.copy()
    for _ in range(piter):
        rho, cp, kk, D = props(case, Cc, T)
        Dm = D.reshape(Nr, Nz)
        km = kk.reshape(Nr, Nz)
        # ---- 组分 ----
        gr, gz = _faces(Dm, Az, grf, dz, Nr, Nz)
        gw = np.zeros((Nr, Nz))
        gw[-1, :] = 1.0 / (1.0 / (Dm[-1, :] * gint_g) + 1.0 / (HM * gfilm_g))
        src = np.zeros((Nr, Nz))
        src[-1, :] += gw[-1, :] * Cinf
        if endface == "robin":
            gwe = 1.0 / (dz / (2.0 * Dm[:, -1] * Az) + 1.0 / (HM * Az))
            gw[:, -1] += gwe
            src[:, -1] += gwe * Cinf
        A = _build(gr, gz, gw.ravel(), np.full(Nn, 1.0 / dt), Vi, Nr, Nz)
        rhs = (1.0 / dt) * Cold + (src / Vi[:, None]).ravel()
        Cc = spsolve(A, rhs)
        # ---- 温度 ----
        grT, gzT = _faces(km, Az, grf, dz, Nr, Nz)
        gwT = np.zeros((Nr, Nz))
        gwT[-1, :] = 1.0 / (1.0 / (km[-1, :] * gint_g) + 1.0 / (H_Q * gfilm_g))
        srcT = np.zeros((Nr, Nz))
        srcT[-1, :] += gwT[-1, :] * Tamb
        if endface == "robin":
            gweT = 1.0 / (dz / (2.0 * km[:, -1] * Az) + 1.0 / (H_Q * Az))
            gwT[:, -1] += gweT
            srcT[:, -1] += gweT * Tamb
        rc_ = (rho * cp).reshape(Nr, Nz)
        capT = rc_.ravel() / dt
        AT = _build(grT, gzT, gwT.ravel(), capT, Vi, Nr, Nz)
        rhsT = capT * Told + (srcT / Vi[:, None]).ravel()
        T = spsolve(AT, rhsT)
    return Cc, T


def solve2d(Nr, Nz, dt, tmax, case=3, Ccr=0.15, endface="robin", kappa=1.0,
            T0=T0_C, C0=C0, piter=3, stop_at_hit=True, L2=None):
    dr, dz, rc, Vi, Az, grf, gint_g, gfilm_g = geo(Nr, Nz, L2)
    Cc = np.full(Nr * Nz, float(C0))
    T = np.full(Nr * Nz, float(T0) + 273.15)
    t = 0.0
    hit = None
    prev_max = None
    prev_t = 0.0
    probe = None
    while t < tmax - 1e-9:
        h = min(dt, tmax - t)
        t_new = t + h
        Tamb, Cinf = env(t_new, kappa)
        Tamb = float(np.ravel(Tamb)[0])
        Cinf = float(np.ravel(Cinf)[0])
        Cc, T = _step2d(Cc, T, h, case, Nr, Nz, Vi, Az, grf, gint_g, gfilm_g, dz,
                      endface, piter, Cinf, Tamb)
        # 早期探针：端面通量 / 侧壁通量。两者都含膜阻，比值由"串联总导 × 面积"定，
        # 随网格变化 ⇒ 只作定性核验（端面确在起作用、量级为个位数百分比），不当结论数。
        if probe is None and t_new >= 600.0 and endface == "robin":
            Cm = Cc.reshape(Nr, Nz)
            Dm = props(case, Cc, T)[3].reshape(Nr, Nz)
            # 侧壁：末径向行、逐轴位 j（长度 Nz）；端面：末轴向列、逐径向位 i（长度 Nr）
            gsA = 1.0 / (1.0 / (Dm[-1, :] * gint_g) + 1.0 / (HM * gfilm_g))
            side = float((gsA * (Cm[-1, :] - Cinf)).sum())
            geA = 1.0 / (dz / (2.0 * Dm[:, -1] * Az) + 1.0 / (HM * Az))
            endf = float((geA * (Cm[:, -1] - Cinf)).sum())
            probe = (t_new, side, endf, endf / side)
        if hit is None:
            m = float(Cc.max())
            if m <= Ccr and prev_max is not None and prev_max > Ccr:
                frac = 0.0 if prev_max <= m else (prev_max - Ccr) / (prev_max - m)
                hit = prev_t + frac * h
            prev_max = m
        prev_t = t_new
        t = t_new
        if stop_at_hit and hit is not None:
            break
    return {"td_h": None if hit is None else hit / 3600.0, "t_hit_s": hit,
            "C": Cc.reshape(Nr, Nz), "T": T.reshape(Nr, Nz),
            "rc": rc, "Az": Az, "Nr": Nr, "Nz": Nz, "dz": dz, "probe": probe}


# ====================================================================
# 来自 验证_独立有限元.py
# ====================================================================
# 一维径向 Galerkin 有限元（P1 节点型，拉格朗日 xi = r/R(t) 坐标）
# 用途：独立于 fvm1d 的第二种离散，做"多实现逐位互证"意义上的交叉求解器核验。
# 与 fvm1d 的五处实质差异（差异越真，互证越有意义）：
#   1) 未知量在节点（含 xi=0 与 xi=1）；FVM 在单元中心，表面靠壁面串联阻反解。
#   2) 弱形式 + 一致质量阵（非集中质量）；FVM 是通量守恒型。
#   3) 质量阵/刚度阵按权重 ξ dξ 解析积分，无求积误差。
#   4) 表面用裸 Robin（节点恰在 ξ=1）；FVM 用末单元半格阻 + 膜阻串联。
#   5) 单元系数取两端节点均值；FVM 取相邻单元中心均值（相差半格）。
# 方程为同一方程、同一边界设定、同一判据位置（见 cellC 注释）。
import numpy as np
from scipy.linalg import solve_banded


def fem_geo(Nc):
    """节点型几何：返回节点 xi、一致质量阵 Me、刚度阵 Ke（均按权重 ξ dξ 解析积分）。
    Me[e] = [[xa*h/3+h^2/12, xa*h/6+h^2/12], [sym, xa*h/3+h^2/4]]
    Ke[e] = (xa/h+1/2)*[[1,-1],[-1,1]]"""
    xi = np.arange(Nc + 1) / float(Nc)
    h = np.diff(xi)
    xa = xi[:-1]
    Me = np.empty((Nc, 2, 2))
    Me[:, 0, 0] = xa * h / 3.0 + h * h / 12.0
    Me[:, 0, 1] = xa * h / 6.0 + h * h / 12.0
    Me[:, 1, 0] = Me[:, 0, 1]
    Me[:, 1, 1] = xa * h / 3.0 + h * h / 4.0
    Ke = np.empty((Nc, 2, 2))
    q = xa / h + 0.5
    Ke[:, 0, 0] = q
    Ke[:, 1, 1] = q
    Ke[:, 0, 1] = -q
    Ke[:, 1, 0] = -q
    return xi, Me, Ke


def _asm(Me, Ke, am, ak, Nn, robin, Cold, Cinf):
    """装配三对角 A C = b。am[e]=容量系数/dt，ak[e]=扩散系数/R^2，末端 robin=h_m/R。
    RHS 一律锁定步首值 Cold（与 FVM 同纪律，防迭代吞时间步）。"""
    Nc = Me.shape[0]
    diag = np.zeros(Nn)
    upper = np.zeros(Nn - 1)
    lower = np.zeros(Nn - 1)
    diag[:-1] += am * Me[:, 0, 0] + ak * Ke[:, 0, 0]
    upper += am * Me[:, 0, 1] + ak * Ke[:, 0, 1]
    lower += am * Me[:, 1, 0] + ak * Ke[:, 1, 0]
    diag[1:] += am * Me[:, 1, 1] + ak * Ke[:, 1, 1]
    diag[-1] += robin
    ab = np.zeros((3, Nn))
    ab[1, :] = diag
    ab[2, :-1] = upper
    ab[0, 1:] = lower
    rhs = np.zeros(Nn)
    rhs[:-1] += am * (Me[:, 0, 0] * Cold[:-1] + Me[:, 0, 1] * Cold[1:])
    rhs[1:] += am * (Me[:, 1, 0] * Cold[:-1] + Me[:, 1, 1] * Cold[1:])
    rhs[-1] += robin * Cinf
    return ab, rhs


def _stepfem(Cc, T, t_new, dt, case, Nc, shrink, Me, Ke, piter, Cinf, Tamb, lam=1.0):
    Rw = float(Rof(t_new, lam)) if shrink else R0
    Told = T.copy()
    Cold = Cc.copy()
    invR2 = 1.0 / (Rw * Rw)
    for _ in range(piter):
        rho, cp, kk, D = props(case, Cc, T)
        Dh = 0.5 * (D[:-1] + D[1:]) * invR2
        kh = 0.5 * (kk[:-1] + kk[1:]) * invR2
        rc = 0.5 * (rho[:-1] + rho[1:]) * 0.5 * (cp[:-1] + cp[1:])
        amC = np.full(Nc, 1.0 / dt)
        ab, rhs = _asm(Me, Ke, amC, Dh, Nc + 1, HM / Rw, Cold, Cinf)
        Cc = solve_banded((1, 1), ab, rhs)
        amT = rc / dt
        ab, rhs = _asm(Me, Ke, amT, kh, Nc + 1, H_Q / Rw, Told, Tamb)
        T = solve_banded((1, 1), ab, rhs)
    return Cc, T


def cellC(C):
    """P1 解在 FVM 单元中心 ξ=(i+0.5)/N 处的值（分段线性 ⇒ 两端节点均值）。
    这样判据采样的空间点与 fvm1d 完全一致，比较才无口径差。"""
    return 0.5 * (C[:-1] + C[1:])


def solve_fem(case, Nc, dt, tmax, kappa=1.0, shrink=False, Ccr=0.15,
              T0=T0_C, C0=C0, piter=3, stop_at_hit=False, lam=1.0):
    xi, Me, Ke = fem_geo(Nc)
    Cc = np.full(Nc + 1, float(C0))
    T = np.full(Nc + 1, float(T0) + 273.15)
    t = 0.0
    tmax = float(tmax)
    hit = None
    prev_max = None
    prev_t = 0.0
    Rw = R0
    while t < tmax - 1e-9:
        h = min(dt, tmax - t)
        t_new = t + h
        Tamb, Cinf = env(t_new, kappa)
        Tamb = float(np.ravel(Tamb)[0])
        Cinf = float(np.ravel(Cinf)[0])
        Cprev, Tprev = Cc, T
        Cc, T = _stepfem(Cc, T, t_new, h, case, Nc, shrink, Me, Ke, piter, Cinf, Tamb, lam)
        Rw = float(Rof(t_new, lam)) if shrink else R0
        if hit is None:
            m = float(cellC(Cc).max())
            if m <= Ccr and prev_max is not None and prev_max > Ccr:
                frac = 0.0 if prev_max <= m else (prev_max - Ccr) / (prev_max - m)
                hit = prev_t + frac * h
                if stop_at_hit and hit - prev_t > 1e-12:
                    h2 = hit - prev_t
                    Tam2, Cin2 = env(hit, kappa)
                    Tam2 = float(np.ravel(Tam2)[0])
                    Cin2 = float(np.ravel(Cin2)[0])
                    Cc, T = _stepfem(Cprev, Tprev, hit, h2, case, Nc, shrink, Me, Ke,
                                  piter, Cin2, Tam2, lam)
                    Rw = float(Rof(hit, lam)) if shrink else R0
            prev_max = m
        prev_t = t_new
        t = t_new
        if stop_at_hit and hit is not None:
            break
    return {"td_h": None if hit is None else hit / 3600.0, "t_hit_s": hit,
            "C": Cc, "T": T, "r": xi * Rw, "Ri": Rw}


# ---------------- 恒定 Robin 圆柱的 FEM 基准（对解析解验 FEM 自身阶） ----------------
def _cyl(Nc, dt, tmax):
    """恒定 D 的纯扩散 + 裸 Robin（Cinf=0）。与 test_regression._cyl_robin 同一物理题，
    但走 FEM 离散，故可各自对同一条解析解比阶。"""
    _R, _HM, _C0, _D = 0.02, 8.0e-7, 2.55, 1.0e-9
    xi, Me, Ke = fem_geo(Nc)
    invR2 = 1.0 / (_R * _R)
    C = np.full(Nc + 1, _C0)
    t = 0.0
    while t < tmax - 1e-9:
        h = min(dt, tmax - t)
        am = np.full(Nc, 1.0 / h)
        ak = np.full(Nc, _D * invR2)
        ab, rhs = _asm(Me, Ke, am, ak, Nc + 1, _HM / _R, C, 0.0)
        C = solve_banded((1, 1), ab, rhs)
        t += h
    return C, xi * _R


# ---------------- 纯空间阶：时间误差用矩阵指数精确积掉，不留 O(dt^2) 地板 ----------------
def _cyl_exact_time(Nc, tmax):
    """恒定 D 纯扩散 + 裸 Robin。半离散系统 M Ċ = −[D/R²·K + (h_m/R)e_N e_N^T] C 线性自治，
    用 expm 精确积分到 tmax ⇒ 误差纯空间，观测阶不受时间格式污染。"""
    from scipy.linalg import expm
    _R, _HM, _C0, _D = 0.02, 8.0e-7, 2.55, 1.0e-9
    xi, Me, Ke = fem_geo(Nc)
    Nn = Nc + 1
    M = np.zeros((Nn, Nn))
    A = np.zeros((Nn, Nn))
    for e in range(Nc):
        idx = [e, e + 1]
        for a in range(2):
            for b in range(2):
                M[idx[a], idx[b]] += Me[e, a, b]
                A[idx[a], idx[b]] += (_D / (_R * _R)) * Ke[e, a, b]
    A[-1, -1] += _HM / _R
    C = expm(-np.linalg.solve(M, A) * tmax) @ np.full(Nn, _C0)
    return C, xi * _R


# ====================================================================
# 来自 验证_交叉对拍.py
# ====================================================================
# 交叉求解器核验：同一方程、同一判据位置、同一时间格式，两种独立离散（fvm1d / fem1d）同格对拍。
# 产出 支撑材料/figdata/fem_crosscheck.csv
# 纪律：两套解的判据采样点必须重合——FVM 用单元中心 ξ=(i+0.5)/N，
#       FEM 用 P1 分段线性在同样 ξ 处的值 0.5*(C_i+C_{i+1})，否则比的是口径不是方法。
import os
import sys
import csv
import time
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
os.environ.setdefault("HERB_SRC", os.path.join(_ROOT, "data", "raw"))
OUT = os.path.join(_ROOT, "data", "processed", "figdata")


DT = 7.5
TMAX = 4.0e5
GRIDS = (200, 400, 800, 1600)
CASES = ((3, False, "Q3"), (4, True, "Q4"))


def conv_stats(td):
    """dt 固定 ⇒ 时间误差只是常数偏移，不影响逐格差分。返回 (观测阶 p, 用 p=2 外推, 用 p=1 外推)。
    注意：本族在 Nc 方向是预渐近的（逐格差分只缩约 2.3~2.5 倍而非 4 倍），
    因此 p=1 与 p=2 两个外推值是**上下界**而不是答案，两者相差约 10 s ——
    这部分差异要被当成"离散不确定度"，不能当结论报。"""
    if len(td) < 3:
        return None
    d1 = td[-2] - td[-3]
    d2 = td[-1] - td[-2]
    p = float(np.log2(d1 / d2)) if d2 > 1e-12 else float("nan")
    return p, td[-1] + (td[-1] - td[-2]) / 3.0, 2.0 * td[-1] - td[-2]


def 交叉对拍():
    rows = []
    print("A) 交叉求解器同格对拍（dt=%.1f s，判据 max C ≤ 0.15）" % DT)
    for case, shrink, q in CASES:
        fv, fe = [], []
        for Nc in GRIDS:
            t0 = time.time()
            o = solve1d(case=case, Nc=Nc, dt=DT, tmax=TMAX, shrink=shrink,
                              Ccr=0.15, stop_at_hit=True)
            fv.append(float(o["td_h"]))
            rows.append(["cross", q, "FVM", Nc, DT, fv[-1]])
            t1 = time.time()
            o2 = solve_fem(case=case, Nc=Nc, dt=DT, tmax=TMAX, shrink=shrink,
                                 Ccr=0.15, stop_at_hit=True)
            fe.append(float(o2["td_h"]))
            rows.append(["cross", q, "FEM", Nc, DT, fe[-1]])
            print("   %s Nc=%-5d FVM %9.4f h | FEM %9.4f h | 差 %+8.2f s | (%4.0f+%4.0f s)"
                  % (q, Nc, fv[-1], fe[-1], (fe[-1] - fv[-1]) * 3600.0,
                     t1 - t0, time.time() - t1))
        for tag, arr in (("FVM", fv), ("FEM", fe)):
            p, e2, e1 = conv_stats(arr)
            rows.append(["order_obs_nc", q, tag, 0, DT, p])
            rows.append(["extrap_p2", q, tag, 0, DT, e2])
            rows.append(["extrap_p1", q, tag, 0, DT, e1])
            print("   %s %s: Nc 方向观测阶 p=%.3f；外推区间 [%.4f, %.4f] h（p=2 下界 / p=1 上界）"
                  % (q, tag, p, e2, e1))
        gap = [(fe[i] - fv[i]) * 3600.0 for i in range(len(GRIDS))]
        for i, Nc in enumerate(GRIDS):
            rows.append(["gap", q, "FEM-FVM", Nc, DT, gap[i]])
        print("   %s 两解差 (s): " % q + "  ".join("Nc=%d:%+.2f" % (n, g)
                                                 for n, g in zip(GRIDS, gap)))
        print("   %s 生产格两解差 %+.2f s = %+.4f%%" % (q, gap[-1], 100.0 * (fe[-1] / fv[-1] - 1.0)))

    print("B) FEM 纯空间观测阶（expm 精确积分，分位置报告）")
    tmax = 20000.0
    for Nc in (25, 50, 100, 200, 400):
        C, rr = _cyl_exact_time(Nc, tmax)
        d = np.abs(C - cana(rr, tmax))
        rows.append(["order_fem_interior", "bench", "FEM", Nc, 0.0, float(np.max(d[1:-1]))])
        rows.append(["order_fem_wall", "bench", "FEM", Nc, 0.0, float(d[-1])])
        rows.append(["order_fem_axis", "bench", "FEM", Nc, 0.0, float(d[0])])
        print("   Nc=%-5d interior=%.4e wall=%.4e axis=%.4e"
              % (Nc, np.max(d[1:-1]), d[-1], d[0]))

    print("C) 金值逐位互证（同格同格式，两种离散）")
    g1f = solve1d(case=2, Nc=800, dt=0.05, tmax=1800.0, Ccr=-1.0)
    g1e = solve_fem(case=2, Nc=800, dt=0.05, tmax=1800.0, Ccr=-1.0)
    Ta, Ci = env(1800.0)
    Ta, Ci = float(Ta), float(np.ravel(Ci)[0])
    r1, c1, t1 = profile_ext(2, g1f["C"], g1f["T"], 800, g1f["Ri"], Ci, Ta)
    print("   Q1 t=1800 s 中心 T: FVM %.4f | FEM %.4f ℃"
          % (t1[0] - 273.15, g1e["T"][0] - 273.15))
    print("   Q1 t=1800 s 表面 T: FVM %.4f | FEM %.4f ℃"
          % (t1[-1] - 273.15, g1e["T"][-1] - 273.15))
    rows.append(["golden_q1_Tcenter", "Q1", "FVM", 800, 0.05, float(t1[0] - 273.15)])
    rows.append(["golden_q1_Tcenter", "Q1", "FEM", 800, 0.05, float(g1e["T"][0] - 273.15)])
    rows.append(["golden_q1_Tsurf", "Q1", "FVM", 800, 0.05, float(t1[-1] - 273.15)])
    rows.append(["golden_q1_Tsurf", "Q1", "FEM", 800, 0.05, float(g1e["T"][-1] - 273.15)])

    g2f = solve1d(case=3, Nc=800, dt=0.5, tmax=10800.0, Ccr=-1.0)
    Ta, Ci = env(10800.0)
    Ta, Ci = float(Ta), float(np.ravel(Ci)[0])
    cs_f = surfC(3, g2f["C"], g2f["T"], 800, g2f["Ri"], Ci)
    print("   Q2 t=3 h 中心 C: FVM %.4f" % g2f["C"][0])
    print("   Q2 t=3 h 表面 C: FVM(串联阻反解) %.6f" % cs_f)
    print("   Q2 t=3 h 中心 T: FVM %.4f ℃" % (g2f["T"][0] - 273.15))
    rows.append(["golden_q2_Ccenter", "Q2", "FVM", 800, 0.5, float(g2f["C"][0])])
    rows.append(["golden_q2_Csurf", "Q2", "FVM", 800, 0.5, float(cs_f)])
    # 表面值专项：FVM 靠串联阻两点反解，FEM 表面就是节点本身（不可再套反解，会二次外推）
    print("   Q2 t=3 h 表面 C 收敛（两侧离散互证：FVM 串联阻反解 ↔ FEM 节点值）")
    for Nc in (400, 800, 1600, 3200):
        of = solve1d(case=3, Nc=Nc, dt=0.5, tmax=10800.0, Ccr=-1.0)
        sf = surfC(3, of["C"], of["T"], Nc, of["Ri"], Ci)
        oe = solve_fem(case=3, Nc=Nc, dt=0.5, tmax=10800.0, Ccr=-1.0)
        se = float(oe["C"][-1])
        print("      Nc=%-5d FVM %.6f | FEM %.6f | 差 %+.2e" % (Nc, sf, se, se - sf))
        rows.append(["surf_conv", "Q2", "FVM", Nc, 0.5, float(sf)])
        rows.append(["surf_conv", "Q2", "FEM", Nc, 0.5, float(se)])
        rows.append(["surf_conv_center", "Q2", "FVM", Nc, 0.5, float(of["C"][-1])])

    with open(os.path.join(OUT, "fem_crosscheck.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "question", "method", "Nc", "dt", "value"])
        w.writerows(rows)
    print("\n-> fem_crosscheck.csv  %d 行" % len(rows))


# ====================================================================
# 来自 验证_回归测试.py
# ====================================================================
# 永久回归测试：解析解基准 + 观测收敛阶 + 四问金值
# 设计依据：经验卡《数值结果七类假象》——恒等式/常数态保持不算检验；
#           真有信息的是「观测收敛阶 / 多实现逐位互证 / 形式核验」三件。
import os
import sys
import numpy as np
from scipy.linalg import solve_banded
from scipy.special import j0, j1

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
os.environ.setdefault("HERB_SRC", os.path.join(_ROOT, "data", "raw"))

FAIL = []


def check(name, ok, detail):
    print(("  [PASS] " if ok else "  [FAIL] ") + name + "  " + detail)
    if not ok:
        FAIL.append(name)


# ---------- 恒定 Robin 圆柱的解析解（当基准前必须过自洽三关） ----------
_R, _HM, _C0, _L, _D = 0.02, 8.0e-7, 2.55, 0.25, 1.0e-9
_BI = _HM * _R / _D


def _roots(n):
    f = lambda m: m * j1(m) - _BI * j0(m)
    out = []
    for k in range(1, n + 1):
        lo, hi = 1e-9 + (k - 1) * np.pi, k * np.pi
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if f(lo) * f(mid) <= 0:
                hi = mid
            else:
                lo = mid
        out.append(0.5 * (lo + hi))
    return np.array(out)


_MU = _roots(3000)
_AN = 2 * j1(_MU) / (_MU * (j0(_MU) ** 2 + j1(_MU) ** 2))


def cana(r, t, nt=1500):
    rho = np.asarray(r, float) / _R
    out = np.zeros_like(np.asarray(r, float))
    fo = _D * t / _R ** 2
    for k in range(nt):
        out = out + _AN[k] * j0(_MU[k] * rho) * np.exp(-_MU[k] ** 2 * fo)
    return _C0 * out


def _cyl_robin(Nc, dt, tmax):
    xi, Vsh = make_grid(Nc)
    lf = face_logfac(Nc)
    Vi = np.pi * _L * _R ** 2 * Vsh
    xiN = 1.0 - 0.5 / Nc
    lnw = np.log(1.0 / xiN)
    Gf = 2 * np.pi * _L * _D * lf
    Gw = _wall_series(2 * np.pi * _L * _D / lnw, 2 * np.pi * _L * _R * _HM)
    Cc = np.full(Nc, _C0)
    t = 0.0
    while t < tmax - 1e-9:
        h = min(dt, tmax - t)
        ab, rhs = _assemble(Vi, Gf, (1.0 / h) * np.ones(Nc), Gw, 0.0, Cc)
        Cc = solve_banded((1, 1), ab, rhs)
        t += h
    return Cc, xi * _R


def test_analytic_gates():
    print("1) 解析解自洽三关（系数和 / 两端点极限）")
    s = _AN.sum()
    check("ΣA_n → 1", abs(s - 1.0) < 1e-4, "前 3000 项 ΣA_n = %.6f" % s)
    c0 = cana([0.0], 0.0)[0]
    check("t=0 中心 = C0", abs(c0 - _C0) < 5e-2, "C(0,0) = %.6f（应 %.2f）" % (c0, _C0))
    cl = cana([0.0], 1e7)[0]
    check("t→∞ 趋于 0", abs(cl) < 1e-30, "C(0,1e7) = %.3e" % cl)


def test_order():
    print("2) 观测空间收敛阶（恒定 Robin 圆柱 vs 解析解；dt-Richardson 消时间误差）")
    tmax = 20000.0
    ps = []
    prev = None
    for Nc in (25, 50, 100, 200, 400):
        C1, rr = _cyl_robin(Nc, 1.0, tmax)
        Ch, _ = _cyl_robin(Nc, 0.5, tmax)
        err = float(np.max(np.abs((2 * Ch - C1) - cana(rr, tmax))))
        if prev is not None:
            ps.append(np.log2(prev / err))
        print("     Nc=%-4d max|ΔC| = %.3e" % (Nc, err))
        prev = err
    p = float(np.mean(ps[1:]))
    check("观测空间阶 ≈ 2", 1.90 < p < 2.10, "p = %.4f（末尾三段均值）" % p)


def test_golden_q1():
    print("3) 金值 Q1（附录2，Nc=800，内步长 0.05 s，t=1800 s）")
    o = solve1d(case=2, Nc=800, dt=0.05, tmax=1800.0, Ccr=-1.0)
    Ta, Ci = env(1800.0)
    Ta, Ci = float(Ta), float(Ci)
    rr, Cx, Tx = profile_ext(2, o["C"], o["T"], 800, o["Ri"], Ci, Ta)
    tt = np.interp([0.0, 0.005, 0.010, 0.015, 0.020], rr, Tx) - 273.15
    cc = np.interp([0.0, 0.005, 0.010, 0.015, 0.020], rr, Cx)
    goldT = np.array([33.5754, 33.7721, 34.3642, 35.3622, 36.7856])
    goldC = np.array([2.5500, 2.5497, 2.5383, 2.3755, 1.5102])
    check("表1 末行", np.max(np.abs(tt - goldT)) < 5e-4,
          "T = " + " ".join("%.4f" % v for v in tt))
    check("表2 末行", np.max(np.abs(cc - goldC)) < 5e-5,
          "C = " + " ".join("%.4f" % v for v in cc))


def test_golden_q2():
    print("4) 金值 Q2（附录3，Nc=800，内步长 0.5 s，t=3 h）")
    o = solve1d(case=3, Nc=800, dt=0.5, tmax=10800.0, Ccr=-1.0)
    Ta, Ci = env(10800.0)
    Ta, Ci = float(Ta), float(Ci)
    Cs = surfC(3, o["C"], o["T"], 800, o["Ri"], Ci)
    check("表4 中心", abs(o["C"][0] - 1.7662) < 1e-4, "C_center = %.4f" % o["C"][0])
    check("表4 表面", abs(Cs - 1.0081) < 1e-4, "C_surf = %.4f" % Cs)
    check("表3 中心", abs((o["T"][0] - 273.15) - 49.8495) < 2e-3,
          "T_center = %.4f ℃" % (o["T"][0] - 273.15))


def test_golden_q34():
    print("5) 金值 Q3/Q4（Nc=1600，内步长 7.5 s，判据 max C ≤ 0.15）")
    o3 = solve1d(case=3, Nc=1600, dt=7.5, tmax=4.0e5, shrink=False,
                       Ccr=0.15, stop_at_hit=True)
    o4 = solve1d(case=4, Nc=1600, dt=7.5, tmax=4.0e5, shrink=True,
                       Ccr=0.15, stop_at_hit=True)
    check("Q3 t_d", abs(o3["td_h"] - 57.4755) < 0.02, "t_d = %.4f h" % o3["td_h"])
    check("Q4 t_d", abs(o4["td_h"] - 51.0958) < 0.02, "t_d = %.4f h" % o4["td_h"])
    check("Q4 R(t_d)", abs(o4["Ri"] * 100 - 1.2000) < 5e-4,
          "R(t_d) = %.5f cm" % (o4["Ri"] * 100))
    check("达标点恰在阈值", abs(o3["C"].max() - 0.15) < 2e-4,
          "max C(t_d) = %.6f" % o3["C"].max())


def test_constant_state():
    print("6) 常数态保持（弱必要条件：通量形式离散下自动成立，只作冒烟测试）")
    xi, Vsh = make_grid(100)
    lf = face_logfac(100)
    Vi = np.pi * 0.25 * 0.02 ** 2 * Vsh
    Gf = 2 * np.pi * 0.25 * 1e-9 * lf
    Gw = 1e-8
    C = np.full(100, 1.2345)
    ab, rhs = _assemble(Vi, Gf, (1.0 / 10.0) * np.ones(100), Gw, 1.2345, C)
    C2 = solve_banded((1, 1), ab, rhs)
    check("C ≡ const 原地不动", np.max(np.abs(C2 - C)) < 1e-12,
          "max|ΔC| = %.2e" % np.max(np.abs(C2 - C)))


# ====================================================================
# 来自 出图_数据总线.py
# ====================================================================
# 用法：python 出图_数据总线.py            全部
#       python 出图_数据总线.py q1 q3      只跑指定小节
import os
import sys
import csv
import json
import time
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
os.environ.setdefault("HERB_SRC", os.path.join(_ROOT, "data", "raw"))

OUT = os.path.join(_ROOT, "data", "processed", "figdata")
RG_CM = np.round(np.arange(0.0, 2.0001, 0.025), 4)   # 统一固定物理半径网格（cm）
RG_M = RG_CM / 100.0
CCR = 0.15


def dump(name, header, rows):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else ("%.6g" % v if isinstance(v, float) else v)
                        for v in r])
    print("    -> %-26s %d 行" % (name, len(rows)))


def _prof(C, T, Rw, Tamb, Cinf, case, Nc, mask=False):
    """单元中心剖面扩到表面 -> 统一固定物理网格插值；mask=True 时超出 R(t) 记 None"""
    rr, Cx, Tx = profile_ext(case, C, T, Nc, Rw, Cinf, Tamb)
    c = np.interp(RG_M, rr, Cx)
    t = np.interp(RG_M, rr, Tx) - 273.15
    if mask:
        out = RG_M > Rw + 1e-12
        c[out] = np.nan
        t[out] = np.nan
    return c, t


def _f(v):
    return None if (v is None or not np.isfinite(v)) else float(v)


def _on(t, step):
    """t 是否为 step 的整数倍（按步号判定，避开浮点累加误差）。"""
    return t >= 0.0 and abs(t - round(t / step) * step) < 1e-6


# ---------------- A. 环境与半径（动机证据） ----------------
def sec_a():
    print("A) 附件1 环境边界 + 附件2 半径轨迹")
    t1, Ta, Ca = load_att1()
    dump("env_att1.csv", ["t_s", "T_amb_C", "C_amb_kgkg"],
         [[float(a), float(b), float(c)] for a, b, c in zip(t1, Ta, Ca)])
    t2, R2 = load_att2()
    t2 = np.asarray(t2, float)
    R2 = np.asarray(R2, float)
    from scipy.optimize import curve_fit
    f = lambda t, a, b, tau: a + b * np.exp(-t / tau)
    p, cov = curve_fit(f, t2, R2, p0=[1.2, 0.8, 14000.0], maxfev=20000)
    sd = np.sqrt(np.diag(cov))
    tt = np.linspace(0.0, float(t2[-1]), 2000)
    dump("radius_att2.csv", ["t_s", "R_data_cm", "R_fit_cm"],
         [[float(a), float(b), ""] for a, b in zip(t2, R2)]
         + [[float(x), "", float(f(x, *p))] for x in tt])
    with open(os.path.join(OUT, "radius_fit.json"), "w", encoding="utf-8") as fh:
        json.dump({"form": "R(t) = a + b*exp(-t/tau) [cm]",
                   "a": float(p[0]), "b": float(p[1]), "tau_s": float(p[2]),
                   "sd": [float(x) for x in sd],
                   "T_plat_C": TA_PLAT, "C_plat_kgkg": CA_PLAT,
                   "att1_end_s": T1_END, "att2_end_s": T2_END},
                  fh, ensure_ascii=False, indent=2)
    print("    拟合 R(t) = %.4f + %.4f*exp(-t/%.1f) cm" % (p[0], p[1], p[2]))


# ---------------- B. 问题1 ----------------
def sec_q1():
    print("B) 问题1（case2, Nc=800, 内步长 0.05 s, 60 s 存剖面）")
    NC, DT, TMAX, EVERY = 800, 0.05, 1800.0, int(1.0 / 0.05)
    prof, ser = [], []

    def sampler(t, C, T, Rw, Tamb, Cinf):
        if _on(t, 30.0):
            c, tc = _prof(C, T, Rw, Tamb, Cinf, 2, NC)
            for j in range(RG_CM.size):
                prof.append([t, RG_CM[j], c[j], tc[j]])
        ser.append([t, C[0], surfC(2, C, T, NC, Rw, Cinf),
                    T[0] - 273.15, surfT(2, C, T, NC, Rw, Tamb) - 273.15])
        return None

    o = solve1d(case=2, Nc=NC, dt=DT, tmax=TMAX, shrink=False, Ccr=-1.0,
                      sampler=sampler, sample_every=EVERY)
    dump("q1_profiles.csv", ["t_s", "r_cm", "C", "T_C"], prof)
    dump("q1_series.csv", ["t_s", "C_center", "C_surf", "T_center_C", "T_surf_C"], ser)
    # 取最后一个采样时刻（t=1800 s）的 5 点剖面，即表1/表2 的末行
    end = [row for row in prof if row[0] == prof[-1][0]]
    return {"t_end_s": float(end[0][0]),
            "C_end": [round(float(row[2]), 6) for row in end],
            "T_end_C": [round(float(row[3]), 6) for row in end]}


# ---------------- C. 问题2 ----------------
def sec_q2():
    print("C) 问题2（case3, Nc=800, 内步长 0.5 s, 60 s 存剖面）")
    NC, DT, TMAX, EVERY = 800, 0.5, 259200.0, int(60 / 0.5)
    prof, ser = [], []

    def sampler(t, C, T, Rw, Tamb, Cinf):
        if _on(t, 300.0):
            c, tc = _prof(C, T, Rw, Tamb, Cinf, 3, NC)
            for j in range(RG_CM.size):
                prof.append([t, RG_CM[j], c[j], tc[j]])
        ser.append([t, C[0], surfC(3, C, T, NC, Rw, Cinf),
                    T[0] - 273.15, surfT(3, C, T, NC, Rw, Tamb) - 273.15])
        return None

    o = solve1d(case=3, Nc=NC, dt=DT, tmax=TMAX, shrink=False, Ccr=-1.0,
                      sampler=sampler, sample_every=EVERY)
    dump("q2_profiles.csv", ["t_s", "r_cm", "C", "T_C"], prof)
    dump("q2_series.csv", ["t_s", "C_center", "C_surf", "T_center_C", "T_surf_C"], ser)
    # 取最接近 t=3 h 的那一帧的 5 点剖面，即表3/表4 的末行。
    # 时间是累加出来的（t += h），存在浮点漂移，不能拿 == 10800.0 去筛。
    ts = np.array(sorted({row[0] for row in prof}))
    t3 = float(ts[np.argmin(np.abs(ts - 10800.0))])
    if abs(t3 - 10800.0) > 60.0:
        raise RuntimeError("q2 剖面里最接近 3 h 的帧在 %.1f s，采样间隔对不上" % t3)
    end = [row for row in prof if row[0] == t3]
    return {"t_3h_s": t3,
            "C_3h": [round(float(row[2]), 6) for row in end],
            "T_3h_C": [round(float(row[3]), 6) for row in end]}


# ---------------- D. 问题3 ----------------
def sec_q3():
    print("D) 问题3（case3, Nc=1600, 内步长 7.5 s, 300 s 存曲线, 6 h 存剖面）")
    NC, DT, EVERY = 1600, 7.5, int(300 / 7.5)
    prof, ser = [], []

    def sampler(t, C, T, Rw, Tamb, Cinf):
        if _on(t, 21600.0) or t > 2.05e5:
            c, _ = _prof(C, T, Rw, Tamb, Cinf, 3, NC)
            for j in range(RG_CM.size):
                prof.append([t, RG_CM[j], c[j]])
        ser.append([t, float(C.max()), C[0], surfC(3, C, T, NC, Rw, Cinf)])
        return None

    o = solve1d(case=3, Nc=NC, dt=DT, tmax=4.0e5, shrink=False, Ccr=CCR,
                      sampler=sampler, sample_every=EVERY, stop_at_hit=True)
    dump("q3_profiles_6h.csv", ["t_s", "r_cm", "C"], prof)
    dump("q3_maxC.csv", ["t_s", "C_max", "C_center", "C_surf"], ser)
    return {"td_h": o["td_h"], "t_hit_s": o["t_hit_s"]}


# ---------------- E. 问题4 ----------------
def sec_q4():
    print("E) 问题4（case4, Nc=1600, 内步长 7.5 s, 收缩, 超出 R(t) 记空）")
    NC, DT, EVERY = 1600, 7.5, int(300 / 7.5)
    prof, ser = [], []

    def sampler(t, C, T, Rw, Tamb, Cinf):
        if _on(t, 21600.0) or t > 1.8e5:
            c, _ = _prof(C, T, Rw, Tamb, Cinf, 4, NC, mask=True)
            for j in range(RG_CM.size):
                prof.append([t, RG_CM[j], _f(c[j])])
        ser.append([t, float(C.max()), Rw * 100.0])
        return None

    o = solve1d(case=4, Nc=NC, dt=DT, tmax=4.0e5, shrink=True, Ccr=CCR,
                      sampler=sampler, sample_every=EVERY, stop_at_hit=True)
    dump("q4_profiles_6h.csv", ["t_s", "r_cm", "C"], prof)
    dump("q4_maxC.csv", ["t_s", "C_max", "R_cm"], ser)
    return {"td_h": o["td_h"], "t_hit_s": o["t_hit_s"], "Ri_cm": o["Ri"] * 100.0}


# ---------------- F. 消融 2×2（几何 × 物性） ----------------
def sec_abl():
    print("F) 消融 2x2（几何 固定/收缩 × 物性 附录3/附录4）")
    out = {}
    for tag, case, shrink in (("a3_fix", 3, False), ("a4_fix", 4, False),
                              ("a3_shr", 3, True), ("a4_shr", 4, True)):
        t0 = time.time()
        # P4×固定 需 ~130 h，tmax 必须留足；取 8e5 s ≈ 222 h
        o = solve1d(case=case, Nc=1600, dt=7.5, tmax=8.0e5, shrink=shrink,
                          Ccr=CCR, stop_at_hit=True)
        if o["t_hit_s"] is None:
            raise RuntimeError("%s 在 tmax 内未达标，须提高 tmax" % tag)
        out[tag] = {"case": case, "shrink": bool(shrink),
                    "td_h": float(o["td_h"]), "t_hit_s": float(o["t_hit_s"]),
                    "Ri_cm": float(o["Ri"]) * 100.0, "wall_s": time.time() - t0}
        print("    %-7s case=%d shrink=%-5s t_d=%9.4f h  (%.0f s)"
              % (tag, case, shrink, o["td_h"], time.time() - t0))
    with open(os.path.join(OUT, "ablation.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


# ---------------- F2. 几何×物性 参数相图（λ 连续扫描） ----------------
def sec_plane():
    print("F2) 参数相图：λ ∈ {0,0.25,0.5,0.75,1} × 物性 {附录3, 附录4}")
    rows = []
    for case in (3, 4):
        for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
            t0 = time.time()
            # lam=0 走固定域路径，与消融的 a3_fix/a4_fix 完全一致
            o = solve1d(case=case, Nc=1600, dt=7.5, tmax=8.0e5,
                              shrink=(lam > 0.0), lam=lam, Ccr=CCR, stop_at_hit=True)
            if o["t_hit_s"] is None:
                raise RuntimeError("case=%d lam=%g 在 tmax 内未达标，须提高 tmax"
                                   % (case, lam))
            rows.append([case, lam, float(o["td_h"])])
            print("    case=%d lam=%.2f  t_d=%9.4f h  (%.0f s)"
                  % (case, lam, o["td_h"], time.time() - t0))
    dump("ablation_plane.csv", ["case", "lam", "td_h"], rows)
    return {"plane": [[float(c), float(l), float(t)] for c, l, t in rows]}


# ---------------- F3. 消融归因的网格无关性（固定 Δt，纯空间取细） ----------------
# 消融四格在生产口径上只给出 3 个倍数；把同一 Δt 下沿 Nc 重算，看的不是 t_d 本身而是
# 三个倍数是否随网格钉住——倍数若不随网格漂移，归因就是模型的性质而非离散的产物。
def sec_ablgrid():
    print("F3) 消融归因的网格无关性：Nc ∈ {200,400,800,1600}，Δt=7.5 s")
    rows = []
    for Nc in (200, 400, 800, 1600):
        t0 = time.time()
        cell = {}
        for tag, case, shrink in (("a3fix", 3, False), ("a3shr", 3, True),
                                  ("a4fix", 4, False), ("a4shr", 4, True)):
            o = solve1d(case=case, Nc=Nc, dt=7.5, tmax=8.0e5, shrink=shrink,
                              Ccr=CCR, stop_at_hit=True)
            if o["t_hit_s"] is None:
                raise RuntimeError("Nc=%d %s 在 tmax 内未达标" % (Nc, tag))
            cell[tag] = float(o["td_h"])
        G = cell["a3shr"] / cell["a3fix"]          # 几何倍数（收缩/固定）
        P = cell["a4fix"] / cell["a3fix"]          # 物性倍数（附录4/附录3）
        I = cell["a4shr"] / (cell["a3fix"] * G * P)  # 交互因子（实测/无交互预测）
        rows.append([Nc, 7.5, cell["a3fix"], cell["a3shr"], cell["a4fix"],
                     cell["a4shr"], G, P, I])
        print("    Nc=%-5d 几何=%.6f 物性=%.6f 交互=%.6f  (%.0f s)"
              % (Nc, G, P, I, time.time() - t0))
    dump("ablation_grid.csv",
         ["Nc", "dt", "td_a3fix", "td_a3shr", "td_a4fix", "td_a4shr",
          "G_geo", "P_prop", "I_int"], rows)
    return {"ablation_grid": [[float(v) for v in r] for r in rows]}


# ---------------- F4. 交互的机理：内部降幅占比随收缩幅度 ----------------
# 在"轴心含水率相同"的状态下比较各 λ 的剖面（同一状态才可比，不按同一钟表时间比）：
# 收缩使扩散路程变短 ⇒ 内部降幅占总降幅的比例下降 ⇒ 走内部输运的物性差异被冲淡。
# 这正是物性劣势倍率随 λ 单调衰减的机制。φ = (C_core − C_surf)/(C_core − C_inf)。
def sec_ablprof():
    print("F4) 交互机理：λ=0…1 的径向剖面与内部降幅占比（共同轴心状态）")
    CMID, NN = 1.0, 41
    rows = []
    for case in (3, 4):
        for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
            t0 = time.time()
            box = {}

            def sampler(t, C, T, Rw, Tamb, Cinf, _b=box, _c=case):
                if "prof" not in _b and float(np.max(C)) <= CMID:
                    rr, Cx, _ = profile_ext(_c, C, T, len(C), Rw, Cinf, Tamb)
                    _b["prof"] = (t, float(np.max(C)), float(Cx[-1]),
                                  float(Cinf), float(Rw), rr, Cx)
                return None

            o = solve1d(case=case, Nc=1600, dt=7.5, tmax=8.0e5,
                              shrink=(lam > 0.0), lam=lam, Ccr=CCR,
                              sampler=sampler, sample_every=int(300 / 7.5),
                              stop_at_hit=True)
            if "prof" not in box:
                raise RuntimeError("case=%d lam=%g 未捕捉到轴心 ≤ %.2f"
                                   % (case, lam, CMID))
            t_c, cmax, cs, cinf, Rw, rr, Cx = box["prof"]
            phi = (cmax - cs) / (cmax - cinf)
            rq = np.linspace(0.0, Rw, NN)
            cq = np.interp(rq, rr, Cx)
            rows.append([case, lam, t_c / 3600.0, cmax, cs, cinf, phi,
                         float(o["td_h"]), Rw * 100.0] + [float(v) for v in cq])
            print("    case=%d λ=%.2f  t=%.2f h  轴心=%.4f 表面=%.4f  φ=%.4f"
                  "  t_d=%.4f h  (%.0f s)"
                  % (case, lam, t_c / 3600.0, cmax, cs, phi, o["td_h"],
                     time.time() - t0))
    dump("ablation_profile.csv",
         ["case", "lam", "t_h", "C_core", "C_surf", "C_inf", "phi", "td_h",
          "R_cm"] + ["C%02d" % i for i in range(NN)], rows)
    return {"ablation_profile": [[v if isinstance(v, str) else float(v)
                                 for v in r] for r in rows]}


# ---------------- F5. κ 情景扫描（环境含湿量缩放） ----------------
def sec_kap():
    """κ 扫描环境含湿量 C∞·κ。κ 足够大时平台含湿量本身越过达标线 0.15，
    边界条件与判据冲突 ⇒ 干燥不可能达标，t_d 发散。临界点可解析算出：
    κ_crit = Ccr / C∞(平台)，无需扫描即可定位，扫描只用来展示逼近行为。"""
    print("F3) κ 情景扫描（环境含湿量缩放，case3 固定域）")
    kcrit = CCR / float(CA_PLAT)
    print("    κ_crit = %.5f / %.5f = %.6f" % (CCR, CA_PLAT, kcrit))
    # κ 越靠近 κ_crit 曲线越陡，网格在 2.8 之后加密，否则渐近段会画不出来
    kaps = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.4, 2.7,
            2.85, 2.92, 2.96, 2.98, 2.99, 2.995]
    tmax = 2.0e6                     # ≈ 555 h，超出即记为"未达"，本身就是发散证据
    rows = []
    for k in kaps:
        t0 = time.time()
        o = solve1d(case=3, Nc=1600, dt=7.5, tmax=tmax, shrink=False,
                          kappa=k, Ccr=CCR, stop_at_hit=True)
        td = None if o["t_hit_s"] is None else float(o["td_h"])
        rows.append([k, "" if td is None else td, 1 if td is None else 0])
        print("    κ=%-6.3f  t_d=%s  (%.0f s)"
              % (k, "未达标(>%.0f h)" % (tmax / 3600.0) if td is None
                 else "%9.4f h" % td, time.time() - t0))
    dump("kappa_scan.csv", ["kappa", "td_h", "censored"], rows)
    return {"kappa_crit": kcrit,
            "kappa": [float(r[0]) for r in rows],
            "kappa_td_h": [None if r[1] == "" else float(r[1]) for r in rows]}


# ---------------- F6. 消融四格的完整时空场（几何效应 = 域内缩留下的空楔形） ----------------
# 四格各采一条走到达标为止的时空场，沿统一物理半径网格（RG_CM）输出；收缩域两格把
# 超出 R(t) 的节点记空（_prof 的 mask=True）。于是"几何收缩"这件事在图上一句话都不用写：
# 它表现为右侧一块随 τ=t/t_d 逐渐加宽的空楔形，四格共用同一半径轴，可直接比。
def sec_ablfield():
    print("F6) 消融四格时空场：Nc=800, Δt=15 s, 采样 0.5 h")
    NC, DT, TSTEP = 800, 15.0, 1800.0
    EVERY = int(TSTEP / DT)
    rows, meta, edge = [], [], []
    for tag, case, shrink in (("a3fix", 3, False), ("a3shr", 3, True),
                              ("a4fix", 4, False), ("a4shr", 4, True)):
        t0 = time.time()
        buf = []

        def sampler(t, C, T, Rw, Tamb, Cinf, _c=case, _s=shrink, _b=buf):
            c, _ = _prof(C, T, Rw, Tamb, Cinf, _c, NC, mask=_s)
            _b.append((t, Rw, c))
            return None

        o = solve1d(case=case, Nc=NC, dt=DT, tmax=8.0e5, shrink=shrink,
                          Ccr=CCR, sampler=sampler, sample_every=EVERY,
                          stop_at_hit=True)
        if o["t_hit_s"] is None:
            raise RuntimeError("%s 在 tmax 内未达标，须提高 tmax" % tag)
        td = float(o["t_hit_s"])
        for t, Rw, c in buf:
            edge.append([tag, case, int(shrink), t, t / td, Rw * 100.0])
            for j in range(RG_CM.size):
                rows.append([tag, case, int(shrink), t, t / td, RG_CM[j],
                             _f(c[j])])
        meta.append([tag, case, int(shrink), float(o["td_h"]), Rw * 100.0,
                     float(buf[-1][0]) / td])
        print("    %-6s t_d=%9.4f h  采样 %d 帧  末帧 τ=%.6f  壁面 R=%.4f cm"
              "  (%.0f s)" % (tag, o["td_h"], len(buf), buf[-1][0] / td,
                              Rw * 100.0, time.time() - t0))
    dump("ablation_field.csv",
         ["tag", "case", "shrink", "t_s", "tau", "r_cm", "C"], rows)
    dump("ablation_field_meta.csv",
         ["tag", "case", "shrink", "td_h", "R_end_cm", "tau_end"], meta)
    dump("ablation_field_edge.csv",
         ["tag", "case", "shrink", "t_s", "tau", "Rw_cm"], edge)
    return {"ablfield": [[r[0], int(r[1]), int(r[2]), float(r[3]), float(r[4]),
                          float(r[5]), None if r[6] is None else float(r[6])]
                         for r in rows]}


# ---------------- F7. 固定域成本景观 t_d(R, Ccr)（准静态预测的参照面） ----------------
# 半径不是 solve1d 的形参，而是模块级 R0；这里只在驱动脚本里临时改写 R0，
# 不改任何源文件（与 _push_props 同一套"临时缩放"惯例），用完 finally 还原。
# R=2.0 cm、Ccr=0.15 两列即消融的 a3fix/a4fix，用来当场验算景观与生产口径是否接得上。
def sec_ablland():
    print("F7) 固定域成本景观 t_d(R, Ccr)：R×Ccr × 物性")
    RR = (1.2, 1.4, 1.6, 1.8, 2.0)
    CC = (0.15, 0.25, 0.35, 0.45)
    rows = []
    keep = R0
    try:
        for case in (3, 4):
            for R in RR:
                R0 = R / 100.0
                for cr in CC:
                    t0 = time.time()
                    o = solve1d(case=case, Nc=400, dt=15.0, tmax=8.0e5,
                                      shrink=False, Ccr=cr, stop_at_hit=True)
                    if o["t_hit_s"] is None:
                        raise RuntimeError("case=%d R=%.4f Ccr=%.2f 未达标"
                                           % (case, R, cr))
                    rows.append([case, R, cr, float(o["td_h"])])
                    print("    case=%d R=%.4f cm Ccr=%.2f  t_d=%9.4f h  (%.0f s)"
                          % (case, R, cr, o["td_h"], time.time() - t0))
    finally:
        R0 = keep
    dump("ablation_landscape.csv", ["case", "R_cm", "Ccr", "td_h"], rows)
    ref = {3: 57.4755, 4: 129.8492}
    for case in (3, 4):
        got = [r[3] for r in rows if r[0] == case and r[1] == 2.0 and r[2] == 0.15][0]
        print("    接口验算 case=%d R=2.0 Ccr=0.15: 景观 %.4f h vs 消融 %.4f h"
              "  相对差 %.4f%%" % (case, got, ref[case],
                                  (got - ref[case]) / ref[case] * 100.0))
    return {"ablland": [[int(c), float(R), float(cr), float(t)]
                        for c, R, cr, t in rows]}


# ---------------- G. 灵敏度 S_p（±5%） ----------------
def sec_sens():
    print("G) 灵敏度（±5%，Nc=1600，内步长 7.5 s）")
    rows = []
    cases = [("q3", 3, False, ["D", "hm", "h"]),
             ("q4", 4, True, ["D", "hm", "h", "lam"])]
    for qn, case, shrink, keys in cases:
        t0 = time.time()
        o = solve1d(case=case, Nc=1600, dt=7.5, tmax=4.0e5, shrink=shrink,
                          Ccr=CCR, stop_at_hit=True)
        td0 = float(o["td_h"])
        rows.append([qn, "base", 0.0, td0, ""])
        print("    %s base           t_d=%9.4f h" % (qn, td0))
        for k in keys:
            vals = {}
            for sgn, f in ((-1, 0.95), (+1, 1.05)):
                _save, _ = _push_props(k, f)
                try:
                    oo = solve1d(case=case, Nc=1600, dt=7.5, tmax=4.0e5,
                                       shrink=shrink, Ccr=CCR, stop_at_hit=True,
                                       lam=(f if k == "lam" else 1.0))
                finally:
                    _restore_props(k, _save)
                vals[sgn] = float(oo["td_h"])
            S = np.log(vals[+1] / vals[-1]) / np.log(1.05 / 0.95)
            rows.append([qn, k, -5.0, vals[-1], ""])
            rows.append([qn, k, +5.0, vals[+1], "%.4f" % S])
            print("    %s %-4s -5%%=%9.4f  +5%%=%9.4f   S_p=%+.4f"
                  % (qn, k, vals[-1], vals[+1], S))
        print("    （%s 段用时 %.0f s）" % (qn, time.time() - t0))
    dump("sensitivity.csv", ["question", "param", "delta_pct", "td_h", "S_p"], rows)


def _push_props(k, f):
    """临时缩放物性/系数：D 乘 f、h_m 乘 f、h 乘 f；返回原值供还原。"""
    if k == "D":
        orig = props
        def patched(case, C, Tk):
            rho, cp, kk, D = orig(case, C, Tk)
            return rho, cp, kk, D * f
        props = patched
        props = patched
        return orig, None
    if k == "hm":
        orig_h, orig_hm = HM, HM
        HM = orig_h * f
        HM = orig_hm * f
        return (orig_h, orig_hm), None
    if k == "h":
        orig_h, orig_q = H_Q, H_Q
        H_Q = orig_h * f
        H_Q = orig_q * f
        return (orig_h, orig_q), None
    if k == "lam":
        return None, None      # lam 由 solve1d 形参直接传，无需打补丁
    return None, None


def _restore_props(k, saved):
    if k == "D" and saved is not None:
        props = saved
        props = saved
    elif k == "hm" and saved is not None:
        HM, HM = saved
    elif k == "h" and saved is not None:
        H_Q, H_Q = saved


# ---------------- H. 控制点自创指标 Γ_* / Ψ_*（两个口径各落一文件） ----------------
# Γ_* = α/D 描述烘干过程本身，取问题三正式解（附录3、固定域）；
# Ψ_* = (R/R0)^2 · D3/D4 描述问题三→问题四的竞争，取问题四收缩域轨迹。
# 两指标状态轨迹不同，故分文件落盘，杜绝"同一量两条算路"。
def sec_gp():
    print("H) 控制点指标：Γ_* 取 Q3 正式解、Ψ_* 取 Q4 收缩域轨迹")
    NC, DT, EVERY = 1600, 7.5, int(300 / 7.5)

    rows3 = []

    def sampler(t, C, T, Rw, Tamb, Cinf):
        i = int(np.argmax(C))
        rho, cp, kk, D = props(3, C, T)
        G = (kk / (rho * cp)) / D
        _, _, _, D3 = props(3, C, T)
        _, _, _, D4 = props(4, C, T)
        rows3.append([t, float(G[i]), float(C[i]), float(T[i]) - 273.15,
                      float(Rw) * 100.0, float(D[i]) * 1e9, float(D3[i] / D4[i])])
        return None

    o3 = solve1d(case=3, Nc=NC, dt=DT, tmax=4.0e5, shrink=False, Ccr=CCR,
                       sampler=sampler, sample_every=EVERY, stop_at_hit=True)
    dump("gammapsi_q3.csv",
         ["t_s", "Gamma_star", "C_star", "T_star_C", "R_cm", "D1e9", "D3_over_D4"],
         rows3)

    rows4 = []

    def sampler4(t, C, T, Rw, Tamb, Cinf):
        i = int(np.argmax(C))
        _, _, _, D3 = props(3, C, T)
        _, _, _, D4 = props(4, C, T)
        P = (Rw / R0) ** 2 * (D3 / D4)
        rows4.append([t, float(P[i]), float(C[i]), float(T[i]) - 273.15,
                      float(Rw) * 100.0, float(D3[i] / D4[i])])
        return None

    o4 = solve1d(case=4, Nc=NC, dt=DT, tmax=4.0e5, shrink=True, Ccr=CCR,
                       sampler=sampler4, sample_every=EVERY, stop_at_hit=True)
    dump("gammapsi_q4.csv",
         ["t_s", "Psi_star", "C_star", "T_star_C", "R_cm", "D3_over_D4"], rows4)
    return {"td_h_q3": o3["td_h"], "td_h_q4": o4["td_h"]}


# ---------------- H. 收敛性（空间观测阶 + 时间观测阶） ----------------
def sec_conv():
    """恒定 Robin 圆柱 vs 解析解。空间阶必须先用 dt 做 Richardson（2C_{h/2}−C_h）
    消掉一阶时间误差，否则量到的是时间阶，不是空间阶；时间阶则固定 Nc 直接比。"""
    print("H) 收敛性：空间观测阶（Richardson 消时间误差）+ 时间观测阶")
    tmax = 20000.0
    rows = []
    for Nc in (25, 50, 100, 200, 400):
        C1, rr = _cyl_robin(Nc, 1.0, tmax)
        Ch, _ = _cyl_robin(Nc, 0.5, tmax)
        rows.append(["space", float(Nc), float(np.max(np.abs((2 * Ch - C1) - cana(rr, tmax))))])
    for dtv in (4.0, 2.0, 1.0, 0.5, 0.25):
        Ct, rr = _cyl_robin(200, dtv, tmax)
        rows.append(["time", float(dtv), float(np.max(np.abs(Ct - cana(rr, tmax))))])
    for kind, x, e in rows:
        print("    %-5s x=%-6.4g err=%.4e" % (kind, x, e))
    dump("convergence.csv", ["kind", "x", "err"], rows)
    # 二维联合视图：把两个离散方向联立成 (Nc, dt) 网格，供误差曲面图读取。
    # 网格比一维族多两档 Nc 与一档 dt，故另存为高精度文件（%.8e），不与上面的 %.6g 混用。
    grid = []
    for Nc in (25, 50, 100, 200, 400, 800, 1600):
        for dtv in (8.0, 4.0, 2.0, 1.0, 0.5, 0.25):
            Cg, rr = _cyl_robin(Nc, dtv, tmax)
            grid.append((Nc, dtv, float(np.max(np.abs(Cg - cana(rr, tmax))))))
    with open(os.path.join(OUT, "cand_surface.csv"), "w", newline="", encoding="utf-8") as f:
        f.write("Nc,dt,err\n")
        for Nc, dtv, e in grid:
            f.write("%d,%s,%.8e\n" % (Nc, dtv, e))
    print("    -> %-26s %d 行" % ("cand_surface.csv", len(grid)))
    return {"conv": [[k, float(x), float(e)] for k, x, e in rows]}


SECTIONS = {"a": sec_a, "q1": sec_q1, "q2": sec_q2, "q3": sec_q3, "q4": sec_q4,
            "abl": sec_abl, "plane": sec_plane, "kap": sec_kap,
            "ablgrid": sec_ablgrid, "ablprof": sec_ablprof,
            "ablfield": sec_ablfield, "ablland": sec_ablland,
            "sens": sec_sens, "gp": sec_gp, "conv": sec_conv}


def 出图数据():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    keys = ([a.lower() for a in sys.argv[1:]]
            or ["a", "q1", "q2", "q3", "q4", "abl", "plane", "kap", "sens", "gp"])
    # 合并而非覆盖：分段补跑（如只跑 kap）时不至于把已算好的其它节摘要抹掉，
    # 否则"最后跑的那一节"就是摘要的全部内容，很容易误读成整条链的结论。
    sp = os.path.join(OUT, "figdata_summary.json")
    res = {}
    if os.path.isfile(sp):
        try:
            with open(sp, encoding="utf-8") as f:
                res = json.load(f)
        except ValueError:
            print("警告：旧 figdata_summary.json 解析失败，改为重建")
            res = {}
    for k in keys:
        if k not in SECTIONS:
            print("未知小节 %s（可选 %s）" % (k, " ".join(SECTIONS)))
            continue
        t0 = time.time()
        r = SECTIONS[k]()
        if r is not None:
            res[k] = r
        print("    (%s 用时 %.0f s)" % (k, time.time() - t0))
        with open(sp, "w", encoding="utf-8") as f:
            # 各段返回值可能带 numpy 标量/单元素数组，default=float 会栽在数组上
            json.dump(res, f, ensure_ascii=False, indent=2,
                      default=lambda o: float(np.asarray(o).ravel()[0]))
    print("\n数据输出目录：%s" % OUT)


# ====================================================================
# 来自 敏感性_蒙特卡洛.py
# ====================================================================
# 参数不确定度的蒙特卡洛传播：D、h_m、h、λ 各自独立服从 U(0.95, 1.05)，
# 各问采样 N 次，用生产配置（Nc=1600、Δt=7.5 s）逐个正解，多进程并行。
# 口径声明：±5% 在此读作参数的“可能范围”而非某一置信水平的区间。
# 输出 figdata/mc_sensitivity.csv 与 figdata/mc_sensitivity_summary.json。
import os
import sys
import csv
import json
import time

# 必须在 import numpy/scipy 之前锁定 BLAS 线程数：本机可用物理内存仅约 3 GB，
# 默认多线程 BLAS 会让每个 worker 进程预留大量线程栈，多个 worker 并发加载时
# 提交内存击穿页面文件，报 WinError 1455（页面文件太小）/ scipy DLL 加载失败。
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
os.environ.setdefault("HERB_SRC", os.path.join(_ROOT, "data", "raw"))

RES = os.path.join(_ROOT, "data", "processed", "figdata")
NC, DT, CCR, TMAX = 1600, 7.5, 0.15, 4.0e5
NMC = 500
SEED = 20260912
LOW, HIGH = 0.95, 1.05

MC_CASES = {"q3": {"case": 3, "shrink": False, "keys": ["D", "hm", "h"]},
         "q4": {"case": 4, "shrink": True, "keys": ["D", "hm", "h", "lam"]}}
QLAB = {"q3": "问题三（固定域）", "q4": "问题四（收缩域）"}


def _run_one(arg):
    qn, sid, fac = arg
    spec = MC_CASES[qn]
    saved = []
    if "D" in fac:
        orig = props
        fD = fac["D"]

        def patched(case, C, Tk, _o=orig, _f=fD):
            rho, cp, kk, D = _o(case, C, Tk)
            return rho, cp, kk, D * _f

        props = patched
        props = patched
        saved.append(("D", orig))
    if "hm" in fac:
        oh, ohm = HM, HM
        HM = oh * fac["hm"]
        HM = ohm * fac["hm"]
        saved.append(("hm", (oh, ohm)))
    if "h" in fac:
        oq, oqq = H_Q, H_Q
        H_Q = oq * fac["h"]
        H_Q = oqq * fac["h"]
        saved.append(("h", (oq, oqq)))
    try:
        o = solve1d(case=spec["case"], Nc=NC, dt=DT, tmax=TMAX,
                          shrink=spec["shrink"], Ccr=CCR, stop_at_hit=True,
                          lam=float(fac.get("lam", 1.0)))
        td = None if o["t_hit_s"] is None else float(o["td_h"])
    finally:
        for k, v in reversed(saved):
            if k == "D":
                props = v
                props = v
            elif k == "hm":
                HM, HM = v
            elif k == "h":
                H_Q, H_Q = v
    return qn, sid, dict(fac), td


def 敏感性():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else NMC
    rng = np.random.default_rng(SEED)
    tasks = []
    for qn, spec in MC_CASES.items():
        for sid in range(n_target):
            fac = {k: float(rng.uniform(LOW, HIGH)) for k in spec["keys"]}
            tasks.append((qn, sid, fac))
    # 本机可用物理内存约 3 GB（页面文件 5.6 GB 自动管理）：每个 worker 加载
    # numpy/scipy 约 150 MB，故并行上限取 8；再高会触发 WinError 1455（页面文件太小）。
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    print("蒙特卡洛：%d 任务（每问 %d）× 生产配置 Nc=%d, dt=%g s"
          % (len(tasks), n_target, NC, DT))
    print("扰动分布：各参数独立 U(%.2f, %.2f)，种子 %d，并行 %d 进程"
          % (LOW, HIGH, SEED, nproc))
    t0 = time.time()
    res = []
    with Pool(nproc) as pool:
        for n, r in enumerate(pool.imap_unordered(_run_one, tasks), 1):
            res.append(r)
            if n % 50 == 0 or n == len(tasks):
                el = time.time() - t0
                print("  %4d/%d  已用 %5.1f min  预计总 %5.1f min"
                      % (n, len(tasks), el / 60.0, el / n * len(tasks) / 60.0))
    res.sort(key=lambda r: (r[0], r[1]))

    keys = sorted({k for _, _, fac, _ in res for k in fac})
    path = os.path.join(RES, "mc_sensitivity.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["question", "sample_id"] + ["f_" + k for k in keys] + ["td_h"])
        for qn, sid, fac, td in res:
            w.writerow([qn, sid] + ["%.6f" % fac[k] if k in fac else ""
                                    for k in keys]
                       + ["" if td is None else "%.6f" % td])

    summary = {}
    for qn in MC_CASES:
        v = np.array([r[3] for r in res if r[0] == qn and r[3] is not None])
        if v.size == 0:
            continue
        qs = np.percentile(v, [2.5, 5, 50, 95, 97.5])
        summary[qn] = {
            "label": QLAB[qn], "n": int(v.size),
            "mean_h": round(float(v.mean()), 4), "sd_h": round(float(v.std(ddof=1)), 4),
            "median_h": round(float(qs[2]), 4), "min_h": round(float(v.min()), 4),
            "max_h": round(float(v.max()), 4),
            "ci95_h": [round(float(qs[0]), 4), round(float(qs[4]), 4)],
            "ci90_h": [round(float(qs[1]), 4), round(float(qs[3]), 4)],
            "w95_h": round(float(qs[4] - qs[0]), 4),
            "rel_w95_pct": round(float((qs[4] - qs[0]) / qs[2] * 100.0), 4)}
        s = summary[qn]
        print("  %s  n=%d  中位 %.4f h  95%%区间 [%.4f, %.4f]  宽 %.4f h (%.2f%%)"
              % (QLAB[qn], s["n"], s["median_h"], s["ci95_h"][0], s["ci95_h"][1],
                 s["w95_h"], s["rel_w95_pct"]))
    with open(os.path.join(RES, "mc_sensitivity_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump({"N": n_target, "seed": SEED,
                   "dist": "U(%.2f,%.2f)" % (LOW, HIGH),
                   "Nc": NC, "dt": DT, "Ccr": CCR, "params": keys,
                   "result": summary}, f, ensure_ascii=False, indent=2)
    print("总用时 %.1f min -> %s" % ((time.time() - t0) / 60.0, path))


# ====================================================================
# 来自 一键复现.py
# ====================================================================
# 一键复现：四问结果文件 + 表1~表6 + 回归测试
# 用法：python 一键复现.py          （全跑，约 3~5 分钟）
#       python 一键复现.py q1 q3    （只跑指定问）
import os
import sys
import runpy
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
DRIVERS = {
    "q1": os.path.join(_ROOT, "代码", "第一问.py"),
    "q2": os.path.join(_ROOT, "代码", "第二问.py"),
    "q3": os.path.join(_ROOT, "代码", "第三问.py"),
    "q4": os.path.join(_ROOT, "代码", "第四问.py"),
}


def run_script(path):
    t0 = time.time()
    ns = {"__name__": "__main__", "__file__": path}
    runpy.run_path(path, run_name="__main__")
    print("   ... %s 用时 %.1f s" % (os.path.basename(path), time.time() - t0))


def 一键复现():
    keys = [a.lower() for a in sys.argv[1:]] or list(DRIVERS)
    for k in keys:
        if k not in DRIVERS:
            print("未知任务 %s（可选 %s）" % (k, " ".join(DRIVERS)))
            continue
        print("\n" + "=" * 72)
        print("运行 %s" % DRIVERS[k])
        print("=" * 72)
        run_script(DRIVERS[k])
    if not sys.argv[1:]:
        print("\n" + "=" * 72)
        print("回归测试")
        print("=" * 72)
        回归测试()


def 回归测试():
        print("=" * 72)
        print("回归测试：解析解基准 / 观测收敛阶 / 四问金值")
        print("=" * 72)
        test_analytic_gates()
        test_order()
        test_golden_q1()
        test_golden_q2()
        test_golden_q34()
        test_constant_state()
        print("=" * 72)
        if FAIL:
            print("结果：%d 项未通过 -> %s" % (len(FAIL), "; ".join(FAIL)))
            sys.exit(1)
        print("结果：全部通过")


if __name__ == "__main__":
    a = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    if a in ("fig", "出图数据"):
        出图数据()
    elif a in ("mc", "敏感性"):
        敏感性()
    elif a in ("reg", "回归测试"):
        回归测试()
    elif a in ("xc", "交叉对拍"):
        交叉对拍()
    elif a in ("all", "一键复现", ""):
        一键复现()
    else:
        print("用法：python 公共.py [all|fig|mc|reg|xc]")
