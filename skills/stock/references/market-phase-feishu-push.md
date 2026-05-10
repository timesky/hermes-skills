# 市场阶段判定飞书推送流程

## Cron Job 配置

| 任务 | 时间 | 脚本 | 输出 |
|------|------|------|------|
| 每日市场阶段判定 | 工作日 9:16 | `market_phase_detector_daily.py` | JSON + MD + 飞书 |

## 执行流程

```bash
# 1. 运行判定脚本（⚠️ 需要 300s 超时，默认 60s 会超时）
cd ~/.hermes/profiles/stock
python3 scripts/market_phase_detector_daily.py

# 输出文件：
#   ~/.hermes/profiles/stock/data/market_phase/market_phase_YYYYMMDD.json
#   ~/.hermes/profiles/stock/data/market_phase/market_phase_YYYYMMDD.md
```

## JSON 输出结构

```json
{
  "date": "2026-05-06",
  "time": "09:17",
  "indicators": {
    "ma60_slope": NaN,
    "drawdown": -1.68,
    "volatility": 12.54
  },
  "phase": {
    "phase": "bull",
    "phase_name": "牛市",
    "bull_signals": 2,
    "bear_signals": 0,
    "confidence": 66.67
  },
  "strategies": [
    {
      "name": "进攻策略",
      "priority": "首选",
      "performance": {
        "return": 22.62,
        "drawdown": -7.05,
        "win_rate": 50.0,
        "sharpe": 1.78
      }
    }
  ]
}
```

## 飞书推送代码

### 1. 环境变量获取

飞书配置存储在 `~/.hermes/.env`：

```bash
FEISHU_APP_ID=cli_a9106eb76178dbc2
FEISHU_APP_SECRET=TjKXYA...
FEISHU_CHAT_ID=oc_df56ebbde379284316e67395df51fa3d
```

### 2. Python 推送代码模板

```python
import json
import requests
from pathlib import Path

# 加载飞书配置
env_path = Path.home() / ".hermes" / ".env"
env_config = {}
with open(env_path) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, val = line.strip().split('=', 1)
            env_config[key] = val

app_id = env_config.get('FEISHU_APP_ID')
app_secret = env_config.get('FEISHU_APP_SECRET')
chat_id = env_config.get('FEISHU_CHAT_ID')

# 获取 tenant_access_token
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": app_id, "app_secret": app_secret}
)
token = resp.json()['tenant_access_token']

# 发送消息（Interactive Card）
send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

card = {
    "header": {
        "title": {"tag": "plain_text", "content": f"📊 市场阶段判定日报 - {date}"},
        "template": "blue"
    },
    "elements": [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**当前阶段:** 📈 {phase_name}\n**置信度:** {confidence}%\n**信号:** 牛市{bull_signals}个 / 熊市{bear_signals}个"}
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**推荐策略:** {strategy_name}\n• 预期收益: **+{ret}%**\n• 最大回撤: {drawdown}%\n• 胜率: {win_rate}%"}
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**操作建议:**\n• 仓位控制: 70%~80%\n• 止损阈值: -5%\n• 止盈点: +15%~+20%\n• 持仓周期: 10~20日"}
        },
        {"tag": "hr"},
        {
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": "风险提示: 关注MA60斜率变化 | 警惕高位回调 | 逐步止盈锁定收益"}
            ]
        }
    ]
}

body = {
    "receive_id": chat_id,
    "msg_type": "interactive",
    "content": json.dumps(card)
}

resp = requests.post(send_url, headers=headers, json=body)
result = resp.json()

# 检查结果
if result.get('code') == 0:
    print("✅ 飞书消息推送成功！")
else:
    print(f"❌ 推送失败: {result}")
```

## Pitfalls

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **脚本超时** | Baostock数据获取耗时 | 使用 `timeout=300` 执行 |
| **Token获取失败** | App ID/Secret 错误 | 检查 `.env` 文件 |
| **消息发送失败** | Chat ID 无效 | 检查群权限 |

## 三指标判定逻辑

| 指标 | 牛市阈值 | 熊市阈值 | 当前判定 |
|------|----------|----------|----------|
| **MA60斜率** | >+0.5% | <-0.3% | 中性（NaN时跳过） |
| **回撤深度** | <10% | >20% | ✓ 牛市信号 |
| **波动率** | <15% | >25% | ✓ 牛市信号 |

## 操作建议映射

| 阶段 | 仓位 | 止损 | 止盈 | 持仓周期 |
|------|------|------|------|----------|
| **牛市** | 70%~80% | -5% | +15%~+20% | 10~20日 |
| **熊市** | 30%~40% | -3% | +5%~+10% | 3~5日 |
| **震荡** | 50%~60% | -7% | +10%~+15% | 5~10日 |

---

**创建时间**: 2026-05-06  
**验证状态**: ✅ 已成功推送