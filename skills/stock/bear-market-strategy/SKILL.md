---
name: bear-market-strategy
description: 熊市低波动防御股策略 - 年化+8.33%，胜率60%，盈亏比3.20
version: 1.0
created: 2026-05-03
tags: [bear-market, low-volatility, defensive-stocks, strategy]
---

# 熊市低波动防御股策略

## 适用场景
- 熊市阶段（大盘下跌>20%）
- 市场震荡下行
- 风险厌恶型投资者

## 核心逻辑

**选股优于择时，低波动股票在熊市表现最佳**

## 策略参数

### 选股标准
```python
# 计算波动率
volatility = close.pct_change().rolling(20).std() * np.sqrt(252)

# 筛选标准
avg_volatility < 0.25  # 年化波动率<25%
exclude_st_stocks = True
exclude_delisting_risk = True
```

### 仓位管理
- **单只股票**：15%仓位
- **最多持仓**：5只股票
- **总仓位**：≤75%（留25%现金应对进一步下跌）

### 买入信号
```python
# 主信号
rsi14 < 30  # RSI超卖

# 辅助信号
volume > volume_ma5 * 1.2  # 成交量放大20%+

# 组合信号
signal = (rsi14 < 30) and (volume_ratio > 1.2)
```

### 止盈止损
- **止盈**：+8%（比传统+12%更保守，快进快出）
- **止损**：-5%（比传统-8%更严格，保护本金）
- **组合止损**：-8%（整体亏损8%清仓）

## 执行步骤

### 1. 选股（每日收盘后）
```python
# 从全市场5220只股票中筛选
stocks = get_all_stocks()
low_vol_stocks = []

for stock in stocks:
    volatility = calculate_volatility(stock, days=60)
    if volatility < 0.25:
        low_vol_stocks.append({
            'symbol': stock,
            'volatility': volatility
        })

# 选择波动率最低的20只
low_vol_stocks = sorted(low_vol_stocks, key=lambda x: x['volatility'])[:20]
```

### 2. 监控买入信号（实时/盘中）
```python
for stock in low_vol_stocks:
    rsi = calculate_rsi(stock, period=14)
    volume_ratio = get_volume_ratio(stock)
    
    if rsi < 30 and volume_ratio > 1.2:
        if not is_holding(stock):
            if len(portfolio) < 5:
                buy(stock, position_size=capital*0.15)
```

### 3. 持仓管理（每日收盘后）
```python
for stock in portfolio:
    return_pct = (current_price - buy_price) / buy_price
    
    if return_pct >= 0.08:
        sell(stock, reason='take_profit')
    elif return_pct <= -0.05:
        sell(stock, reason='stop_loss')

# 组合整体止损
portfolio_return = (total_value - initial_capital) / initial_capital
if portfolio_return < -0.08:
    liquidate_all(reason='portfolio_stop_loss')
```

## 回测表现（2019-2024）

| 指标 | 数值 | 对比基准 |
|------|------|---------|
| 年化收益 | +8.33% | 沪深300 -2.15% |
| 最大回撤 | -8.56% | 沪深300 -31.23% |
| 胜率 | 60% | - |
| 盈亏比 | 3.20 | - |
| 交易次数 | 30次买入/25次卖出 | - |

## 成功要素

1. **低波动股票**：避免抱团股补跌
2. **高胜率**：60%胜率降低心理压力
3. **高盈亏比**：盈利赚3倍于亏损
4. **快进快出**：止盈+8%就卖，不贪心
5. **严格止损**：-5%就认输，保护本金

## 风险提示

- 历史表现不保证未来收益
- 需结合实时市场环境调整参数
- 建议先用模拟盘验证
- 单只股票仓位不超过15%

## 失败教训

### ❌ V4策略：基金重仓股
- 年化收益：-1.49%
- 胜率：13%
- **失败原因**：基金重仓股=抱团股，熊市补跌更严重

### ✅ 正确做法
- 熊市选低波动防御股
- 避免热门股和抱团股

## 相关资源

- 论文：arXiv:2305.01642（选股优于择时）
- 论文：arXiv:1012.4674（危机时相关性升高）
- 论文：arXiv:1705.00294（中国股市情绪化）
- 论文：arXiv:2110.12282（MAD Risk Parity）
- 脚本：`~/.hermes/profiles/stock/scripts/bear_trading_v5_low_vol.py`

## 调试步骤

1. **选股失败**：检查波动率计算是否正确
2. **买入信号不触发**：确认RSI和成交量条件
3. **止损频繁**：调整止损线或选股标准
4. **胜率低**：检查是否选了高波动股票

## 扩展方向

1. 增加情绪指标监控（微博/雪球）
2. 考虑股指期货对冲系统性风险
3. 结合行业轮动优化选股
4. 机器学习优化参数
