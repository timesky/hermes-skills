# A股 AkShare API 参考

## 核心接口

```python
import akshare as ak

# A股实时行情 (东方财富数据源)
df = ak.stock_zh_a_spot_em()
# 字段: 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 最高, 最低, 今开, 昨收

# A股历史数据
df = ak.stock_zh_a_hist(symbol="000001", period="daily", 
                        start_date="20240101", end_date="20240401", adjust="qfq")
# period: daily, weekly, monthly
# adjust: qfq(前复权), hfq(后复权), None(不复权)

# A股指数
df = ak.index_zh_a_hist(symbol="sh000001", period="daily")
```

## 返回格式

所有接口返回 pandas DataFrame:

```python
import json
data = json.loads(df.to_json(orient='records'))
```

## 指数代码

| 代码 | 名称 |
|------|------|
| sh000001 | 上证指数 |
| sz399001 | 深证成指 |
| sh000300 | 沪深300 |
| sz399006 | 创业板指 |
| sh000016 | 上证50 |
| sh000905 | 中证500 |

---

*文档更新于 2026-04-25*