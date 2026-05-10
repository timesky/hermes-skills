# A股量化框架选择指南

## 场景分类

### 场景1：个人研究/学习（零成本，纯本地分析）

**推荐组合：**
```
pytdx(实时行情) + Baostock(历史数据) + Backtrader(回测)
```

**不推荐 vn.py 的原因：**
| 对比项 | vn.py | Backtrader |
|--------|-------|------------|
| 定位 | 全功能交易框架 | 纯回测框架 |
| 学习曲线 | 陡峭（事件驱动引擎） | 平缓（声明式策略） |
| A股数据接入 | 需额外配置 | Baostock直接整合 |
| 场景1适用性 | 大材小用 | 刚好合适 |

**结论：** 纯本地分析回测，Backtrader更适合。vn.py等需要实盘时再升级。

### 场景2：个人自动化交易（低成本）

**推荐：** easytrader（免费，但有不稳定/封号风险）

### 场景3：专业量化（机构级别）

**推荐：** vn.py + QMT/PTrade（需资金门槛50万+）

---

## 数据源对比

| 数据源 | 特点 | 适用场景 |
|--------|------|---------|
| **pytdx** | 秒级延迟、免费、无需token | 实时行情监控 |
| **Baostock** | 完整历史K线、免费稳定 | 历史回测 |
| **AkShare** | 数据全面、1-5分钟延迟 | 补充数据/财务/板块 |
| **Tushare Pro** | 数据质量高、积分制 | 专业研究/因子分析 |

---

## 通达信服务器（实测可用）

| 服务器 | IP | 端口 | 状态 |
|--------|-----|------|------|
| 主用 | 218.75.126.9 | 7709 | ✅ 已验证 |
| 备用1 | 119.147.212.81 | 7709 | 待验证 |
| 备用2 | 115.238.56.198 | 7709 | 待验证 |
| 备用3 | 106.14.95.149 | 7709 | 待验证 |
| 备用4 | 180.153.39.51 | 7709 | 待验证 |

**连接代码：**
```python
from pytdx.hq import TdxHq_API

api = TdxHq_API()
for host, port in TDX_SERVERS:
    if api.connect(host, port, time_out=5):
        # 连接成功
        break
```

---

## 市场代码映射

```python
def _get_market(code: str) -> int:
    """根据股票代码判断市场"""
    code = code.zfill(6)
    if code.startswith(('6', '5', '9')):
        return 1  # 上海
    return 0  # 深圳
```

---

## Baostock 代码格式

Baostock 需要前缀：
- 上海：`sh.600000`
- 深圳：`sz.000001`

```python
import baostock as bs

lg = bs.login()  # 无需注册，自动匿名登录

rs = bs.query_history_k_data_plus(
    "sh.600000",  # 注意前缀
    "date,open,high,low,close,volume",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="d",
    adjustflag="2"  # 前复权
)
```

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| pytdx连接失败 | 切换服务器IP列表 |
| pytdx成交量单位 | 返回的是"手"，需乘100换算股数 |
| Baostock代码格式 | 必须加sh./sz.前缀 |
| AkShare代理错误 | 检查代理设置或直连 |
| Backtrader中文乱码 | matplotlib字体配置 |

---

*更新于 2026-04-26*