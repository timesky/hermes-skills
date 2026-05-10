---
name: financial-cache-operations
description: 全市场财务数据缓存系统操作指南 - 补充失败股票、增量更新、状态检查
version: 1.0
created: 2026-05-03
tags: [financial-data, cache, operations, akshare]
---

# 财务数据缓存系统操作指南

## 系统概述

缓存A股全部股票的财务报表（资产负债表、利润表、现金流量表）和财务指标

**数据源**: AkShare（新浪财经 + 同花顺）
**数据量**: 全市场5220只股票，约600MB
**更新频率**: 季度财报发布后增量更新

## 目录结构

```
~/.hermes/profiles/stock/data/financial_cache/
├── balance/      # 资产负债表 (234M)
├── profit/       # 利润表 (143M)
├── cashflow/     # 现金流量表 (150M)
├── indicator/    # 财务指标摘要 (59M)
└── metadata.json # 元数据
```

## 核心脚本

**路径**: `~/.hermes/profiles/stock/scripts/financial_cache.py`

## 常用操作

### 1. 查看缓存状态

```bash
python3 financial_cache.py status
```

**输出示例**:
- 成功股票数
- 失败股票数
- 最后更新时间
- 数据完整性检查

### 2. 全量更新

```bash
python3 financial_cache.py full
```

**适用场景**: 首次运行，下载全部历史财报

### 3. 补充失败股票（重点）

```bash
python3 financial_cache.py full --resume
```

**关键参数**: `--resume` 从上次中断处继续

**典型场景**:
- 初次抓取后失败321只（API限制/网络超时）
- 使用`--resume`后只剩1只失败
- 成功率从94%提升到99.98%

**经验教训**: 失败股票主要是API请求限制，重试即可成功

### 4. 增量更新

```bash
python3 financial_cache.py incremental
```

**适用场景**: 季度财报发布后，追加新数据

**更新逻辑**:
- 检查最新报告期
- 只下载缺失的季度数据
- 避免重复下载历史数据

### 5. 测试模式

```bash
python3 financial_cache.py test
```

**适用场景**: 测试单只股票数据抓取，快速验证

## 数据字段

### 资产负债表 (balance)
- 报告日、流动资产、货币资金、应收账款、存货
- 固定资产、无形资产、商誉
- 负债、所有者权益
- 数据源、是否审计、公告日期
- **字段数**: 100+

### 利润表 (profit)
- 营业收入、营业成本、营业利润
- 净利润、每股收益
- 扣非净利润

### 现金流量表 (cashflow)
- 经营活动现金流
- 投资活动现金流
- 筹资活动现金流

### 财务指标 (indicator)
- PE、PB、ROE
- 毛利率、净利率
- 资产负债率
- 流动比率、速动比率

**字段格式说明**：
- 百分比字段（ROE、净利率、资产负债率等）：含 `%` 符号，如 `29.86%`
- 金额字段（净利润、现金流等）：含 `亿` 或 `万` 单位
- 字段名均为中文（如 `净资产收益率` 而非 `roe`）

**正确解析方式**：
```python
# 百分比字段
roe_str = str(latest.get('净资产收益率', '0'))
roe = float(roe_str.replace('%', '')) if '%' in roe_str else float(roe_str)

# 资产负债率（转为小数）
debt_str = str(latest.get('资产负债率', '0'))
debt_ratio = float(debt_str.replace('%', '')) / 100 if '%' in debt_str else float(debt_str) / 100

# 金额字段
profit_str = str(latest.get('净利润', '0'))
profit = float(profit_str.replace('亿', '').replace('万', ''))
```

## 常见问题

### Q1: 失败股票无法补充？

**常见原因**: 指数代码混入（非API限制）

**诊断方法**:
```bash
# 统计代码前缀分布
cat stock_list.json | python3 -c "
import sys, json
stock_list = json.load(sys.stdin)
prefix_stats = {}
for item in stock_list:
    code = item['symbol'] if isinstance(item, dict) else item
    prefix = code[:3]
    prefix_stats[prefix] = prefix_stats.get(prefix, 0) + 1
for prefix, count in sorted(prefix_stats.items()):
    print(f'{prefix}开头: {count}只')
"
```

**关键发现**:
- **399开头代码是指数，不是股票**（如深证成指399001、创业板指399006）
- 指数没有财务数据，注定失败
- 如果失败数=399开头数，说明是指数代码混入问题

**解决方案**:
1. **过滤指数代码**（推荐）:
   ```python
   # 从stock_list.json中排除399xxx
   filtered = [s for s in stock_list if not s['symbol'].startswith('399')]
   ```
2. 如果确实是API限制，使用`--resume`参数重试
3. 检查网络连接稳定性

**实际案例**:
- 初次抓取：失败321只
- 诊断发现：399开头刚好321只（指数代码）
- 修复后：成功率100%，真实股票4899只

### Q2: 数据量太大？

**实际情况**: 全市场约600MB

**存储策略**:
- 本地缓存避免重复下载
- 增量更新只下载新数据
- 历史数据永久保留

### Q3: 如何查询特定股票？

```python
import pandas as pd

# 读取资产负债表
df = pd.read_csv('~/.hermes/profiles/stock/data/financial_cache/balance/600519.csv')

# 最新报告
latest = df.iloc[0]
print(f"报告期: {latest['报告日']}")
print(f"总资产: {latest['资产总计']}")
```

### Q4: 数据时效性？

**最新报告**: 2026年一季报（2026Q1）  
**覆盖范围**: 近2年（2024-2026），共9个季度  
**更新周期**: 每季度财报发布后  
**延迟**: 财报发布后1-2天更新

**验证数据完整性**（近2年应有9个报告期）:
```bash
# 检查某股票近2年数据
file=~/.hermes/profiles/stock/data/financial_cache/balance/600584.csv

echo "应包含报告期："
echo "2026: 20260331"
echo "2025: 20250331, 20250630, 20250930, 20251231"
echo "2024: 20240331, 20240630, 20240930, 20241231"

# 实际检查
grep -E "^202[456][0-9]{5}" "$file" | cut -d',' -f1 | sort -u
```

**输出应为9个日期**，如不足则说明数据不完整

## 定时任务配置

现有cron任务自动运行增量更新：

**任务ID**: 54c196ee194b
**执行时间**: 每年1/4/7/10月1日 02:00
**内容**: 季度财报发布后自动更新

**检查方式**:
```bash
crontab -l | grep financial
```

## 性能指标

| 操作 | 耗时 | 适用场景 |
|------|------|---------|
| status | <1s | 状态检查 |
| test | <10s | 单股测试 |
| incremental | 5-10分钟 | 季度更新 |
| full --resume | 10-30分钟 | 补充失败股票 |
| full | 30-60分钟 | 首次全量 |

## 注意事项

1. **避免频繁全量更新**: 会触发API限制
2. **使用--resume**: 失败重试比重新开始更高效
3. **网络稳定性**: WiFi比移动网络更稳定
4. **磁盘空间**: 确保有至少1GB可用空间

## 调试技巧

### 检查失败原因

```bash
# 查看progress日志
tail -50 ~/.hermes/profiles/stock/data/financial_cache/progress.txt | grep -i error
```

### 验证数据完整性

```bash
# 统计各目录文件数
ls ~/.hermes/profices/stock/data/financial_cache/{balance,profit,cashflow,indicator} | wc -l
```

### 手动测试单只股票

```python
import akshare as ak

# 测试贵州茅台
df = ak.stock_balance_sheet_by_report_em(symbol="600519")
print(f"获取到 {len(df)} 条记录")
```
