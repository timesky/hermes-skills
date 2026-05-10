# Stock 技能配置状态

**配置日期**: 2026-04-26
**状态**: ✅ 已完成（场景1量化环境已搭建）
**场景**: 个人研究/学习（零成本，纯本地分析）

## 技能路径

```
~/.hermes/profiles/stock/skills/stock/
├── SKILL.md                      # 技能文档
├── scripts/stock.py              # A股量化CLI脚本 (500+行)
├── scripts/test_quant_env.py     # 环境测试脚本
├── references/api-endpoints.md   # AkShare API参考
└── references/quant-framework.md # 量化框架选择指南
```

## 已安装依赖（多数据源架构）

| 包名 | 版本 | 用途 | 数据源类型 |
|------|------|------|-----------|
| pytdx | 1.72 | 通达信实时行情 | 秒级延迟 |
| baostock | 0.9.1 | A股历史K线 | 免费/稳定 |
| backtrader | 1.9.78 | 策略回测引擎 | 纯回测 |
| akshare | 1.18.57 | 补充数据源 | 财务/板块 |
| pandas | 2.3.3 | 数据处理 | - |
| numpy | 2.0.2 | 数值计算 | - |

## 数据源架构

```
实时数据层 → pytdx (通达信服务器，秒级行情)
历史数据层 → Baostock (证券宝，完整K线)
补充数据层 → AkShare (东方财富，财务/板块)
回测引擎   → Backtrader (双均线/RSI/布林带)
```

## 用户偏好

- **场景**: 个人研究学习，零成本，纯本地分析
- **不做自动交易**，只做回测分析
- **不使用 vn.py**（学习曲线陡，大材小用）
- Backtrader更适合纯回测场景

## CLI 命令

```bash
# 实时行情 (pytdx秒级数据)
python3 stock.py quote 000001

# 历史K线 (Baostock)
python3 stock.py history 000001 --start 20240101 --end 20241231

# 指数
python3 stock.py index sh000001

# 涨幅榜
python3 stock.py trending --limit 20

# 搜索
python3 stock.py search 平安

# 策略回测 (Backtrader)
python3 stock.py backtest 000001 --fast 5 --slow 20

# 技术指标
python3 stock.py indicator 000001 --ma 5,10,20 --rsi 14
```

## 通达信服务器（已验证）

| 服务器 | 状态 |
|--------|------|
| 218.75.126.9:7709 | ✅ 主用 |
| 119.147.212.81:7709 | 备用 |
| 115.238.56.198:7709 | 备用 |

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| pytdx连接失败 | 切换服务器IP列表 |
| AkShare代理错误 | 检查代理设置或直连 |
| pytdx成交量单位 | 返回"手"，需×100换算股数 |
| Baostock代码格式 | 必须加sh./sz.前缀 |