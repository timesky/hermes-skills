---
name: autonomous-trading
description: 自主交易系统 — 市场阶段判定、策略选股、回测筛选、自动交易（目标盈利）
version: 1.0
created: 2026-05-04
author: Stock专家
---

# 自主交易系统

## 触发条件
- 用户要求"自主交易"、"自由选股"、"不要盯持股"
- 用户明确"目标是盈利"
- 用户要求系统独立运行策略和交易

## 核心理念
**不依赖用户持股，自主选股交易，目标盈利**

---

## ⚠️ 设计原则：动态双池架构（重要）

**不要使用硬编码股票列表！**

正确的设计是**双池模式**：

### 1. 选股池（Buy Pool）- 候选买入
- **来源**: 每日从全市场动态筛选
- **筛选逻辑**: 根据市场阶段选择策略
  - 熊市: RSI<30超卖反弹
  - 牛市: 回调3%-10%买入
  - 震荡: 网格策略底部（区间下沿30%）
- **输出**: `buy_pool.json`（前30名候选）

### 2. 持股池（Hold Pool）- 候选卖出
- **来源**: 从模拟账户持仓读取
- **检测信号**: 
  - 止损触发（-10%）
  - 止盈触发（+20%）
  - 策略反转（RSI>70、MA死叉）
  - 时间止盈（持仓>30天盈利5%+）
- **输出**: `sell_pool.json`

---

## 完整流程（动态双池）

```
【1. 市场阶段判定】
  ↓ MA60斜率 + 回撤深度 + 波动率
  ↓ 输出：bull/bear/oscillation

【2. 持股池检测】（先检查卖出）
  ↓ 读取portfolio.json持仓
  ↓ 检查止损/止盈/策略反转
  ↓ 输出：sell_pool.json

【3. 选股池扫描】（后检查买入）
  ↓ 根据市场阶段筛选全市场
  ↓ 熊市: RSI超卖 | 牛市: 回调 | 震荡: 网格底部
  ↓ 输出：buy_pool.json（前30名）

【4. 预测生成】（仅对有操作意图的股票）
  ↓ 合成预测池 = sell_pool + buy_pool[:5] + hold_positions
  ↓ 预测次日：高点、低点、振幅、走势模式

【5. 执行交易】
  ↓ 卖出: 执行sell_pool信号
  ↓ 买入: 执行buy_pool前2名（控制风险）
  ↓ 记录交易、更新持仓

【6. 生成报告】
  ↓ 输出：卖出预测、买入预测、持仓状态、账户状态
  ↓ 推送飞书（自动）
```

---

## 策略配置

### 市场阶段 → 策略池

| 阶段 | 策略池 | 仓位上限 | 股票池 |
|------|--------|---------|--------|
| 牛市 | 进攻、动量、趋势 | 70% | 成长股 |
| 熊市 | V5低波动、防御、逆向 | 50% | 价值股 |
| 震荡 | 进攻、波段、网格 | 60% | 混合 |

---

## 选股标准

### 基础筛选
```python
FILTER_CRITERIA = {
    'change_pct': (2, 9.5),      # 涨幅2%~9.5%（非涨停）
    'volume': 1e8,                # 成交额>1亿
    'turnover': (2, 15),          # 换手率2%~15%
    'exclude_st': True,           # 排除ST
    'exclude_new': ['68', '30'],  # 排除科创板、创业板新股
}
```

### 评分公式
```python
score = (
    涨幅 × 0.4 +
    (成交额/1亿) × 0.3 +
    换手率 × 0.3
)
```

---

## 回测筛选（关键调整）

### ⚠️ 评分阈值调整（重要经验）

**问题**：原阈值50分，无股票通过筛选  
**调整**：放宽至40分，成功选出股票

```python
# 评分规则（已调整）
def backtest_score(return_pct, max_drawdown, volatility):
    score = 0
    
    # 收益评分（放宽至5%）
    if return_pct > 0.05:
        score += 30
    elif return_pct > -0.05:  # 允许小幅亏损
        score += 10
    
    # 回撤评分（放宽至15%）
    if max_drawdown > -0.15:
        score += 30
    elif max_drawdown > -0.25:
        score += 10
    
    # 波动率评分（放宽至35%）
    if volatility < 0.35:
        score += 20
    elif volatility < 0.50:
        score += 10
    
    # 趋势加成
    if return_pct > 0 and max_drawdown > -0.20:
        score += 20
    
    return score

# 推荐阈值：≥40分（非50分）
RECOMMEND_THRESHOLD = 40
```

---

## 实际案例（2026-05-04）

### 市场判定
```
当前点位: 4112.16
MA60: 4051.63
回撤深度: -1.68%
判定结果: 震荡市
```

### 选股结果（340只符合条件）
```
1. 北方稀土 - 涨幅4.10%，成交143亿
2. 光迅科技 - 涨幅8.59%，成交113亿 ✅ 评分40分
3. 天赐材料 - 涨幅2.01%，成交109亿 ✅ 评分60分
4. 天齐锂业 - 涨幅5.97%，成交103亿 ✅ 评分60分
```

### 执行交易
```
最优选择: 天赐材料（002709）
  评分: 60分
  60日收益: +44.66%
  最大回撤: -15.23%
  波动率: 中等

买入: 100股 × 60.51元 = 6051元
剩余现金: 10084元（50%仓位）
```

---

## 运行命令

### 完整运行
```bash
cd ~/.hermes/profiles/stock
python3 scripts/autonomous_trading.py
```

### 输出文件
- **报告**: `data/autonomous_trading/trading_report_{timestamp}.json`
- **持仓**: `data/paper_trading/portfolio.json`
- **交易**: `data/paper_trading/trades.json`

---

## 持仓管理

### 当前持仓（实盘模拟）
```json
{
  "capital": 10084.0,
  "positions": {
    "600036": {"shares": 100, "cost_price": 38.65},
    "002709": {"shares": 100, "cost_price": 60.51}
  }
}
```

### 动态止损
- 持仓股票自动应用动态止损（波动率分类）
- 集成到 `risk_controller.py` 的 `check_sell_signal()`

---

## 注意事项

### ⚠️ 关键参数
1. **回测评分阈值**: 40分（非50分）— 这是经过实践调整的
2. **仓位控制**: 根据市场阶段动态调整（震荡市60%）
3. **选股范围**: 排除ST、科创板、创业板新股
4. **脚本超时**: `market_phase_detector_daily.py` 需要 300s 超时（默认60s会超时）

### 用户反馈处理
- 用户说"不要盯持股" → 系统自主选股，不参考用户持仓
- 用户说"目标是盈利" → 优先选择评分高、回撤可控的股票
- 用户说"自由发挥" → 从全市场筛选，不受限制

---

## 核心脚本（动态双池架构）

| 脚本 | 用途 | 输出 |
|------|------|------|
| `scripts/market_phase_detector_daily.py` | 市场阶段判定（每日9:15） | `market_phase_YYYYMMDD.json` + 飞书推送 |
| `scripts/stock_pool_generator.py` | 选股池生成 | `buy_pool.json` |
| `scripts/sell_signal_detector.py` | 卖出信号检测 | `sell_pool.json` |
| `scripts/pattern_predictor.py` | 走势模式预测模块 | 低开高走/震荡上行/强势上涨等6种模式 |
| `scripts/paper_trading_daily.py` | 每日运行主脚本 | `next_day_prediction.txt` |
| `scripts/paper_trading.py` | 实盘模拟引擎 | 预测/交易/持仓管理 |

---

## SQLite数据库架构（可追溯）

所有预测、交易、验证数据存储在SQLite数据库，支持历史查询：

### 数据库路径
```
~/.hermes/profiles/stock/data/paper_trading/paper_trading.db
```

### 五张核心表

| 表名 | 功能 | 关键字段 |
|------|------|----------|
| **account_summary** | 账户概况 | 总成本、总盈亏、股票价值、可用资金、仓位比例 |
| **positions** | 持仓记录 | 代码、数量、成本价、当前价、止损价、止盈价 |
| **predictions** | 预测记录 | 次日高低点、操作、操作价格、预期金额、验证结果 |
| **trades** | 交易记录 | 买卖操作、价格、金额、成功/失败 |
| **verification_analysis** | 验证分析 | 操作是否在价格区间、失败原因、改进建议 |

### 次日验证逻辑

核心验证规则（自动运行）：
- **买入验证**: 预期买入价 ≥ 当日最低价 → ✅ 可行
- **卖出验证**: 预期卖出价 ≤ 当日最高价 → ✅ 可行
- **失败判定**: 操作价格不在实际区间内 → 记录失败原因

```python
# 验证示例
result = verify_prediction(
    target_date="2026-05-08",
    symbol="605108",
    actual_low=15.5,  # 实际最低价
    actual_high=16.8, # 实际最高价
    actual_open=15.9,
    actual_close=16.5
)
# 输出: {'is_success': 1, 'analysis': '买入可行：预期价15.6元在区间[15.5-16.8]内'}
```

---

## 预测报告格式（规范）

每日15:15运行后自动推送飞书，格式：

```
============================================================
📊 实盘模拟每日报告（2026-05-10）
============================================================

【一、昨日预测验证】
验证次数: 1/1
成功率: 100.0%
平均准确度: 94.4分 🎯

【二、账户概况】
总成本: 20000元
总盈亏: +1345元 (+6.73%)
股票价值: 9063元
可用资金: 12282元
总资产: 21345元
仓位比例: 42.5%

【三、持股监控】（2只）
代码       名称           数量       成本       现价      盈亏%       操作
------------------------------------------------------------
600036   招商银行        100    38.65    37.95    -1.8%     持有 ✅
601966   601966      400    13.17    13.17    +0.0%     持有 ✅

【四、持股次日预测】
代码       名称           预测高点     预测低点      振幅%       走势           操作     预期价格
------------------------------------------------------------------------
600036   招商银行        38.44    37.53    2.4%       低开高走       持有        -
601966   601966      13.41    13.07    2.6%       震荡上行       持有        -

【五、次日买入候选】
代码       名称           预测高点     预测低点     振幅%       走势       数量      买入价
------------------------------------------------------------------------
000825   000825       4.31     4.20    2.4%       低开高走   1500     4.16
002572   002572      12.13    11.77    3.0%       弱势下跌    500    11.75
600059   600059       8.69     8.65    700     8.50
601236   601236       7.52     7.48    800     7.35

============================================================
✅ 报告完成
============================================================
```

**报告生成脚本**：`scripts/paper_trading_summary.py`（轻量版，<1秒）

**关键改进（2026-05-10）**：
- 新增【四、持股次日预测】：显示预测高低点、振幅%、**走势模式**
- 新增走势模式预测：低开高走/震荡上行/强势上涨等6种模式
- 持股监控显示成本、现价、盈亏%（更直观）
- 新增昨日预测验证准确度评分

---

## 走势模式预测系统

### 模块：`scripts/pattern_predictor.py`

基于技术指标判断次日走势模式，输出6种模式类型：

| 模式 | 触发条件 | 置信度 | 预期开盘 |
|------|----------|--------|----------|
| **低开高走** | RSI超卖+连续下跌≥3日 | 55-60% | 低开 |
| **高开低走** | 连续上涨≥3日 | 55% | 高开 |
| **震荡上行** | RSI超卖+趋势向上(MA5>MA20) | 60% | 高开 |
| **震荡下行** | RSI超买+趋势向下 | 60% | 低开 |
| **强势上涨** | 放量+均线向上 | 65-70% | 高开 |
| **弱势下跌** | 放量+均线向下 | 65-70% | 低开 |
| **窄幅震荡** | 波动率<2% | 70% | 平开 |

### 技术指标使用

```python
# pattern_predictor.py 核心指标
indicators = {
    'RSI': 14日RSI（超买>70，超卖<30）,
    'trend': MA5 vs MA20（判断趋势方向）,
    'vol_change': 成交量/10日均量（放量信号）,
    'atr_pct': ATR/收盘价（波动率）,
    'up_days': 连续上涨天数,
    'down_days': 连续下跌天数
}
```

### 数据库Schema新增字段

```sql
-- predictions 表新增
ALTER TABLE predictions ADD COLUMN predict_pattern TEXT DEFAULT '窄幅震荡';
ALTER TABLE predictions ADD COLUMN predict_amplitude REAL DEFAULT 0;
```

### 振幅预测逻辑

根据模式调整预测振幅：

| 模式 | 振幅因子 | 方向偏移 |
|------|----------|----------|
| 强势上涨 | ×1.5 | +0.3%（向上） |
| 弱势下跌 | ×1.5 | -0.3%（向下） |
| 低开高走 | ×1.2 | +0.1% |
| 高开低走 | ×1.2 | -0.1% |
| 震荡上行 | ×1.3 | +0.15% |
| 震荡下行 | ×1.3 | -0.15% |
| 窄幅震荡 | ×0.8 | 0 |

---

## 查询历史数据

```bash
# 查看账户概况历史
sqlite3 paper_trading.db "SELECT * FROM account_summary ORDER BY date DESC LIMIT 7;"

# 查看失败预测（重点分析）
sqlite3 paper_trading.db "SELECT * FROM predictions WHERE is_success=0;"

# 查看某股票预测历史
sqlite3 paper_trading.db "SELECT * FROM predictions WHERE symbol='605108';"

# 查看持仓记录
sqlite3 paper_trading.db "SELECT date, symbol, shares, cost_price, current_price FROM positions;"
```

---

## ⚠️ 常见错误（Pitfalls）

### 1. 使用硬编码股票列表
```python
# ❌ 错误做法
watch_list = ['600584', '601012', '601698', '000506']  # 固定列表

# ✅ 正确做法
sell_pool = detect_sell_signals()  # 从持仓动态生成
buy_pool = generate_buy_pool(phase)  # 从全市场动态筛选
```

### 2. 预测所有股票
不要预测固定股票池，只预测**有操作意图的股票**：
- sell_pool（有卖出信号）
- buy_pool前5名（有买入意图）
- 当前持仓（继续监控）

### 3. 忽略市场阶段
选股逻辑必须根据市场阶段调整：
- 熊市用RSI超卖策略（不是回调买入）
- 牛市用回调买入策略（不是超卖）
- 震荡用网格策略（不是趋势追踪）

### 4. 飞书推送认证错误
```python
# ❌ 错误：使用 webhook 端点
url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_HOME_CHANNEL}"
# FEISHU_HOME_CHANNEL 是 chat_id，不是 webhook token！

# ✅ 正确：使用 Open API 认证流程
# 详见 references/feishu-push-workflow.md
```

### 5. Python环境变量读取问题
```python
# ❌ execute_code 可能无法读取完整环境变量
import os
secret = os.environ.get('FEISHU_APP_SECRET')  # 可能返回空

# ✅ 使用 terminal 命令或直接硬编码完整值
# printenv | grep FEISHU_APP_SECRET
```

---

## 文件路径

| 文件 | 用途 |
|------|------|
| `scripts/stock_pool_generator.py` | 选股池生成（动态） |
| `scripts/sell_signal_detector.py` | 卖出信号检测 |
| `scripts/paper_trading_daily.py` | 每日运行（双池模式） |
| `scripts/paper_trading_db.py` | SQLite数据库操作 |
| `scripts/autonomous_trading.py` | 自主交易主脚本 |
| `data/paper_trading/paper_trading.db` | SQLite数据库（可追溯） |
| `data/paper_trading/buy_pool.json` | 当日选股池 |
| `data/paper_trading/sell_pool.json` | 当日卖出池 |
| `data/paper_trading/next_day_prediction.txt` | 次日预测报告 |
| `data/paper_trading/portfolio.json` | 实盘模拟持仓 |
| `data/paper_trading/trades.json` | 交易记录 |
| `skills/stock/autonomous-trading/references/sqlite-database-design.md` | 数据库设计文档 |

---

## 后续优化

### 已实现功能 ✅
1. **动态双池架构**: 选股池（买入候选）+ 持股池（卖出候选）
2. **卖出信号检测**: 止损/止盈/策略反转自动检测
3. **次日预测报告**: 高低点、振幅、走势模式、建议价格
4. **飞书自动推送**: Open API认证流程 + 富文本卡片（详见 [references/feishu-push-workflow.md](references/feishu-push-workflow.md)）

### 待开发功能
1. **回测验证优化**: 策略微调后需回测对比再决定应用/回滚
2. **预测准确度跟踪**: 统计各策略的预测准确度，优胜劣汰
3. **持仓轮动**: 定期评估持仓，淘汰弱股换强股

### 策略扩展
1. **板块轮动**: 根据热点板块调整选股池
2. **多因子组合**: ROE、PB、动量等因子组合选股
3. **机器学习**: LSTM预测次日走势

---

**创建日期**: 2026-05-04  
**状态**: 已验证运行，成功买入天赐材料  
**下次运行**: 每日自动运行（可配置cron）
