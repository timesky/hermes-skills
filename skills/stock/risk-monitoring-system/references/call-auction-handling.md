# 集合竞价阶段数据处理

## 背景

A股集合竞价时段（9:15-9:25），数据源返回的实时行情数据特征：
- `涨跌幅` 列全为 0（尚未成交）
- `成交额` 列全为 0（尚未成交）
- `昨收` 列正常（昨日收盘价）
- `买入` 和 `卖出` 列正常（买卖挂单价格）
- `今开` 列仅少数股票有值（已开盘）

## 解决方案：使用买卖价预估涨跌停

```python
# 计算预期涨跌停（基于买入价）
df_valid = df[df['昨收'] > 0].copy()
df_valid['bid_change'] = (df_valid['买入'] - df_valid['昨收']) / df_valid['昨收'] * 100

# 预期涨停（买入价 ≥ 昨收+10%）
limit_up = len(df_valid[df_valid['bid_change'] >= 9.9])

# 预期跌停（买入价 ≤ 昨收-10%）
limit_down = len(df_valid[df_valid['bid_change'] <= -9.9])
```

## 数据列对比

| 列名 | Eastmoney | Sina | 说明 |
|------|-----------|------|------|
| 涨跌幅 | `涨跌幅` | `涨跌幅` | 竞价期间为0 |
| 成交额 | `成交额` | `成交额` | 竞价期间为0 |
| 昨收价 | `昨收` | `昨收` | 正常 |
| 买入价 | - | `买入` | Sina 有此列 |
| 卖出价 | - | `卖出` | Sina 有此列 |
| 今开价 | - | `今开` | 少数股票有值 |

## 时间段判断代码

```python
from datetime import time

def is_trading_hours():
    """判断当前是否在交易时段"""
    now = datetime.now()
    current_time = now.time()
    
    # 上午交易时段: 9:30 - 11:30
    # 下午交易时段: 13:00 - 15:00
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)

def is_call_auction():
    """判断当前是否在集合竞价阶段"""
    now = datetime.now()
    current_time = now.time()
    
    # 开盘集合竞价: 9:15 - 9:25
    # 收盘集合竞价: 14:57 - 15:00
    morning_auction_start = time(9, 15)
    morning_auction_end = time(9, 25)
    afternoon_auction_start = time(14, 57)
    afternoon_auction_end = time(15, 0)
    
    return (morning_auction_start <= current_time <= morning_auction_end) or \
           (afternoon_auction_start <= current_time <= afternoon_auction_end)
```

## 预警级别调整

集合竞价阶段使用更宽松的预警阈值：
- 跌停 > 50只 → WARNING（而非交易时段的100只）
- 原因：竞价阶段数据为预估，实际开盘可能变化

---

**更新日期**: 2026-05-07  
**脚本**: `scripts/liquidity_monitor.py`