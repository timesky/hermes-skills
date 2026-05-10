# Market Cache 增量更新 Bug 诊断

## Bug 位置

**文件**: `~/.hermes/profiles/stock/scripts/market_cache.py`
**行号**: 585

## 问题代码

```python
# 检查是否需要更新
if last_date and last_date >= end_date.replace('-', '')
    continue  # 已是最新
```

## Bug 根本原因

| 变量 | 格式 | 示例值 |
|------|------|--------|
| `last_date` | YYYY-MM-DD（带连字符） | `'2026-05-06'` |
| `end_date.replace('-', '')` | YYYYMMDD（无连字符） | `'20260506'` |

字符串比较规则：
- ASCII `'-'` = 45
- ASCII `'0'` = 48
- 因此 `'2026-05-06' < '20260506'`（第一个连字符位置字符更小）

**错误判断**：即使数据已是最新（2026-05-06），仍被判定为"需要更新"

## 影响

1. 每只股票都尝试下载新数据
2. 由于 `update_start` = `last_date + 1天` > `end_date`
3. Baostock 返回错误：`"起始日期大于终止日期，请修改"`
4. 更新任务无法正确完成
5. 元数据 `last_incremental_update` 始终为 `null`

## 正确修复方案

**方案A**：保持 `end_date` 格式不变
```python
# 正确：两者都保持 YYYY-MM-DD 格式
if last_date and last_date >= end_date:
    continue  # 已是最新
```

**方案B**：统一转换为 YYYYMMDD 格式
```python
# 正确：两者都转为无连字符格式
if last_date and last_date.replace('-', '') >= end_date.replace('-', '')
    continue  # 已是最新
```

## 诊断方法

检查缓存数据的最后日期分布：
```bash
cd ~/.hermes/profiles/stock/scripts

python3 -c "
from pathlib import Path
import csv

cache_dir = Path.home() / '.hermes/profiles/stock/data/market_cache/stocks'
stock_files = list(cache_dir.glob('*.csv'))

date_counts = {}
for f in stock_files:
    with open(f) as file:
        lines = file.readlines()
        if len(lines) > 1:
            date = lines[-1].strip().split(',')[0]
            date_counts[date] = date_counts.get(date, 0) + 1

print('最后日期分布:')
for date in sorted(date_counts.keys(), reverse=True)[:5]:
    print(f'  {date}: {date_counts[date]}只股票')
"
```

## 状态检查命令

```bash
# 查看元数据
cat ~/.hermes/profiles/stock/data/market_cache/metadata.json

# 检查单只股票最后日期
tail -1 ~/.hermes/profiles/stock/data/market_cache/stocks/600000.csv
```

## 时间线

| 日期 | 事件 |
|------|------|
| 2026-05-03 | 全量更新完成，5220只股票，13651717条记录 |
| 2026-05-07 16:00 | 增量更新任务执行，因bug无法完成 |
| 2026-05-07 16:14 | Bug诊断，发现日期格式不一致问题 |

---

## 修复记录（2026-05-08）

### 已应用修复

**修复1**：日期格式统一比较（第584-590行）
```python
# 修复前
if last_date and last_date >= end_date.replace('-', ''):
    continue

# 修复后
if last_date:
    last_date_clean = last_date.replace('-', '')
    end_date_clean = end_date.replace('-', '')
    if last_date_clean >= end_date_clean:
        continue  # 已是最新
```

**修复2**：日期范围有效性检查（第597-602行）
```python
# 检查日期范围是否有效
if update_start.replace('-', '') > end_date.replace('-', ''):
    # 没有新数据需要更新
    continue
```

**修复3**：增量更新时间逻辑（第549-562行）
```python
# 增量更新使用今天的日期（收盘后运行）
# 如果当前时间在16:00之后，使用今天的日期
now = datetime.now()
if now.hour >= 16:
    end_date = now.strftime('%Y-%m-%d')
else:
    end_date = END_DATE  # 默认昨天的日期
```

---

## ⚠️ 关键发现：Baostock数据更新时间

### 问题

定时任务在16:00执行增量更新，但 **Baostock数据源尚未更新当日数据**。

### 验证

```python
# 测试2026-05-08数据获取（16:00执行）
import baostock as bs
bs.login()
rs = bs.query_history_k_data_plus('sh.600000', 'date,close', 
    start_date='2026-05-08', end_date='2026-05-08', frequency='d')
# 结果：空DataFrame（当日数据未就绪）

rs = bs.query_history_k_data_plus('sh.600000', 'date,close',
    start_date='2026-05-07', end_date='2026-05-07', frequency='d')
# 结果：正常返回（昨日数据已就绪）
```

### Baostock数据更新规律

| 时间 | 数据状态 |
|------|----------|
| 16:00（收盘后） | ❌ 当日数据未就绪 |
| 18:00-20:00 | ✅ 当日数据开始更新 |
| 次日早间 | ✅ 数据完全稳定 |

### 建议

**将增量更新定时任务调整至 19:00 或 20:00 执行**，避免因数据未就绪导致无效运行。

---

**状态**: Bug已修复，但发现数据源更新时间限制，建议调整cronjob执行时间