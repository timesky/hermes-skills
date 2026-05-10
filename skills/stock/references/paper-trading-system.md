# 实盘模拟系统 (Paper Trading System)

## 与回测系统的区别

| 维度 | 回测系统 | 实盘模拟系统 |
|------|----------|--------------|
| **数据源** | 历史5年数据 | 实时每日数据（收盘后更新） |
| **方向** | 验证过去表现 | 预测次日走势 |
| **输出** | 策略统计指标 | 次日交易计划 |
| **闭环** | 参数调优 | 预测→验证→反思→回测→应用/回滚 |
| **本金** | 虚拟无限 | 固定2万 |
| **时间** | 批量运行 | 每日运行 |
| **目标** | 策略验证 | 策略进化 |

## 核心闭环流程

```
每日收盘后运行
    │
    ├─→ 【步骤1】验证昨日预测
    │      ├─ 对比预测 vs 实际数据
    │      ├─ 计算偏离度（价格/振幅）
    │      ├─ 判断走势形态是否正确
    │      └─ 判断交易是否成功
    │
    ├─→ 【步骤2】反思分析
    │      ├─ 分析偏离原因
    │      ├─ 识别问题类型（价格偏差/形态错误）
    │      ├─ 生成调整建议
    │      └─ 判断是否需要优化
    │
    ├─→ 【步骤3】策略优化（如有需要）
    │      ├─ 生成新参数方案
    │      ├─ 【关键】回测验证（必须比当前更好）
    │      ├─ 验证通过 → 提交新版本（pending → active）
    │      ├─ 验证失败 → 保持当前版本
    │      └─ 记录版本历史（可回滚）
    │
    └─→ 【步骤4】预测次日
           ├─ 用当前最优策略预测
           ├─ 输出最低/最高价预测
           ├─ 输出振幅预测
           ├─ 输出走势形态预测
           └─ 输出交易计划（价格/数量）
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  实盘模拟系统 (paper_trading.py + paper_trading_daily.py)   │
└─────────────────────────────────────────────────────────────┘
    │
    ├── 策略引擎 (StrategyEngine)
    │     ├─ 管理策略版本
    │     ├─ 预测次日走势
    │     ├─ 创建新版本
    │     └─ 回滚版本
    │
    ├── 账户管理 (AccountManager)
    │     ├─ 管理本金/持仓
    │     ├─ 记录交易
    │     └─ 计算盈亏
    │
    ├── 预测记录 (PredictionManager)
    │     ├─ 保存预测
    │     ├─ 验证预测
    │     ├─ 计算偏离
    │     └─ 记录反思
    │
    └── 每日流程 (paper_trading_daily.py)
          ├─ 验证 → 反思 → 优化 → 预测
          └─ 生成每日报告
```

## 数据结构

### 目录结构

```
~/.hermes/profiles/stock/data/paper_trading/
├── account.json           # 账户状态（本金/持仓/盈亏）
├── predictions.json       # 预测记录及验证
├── trades.json            # 交易记录
├── strategy_history.json  # 策略版本管理（可回滚）
├── logs/                  # 详细日志
├── backups/               # 版本备份
└── report_YYYYMMDD.json   # 每日报告
```

### 核心数据结构

#### account.json（账户状态）

```json
{
  "initial_capital": 20000,
  "current_capital": 20000,
  "positions": {
    "600584": {
      "name": "长电科技",
      "shares": 100,
      "cost_price": 45.56
    }
  },
  "cash": 20000,
  "total_value": 20000,
  "pnl": 0,
  "pnl_pct": 0,
  "trades_count": 0,
  "win_rate": 0,
  "start_date": "2026-05-05",
  "last_update": "2026-05-02 09:15:29"
}
```

#### predictions.json（预测记录）

```json
{
  "records": [
    {
      "date": "2026-05-02",
      "symbol": "600584",
      "name": "长电科技",
      "prediction": {
        "strategy": "RSI策略",
        "predicted_low": 44.47,
        "predicted_high": 47.19,
        "predicted_range": "4.0%",
        "pattern": "震荡整理",
        "action": "hold",
        "confidence": 0.4
      },
      "trade_plan": {
        "action": "hold",
        "reason": "观望"
      },
      "actual": {
        "low": 44.11,
        "high": 45.86,
        "close": 45.56
      },
      "deviation": {
        "low_deviation_pct": 0.81,
        "high_deviation_pct": 2.82,
        "pattern_correct": false
      },
      "trade_result": null,
      "reflection": null
    }
  ]
}
```

#### strategy_history.json（策略版本）

```json
{
  "current_version": "v1.0.0",
  "versions": [
    {
      "version": "v1.0.0",
      "date": "2026-05-01",
      "strategy": "mean_reversion_rsi14",
      "params": {
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70
      },
      "backtest_result": {
        "profit": 2.61,
        "drawdown": 0.87,
        "win_rate": 7.9
      },
      "reason": "初始策略（震荡市最优）",
      "status": "active"
    }
  ]
}
```

## 命令用法

### 基础命令

```bash
# 查看账户状态
python3 ~/.hermes/profiles/stock/scripts/paper_trading.py status

# 预测次日走势
python3 ~/.hermes/profiles/stock/scripts/paper_trading.py predict 600584

# 验证昨日预测
python3 ~/.hermes/profiles/stock/scripts/paper_trading.py validate 600584

# 反思分析
python3 ~/.hermes/profiles/stock/scripts/paper_trading.py reflect 600584

# 回滚策略版本
python3 ~/.hermes/profiles/stock/scripts/paper_trading.py rollback v1.0.0
```

### 每日流程命令

```bash
# 完整闭环（验证→反思→优化→预测）
python3 ~/.hermes/profiles/stock/scripts/paper_trading_daily.py

# 仅预测
python3 ~/.hermes/profiles/stock/scripts/paper_trading_daily.py --predict-only

# 仅验证
python3 ~/.hermes/profiles/stock/scripts/paper_trading_daily.py --validate-only

# 指定股票池
python3 ~/.hermes/profiles/stock/scripts/paper_trading_daily.py --symbols 600584 000001
```

## 策略版本管理

### 版本命名规则

| 版本号 | 说明 |
|--------|------|
| `v1.0.0` | 初始版本 |
| `v1.0.1` | 微调参数（patch） |
| `v1.1.0` | 小幅改进（minor） |
| `v2.0.0` | 大幅改进（major） |

### 版本状态

| 状态 | 说明 |
|------|------|
| `pending` | 待回测验证 |
| `active` | 当前激活 |
| `deprecated` | 已废弃 |
| `rollback` | 已回滚 |

### 回滚机制

```
检测到预测更差
    │
    ├─→ 回滚到上一版本
    │      ├─ 标记当前版本为 rollback
    │      ├─ 激活上一版本
    │      └─ 记录回滚原因
    │
    └─→ 检查回测机制
          ├─ 是否存在未来函数？
          ├─ 是否数据泄露？
          └─ 是否参数过拟合？
```

## 预测偏离度分析

### 偏离度计算

```python
# 价格偏离
low_deviation = abs(actual_low - predicted_low) / predicted_low * 100
high_deviation = abs(actual_high - predicted_high) / predicted_high * 100

# 偏离阈值
偏离 < 3%  → 优秀
偏离 3-5%  → 良好
偏离 5-10% → 需调整
偏离 > 10% → 紧急调整
```

### 常见偏离原因

| 原因 | 表现 | 解决方案 |
|------|------|----------|
| **市场剧烈波动** | 偏离>10% | 增加波动率倍数 |
| **趋势判断错误** | 形态预测错误 | 增加辅助指标（成交量/MACD） |
| **支撑位失效** | 实际跌破预测低点 | 调整止损参数 |
| **阻力位突破** | 实际突破预测高点 | 调整止盈参数 |

## 与持仓建议的关系

```
┌─────────────────────────────────────────────────────────────┐
│  策略来源优先级                                              │
└─────────────────────────────────────────────────────────────┘
    │
    ├─→ 【优先】实盘模拟验证后的策略
    │      ├─ 预测准确率 > 70%
    │      ├─ 持续运行 ≥ 3个月
    │      └─ 累计盈利 ≥ 20%
    │
    └─→ 【兜底】回测最优策略
           ├─ 实盘模拟未开始时
           ├─ 实盘模拟验证失败时
           └─ 新股票加入时
```

## 定时任务设置

### 每日运行（收盘后）

```bash
# 建议时间：交易日 15:30
# cronjob action='create'
# schedule: "30 15 * * 1-5"
# skills: ["stock"]
# deliver: "origin"
# prompt: "执行实盘模拟每日流程：验证昨日预测 → 反思分析 → 策略优化 → 预测次日"

python3 ~/.hermes/profiles/stock/scripts/paper_trading_daily.py --symbols 600584
```

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 周末不运行 | 系统检测到周末 | 正常行为，周一自动恢复 |
| 预测偏离大 | 市场波动超预期 | 检查波动率模型 |
| 策略不进化 | 回测验证未通过 | 检查回测机制 |
| 版本回滚频繁 | 策略不稳定 | 增加验证周期 |

## 未来扩展

### 1. 多股票池

当前只支持单一股票，未来可扩展为多股票池：

```json
{
  "stocks": ["600584", "601012", "601698", "000506"]
}
```

### 2. 机器学习预测

```python
# 使用LSTM预测
from keras.models import Sequential
model = Sequential()
# 训练 → 预测 → 验证 → 进化
```

### 3. 实盘对接

```
实盘模拟验证成功 → 接入券商API → 自动交易
```

---

**创建时间**: 2026-05-02  
**状态**: 已上线  
**起始日期**: 2026-05-05（五一假期后）  
**本金**: 2万元

---

## SQLite数据库系统（2026-05-07升级）

### 数据库位置

```
~/.hermes/profiles/stock/data/paper_trading/paper_trading.db
```

### 表结构

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| **account_summary** | 每日账户概况 | date, total_cost, total_pnl, stock_value, available_cash, total_value, position_ratio |
| **positions** | 每日持仓记录 | date, symbol, name, shares, cost_price, current_price, pnl_pct, stop_loss_price, take_profit_price |
| **predictions** | 预测记录 | predict_date, target_date, symbol, name, predict_type, predict_low, predict_high, action, action_shares, action_price, actual_low, actual_high, deviation_pct, is_success |
| **stock_pool** | 选股池 | date, symbol, name, score, reason |
| **trades** | 交易记录 | date, symbol, action, shares, price, pnl |

### 查询注意事项

**⚠️ 重复记录问题**：positions和predictions表可能存在重复记录，查询时需使用 `GROUP BY symbol`：

```sql
-- 正确查询（去重）
SELECT symbol, name, shares, cost_price, current_price, pnl_pct
FROM positions
WHERE date = (SELECT MAX(date) FROM positions)
GROUP BY symbol
ORDER BY symbol

-- 错误查询（可能重复）
SELECT * FROM positions WHERE date = '2026-05-07'
-- 结果可能：同一股票显示多次
```

### 清理重复记录

```python
import sqlite3
conn = sqlite3.connect('paper_trading.db')
cursor = conn.cursor()

# 清理positions表重复记录（保留id最小的）
cursor.execute("""
    DELETE FROM positions
    WHERE id NOT IN (
        SELECT MIN(id) FROM positions GROUP BY date, symbol
    )
""")

conn.commit()
conn.close()
```

### 验证准确度计算

从predictions表计算，而非verification_analysis表：

```sql
-- 平均偏差
SELECT AVG(deviation_pct) FROM predictions
WHERE actual_low IS NOT NULL AND deviation_pct IS NOT NULL
AND predict_date = (SELECT MAX(predict_date) FROM predictions WHERE actual_low IS NOT NULL)

-- 成功率
SELECT COUNT(*) as total, 
       SUM(CASE WHEN is_success = 1 THEN 1 ELSE 0 END) as success
FROM predictions
WHERE actual_low IS NOT NULL
AND predict_date = (SELECT MAX(predict_date) FROM predictions WHERE actual_low IS NOT NULL)
```

### 轻量级简报脚本

**用途**：Cronjob定时任务（避免超时）

```bash
# 快速生成报告（<1秒）
python3 ~/.hermes/profiles/stock/scripts/paper_trading_summary.py

# 输出内容：
# 一、昨日预测验证（成功率、准确度）
# 二、账户概况（总成本、总盈亏、仓位比例）
# 三、持股监控（去重显示）
# 四、次日买入候选（选股池前5名）
```

**优势**：
- 无网络请求，纯SQLite读取
- 运行时间<1秒（vs paper_trading_daily.py >120s）
- 自动处理重复记录
- 适合Cronjob定时推送

---

## 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Cronjob输出简略/"什么信息都没有" | `paper_trading_daily.py`运行超时(>120s) | 使用`paper_trading_summary.py`轻量脚本 |
| 持股显示重复（同一股票多条） | 数据库有重复记录 | 查询使用`GROUP BY symbol`或清理重复 |
| 仓位比例显示错误(如9333%) | `position_ratio`已是百分比，无需×100 | 直接使用原值显示 |
| verification_analysis表不存在 | 表已废弃，数据迁移到predictions表 | 从predictions计算准确度 |