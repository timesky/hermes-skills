# 策略验证与调试

## 策略自查流程

当策略实现可能存在偏差时，按以下步骤自查：

### 1. 找回原始规则

```bash
# 搜索历史会话中的策略规则
session_search "策略名称 OR 买入条件 OR 止损规则"
```

常见来源：
- 知乎/公众号文章抓取（通过OpenCLI browser）
- 历史会话记录（session_search）
- 抖音视频转录（待实现）

### 2. 制作对照表

| 规则项 | 原文要求 | 当前代码 | 状态 |
|--------|----------|----------|------|
| 入场条件 | ... | `...` | ✅/❌ |
| 止损规则 | ... | `...` | ✅/❌ |
| ... | ... | ... | ... |

### 3. 常见偏差类型

| 偏差类型 | 说明 | 解决方案 |
|----------|------|----------|
| **序列→并行** | 原文是序列条件（先A后B），代码写成并行（A且B） | 增加前置条件检查 |
| **条件遗漏** | 原文有多个条件，代码漏掉部分 | 补充缺失条件 |
| **逻辑冲突** | 止损先触发，其他卖出永不生效 | 调整优先级或合并条件 |
| **无法实现** | "当天无法收回"等盘中逻辑 | 改用收盘价判断 |

---

## 斜率计算与去噪

### 问题背景

判断"上升趋势中的回调" vs "一直下跌"：
- MA22向上（斜率>0）→ 上升趋势中的回调
- MA22向下（斜率<0）→ 下跌趋势

**难点**：斜率有噪点，如何去噪？

### 方法对比

| 方法 | 代码 | 优点 | 缺点 |
|------|------|------|------|
| 简单斜率 | `(ma[-N]-ma[-M])/(M-N)` | 快速 | 噪点多 |
| 线性回归 | `np.polyfit(x, y, 1)` | 去噪效果好 | 计算稍复杂 |
| 双重SMA | `SMA(SMA(ma, 5), 5).roc` | Backtrader原生 | 有滞后 |
| ROC | `RateOfChange(ma, N)` | Backtrader内置 | 需配合平滑 |

### 推荐：线性回归斜率

```python
import numpy as np

class Strategy(bt.Strategy):
    def __init__(self):
        self.ma22 = bt.indicators.SMA(self.data.close, period=22)
        self.ma22_history = []  # 存储历史值
        
    def next(self):
        # 收集MA22历史值
        self.ma22_history.append(self.ma22[0])
        if len(self.ma22_history) > 22:
            self.ma22_history.pop(0)
        
        # 计算线性回归斜率
        if len(self.ma22_history) == 22:
            x = np.arange(22)
            y = np.array(self.ma22_history)
            slope, _ = np.polyfit(x, y, 1)
            slope_pct = slope / y[0] * 100  # 百分比斜率
            
            # 判断趋势：斜率>0.5%视为向上
            ma22_trending_up = slope_pct > 0.5
```

### 判断"回调止跌"的完整逻辑

```python
# 1. 接近MA22（附近）
near_ma22 = abs(close - ma22) / ma22 <= 0.05  # 距离±5%以内

# 2. MA22向上（线性回归斜率>0）
ma22_trending_up = slope_pct > 0

# 3. 止跌信号（最低价不再创新低）
stopped_falling = low >= low[-1]  # 今天最低价>=昨天

# 完整判断
pullback_ok = near_ma22 and ma22_trending_up and stopped_falling
```

---

## 常见原文规则的量化

| 原文描述 | 量化方法 |
|----------|----------|
| "回调到X日均线附近" | `\|close - maX\| / maX <= 0.05` |
| "止跌" | `low >= low[-1]` 连续2天 |
| "温和放量" | `1.2 <= volume/volume_ma5 <= 3.0` |
| "当天无法收回" | 改用收盘价判断（Backtrader只有日线） |
| "均线向上" | 线性回归斜率>0 或 `ma > ma[-3]` |
| "均线拐头" | 斜率由正转负 或 `ma[-1] > ma[-2] and ma[0] < ma[-1]` |

---

*更新于 2026-05-01*
