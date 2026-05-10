# 夜间策略训练工作流

## Cron配置

**任务ID**: 夜间策略调研训练
**执行时间**: 每日 00:00
**命令**: 
```bash
cd ~/.hermes/profiles/stock/scripts && python3 strategy_research_training.py --train
```

## 执行流程

### 1. 数据加载
- 市场缓存: `~/.hermes/profiles/stock/data/market_cache/stocks/*.csv` (500只股票)
- 财务缓存: `~/.hermes/profiles/stock/data/financial_cache/indicator/*.csv` (4880只股票)
- 策略注册表: `~/.hermes/profiles/stock/data/strategy_registry.json`

### 2. 预设策略测试
测试8种策略模板（NEW_STRATEGIES_TEMPLATE）：
- RSI多周期共振策略
- 量价背离策略
- 动量突破+止损策略
- 低波动防御策略V5
- 财务质量+动量组合
- 均线趋势过滤策略
- 布林带均值回归策略
- 海龟交易法则改进版

### 3. 网络新策略搜索
通过delegate_task搜索：
- 知乎量化专栏
- 聚宽社区
- 掘金量化社区

返回策略思路（名称、逻辑、参数、来源）

### 4. 回测验证
- 训练集: 2022-01-01 ~ 2023-12-31
- 测试集: 2024-01-01 ~ 2025-04-30
- 周频调仓
- 初始资金: 20000

### 5. 评估标准
```python
EVALUATION_CRITERIA = {
    "pass": {"annual_return": 0, "max_drawdown": -20},
    "good": {"annual_return": 8, "max_drawdown": -15},
    "excellent": {"annual_return": 15, "max_drawdown": -10}
}
```

### 6. 策略注册
- 生成策略指纹（MD5 hash）
- 检查重复注册
- 按 market_stage 分类

## 输出文件

```
~/.hermes/profiles/stock/data/strategy_research/
├── training_report_YYYYMMDD.json      # 预设策略测试结果
├── new_strategy_report_YYYYMMDD.json  # 新搜索策略结果
└── nightly_training_full_YYYYMMDD.json # 完整汇总报告
```

## 常见问题

### 财务数据字段解析失败
字段含 `%` 符号或 `亿/万` 单位，需字符串处理：
```python
roe_str = str(latest.get('净资产收益率', '0'))
roe = float(roe_str.replace('%', '')) if '%' in roe_str else float(roe_str)
```

### DataFrame布尔判断错误
使用 `if df_s is not None and len(df_s) > 0:` 而非 `if df_s:`

### 新策略回测收益为0
- 检查信号生成条件是否过严
- 检查财务数据是否正确加载
- 放宽筛选条件进行测试

## 2026-05-07 训练总结

**最佳策略**: 低波动防御V5 (测试集+7.0%, 回撤-10.77%)
**新策略**: 全部未通过（熊市环境不适合进攻型策略）
**建议**: 继续使用已验证的防御策略，优化波动率自适应策略参数