# Python 环境配置

## 问题背景

Hermes Agent venv (`~/.hermes/hermes-agent/venv`) 未安装 akshare 及相关金融数据分析库。

## 正确的 Python 环境

使用 pyenv 安装的 Python 3.11.15：

```bash
# Python 解释器路径
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/python

# pip 安装器路径
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/pip
```

## 安装依赖

```bash
# 安装 akshare 及金融数据库
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/pip install akshare pandas numpy

# 解决版本兼容问题
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/pip install --upgrade pandas numpy
```

## 运行脚本

```bash
# 运行流动性监控
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/python ~/.hermes/profiles/stock/scripts/liquidity_monitor.py

# 运行极端行情预警
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/python ~/.hermes/profiles/stock/scripts/extreme_market_alert.py

# 运行动态止损
/Users/hy_timesky/.pyenv/versions/3.11.15/bin/python ~/.hermes/profiles/stock/scripts/dynamic_stop_loss.py
```

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'akshare'` | 使用 venv Python | 切换到 pyenv Python |
| `ValueError: numpy.dtype size changed` | numpy/pandas 版本不兼容 | `pip install --upgrade pandas numpy` |
| `ProxyError: Unable to connect to proxy` | Eastmoney API 被阻断 | 使用 Sina 数据源 |

---

**更新日期**: 2026-05-07