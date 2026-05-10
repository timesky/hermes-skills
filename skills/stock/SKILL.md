---
name: stock
description: A股量化分析技能 — 实时行情、历史数据、策略回测
trigger_words: [股票, 行情, 指数, quote, trending, 回测, 策略, quant]
tags: [stock, finance, market, a-stock, cn, quant, backtest]
---

# Stock A股量化分析技能

## 功能概述

提供A股市场量化分析能力：

| 功能 | 命令 | 说明 |
|------|------|------|
| **实时行情** | `quote <symbol>` | 查询单只股票实时价格（pytdx） |
| **历史K线** | `history <symbol>` | 历史K线数据（Baostock） |
| **指数查询** | `index <code>` | 上证、深成、沪深300等 |
| **搜索** | `search <keyword>` | 搜索股票名称/代码 |
| **策略回测** | `backtest <symbol>` | 运行双均线策略回测 |
| **技术指标** | `indicator <symbol>` | 计算MA/RSI/MACD指标 |
| **实盘模拟** | `paper_trading predict <symbol>` | 预测次日走势（2万本金） |
| **实盘验证** | `paper_trading validate <symbol>` | 验证昨日预测 |
| **实盘状态** | `paper_trading status` | 查看账户状态 |

---

### 手动运行

```bash
cd ~/.hermes/profiles/stock
python3 scripts/market_phase_detector_daily.py
```

**⚠️ 注意**：脚本需要较长执行时间（约2分钟），建议 timeout=300

详见 `references/market-phase-feishu-push.md`

---

## 实盘模拟系统（Paper Trading）

### ⚠️ 核心区别：实盘模拟 vs 回测

| 维度 | 回测 | 实盘模拟 |
|------|------|----------|
| **数据方向** | 验证过去 | **预测未来** |
| **输出** | 策略表现统计 | **次日交易计划** |
| **优化机制** | 参数调优 | **偏差反思→微调→回测→应用/回滚** |
| **数据集** | 历史（训练/验证/测试） | **实时数据，每日更新** |
| **目的** | 找出历史最优策略 | **验证策略在未知未来的表现** |

### 每日循环流程

```
┌─────────────────────────────────────────────────────────────┐
│                    实盘模拟每日循环                            │
├─────────────────────────────────────────────────────────────┤
│  Day N收盘后（15:30）                                          │
│    ↓                                                         │
│  【步骤1：验证昨日预测】                                        │
│    • 对比预测最低价/最高价 vs 实际                              │
│    • 计算偏差%（准确度评分：≥80优秀、60-80中等、<60需优化）      │
│    • 判断交易是否成功                                          │
│    ↓                                                         │
│  【步骤2：反思与策略微调】                                      │
│    • 准确度 < 60分 → 触发策略反思                              │
│    • 分析偏差原因（ATR系数、RSI阈值等）                         │
│    • 生成调整建议                                              │
│    ↓                                                         │
│  【步骤3：更新持仓市值】                                        │
│    • 用最新收盘价更新持仓价值                                   │
│    • 计算总资产、回撤                                          │
│    ↓                                                         │
│  【步骤4：生成次日预测】                                        │
│    • 预测次日最低价/最高价（基于ATR）                          │
│    • 预测振幅、走势模式（低开高走/高开低走/震荡）                │
│    • 给出操作建议（买入/卖出/持有 + 价格 + 数量）               │
│    ↓                                                         │
│  【步骤5：执行模拟交易】                                        │
│    • 自动执行预测中的交易操作                                   │
│    • 更新持仓和现金                                            │
│    ↓                                                         │
│  【步骤6：生成绩效报告】                                        │
│    • 总收益率、胜率、回撤                                      │
│    • 保存每日报告JSON                                          │
└─────────────────────────────────────────────────────────────┘
```

### 预测内容说明

| 预测项 | 计算方法 | 用途 |
|--------|----------|------|
| **预测最低价** | `last_close - ATR × 0.5` | 判断买入价位是否触及 |
| **预测最高价** | `last_close + ATR × 0.5` | 判断卖出价位是否触及 |
| **预测振幅** | `ATR / last_close × 100%` | 预期波动范围 |
| **走势模式** | RSI判断（<30超卖反弹，>70超买回落，否则震荡） | 选择策略方向 |
| **操作建议** | 综合 RSI + 布林带 + 止损止盈规则 | 具体买卖指令 |

### 验证评分标准

```python
# 准确度评分
accuracy_score = 100 - (low_deviation + high_deviation + amplitude_deviation) / 3

# 评分等级
if accuracy_score >= 80:
    level = "优秀，策略有效"
elif accuracy_score >= 60:
    level = "中等，需微调"
else:
    level = "偏差大，触发优化"
```

### 核心脚本

```bash
# 实盘模拟引擎（核心模块）
~/.hermes/profiles/stock/scripts/paper_trading.py

# 每日运行脚本（6步流程，可能超时）
~/.hermes/profiles/stock/scripts/paper_trading_daily.py

# 轻量级简报脚本（用于Cronjob，<1秒运行）← 推荐用于定时任务
~/.hermes/profiles/stock/scripts/paper_trading_summary.py

# 手动运行完整流程
python3 ~/.hermes/profiles/stock/scripts/paper_trading_daily.py

# 手动运行简报（快速查看）
python3 ~/.hermes/profiles/stock/scripts/paper_trading_summary.py

# 查看SQLite数据库
sqlite3 ~/.hermes/profiles/stock/data/paper_trading/paper_trading.db
# 常用查询：SELECT * FROM positions WHERE date='2026-05-07' GROUP BY symbol;
```

### 数据存储结构

```
~/.hermes/profiles/stock/data/paper_trading/
├── paper_trading.db     # SQLite数据库（主数据源，2026-05-07升级）
│   ├── account_summary  # 每日账户概况
│   ├── positions        # 每日持仓记录
│   ├── predictions      # 预测记录+验证结果
│   ├── stock_pool       # 选股池
│   └── trades           # 交易记录
├── portfolio.json       # 当前持仓（备份）
├── trades.json          # 交易记录列表（备份）
├── predictions.json     # 预测记录列表（备份）
├── strategy.json        # 当前策略版本
└── reports/             # 每日报告
    └── daily_2026-05-02.json
```

**⚠️ 注意**：2026-05-07后数据主要存储在SQLite，JSON文件为备份格式。查询优先使用SQLite。

### 定时任务

| 任务 | 时间 | ID | 说明 |
|------|------|-----|------|
| 实盘模拟每日运行 | 15:30 | 796080992d59 | 预测→验证→优化循环 |

### 策略微调与回滚机制

```python
# 微调触发条件
if accuracy_score < 60:
    # 反思偏差原因
    adjustments = analyze_deviation(verification)
    
    # 生成新策略版本
    new_strategy = adjust_parameters(current_strategy, adjustments)
    new_strategy['version'] += 1
    
    # 回测验证
    backtest_result = backtest(new_strategy)
    
    # 决定应用或回滚
    if backtest_result > current_strategy['backtest_score']:
        apply_strategy(new_strategy)  # 应用
    else:
        rollback()  # 回滚，保持原策略
```

### 初始化参数

```python
INITIAL_CAPITAL = 20000       # 初始本金2万
MAX_POSITION_PCT = 0.70       # 总仓位≤70%
MAX_SINGLE_STOCK_PCT = 0.30   # 单股≤30%
STOP_LOSS_PCT = -0.10         # 止损-10%
TAKE_PROFIT_PCT = 0.20        # 止盈+20%
MAX_DRAWDOWN_PCT = 0.05       # 回撤≤5%
```

### 与三层架构的关系

```
┌─────────────────────────────────────────────────────────────┐
│ 第一层：策略调研层（0:00）                                    │
│   抓取新策略 → 历史数据回测 → 注册到策略库                     │
└─────────────────────────────────────────────────────────────┘
                           ↓ 提供策略
┌─────────────────────────────────────────────────────────────┐
│ 第二层：实盘模拟层（15:30）← 本系统                           │
│   预测次日 → 验证偏差 → 反思微调 → 回测对比 → 应用/回滚        │
└─────────────────────────────────────────────────────────────┘
                           ↓ 输出验证后策略
┌─────────────────────────────────────────────────────────────┐
│ 第三层：实际持股建议层（9:15）                                 │
│   读取验证后策略 → 结合用户持股 → 生成今日操作建议             │
└─────────────────────────────────────────────────────────────┘
```

**关键点**：第三层使用的是实盘模拟验证后的策略，而非直接使用第一层的回测策略。实盘模拟充当了"策略过滤器"的角色。

---

## 选股池生成系统（热门板块优先）

**核心设计**：热门板块用趋势跟随策略，全市场用底部反转策略

### 双策略架构

| 策略类型 | 适用对象 | 核心指标 |
|----------|----------|----------|
| 趋势跟随 | 热门板块成分股 | 均线多头、RSI适中、放量上涨 |
| 底部反转 | 全市场股票 | RSI超卖、震荡底部、回调买入 |

### 热门板块加分权重

| 排名 | 加分 | 说明 |
|------|------|------|
| TOP1 | +50分 | 今日涨幅最大板块 |
| TOP2-3 | +40分 | 第二梯队板块 |
| TOP4-5 | +30分 | 第三梯队板块 |

### 关键发现

热门板块股票不适合底部反转策略：
- 热门板块今日涨幅+5%~+7%，成分股正在上涨
- 底部反转策略寻找震荡区间底部 → 热门股票不符合
- **必须用趋势跟随策略评估热门股票**

详见 references/hot-sector-stock-selection.md

### 脚本路径

```bash
# 运行选股池生成
python3 ~/.hermes/profiles/stock/scripts/stock_pool_generator.py

# 输出文件
~/.hermes/profiles/stock/data/paper_trading/buy_pool.json
```

---

## 命令用法

```bash
# 实时行情（通达信数据，秒级延迟）
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py quote 000001

# 历史K线
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py history 000001 --start 20240101 --end 20241231

# 指数查询
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py index sh000001

# 涨幅榜
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py trending --limit 20

# 搜索股票
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py search 平安

# 策略回测（双均线策略）
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py backtest 000001 --fast 5 --slow 20

# 技术指标
python3 ~/.hermes/profiles/stock/skills/stock/scripts/stock.py indicator 000001 --ma 5,10,20 --rsi 14

# ========== 每日分析（自动缓存+增量更新） ==========
# 执行分析（自动判断全量/增量）
python3 ~/.hermes/profiles/stock/skills/stock/scripts/daily_analyzer.py analyze 600584

# 强制全量更新
python3 ~/.hermes/profiles/stock/skills/stock/scripts/daily_analyzer.py analyze 600584 --full

# 查看缓存状态
python3 ~/.hermes/profiles/stock/skills/stock/scripts/daily_analyzer.py status 600584

# 清理缓存
python3 ~/.hermes/profiles/stock/skills/stock/scripts/daily_analyzer.py clean 600584

# ========== 持仓管理 ==========
# 查看持仓列表
python3 ~/.hermes/profiles/stock/skills/stock/scripts/portfolio.py list

# 持仓分析（结合策略）
python3 ~/.hermes/profiles/stock/skills/stock/scripts/portfolio.py analyze

# 添加持仓
python3 ~/.hermes/profiles/stock/skills/stock/scripts/portfolio.py add 600584 --shares 200 --price 45.56 --strategy 5日线

# 调整持仓
python3 ~/.hermes/profiles/stock/skills/stock/scripts/portfolio.py update 600584 --shares 300

# 清仓
python3 ~/.hermes/profiles/stock/skills/stock/scripts/portfolio.py remove 600584
```

## 数据源架构

```
┌─────────────────────────────────────────────────────┐
│  实时数据层      │  pytdx (通达信服务器)             │
│                  │  - 秒级行情                       │
│                  │  - 无需token                       │
│                  │  - 支持K线/分时/板块               │
├─────────────────────────────────────────────────────┤
│  历史数据层      │  Baostock (证券宝)                │
│                  │  - 完整历史K线                     │
│                  │  - 复权数据                        │
│                  │  - 免费、稳定                      │
│                  │  - 全市场缓存：5220只，1GB         │
├─────────────────────────────────────────────────────┤
│  财务数据层      │  AkShare (新浪财经+同花顺)        │
│                  │  - 资产负债表/利润表/现金流量表   │
│                  │  - 财务指标摘要                    │
│                  │  - 全市场缓存：5220只，~1GB        │
│                  │  - 每季度更新                      │
├─────────────────────────────────────────────────────┤
│  补充数据层      │  AkShare (东方财富)               │
│                  │  - 板块数据                        │
│                  │  - 涨跌幅榜                        │
├─────────────────────────────────────────────────────┤
│  回测引擎        │  Backtrader                       │
│                  │  - 策略回测                        │
│                  │  - 技术指标                        │
│                  │  - 绩效分析                        │
└─────────────────────────────────────────────────────┘
```

## 财务数据缓存系统

### 功能

缓存A股全市场财务报表数据，支持策略分析时快速查询。

### 数据内容

| 类型 | 接口 | 说明 |
|------|------|------|
| **资产负债表** | `stock_financial_report_sina` | 147列 × 95行 |
| **利润表** | `stock_financial_report_sina` | 83列 × 98行 |
| **现金流量表** | `stock_financial_report_sina` | 71列 × 93行 |
| **财务指标摘要** | `stock_financial_abstract_ths` | 25列 × 98行 |

### 命令用法

```bash
# 全量更新（首次运行，约3小时）
python3 ~/.hermes/profiles/stock/scripts/financial_cache.py full

# 断点续传
python3 ~/.hermes/profiles/stock/scripts/financial_cache.py full --resume

# 增量更新（季度财报发布后）
python3 ~/.hermes/profiles/stock/scripts/financial_cache.py incremental

# 查看状态
python3 ~/.hermes/profiles/stock/scripts/financial_cache.py status
```

### 数据路径

```
~/.hermes/profiles/stock/data/financial_cache/
├── balance/              # 资产负债表
├── profit/               # 利润表
├── cashflow/             # 现金流量表
├── indicator/            # 财务指标摘要
└── metadata.json         # 元数据
```

### 定时任务

| 任务 | 时间 | ID | 说明 |
|------|------|-----|------|
| 财务数据季度更新 | 每季度首日2:00 | 54c196ee194b | 增量更新最新财报 |

### 使用示例

```python
import pandas as pd

# 加载资产负债表
balance = pd.read_csv('~/.hermes/profiles/stock/data/financial_cache/balance/600584.csv')

# 查看最新季度总资产
latest = balance.iloc[0]
print(f"总资产: {latest['资产总计']}")

# 加载财务指标
indicator = pd.read_csv('~/.hermes/profiles/stock/data/financial_cache/indicator/600584.csv')
print(f"ROE: {indicator.iloc[0]['净资产收益率']}")
```

## 策略注册表系统

**目的**：策略去重、版本管理、演化追踪

### 核心概念

| 概念 | 说明 |
|------|------|
| **策略指纹** | `md5(策略类型 + 参数排序)` 的前16位，唯一标识一个策略配置 |
| **版本管理** | 记录策略状态：discovered → tested → applied → evolved |
| **演化追踪** | 子策略记录 `parent_id`，建立演化树 |

### 文件路径

```
~/.hermes/profiles/stock/data/strategy_registry.json
~/.hermes/profiles/stock/scripts/strategy_registry.py
~/.hermes/profiles/stock/scripts/strategy_researcher.py
```

### 注册表结构

```json
{
  "strategies": {
    "macd_12_26_9": {
      "name": "MACD策略",
      "fingerprint": "macd_12_26_9",
      "source": "经典技术指标",
      "params": {"fast": 12, "slow": 26, "signal": 9},
      "status": "classic",
      "added_date": "2026-05-01"
    }
  },
  "metadata": {
    "total_strategies": 16,
    "last_updated": "2026-05-01"
  }
}
```

### 去重逻辑

```python
# 添加新策略前检查
fingerprint = generate_fingerprint(strategy_type, params)
if fingerprint in registry["strategies"]:
    return "duplicate"  # 跳过
```

### 定期调研任务

| 任务 | 时间 | ID | 说明 |
|------|------|-----|------|
| 每周策略调研 | 周日9:00 | 80c690256697 | 知乎搜索新策略，自动去重 |

---

## 策略来源大全

详细来源见 `references/strategy_sources.md`

### 一、已集成策略来源

| 来源 | 策略 | 文件 | 状态 |
|------|------|------|------|
| **知乎** | 自定义均线(MA7/22/53/87) | `custom_ma_strategy.py` | ✅ |
| **抖音** | 五日不破策略 | `five_day_hold_strategy.py` | ✅ |
| **经典** | 双均线、海龟、RSI、布林带 | `quant_platform.py` | ✅ |

### 二、待调研来源（优先级）

#### 高优先级 ✅

| 来源 | 网址 | 策略类型 |
|------|------|----------|
| **知乎** | zhihu.com | A股实战策略 |
| **聚宽** | joinquant.com | 回测验证策略 |
| **米筐** | ricequant.com | 因子研究 |
| **经典书籍** | 海龟交易法则、量化交易 | 书籍策略 |

#### 中优先级 ⚠️

| 来源 | 内容 | 注意事项 |
|------|------|----------|
| **X/Twitter** | 海外量化讨论 | 需验证可信度 |
| **GitHub** | vn.py/qlib开源策略 | 需筛选质量 |
| **券商研报** | 因子研究报告 | 可能过拟合 |

### 三、经典策略推荐

#### 技术分析策略（易实现）

| 策略 | 来源 | 适用行情 | 难度 |
|------|------|----------|------|
| 双均线 | 经典 | 上升 | ⭐ |
| 海龟交易 | 书籍 | 上升 | ⭐⭐ |
| RSI超买超卖 | 经典 | 震荡 | ⭐ |
| 布林带 | 经典 | 震荡 | ⭐⭐ |
| KDJ金叉死叉 | 经典 | 短期 | ⭐ |

#### 因子策略（中等难度）

| 因子 | 论文来源 | 适用行情 |
|------|----------|----------|
| **动量因子** | Jegadeesh(1993) | 上升 |
| **价值因子** | Fama-French(1992) | 全行情 |
| **质量因子** | Novy-Marx(2013) | 全行情 |
| **低波动因子** | Ang(2006) | 下行 |
| **反转因子** | De Bondt(1985) | 下行 |

#### 机器学习策略（高难度）

| 方法 | 书籍来源 | 特点 |
|------|----------|------|
| **LSTM时序预测** | AFML(2018) | 需大量数据 |
| **XGBoost分类** | ML for AM(2020) | 特征工程复杂 |
| **随机森林** | 经典ML | 相对稳健 |

### 四、策略调研流程

```bash
# 1. 搜索知乎策略
# 关键词："A股量化"、"均线系统"、"因子投资"

# 2. 注册聚宽社区
# https://www.joinquant.com/
# 筛选：年化>15%，夏普>1，回撤<20%

# 3. 阅读经典论文
# 动量：Jegadeesh & Titman (1993)
# 价值：Fama & French (1992)
# 质量：Novy-Marx (2013)

# 4. 复现GitHub策略
# vn.py内置策略
# qlib因子库
```

**验证方法论**详见 `references/zhihu-strategy-verification.md`

---

## 内置策略

### 1. 双均线策略 (MaCross)
- 快均线上穿慢均线买入
- 快均线下穿慢均线卖出
- 参数：`--fast` (默认5), `--slow` (默认20)

### 2. RSI策略
- RSI < 30 超卖买入
- RSI > 70 超买卖出
- 参数：`--period` (默认14)

### 3. 布林带策略
- 突破下轨买入
- 突破上轨卖出
- 参数：`--period` (默认20), `--dev` (默认2)

### 4. 五日不破策略（经典策略）
- 核心规则：收盘价不破5日均线则持有
- 选股：站稳60日线 + 5日线向上 + 市值50-500亿
- 操作：3成建仓 + 3成加仓

**三重止损机制（原文规则）：**
| 止损类型 | 触发条件 | 说明 |
|----------|----------|------|
| 策略止损 | 收盘价 < MA5 × 0.98 | MA5下方2%，快速止损 |
| 清仓条件 | 连续2日收盘跌破MA5 | 慢速止损，给确认机会 |
| 硬止损 | -10% | 保底止损 |

**⚠️ 止损优先级问题：**
- 当前代码先检查MA5下方2%，再检查连续2日跌破
- 大幅下跌时（如-7%），"有效跌破"需连续2日确认，滞后导致更大损失
- **优化建议**：增加"单日跌破MA5超过5%"快速止损

详见 `references/strategies.md`

### 5. 自定义均线策略（MA7/MA22/MA53/MA87）
- 来源：知乎文章《亏了3年才懂：默认均线就是主力陷阱》
- 核心思想：避开主力操控的默认均线(5/10/20/60)

**均线参数：**
| 均线 | 作用 | 替代默认 |
|------|------|----------|
| MA7 | 短期资金动向线 | MA5 |
| MA22 | 主力洗盘临界线（核心） | MA10 |
| MA53 | 中期成本均线 | MA20 |
| MA87 | 大趋势判断线 | MA60 |

**交易规则：**
| 操作 | 条件 |
|------|------|
| 买入 | ① 回调到MA22附近止跌（前置） + ② MA7金叉MA22（确认） + ③ 温和放量(1.2-3倍) + ④ 站稳MA87上方 |
| 持有 | 不破MA22 + MA87保持向上 |
| 卖出 | ① 跌破MA22+MA7死叉MA22 OR ② 跌破MA87+MA87向下拐头 |
| 止损 | 跌破MA22（收盘价 < MA22） |

**⚠️ 注意：买入条件是序列条件，不是并行条件**
- 原文："股价回调到22日均线附近止跌，**随后**7日均线上穿22日均线形成金叉"
- 必须先满足"回调止跌"，再等金叉确认
- 当前代码只检查金叉，漏掉了前置的"回调止跌"判断

```bash
# 回测自定义均线策略
python3 ~/.hermes/profiles/stock/skills/stock/scripts/custom_ma_strategy.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
```

## 策略对比回测

同时运行多个策略对比效果：

```bash
# 五日不破 vs 自定义均线 对比回测
python3 ~/.hermes/profiles/stock/skills/stock/scripts/strategy_comparison.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
```

**回测结论（2023-2026）：**

| 股票类型 | 推荐策略 | 原因 |
|----------|----------|------|
| 趋势蓝筹（招行、茅台） | 五日不破 | 捕捉主升浪，频繁加仓 |
| 震荡股（长电科技） | 自定义均线 | 严控回撤，过滤假信号 |
| 高波动股（比亚迪） | 都不适合 | 需结合其他指标 |

**关键发现：**
- 自定义均线策略：交易少(2-3次)、回撤小(8-10%)、盈亏比高(6:1)
- 五日不破策略：交易多(25-35次)、适合趋势股、蓝筹表现好

## 策略验证工作流

**策略实现后必须对照原文验证！** 常见偏差来源：

1. **用 session_search 找回原文规则**
   ```python
   session_search(query="五日不破 OR 策略规则")
   ```

2. **制作对照表逐项核对**
   | 规则项 | 原文要求 | 代码实现 | 状态 |
   |--------|----------|----------|------|
   | 入场条件 | 连续2日站稳MA5 | `days_above_ma5 >= 2` | ✅ |
   | 止损条件 | MA5下方2% | 缺失 | ❌ |

3. **常见偏差类型**
   - **序列条件变并行**：原文"先A，随后B"，代码实现成"A and B"同时检查
   - **止损优先级错误**：止损先触发导致其他卖出条件永不生效
   - **模糊规则未量化**："当天无法收回"需要明确为"收盘价<均线"

详见 `references/strategy-validation.md`

---

## 斜率计算与回调识别

### 均线斜率计算（推荐线性回归）

```python
import numpy as np

def linear_regression_slope(values, period=22):
    """计算均线斜率（百分比）"""
    x = np.arange(period)
    y = np.array(values[-period:])
    slope, _ = np.polyfit(x, y, 1)
    slope_pct = (slope / y[0]) * 100  # 百分比斜率
    return slope_pct

# 斜率阈值：
# slope_pct > 0.5  → 上升趋势（适合判断"回调"）
# slope_pct < -0.5 → 下降趋势（不是回调，是下跌）
```

### 回调识别三要素

```python
# "回调到MA22附近止跌"判断：

# 1. MA22斜率向上（上升趋势未破坏）
ma22_slope_pct > 0.5

# 2. 从高点回撤到MA22附近
recent_high = max(high[-20:])
drawdown = (recent_high - close) / recent_high
near_ma22 = abs(close - ma22) / ma22 <= 0.05
pullback_ok = 0.05 <= drawdown <= 0.15 and near_ma22

# 3. 止跌信号
stopped_falling = low[0] >= low[-1]  # 最低价不再创新低

# 综合判断
is_pullback = ma22_slope_pct > 0.5 and pullback_ok and stopped_falling
```

**方法对比：**
| 方法 | 噪点控制 | 滞后性 | 推荐度 |
|------|----------|--------|--------|
| 简单斜率/ROC | ❌ 差 | ✅ 无 | 不推荐 |
| 双重SMA | ✅ 好 | ❌ 有滞后 | 备选 |
| **线性回归** | ✅ 最佳 | ✅ 较小 | **推荐** |

详见 `references/slope-calculation-methods.md`

---

---

## 策略行情适配测试（按行情阶段测试）

**核心原则**：策略测试按行情阶段分类，找出每个行情下的最优策略，而非针对特定股票。

### 行情阶段定义

| 行情阶段 | 判断标准 | 推荐策略类型 |
|----------|----------|--------------|
| **震荡市** | 近20日涨跌±10%，波动率<2% | RSI、布林带、均值回归、均线乖离率 |
| **上升趋势** | 近20日涨跌>+10%，MA20向上 | 海龟、唐奇安、双均线、动量因子 |
| **下跌趋势** | 近20日涨跌<-10%，MA20向下 | 均值回归（防御）、空仓/减仓 |

### 测试流程

```bash
# 1. 判断当前行情状态（基于沪深300）
# 2. 选取代表性时期历史数据
# 3. 对所有策略进行回测
# 4. 输出该行情阶段的最优策略排名

# 运行行情适配测试
python3 ~/.hermes/profiles/stock/scripts/strategy_market_test_full.py
```

### 测试结果解读

| 输出字段 | 含义 | 说明 |
|----------|------|------|
| `收益%` | 策略收益率 | 正值盈利，负值亏损 |
| `胜率%` | 盈利交易占比 | 高胜率≠高收益（需结合回撤） |
| `回撤%` | 最大回撤 | 回撤控制比收益更重要 |
| `适配` | 策略-行情匹配 | ✅表示策略适用当前行情 |

### 测试结论示例（震荡市）

| 排名 | 策略 | 收益率 | 回撤 | 适配 |
|------|------|--------|------|------|
| **1** | 三均线系统MA5-20-60 | +2.61% | 0.87% | |
| 2 | 均线乖离率策略 | +1.28% | 0.00% | ✅ |
| 3 | 布林带突破策略 | +1.15% | 3.62% | ✅ |
| ... | MACD策略 | -2.28% | 7.40% | ❌不适合震荡 |

**关键发现**：
- 趋势策略（MACD、海龟）在震荡市表现不佳
- 震荡适配策略（布林带、均值回归）表现稳定
- 回撤控制是核心指标，比收益更重要

### 策略注册表测试状态

测试后自动更新策略注册表，每条策略添加 `test_result` 字段：

```json
{
  "test_result": {
    "profit_pct": 2.61,
    "win_rate": 7.9,
    "max_drawdown": 0.87,
    "tested_date": "2026-05-01",
    "market_state": "震荡市"
  },
  "status": "tested"
}
```

### Pitfalls

| 问题 | 解决方案 |
|------|----------|
| pytdx连接失败 | 切换服务器IP列表，218.75.126.9:7709已验证可用 |
| AkShare代理错误 | 检查代理设置或直连 |
| 股票代码格式 | 深市前加0，沪市前加1 (pytdx格式) |
| Baostock登录失败 | 无需注册，自动匿名登录 |
| Backtrader中文乱码 | 设置 matplotlib 字体 |
| pytdx成交量单位 | 返回值是"手"，需×100换算股数 |
| Baostock代码格式 | 必须加sh./sz.前缀 (如sh.600000) |
| **Vision识别股票截图错误** | 交易截图OCR常出错：代码/方向/价格小数点，必须二次核对 |
| **截图识别问题清单** | ①股票代码错误 ②买卖方向颠倒 ③价格小数点错位 ④数量级错误（5千变5万） |
| **回测数据缓存缺失** | 使用带缓存的回测脚本 `five_day_hold_backtest.py`，缓存路径 `~/.hermes/profiles/stock/data/cache/{symbol}/` |
| **rolling()参数错误** | `window`必须是正整数，用`max(int(period), 5)`保护 |
| **策略调用参数丢失** | 策略函数需显式传递参数（如`period=14, std_dev=2`），不能依赖默认值 |
| **行情状态判断数据不足** | 至少需要20根K线判断行情状态，否则返回'unknown' |
| **进化结果文件路径** | `~/.hermes/profiles/stock/data/evolution/evolution_gen*.json`，文件名含时间戳 |
| **网页抓取方式** | 使用OpenCLI browser命令，非内置browser工具。用完执行 `opencli browser close` |
详见 `references/akshare-network-troubleshooting.md`
| **market_cache.py日期比较bug** | 第585行 `last_date >= end_date.replace('-', '')` 格式不一致：`last_date`='2026-05-06'（带连字符），`end_date.replace('-', '')`='20260506'（无连字符），字符串比较 `'2026-05-06' < '20260506'`（因ASCII '-'(45) < '0'(48)），导致所有股票被误判需要更新 → **修复方案**：统一格式为 `last_date >= end_date` 或 `last_date.replace('-', '') >= end_date.replace('-', '')`。详见 `references/market-cache-incremental-bug.md` |
| **Baostock数据更新时间** | Baostock当日K线数据在收盘后约 **18:00-20:00** 才更新完成，非16:00立即更新 → **Cronjob安排**：增量更新任务应在 **19:00或20:00** 执行，而非16:00。16:00运行时当日数据返回空结果。详见 `references/market-cache-incremental-bug.md` |
| **Cronjob输出简略/空洞** | `paper_trading_daily.py` 运行超时（>120s）导致cronjob只收到部分输出 → **解决方案**：使用轻量级脚本 `paper_trading_summary.py`（从SQLite读取，无网络请求，<1秒运行）。详见 `references/paper-trading-system.md` |
| **SQLite查询重复记录** | positions/predictions表可能有重复记录 → **查询时使用 GROUP BY symbol** 避免重复显示。详见 `references/paper-trading-system.md`（SQLite数据库结构） |

---

## 工作流聚焦原则

**用户反馈**："你不是在做板块分析和实际对比吗？怎么又跑到那个平台分析去了？"

**原则**：
- 用户指定任务时，聚焦主线任务，不要分支到相关研究
- 例如：用户要对比板块涨跌 → 直接获取数据对比，不要跑去调研量化平台
- 相关研究可以并行记录，但不要打断主线流程输出
| **策略调研流程（知乎）** | ① `opencli browser open "https://www.zhihu.com/search?type=content&q=关键词"` → ② `opencli browser wait time 3`（等待加载）→ ③ `opencli browser state`（查看页面结构）→ ④ `opencli browser click @eN`（进入文章详情）→ ⑤ `opencli browser extract \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d['content'])"` → ⑥ `opencli browser close` |
| **评论验证技巧** | ⚠️ 知乎策略文章常夸大胜率（营销卖软件）。务必检查评论区是否有用户回测验证。案例：声称88%胜率→评论区验证31.9%实际胜率。发现夸大时，记录 `verification_note` 字段，标记为 `verified: false` |
| **OpenCLI browser常用命令** | `open`（打开URL）、`state`（查看页面元素）、`click @eN`（点击元素）、`extract`（提取内容）、`back`（后退）、`wait time N`（等待秒数）、`close`（关闭窗口） |
| **持仓文件格式兼容** | portfolio.json 支持字典和列表两种格式，字段名 `shares`/`quantity`、`cost_price`/`cost` 均可识别 |

---

## 板块分析与科创板跟踪

### 板块预测验证工作流

用户有中长期板块预期时，对比实际市场表现验证判断：

```bash
# 获取当日板块排行
python3 -c "
import akshare as ak
df = ak.stock_board_industry_name_em()
print(df.head(20))  # TOP20板块
"
```

**关键步骤**：
1. 定义预期板块关键词映射（如"CPO" → ["通信线缆", "通信设备"])
2. 搜索匹配板块，查看排名和涨跌幅
3. 计算准确度（命中率）
4. 保存报告到 `knowledge/raw/` → 推送飞书

详见 `references/sector-analysis-star-market.md`

### 科创板指数跟踪

**投资门槛**：50万元+2年经验（用户资金不足）

**替代方案**：
- 科创50ETF (588000)：几十元门槛
- 场外联接基金：10元起购

**科创50成分股匹配度**：
- 半导体权重25%（与用户预期高度匹配）
- 光通信权重15%
- 军工航天权重10%

详见 `references/sector-analysis-star-market.md`

---

## 未来函数验证

**回测策略必须验证未来函数问题！**

### 验证要点

| 数据 | Backtrader获取方式 | 未来函数风险 |
|------|-------------------|--------------|
| 当天收盘 | `close[0]` | ✅ 安全（收盘后数据） |
| 当天MA5 | `ma5[0]` | ✅ 安全（含当天收盘） |
| 次日数据 | `close[-1]` | ❌ **危险！未来数据** |
| 指标未来值 | `ma5[-1]` | ❌ **危险！未来数据** |

### Backtrader索引规则

```python
# 正确用法（当天数据，收盘后可用）
current_close = self.close[0]  # 当天收盘价
ma5_today = self.ma5[0]        # 当天MA5（含当天收盘）

# 错误用法（未来函数）
next_close = self.close[-1]    # 次日收盘价 - 未来数据！
ma5_next = self.ma5[-1]        # 次日MA5 - 未来数据！
```

### 验证方法

1. **打印信号判断数据**
   ```python
   def next(self):
       current_date = self.data.datetime.date(0)
       current_close = self.close[0]
       ma5 = self.ma5[0]
       print(f'[{current_date}] 信号判断: 收盘{current_close:.2f}, MA5{ma5:.2f}')
   ```

2. **检查执行时机**
   - 信号触发：当天收盘后判断
   - 订单执行：次日开盘价（正常滑点）
   - 若执行价格 = 信号价格，需警惕是否用了未来数据

3. **典型未来函数案例**
   | 错误写法 | 问题 |
   |----------|------|
   | `if close[-1] > ma5[-1]` | 用次日数据判断，次日不可能知道 |
   | `order = self.buy(execute=close[0])` | 用当天收盘价成交，实际需次日开盘 |

### 带缓存的回测脚本

```bash
# 使用带缓存的回测（避免重复下载）
python3 ~/.hermes/profiles/stock/skills/stock/scripts/five_day_hold_backtest.py \
  --code sh.600584 --start 2024-01-01 --end 2026-04-30

# 缓存文件位置
~/.hermes/profiles/stock/data/cache/sh_600584/2024-01-01_2026-04-30.csv
```

## 框架选择原则

**纯本地分析/回测场景 → 用 Backtrader，不用 vn.py**

| 对比 | vn.py | Backtrader |
|------|-------|------------|
| 定位 | 全功能交易框架 | 纯回测框架 |
| 学习曲线 | 陡峭（事件驱动引擎） | 平缓（声明式策略） |
| A股数据接入 | 需额外配置 | Baostock直接整合 |
| 纯回测适用性 | 大材小用 | 刚好合适 |

**结论：** 纯本地分析用Backtrader；vn.py等需要实盘时再升级。详见 `references/quant-framework.md`

## 通达信服务器列表

| 服务器 | IP | 端口 |
|--------|-----|------|
| 通达信1 | 119.147.212.81 | 7709 |
| 通达信2 | 218.75.126.9 | 7709 |
| 通达信3 | 115.238.56.198 | 7709 |

## 支持的指数

| 代码 | 名称 | Baostock代码 |
|------|------|-------------|
| sh000001 | 上证指数 | sh.000001 |
| sz399001 | 深证成指 | sz.399001 |
| sh000300 | 沪深300 | sh.000300 |
| sz399006 | 创业板指 | sz.399006 |
| sh000016 | 上证50 | sh.000016 |
| sh000905 | 中证500 | sh.000905 |

## 统一量化平台架构（自进化闭环）

**核心设计**：数据/缓存/策略/模拟统一，自进化运行

```
┌─────────────────────────────────────────────────────────────┐
│ 自进化引擎 (strategy_evolution.py)                           │
│ 目标：2万本金持续盈利，自动发现/筛选/测试/进化策略            │
└─────────────────────────────────────────────────────────────┘
 │
 ┌───────────────────────────────────────────────────────────┐
 ▼                                                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1.策略发现    │ → │ 2.策略筛选    │ → │ 3.策略回测    │
│ 指标组合生成  │    | 可行性验证   │    │ 历史表现     │
└──────────────┘    └──────────────┘    └──────────────┘
                                             │
                      ┌──────────────────────┴────────────────────┐
                      ▼                                           ▼
               ┌──────────────┐                          ┌──────────────┐
               │ 4.策略对比    │                          │ 5.策略进化    │
               │ 多维度排名    │ ←─────────────────────── │ 参数变异     │
               └──────────────┘                          └──────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────┐      ┌──────────────────┐
│ 纯模拟实验        │      │ 持仓建议         │
│ (验证策略)        │      │ (最优策略应用)   │
│ 持续运行 ≥3个月   │      │ 给出操作建议     │
└──────────────────┘      └──────────────────┘
```

### 最优策略筛选标准

| 指标 | 阈值 | 说明 |
|------|------|------|
| 持续时间 | ≥3个月 | 实盘验证周期 |
| 盈利要求 | ≥20% | 累计盈利 |
| 胜率要求 | ≥70% | 盈利交易占比 |
| **判定** | 盈利20% **或** 胜率70% | 满足任一即为最优 |

### 行情状态自动匹配策略

| 行情状态 | 自动匹配策略 | 说明 |
|----------|--------------|------|
| **upward**（上升） | 双均线、海龟 | 趋势跟踪 |
| **sideways**（震荡） | 均值回归、RSI | 区间交易 |
| **downward**（下行） | 均值回归（防御） | 超跌反弹 |

### 自进化运行命令

```bash
# 运行一轮进化周期（发现→筛选→测试→对比）
python3 strategy_evolution.py test --symbol 600584

# 多轮进化（最多5轮，找到最优即停止）
python3 strategy_evolution.py evolve --symbol 600584 --generations 5
```

### 策略生成规则

```python
# 趋势策略（upward）
双均线: fast∈{5,7,10}, slow∈{20,22,60}
海龟: entry∈{20,55}, exit=entry//2

# 震荡策略（sideways）
布林带: period∈{10,20,30}, std∈{1.5,2,2.5}
RSI: period∈{6,9,14}, oversold∈{25,30}, overbought∈{70,75}

# 防御策略（downward）
均值回归: period∈{20,30}, std∈{2,2.5}
```

### 定时任务

| 任务 | 时间 | ID | 说明 |
|------|------|-----|------|
| 每日持仓分析 | 工作日15:30 | 157301551f27 | 用最优策略给建议 |
| 沪金价格监控 | 每30分钟 | e18d4a35ea34 | 触发阈值通知 |
| 每周策略进化 | 周六10:00 | 1188cde8b4be | 发现/测试新策略 |

### 数据流转

```
Baostock → 缓存（CSV） → 回测引擎 → JSON报告
    ↓
行情判断（upward/sideways/downward）
    ↓
策略匹配 → 模拟交易 → 结果评估
    ↓
是否最优？ → 是 → 应用于持仓
         ↓
         否 → 参数变异 → 下一轮进化
```

---

## 统一量化平台架构（组件层）

```
┌─────────────────────────────────────────────────────────────┐
│ 统一量化平台 (quant_platform.py)                             │
│ 目标：2万本金持续盈利                                         │
└─────────────────────────────────────────────────────────────┘
 │
 ┌─────────────────────┴─────────────────────┐
 ▼                                           ▼
 ┌──────────────────┐                    ┌──────────────────┐
 │ 数据层（统一）    │                    │ 策略层（统一）    │
 │ - K线数据         │                    │ - 五日不破        │
 │ - 缓存管理        │                    │ - 双均线          │
 │ - 行情状态判断    │                    │ - 均值回归        │
 │   (upward/       │                    │ - 海龟交易        │
 │    sideways/     │                    │ - 行情匹配        │
 │    downward)     │                    │   (自动切换)      │
 └──────────────────┘                    └──────────────────┘
 │                                           │
 └─────────────────────┬─────────────────────┘
                       ▼
               ┌──────────────────┐
               │ 模拟层（统一）    │
               └──────────────────┘
                │            │
      ┌─────────┴─┐    ┌────┴─────┐
      ▼           ▼    ▼          ▼
┌──────────┐ ┌──────────┐
│ 纯模拟实验│ │ 持仓建议 │
│ (验证策略)│ │ (操作建议)│
└──────────┘ └──────────┘
```

### 最优策略筛选标准

| 指标 | 阈值 | 说明 |
|------|------|------|
| 持续时间 | ≥3个月 | 实盘验证周期 |
| 盈利要求 | ≥20% | 累计盈利 |
| 胜率要求 | ≥70% | 盈利交易占比 |
| **判定** | 盈利20% **或** 胜率70% | 满足任一即为最优 |

### 行情状态匹配策略

| 行情状态 | 推荐策略 | 说明 |
|----------|----------|------|
| **upward**（上升） | 五日不破、海龟 | 趋势跟踪，捕捉主升浪 |
| **sideways**（震荡） | 均值回归、双均线 | 区间交易，低买高卖 |
| **downward**（下行） | 均值回归 | 超跌反弹，谨慎操作 |

### 运行命令

```bash
# 纯模拟实验（验证策略）
python3 quant_platform.py simulate 600584 --start 2024-01-01 --end 2026-04-30

# 持仓操作建议（用最优策略）
python3 quant_platform.py position ~/.hermes/profiles/stock/data/portfolio.json
```

---

## 持仓监控系统（基于统一平台）

**用户要求**：只定期分析，分策略给出建议，不执行交易

### 运行命令

```bash
cd /Users/hy_timesky/.hermes/profiles/stock/scripts
python3 position_monitor.py
```

### 输出格式

1. 每只股票单独列出
2. **6个策略独立建议**：五日不破、双均线、均值回归、RSI、布林带、海龟交易
3. 紧急程度标记：
   - ⚠️ HIGH（紧急）：止损触发、死叉信号
   - 📍 MEDIUM（关注）：买入信号、金叉信号
   - ✅ LOW（正常）：持有信号
4. 关键指标：MA5、止损价、快慢线、上下轨、持仓盈亏
5. 不推荐新股票，只分析已持仓

### 定时任务

| 任务 | 时间 | ID |
|------|------|-----|
| 每日持仓分析 | 工作日 15:30 | 157301551f27 |
| 沪金价格监控 | 每30分钟 | e18d4a35ea34 |

### 持仓文件

支持两种格式（quant_platform.py 已兼容）：

**格式A：字典格式（旧版）**
```json
{
  "initial_capital": 20000,
  "positions": {
    "601012": {
      "name": "隆基绿能",
      "shares": 100,
      "cost_price": 18.38,
      "strategies": ["five_day_hold", "ma_cross"]
    }
  }
}
```

**格式B：列表格式（推荐）**
```json
{
  "positions": [
    {
      "symbol": "600584",
      "name": "长电科技",
      "quantity": 200,
      "cost": 48.19,
      "buy_date": "2026-04-XX"
    }
  ],
  "total_cost": 16830.00,
  "updated_at": "2026-05-02"
}
```

**字段名兼容**: `shares`/`quantity`、`cost_price`/`cost` 均可识别。

**仓位调整需用户确认**，系统只给建议不执行交易。

### 多策略分析说明

持仓监控默认使用**全部6个策略**进行多角度分析，而非单一进化最优策略：

| 策略 | 适用行情 | 核心指标 |
|------|----------|----------|
| 五日不破 | 上升趋势 | MA5、止损价(MA5×0.98) |
| 双均线 | 上升/震荡 | 快线(MA5)、慢线(MA20)、金叉/死叉 |
| 均值回归 | 震荡/下行 | 20日均价、±2标准差上下轨 |
| RSI | 震荡 | RSI(14)、超卖(<30)/超买(>70) |
| 布林带 | 震荡 | 中轨(MA20)、上轨/下轨(±2σ) |
| 海龟交易 | 上升 | 20日高点、10日低点 |

**设计原因**：不同策略从不同维度分析持仓，综合判断比单一策略更可靠。

---

## 每日分析系统

### 架构设计

```
┌────────────────────────────────────────────────────────────┐
│  Cron Job (15:30 交易日)                                    │
│  └─→ daily_analyzer.py analyze <symbol>                     │
│       ├─ 检查交易日历（AkShare）                             │
│       ├─ 加载缓存元数据                                     │
│       └─ 判断更新策略                                       │
├────────────────────────────────────────────────────────────┤
│  数据层                                                     │
│  ├─ 日线K线: Baostock（免费稳定）                           │
│  ├─ 财报数据: AkShare（东方财富API）                        │
│  └─ 交易日历: AkShare（新浪接口）                           │
├────────────────────────────────────────────────────────────┤
│  缓存层 (~/.hermes/profiles/stock/data/cache/{symbol}/)     │
│  ├─ metadata.json      # 最后更新时间、上市日期              │
│  ├─ daily_kline.csv    # 日线数据（CSV格式，高效追加）       │
│  ├─ financials.json    # 财报数据（JSON格式）                │
│  └─ fundamentals.json  # 基本面数据（JSON格式）             │
├────────────────────────────────────────────────────────────┤
│  更新策略                                                   │
│  ├─ 首次运行: 全量获取5年历史（或从上市起）                   │
│  ├─ 日常运行: 增量获取新交易日数据（秒级响应）                │
│  └─ 强制全量: --full 参数                                   │
└────────────────────────────────────────────────────────────┘
```

### 定时任务设置模式

```bash
# 创建每日分析定时任务（cronjob action='create'）
# schedule: "30 15 * * 1-5" 表示周一到周五 15:30 执行

# 关键配置：
# - skills: ["stock"] 加载股票技能
# - deliver: "origin" 发送回原会话
# - prompt 中包含：
#   1. 检查交易日（非交易日跳过）
#   2. 执行分析命令
#   3. 发送报告
```

### 股票池扩展

编辑定时任务的 prompt，添加多个股票：

```
执行每日股票分析：
for symbol in 600584 000001 600519; do
  python3 ~/.hermes/profiles/stock/skills/stock/scripts/daily_analyzer.py analyze $symbol
done
```

### 已知问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 财报API超时 | 东方财富接口网络不稳定 | 等待网络恢复或使用代理 |
| 基本面数据缺失 | 同上 | 同上 |
| 非交易日执行 | cron无法判断交易日 | 脚本内置交易日判断逻辑 |

## 黄金股与金价相关性分析

### 核心概念

| 指标 | 含义 | 计算方法 |
|------|------|----------|
| **相关系数** | 黄金股与金价的同步性 | `df['股票'].corr(df['金价'])`，范围[-1, 1] |
| **贝塔系数** | 黄金股对金价的弹性（杠杆效应） | 股票涨跌幅 / 金价涨跌幅 |
| **建仓时金价** | 判断买入时机高低的关键 | 获取建仓日期对应的期货价格 |

### 相关性解读

| 相关系数 | 解读 | 操作建议 |
|----------|------|----------|
| > 0.7 | 强正相关 | 紧跟金价走势，金价跌则减仓 |
| 0.4-0.7 | 中等正相关 | 参考金价但不完全同步 |
| < 0.4 | 弱相关 | 金价参考价值有限 |

### 贝塔系数解读

| 贝塔系数 | 含义 | 风险特征 |
|----------|------|----------|
| > 5 | 高杠杆 | 金价涨1%股票涨5%+，波动剧烈 |
| 2-5 | 中等杠杆 | 标准黄金股弹性 |
| < 2 | 低杠杆 | 相对稳健，适合长期持有 |

### 分析脚本模板

```python
import akshare as ak
import pandas as pd
from datetime import datetime

# 1. 获取黄金股历史数据
stock_df = ak.stock_zh_a_hist(symbol="000506", period="daily",
                               start_date="20260101", end_date="20260430",
                               adjust="qfq")

# 2. 获取沪金期货主力合约数据
gold_df = ak.futures_zh_daily_sina(symbol="AU0")

# 3. 合并数据计算相关性
merged = pd.merge(stock_df[['日期', '收盘']], 
                  gold_df[['date', 'close']], 
                  left_on='日期', right_on='date')
corr = merged['收盘'].corr(merged['close'])

# 4. 计算贝塔系数
stock_change = (stock_df['收盘'].iloc[-1] / stock_df['收盘'].iloc[0] - 1) * 100
gold_change = (gold_df['close'].iloc[-1] / gold_df['close'].iloc[0] - 1) * 100
beta = stock_change / gold_change if gold_change != 0 else None

print(f"相关系数: {corr:.4f}")
print(f"贝塔系数: {beta:.2f}")
```

### 沪金期货数据源

| 接口 | 说明 | 用法 |
|------|------|------|
| `futures_zh_daily_sina` | 沪金主力历史数据 | `symbol="AU0"` 返回DataFrame |
| `futures_display_main_sina` | 主力合约列表 | 筛选 `symbol.str.contains('AU')` |

### 黄金股分析要点

1. **建仓时机判断**：对比建仓时金价与当前金价，判断是否高位建仓
2. **止损位设置**：根据贝塔系数推算，金价跌破关键位时股票对应价位
3. **反弹信号**：金价企稳（连续3日不创新低）是补仓窗口

### 典型黄金股

| 股票 | 代码 | 特点 |
|------|------|------|
| 招金矿业 | 000506 | A股黄金龙头，弹性大 |
| 山东黄金 | 600547 | 业绩稳定，贝塔中等 |
| 紫金矿业 | 601899 | 多金属布局，与金价相关性减弱 |
| 中金黄金 | 600489 | 央企背景，稳健型 |

---

## 输出示例

### 实时行情
```
=== 000001 平安银行 实时行情 ===

当前价: 11.06
涨跌幅: +0.45%
今开: 11.01
最高: 11.07
最低: 10.96
成交量: 63.0万手
成交额: 6952万
时间: 2026-04-20 15:00
```

### 策略回测
```
=== 双均线策略回测报告 ===

策略: 双均线(5/20)
标的: 000001 平安银行
周期: 2024-01-01 ~ 2024-12-31

回测结果:
  总收益率: +12.5%
  年化收益: 12.5%
  最大回撤: -8.3%
  夏普比率: 1.25
  胜率: 58.3%
  交易次数: 24
```

### 每日分析报告
```
## 📊 600584 每日分析报告
📅 2026-04-30

### 📈 行情概览
| 指标 | 数值 |
|------|------|
| 收盘价 | 45.56元 |
| 日涨跌 | +2.71% |
| 成交量 | 1.01亿股 |

### 🔧 技术指标
| 指标 | 数值 | 状态 |
|------|------|------|
| MA5 | 45.25 | 站上 |
| MA20 | 43.28 | 站上 |
| RSI(14) | 61.1 | 正常 |

### 📉 近期走势
- 5日: +1.49%
- 20日: +18.40%
```