# 均线斜率计算与趋势判断方法调研

## 一、均线斜率计算方法对比

### 方法1：简单斜率（差分法）
```python
slope = (ma[N] - ma[0]) / N  # N天内的平均变化率
```
- **优点**：计算简单，响应快
- **缺点**：只看首尾两点，忽略中间波动，噪点多
- **适用**：短期快速判断，不适合趋势确认

### 方法2：ROC（变化率指标）
```python
# Backtrader内置
roc = bt.indicators.RateOfChange(ma, period=N)
slope_pct = roc[0]  # 百分比变化率
```
- **优点**：Backtrader原生支持，无需额外计算
- **缺点**：本质是差分法，仍有噪点
- **适用**：配合平滑处理使用

### 方法3：双重平滑法（SMA of SMA）
```python
# 先对均线做平滑，再计算斜率
ma_smoothed = bt.indicators.SMA(ma, period=5)  # 平滑均线
slope = bt.indicators.RateOfChange(ma_smoothed, period=5)
```
- **优点**：去噪效果好，Backtrader原生支持
- **缺点**：有滞后（双重平滑延迟约5-10天）
- **适用**：趋势确认，不适合短期信号

### 方法4：线性回归斜率（最推荐）
```python
import numpy as np

def linear_regression_slope(values, period):
    """对过去period天的值做线性回归，返回斜率"""
    x = np.arange(period)
    y = np.array(values[-period:])
    slope, intercept = np.polyfit(x, y, 1)
    # 转换为百分比斜率（相对于起点）
    slope_pct = (slope / y[0]) * 100 if y[0] != 0 else 0
    return slope_pct, intercept
```
- **优点**：
  - 最小二乘拟合，去噪效果最佳
  - 考虑所有数据点，不只首尾
  - 可给出置信度（R²值）
- **缺点**：计算稍复杂，需要numpy
- **适用**：趋势判断、回调识别

### 方法5：TA-Lib LINEARREG（专业标准）
```python
import talib

# TA-Lib内置线性回归斜率
slope = talib.LINEARREG_SLOPE(close, timeperiod=14)
angle = talib.LINEARREG_ANGLE(close, timeperiod=14)  # 角度（度）
```
- **优点**：行业标准，性能优化
- **缺点**：需要安装TA-Lib C库
- **适用**：专业量化系统

---

## 二、方法对比表

| 方法 | 噪点控制 | 滞后性 | 计算复杂度 | Backtrader支持 | 推荐场景 |
|------|----------|--------|------------|----------------|----------|
| 简单斜率 | ❌ 差 | ✅ 无 | ✅ 简单 | ✅ 手动实现 | 不推荐 |
| ROC | ❌ 差 | ✅ 无 | ✅ 简单 | ✅ 内置 | 配合平滑 |
| 双重SMA | ✅ 好 | ❌ 有滞后 | ✅ 简单 | ✅ 内置 | 趋势确认 |
| 线性回归 | ✅ 最佳 | ✅ 较小 | ❌ 中等 | ✅ numpy | **推荐** |
| TA-Lib | ✅ 最佳 | ✅ 较小 | ❌ 需安装 | ✅ talib | 专业系统 |

---

## 三、斜率阈值设定

### 百分比斜率参考值
| 斜率范围 | 趋势判断 | 含义 |
|----------|----------|------|
| slope_pct > 1.0 | 强上升趋势 | 明显上涨趋势 |
| 0.3 < slope_pct < 1.0 | 温和上升 | 正常上升趋势 |
| -0.3 < slope_pct < 0.3 | 横盘震荡 | 无明显趋势 |
| -1.0 < slope_pct < -0.3 | 温和下降 | 正常下跌趋势 |
| slope_pct < -1.0 | 强下降趋势 | 明显下跌趋势 |

### 22日均线斜率建议阈值
```python
# 对于22日均线（主力洗盘临界线）
MA22_SLOPE_THRESHOLD = 0.5  # 斜率>0.5%视为上升趋势

# 上升趋势中的回调：
# - MA22斜率 > 0.5%（上升趋势未破坏）
# - 股价从高位回落到MA22附近
# - 在MA22附近止跌（最低价不再创新低）
```

---

## 四、回调识别方法

### 方法1：距离均线法
```python
# 股价距离MA22在±5%以内视为"附近"
near_ma = abs(close - ma22) / ma22 <= 0.05
```

### 方法2：前期涨幅检查（识别"回调"而非"一直下跌"）
```python
# 过去10天最高价 vs 20天前收盘价
high_10d = max(high[-10:])
close_20d_ago = close[-20]

# 前期涨幅 > 5% 才算"上升后回调"
had_uptrend = (high_10d - close_20d_ago) / close_20d_ago > 0.05

# 当前回落到MA22附近
pullback_to_ma = close <= ma22 * 1.05  # 不超过MA22的5%

# 综合判断：上升趋势中的回调
is_pullback = had_uptrend and pullback_to_ma and ma22_slope > 0.5
```

### 方法3：最高点回撤法（推荐）
```python
# 记录近期最高点
recent_high = max(high[-20:])  # 20天内最高价

# 从高点回撤幅度
drawdown_from_high = (recent_high - close) / recent_high

# 回撤到MA22附近 = 从高点回撤5%-15%
pullback_range = 0.05 <= drawdown_from_high <= 0.15

# 且MA22斜率向上（趋势未破坏）
is_pullback = pullback_range and ma22_slope_pct > 0.5
```

---

## 五、止跌判断方法

### 方法1：最低价不再创新低
```python
# 连续2天最低价不再下降
stopped_falling = low[0] >= low[-1] and low[-1] >= low[-2]
```

### 方法2：收盘价站稳均线
```python
# 收盘价连续2天站稳MA22上方
stands_ma22 = close[0] > ma22 and close[-1] > ma22
```

### 方法3：价格收敛（横盘）
```python
# 价格波动收窄，开始横盘
price_range = max(high[-3:]) - min(low[-3:])
range_narrowing = price_range < atr * 1.5  # 波动小于1.5倍ATR
```

---

## 六、推荐实现方案

### 自定义均线策略的"回调到MA22附近止跌"判断：

```python
def check_pullback_and_stop_falling(self):
    """
    检查是否满足"回调到MA22附近止跌"条件
    
    条件序列：
    1. MA22斜率向上（上升趋势）
    2. 股价从高点回撤到MA22附近（5%-15%回撤）
    3. 止跌信号（最低价不再创新低）
    """
    
    # 1. MA22斜率（线性回归，22天）
    ma22_values = [self.ma22[-i] for i in range(21, -1, -1)]
    slope_pct = linear_regression_slope(ma22_values, 22)
    ma22_trending_up = slope_pct > 0.5  # 斜率>0.5%
    
    # 2. 从高点回撤到MA22附近
    recent_high = max([self.data.high[-i] for i in range(1, 21)])
    drawdown = (recent_high - self.data.close[0]) / recent_high
    near_ma22 = abs(self.data.close[0] - self.ma22[0]) / self.ma22[0] <= 0.05
    pullback_ok = 0.05 <= drawdown <= 0.15 and near_ma22
    
    # 3. 止跌信号
    stopped_falling = self.data.low[0] >= self.data.low[-1]
    
    return ma22_trending_up and pullback_ok and stopped_falling
```

---

## 七、注意事项

1. **斜率周期选择**：
   - 22日均线斜率建议用22天线性回归（与均线周期一致）
   - 短期斜率可用10天，长期趋势可用44天

2. **阈值调整**：
   - 不同股票波动性不同，阈值需调整
   - 蓝筹股阈值可降低（如0.3%）
   - 小盘股阈值可提高（如0.8%）

3. **Backtrader实现**：
   - 线性回归需要在 `next()` 中计算，不能在 `__init__` 中预定义
   - 可用 `numpy.polyfit` 或 `scipy.stats.linregress`

4. **与策略结合**：
   - "回调到MA22附近止跌"是**前置条件**
   - 金叉（MA7上穿MA22）是**触发信号**
   - 两者结合才是完整买入条件

---

*调研日期：2026-05-01*
*来源：量化分析技术文献、Backtrader文档、TA-Lib规范*