---
name: risk-monitoring-system
description: 风控监控系统 — 流动性监控、极端行情预警、动态止损
version: 1.0
created: 2026-05-04
author: Stock专家
---

# 风控监控系统

## 触发条件
- 用户要求"优化风控"、"增加监控"
- 用户提出"流动性"、"极端行情"、"动态止损"需求
- 用户要求"对冲工具"（当前无对冲，用监控替代）

## 系统架构

### 三层监控体系

```
【第一层：流动性监控】（9:15运行）
  ↓ 正常 → 进入第二层
  ↓ 警告 → 减仓至50%
  ↓ 危险 → 减仓至20%，启动极端行情预警

【第二层：极端行情预警】（9:30运行）
  ↓ 正常/警告 → 正常交易
  ↓ 危险 → 紧急减仓至20%
  ↓ 极端 → 清仓

【第三层：动态止损】（实时检查）
  ↓ 波动率分类 → 计算止损线
  ↓ 市场阶段调整 → 最终止损线
  ↓ 触发止损 → 立即卖出
```

## 核心脚本

### 1. 流动性监控（liquidity_monitor.py）

**功能**：
- 跌停数量统计（恐慌程度）
- 成交量变化（流动性枯竭预警）
- 换手率监控（市场活跃度）

**阈值**：
```python
ALERT_THRESHOLDS = {
    'limit_down': {
        'level_1': 100,   # 跌停100只（警告）
        'level_2': 200,   # 跌停200只（危险）
        'level_3': 500,   # 跌停500只（极端）
    },
    'volume_drop': {
        'level_1': -0.30,  # 成交量下降30%（警告）
        'level_2': -0.50,  # 成交量下降50%（危险）
        'level_3': -0.70,  # 成交量下降70%（极端）
    }
}
```

**运行命令**：
```bash
# 必须使用 pyenv Python（venv 缺少 akshare）
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/python ~/.hermes/profiles/stock/scripts/liquidity_monitor.py
```

**⚠️ 重要：数据源切换**
- Eastmoney API (`ak.stock_zh_a_spot_em()`) 在此环境被代理阻断
- 已切换到 Sina 数据源 (`ak.stock_zh_a_spot()`)
- Sina 数据列名略有不同，脚本已适配

**⚠️ 重要：集合竞价阶段处理**
- 9:15-9:25 集合竞价期间，`涨跌幅` 和 `成交额` 全为 0
- 脚本使用 `买入价/昨收价` 计算预期涨跌停
- 输出显示"预期涨停/预期跌停"而非实际值

**输出示例**：
```
【涨跌停统计】(集合竞价阶段基于买卖价预估)
  预期涨停: 21只
  预期跌停: 67只

【预警级别】
  当前级别: ⚠️ WARNING
```

---

### 2. 极端行情预警（extreme_market_alert.py）

**功能**：
- 熔断信号检测（指数跌幅）
- 千股跌停预警
- 停牌潮监控

**历史场景支持**：
```bash
# 测试历史场景
python3 scripts/extreme_market_alert.py --test 2015_crash
python3 scripts/extreme_market_alert.py --test 2020_crash
python3 scripts/extreme_market_alert.py --test 2016_circuit_breaker
```

**阈值**：
```python
EXTREME_THRESHOLDS = {
    'index_drop': {
        'level_1': -0.05,  # 跌幅5%（一级预警）
        'level_2': -0.07,  # 跌幅7%（二级预警）
        'level_3': -0.10,  # 跌幅10%（极端，类似熔断）
    },
    'limit_down_ratio': {
        'level_1': 0.02,   # 2%股票跌停（~100只）
        'level_2': 0.05,   # 5%股票跌停（~250只）
        'level_3': 0.10,   # 10%股票跌停（~500只，千股跌停）
    }
}
```

**运行命令**：
```bash
cd ~/.hermes/profiles/stock
python3 scripts/extreme_market_alert.py
```

---

### 3. 动态止损（dynamic_stop_loss.py）

**功能**：
- 根据波动率调整止损线
- 结合市场阶段优化参数

**止损规则**：
| 波动率 | 基础止损线 | 适用场景 |
|--------|-----------|---------|
| 低波动（<15%） | -5% | 蓝筹股 |
| 中波动（15%~25%） | -4% | 成长股 |
| 高波动（25%~40%） | -3% | 周期股 |
| 极端波动（>40%） | -2% | 妖股/ST |

**市场阶段调整**：
```python
MARKET_ADJUSTMENT = {
    'bull': -0.005,     # 牛市放宽0.5%
    'bear': 0.005,      # 熊市收紧0.5%
    'sideways': 0.0     # 震荡维持
}
```

**运行命令**：
```bash
# 计算单只股票止损线
python3 scripts/dynamic_stop_loss.py --symbol 600584 --phase bull

# 回测动态止损效果
python3 scripts/dynamic_stop_loss.py --test
```

---

## 部署方式

### Cron任务配置

```python
# 创建任务（注意：使用正确的 Python 路径）
cronjob(action='create', 
    name='流动性监控-每日9:15',
    prompt='执行流动性监控脚本，输出预警级别和操作建议。脚本路径：~/.hermes/profiles/stock/scripts/liquidity_monitor.py。使用 pyenv Python: /Users/hy_timesky/.pyenv/versions/3.11.15/bin/python',
    schedule='15 9 * * 1-5',
    deliver='origin'
)

cronjob(action='create',
    name='极端行情预警-每日9:30',
    prompt='执行极端行情预警脚本，检测熔断/停牌潮/流动性枯竭信号。脚本路径：~/.hermes/profiles/stock/scripts/extreme_market_alert.py',
    schedule='30 9 * * 1-5',
    deliver='origin'
)
```

### 集成到风控模块

动态止损已集成到 `risk_controller.py` 的 `check_sell_signal()` 方法：

```python
# 旧版本（固定止损）
result = rc.check_sell_signal('600584', current_price)

# 新版本（动态止损）
result = rc.check_sell_signal('600584', current_price, 
                               volatility=0.42,    # 年化波动率
                               market_phase='bull') # 市场阶段
```

**返回新增字段**：
```python
{
    "should_sell": False,
    "reason": "未触发止损止盈",
    "profit_pct": -0.04,
    "stop_loss_pct": 0.015,      # 当前止损线（动态计算）
    "volatility_class": "extreme"  # 波动率分类
}
```

---

## 实际测试结果（2026-05-04）

### 流动性监控
```
跌停股票: 30只（正常）
总成交额: 2759亿元（正常）
预警级别: ✓ NORMAL
```

### 极端行情预警
```
指数涨跌: +0.11%（正常）
跌停比例: 0.5%（正常）
预警级别: ✓ NORMAL
```

### 动态止损（持仓股票）
| 股票 | 波动率 | 分类 | 止损线 | 当前价 | 止损价 |
|------|--------|------|--------|--------|--------|
| 600584 长电科技 | 42.17% | 极端 | -2.00% | 45.56 | 44.65 |
| 601012 隆基绿能 | 29.75% | 高 | -3.00% | 16.46 | 15.97 |
| 601698 中国卫通 | 54.93% | 极端 | -2.00% | 36.67 | 35.94 |

---

## 硬指标（不可突破）

```python
RISK_HARD_LIMITS = {
    'single_stop_loss': -0.05,       # 单只止损-5%（基础）
    'portfolio_stop_loss': -0.10,    # 组合止损-10%（硬指标）
    'max_single_position': 0.30,     # 单股最大仓位30%
    'max_total_position': 0.70,      # 总仓位上限70%
}
```

**动态止损调整范围**：
- 单只止损：-2%（极端波动）~ -5.5%（低波动+牛市）
- 不突破组合止损-10%底线

---

## 历史教训

### 2015股灾（千股跌停）
- **现象**：跌停比例45%，流动性枯竭
- **后果**：止损失效，无法卖出
- **教训**：预警信号提前出现（连续暴跌），应提前减仓

### 2020疫情（开盘暴跌）
- **现象**：开盘跌幅8%，3000只跌停
- **特点**：次日反弹，但仍需减仓
- **教训**：极端行情预警触发后应立即行动

### 2016熔断（机制缺陷）
- **现象**：4天内2次熔断
- **后果**：恐慌性抛售
- **教训**：熔断信号是清仓信号

---

## 后续优化方向

### 待开发功能
1. **对冲工具**：股指期货、期权策略（当前无对冲）
2. **机器学习预警**：极端行情预测模型
3. **情绪指标**：舆情监控、资金流向分析

### 系统升级
1. **自适应止损**：强化学习优化参数
2. **跨市场对冲**：AH股套利策略
3. **实时推送**：WebSocket接入飞书通知

---

## 参考文档

- `references/call-auction-handling.md` — 集合竞价阶段数据处理技术详解
- `references/python-environment.md` — Python 环境配置与依赖安装

---

## 文件路径

| 文件 | 用途 |
|------|------|
| `scripts/liquidity_monitor.py` | 流动性监控脚本 |
| `scripts/extreme_market_alert.py` | 极端行情预警脚本 |
| `scripts/dynamic_stop_loss.py` | 动态止损计算脚本 |
| `scripts/risk_controller.py` | 风控模块（已集成动态止损） |
| `data/liquidity_monitor/` | 流动性监控数据存储 |
| `data/extreme_alerts/` | 极端预警数据存储 |
| `data/dynamic_stop_loss/` | 动态止损报告存储 |

---

## 注意事项

1. **Cron时间**：流动性监控9:15，极端行情预警9:30（开盘后5分钟）
2. **波动率计算**：使用20日历史波动率，年化（×√252）
3. **市场阶段**：从 `market_phase_detector_daily.py` 获取
4. **数据源**：AkShare（Sina实时行情）+ Baostock（历史数据）

---

## 常见问题与陷阱

### Pitfall #1: Eastmoney API 代理阻断
- **现象**：`ak.stock_zh_a_spot_em()` 报错 `ProxyError: Unable to connect to proxy`
- **原因**：东方财富 API 在此环境被代理阻断
- **解决**：使用 Sina 数据源 `ak.stock_zh_a_spot()`
- **注意**：Sina 数据列名略有不同，脚本已适配

### Pitfall #2: 集合竞价阶段数据为空
- **现象**：9:15-9:25 运行时，所有 `涨跌幅=0`、`成交额=0`
- **原因**：集合竞价尚未成交，数据尚未生成
- **解决**：使用 `买入价/昨收价` 计算预期涨跌停
- **验证**：已有开盘股票数（`今开>0`）可作为参考

### Pitfall #3: Python 环境问题
- **现象**：venv Python 报 `ModuleNotFoundError: No module named 'akshare'`
- **原因**：hermes-agent venv 未安装 akshare
- **解决**：使用 `/Users/hy_timesky/.pyenv/versions/3.11.15/bin/python`
- **注意**：安装依赖用 `/Users/hy_timesky/.pyenv/versions/3.11.15/bin/pip`

### Pitfall #4: numpy/pandas 版本兼容
- **现象**：`ValueError: numpy.dtype size changed`
- **原因**：pandas 与 numpy 版本不兼容
- **解决**：`pip install --upgrade pandas numpy`
- **预防**：使用 pyenv Python 已安装正确版本

---

**创建日期**: 2026-05-04  
**状态**: 已部署并验证
