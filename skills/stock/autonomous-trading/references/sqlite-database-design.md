# SQLite数据库设计（实盘模拟）

创建日期：2026-05-07

---

## 数据库路径

```
~/.hermes/profiles/stock/data/paper_trading/paper_trading.db
```

---

## 表结构设计

### 1. account_summary（账户概况）

每日记录账户状态，追踪资金变化：

```sql
CREATE TABLE account_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    total_cost REAL NOT NULL,       -- 初始本金
    total_pnl REAL NOT NULL,        -- 总盈亏（元）
    stock_value REAL NOT NULL,      -- 股票市值
    available_cash REAL NOT NULL,   -- 可用现金
    total_value REAL NOT NULL,      -- 总资产
    position_ratio REAL NOT NULL,   -- 仓位比例（%）
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 2. positions（持仓记录）

每日记录持仓状态，包含止损止盈价格：

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    shares INTEGER NOT NULL,
    cost_price REAL NOT NULL,       -- 成本价
    current_price REAL NOT NULL,    -- 当前价
    position_value REAL NOT NULL,   -- 持仓市值
    pnl_pct REAL NOT NULL,          -- 盈亏百分比
    stop_loss_price REAL NOT NULL,  -- 止损价（成本×0.90）
    take_profit_price REAL NOT NULL, -- 止盈价（成本×1.20）
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 3. predictions（预测记录）

核心表，记录所有预测及次日验证结果：

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    predict_date TEXT NOT NULL,     -- 预测日期
    target_date TEXT NOT NULL,      -- 目标验证日期
    symbol TEXT NOT NULL,
    name TEXT,
    predict_type TEXT NOT NULL,     -- '持股' | '选股'
    
    -- 价格预测
    predict_low REAL NOT NULL,      -- 预测最低价
    predict_high REAL NOT NULL,     -- 预测最高价
    current_price REAL NOT NULL,    -- 当前价格
    
    -- 操作预测
    action TEXT NOT NULL,           -- '持有' | '买入' | '止损卖出' | '止盈卖出'
    action_shares INTEGER NOT NULL, -- 操作数量
    action_price REAL NOT NULL,     -- 操作价格
    action_amount REAL NOT NULL,    -- 预期金额
    
    -- 次日验证（初始为空）
    actual_low REAL,                -- 实际最低价
    actual_high REAL,               -- 实际最高价
    actual_open REAL,               -- 实际开盘价
    actual_close REAL,              -- 实际收盘价
    is_success INTEGER,             -- 1=成功, 0=失败, NULL=未验证
    deviation_pct REAL,             -- 偏差百分比
    analysis TEXT,                  -- 分析说明
    verified_at TEXT,               -- 验证时间
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 4. trades（交易记录）

记录所有买卖交易：

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    action TEXT NOT NULL,           -- '买入' | '卖出' | '止损卖出' | '止盈卖出'
    shares INTEGER NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    success INTEGER DEFAULT 1,      -- 交易是否成功
    reason TEXT,                    -- 操作原因
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 5. verification_analysis（验证分析）

重点关注失败预测，用于策略优化：

```sql
CREATE TABLE verification_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    predict_date TEXT NOT NULL,
    target_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    predict_action TEXT NOT NULL,   -- 预测操作
    predict_price REAL NOT NULL,    -- 预测价格
    actual_low REAL NOT NULL,       -- 实际最低价
    actual_high REAL NOT NULL,      -- 实际最高价
    is_in_range INTEGER NOT NULL,   -- 是否在区间内
    failure_reason TEXT,            -- 失败原因
    improvement TEXT,               -- 改进建议
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 次日验证逻辑

验证函数 `verify_prediction()` 核心规则：

### 买入验证

```python
# 买入操作：预期买入价必须在当日低点范围内
is_success = 1 if action_price >= actual_low else 0

if is_success == 0:
    analysis = f"买入失败：预期价{action_price}元低于当日最低价{actual_low}元，无法成交"
else:
    analysis = f"买入可行：预期价{action_price}元在当日区间[{actual_low}-{actual_high}]内"
```

### 卖出验证

```python
# 卖出操作：预期卖出价必须在当日高点范围内
is_success = 1 if action_price <= actual_high else 0

if is_success == 0:
    analysis = f"卖出失败：预期价{action_price}元高于当日最高价{actual_high}元，无法成交"
else:
    analysis = f"卖出可行：预期价{action_price}元在当日区间[{actual_low}-{actual_high}]内"
```

---

## Python接口函数

### 初始化数据库

```python
from paper_trading_db import init_database

init_database()  # 创建所有表
```

### 保存预测

```python
save_prediction(
    predict_date="2026-05-07",
    target_date="2026-05-08",
    symbol="605108",
    name="恒润股份",
    predict_type="选股",
    predict_low=15.84,
    predict_high=16.00,
    current_price=15.92,
    action="买入",
    action_shares=100,
    action_price=15.60
)
```

### 验证预测

```python
result = verify_prediction(
    target_date="2026-05-08",
    symbol="605108",
    actual_low=15.5,
    actual_high=16.8,
    actual_open=15.9,
    actual_close=16.5
)

# 返回：
# {
#     'symbol': '605108',
#     'action': '买入',
#     'predict_price': 15.6,
#     'actual_range': [15.5, 16.8],
#     'is_success': 1,
#     'analysis': '买入可行：预期价15.6元在当日区间[15.5-16.8]内'
# }
```

### 查询失败预测

```python
from paper_trading_db import get_failed_predictions

failed = get_failed_predictions(days=7)  # 最近7天失败预测

# 用于重点分析和策略优化
```

---

## 常用查询SQL

```bash
# 查看账户概况历史（最近7天）
sqlite3 paper_trading.db "
SELECT date, total_cost, total_pnl, stock_value, available_cash, position_ratio 
FROM account_summary 
ORDER BY date DESC LIMIT 7;
"

# 查看失败预测（重点分析）
sqlite3 paper_trading.db "
SELECT predict_date, target_date, symbol, action, action_price, 
       actual_low, actual_high, analysis
FROM predictions 
WHERE is_success = 0;
"

# 查看某股票预测历史
sqlite3 paper_trading.db "
SELECT predict_date, target_date, predict_low, predict_high, 
       action, action_price, actual_low, actual_high, is_success
FROM predictions 
WHERE symbol = '605108' 
ORDER BY target_date DESC;
"

# 统计预测成功率
sqlite3 paper_trading.db "
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN is_success=1 THEN 1 ELSE 0 END) as success,
    ROUND(SUM(CASE WHEN is_success=1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM predictions 
WHERE is_success IS NOT NULL;
"

# 查看持仓变化历史
sqlite3 paper_trading.db "
SELECT date, symbol, shares, cost_price, current_price, pnl_pct 
FROM positions 
WHERE symbol = '603626' 
ORDER BY date DESC;
"
```

---

## 设计要点

1. **所有数据可追溯**: 每日记录，历史查询不丢失
2. **验证自动化**: 次日自动填充actual字段，判断is_success
3. **失败重点分析**: verification_analysis表专门记录失败原因
4. **索引优化**: 频繁查询字段（date, symbol, target_date）可加索引
5. **数据完整性**: 使用NOT NULL约束关键字段

---

**脚本路径**: `~/.hermes/profiles/stock/scripts/paper_trading_db.py`