# 数据说明

## raw/ — 原始输入（只读）

| 文件 | 内容 | 时间范围 | 采样 |
|---|---|---|---|
| 附件1.xlsx | 环境温度 `T_amb` 与有效含水率边界值 `C_amb` | 0–4 h | 60 s（241 点） |
| 附件2.xlsx | 物料半径 `R` | 0–72 h | 1800 s（145 点） |

圆柱几何：初始半径 `R0 = 0.02 m`，长度 `L = 0.25 m`；初温 28 °C，初始干基含水率 2.55 kg/kg；达标判据 `max_r C <= 0.15 kg/kg`。

## processed/ — 派生数据

- `figdata/`：49 个算例中间结果，论文中所有曲线、剖面与收敛性数据均从这里读取。
- `results/`：四组主算例的汇总（`qN_summary.json`）与论文表格数值（`表N_*.csv`）。
- `numeric_facts.json`：由 `scripts/build_facts.py` 从源数据机器重算的数值事实表，记录每个数的来源文件与算法。
- `mc_ensemble.*`、`morris_screen.*`、`strict_closure.*`、`boundary_extrapolation.*`：论文第 5、6 章的不确定性分析结果。

这些文件可以删除后由脚本重新生成，但 `mc_ensemble.py` 的 512 次抽样耗时较长。
