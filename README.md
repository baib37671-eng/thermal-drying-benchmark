# 圆柱物料热湿耦合干燥模型：干燥终点预测与收缩一致性

径向热湿耦合有限体积模型，用于预测圆柱物料在 convective drying 过程中的干燥终点（局部含水率达标时刻），并量化物性、几何收缩、环境边界与达标判据对终点的影响。

配套论文：《基于热湿耦合模型的圆柱物料干燥终点预测与收缩一致性分析》

## 仓库内容

```
.
├── data/
│   ├── raw/                  原始输入（不可修改）
│   │   ├── 附件1.xlsx         环境温度与有效含水率边界记录（0–4 h，60 s 采样）
│   │   └── 附件2.xlsx         半径收缩轨迹（0–72 h，1800 s 采样）
│   └── processed/            派生数据（论文表格与图形的数值来源）
│       ├── figdata/          49 个中间算例 CSV（收敛性、消融、剖面、敏感性等）
│       ├── results/          四组主算例汇总与论文表格数值
│       ├── numeric_facts.json 机器重算的数值事实表
│       ├── mc_ensemble.csv    512 成员蒙特卡洛集合
│       ├── morris_screen.csv  Morris 全局筛选
│       ├── strict_closure.csv 干质量严格闭合检验
│       └── boundary_extrapolation.csv 记录后边界延拓情景
├── src/
│   └── 公共.py                有限体积求解器本体（物性、装配、时间推进、终点事件）
├── scripts/
│   ├── 第一问.py ~ 第四问.py   四组主算例的驱动脚本
│   ├── verify_solver_endpoints.py  求解器探针（先跑这个）
│   ├── boundary_extrapolation.py   边界延拓敏感性
│   ├── mc_ensemble.py              蒙特卡洛集合
│   ├── morris_screen.py            Morris 全局筛选
│   ├── strict_closure.py           干质量闭合
│   ├── build_facts.py              由源数据重算数值事实表
│   ├── figures_ts.R / fig_sensitivity.R / 出图_R绘制.R   R 出图
│   └── fig18_ts.m / figs_matlab.m   MATLAB 出图
└── results/                  脚本运行输出（默认不纳入版本控制）
```

## 环境

```bash
pip install -r requirements.txt
```

R 图形依赖：`ggplot2`、`patchwork`、`showtext`、`jsonlite`、`dplyr`、`scales`、`ragg`

MATLAB 图形依赖：R2021a 或更新（`exportgraphics`）

## 复现步骤

**1. 先验证求解器**（约 30 s，逐位复现两个基准端点 57.475473 h / 51.095835 h）：

```bash
python scripts/verify_solver_endpoints.py
```

**2. 四组主算例**：

```bash
python scripts/第一问.py      # 预热阶段（0–1800 s）
python scripts/第二问.py      # 全过程 + 冻结物性对照
python scripts/第三问.py      # 定半径构型的达标时长
python scripts/第四问.py      # 收缩构型的达标时长
```

结果写入 `results/q1` … `results/q4`。

**3. 论文中的全局分析**：

```bash
python scripts/boundary_extrapolation.py   # 记录后边界延拓（约 30 次算例）
python scripts/morris_screen.py            # Morris 筛选（约 24 min）
python scripts/mc_ensemble.py 512          # 蒙特卡洛集合（耗时较长）
python scripts/strict_closure.py           # 干质量闭合
python scripts/build_facts.py              # 重算数值事实表
```

**4. 出图**：

```bash
Rscript scripts/figures_ts.R
Rscript scripts/fig_sensitivity.R
# MATLAB: run scripts/fig18_ts.m
```

所有脚本按自身位置定位仓库根目录，可在任意路径下克隆运行。图像输出到 `results/figures/`。

## 数据说明

- `data/raw/` 是论文的原始输入，脚本只读不写。
- `data/processed/` 是已经跑出来的结果，可直接用于核对论文表格；重跑脚本会在 `results/` 下生成新副本。
- 扩散系数、热物性随温度与含水率变化的经验关系来自 `附件1.xlsx` 所在题面，代码中集中定义在 `src/公共.py` 的 `props()`。

## 引用

```bibtex
@article{thermal_drying_2026,
  author  = {夏天宇},
  title   = {基于热湿耦合模型的圆柱物料干燥终点预测与收缩一致性分析},
  year    = {2026}
}
```
