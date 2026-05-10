---
name: mcn-feishu-push
description: MCN飞书推送 - 使用FEISHU_HOME_CHANNEL环境变量推送选题报告到飞书群
version: 1.0.0
triggers:
  - 飞书推送
  - feishu
  - 推送到飞书
  - send to feishu
---

# MCN飞书推送技能

## 概述

使用飞书开放API推送消息到飞书群组。适用于定时任务和自动化场景。

---

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `FEISHU_APP_ID` | 飞书应用ID | `cli_a9660d2d93f85bb5` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 32位字符串 |
| `FEISHU_HOME_CHANNEL` | 目标群组ID | `oc_5a3891c4ba840ab64a425a91d3ce9fe4` |

---

## 认证流程

### 步骤1：获取 tenant_access_token

```bash
# 注意：环境变量可能被截断显示，使用 printenv 获取完整值
FEISHU_SECRET=$(printenv | grep FEISHU_APP_SECRET | cut -d= -f2)

TOKEN_RESPONSE=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_SECRET\"}")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.tenant_access_token')
```

### 步骤2：发送消息

```bash
curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "receive_id": "'"$FEISHU_HOME_CHANNEL"'",
    "msg_type": "text",
    "content": "{\"text\":\"消息内容\"}"
  }'
```

---

## 常见陷阱

### 陷阱1：Webhook token 误用

❌ **错误做法**：
```bash
# FEISHU_HOME_CHANNEL 是 chat_id，不是 webhook token
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/$FEISHU_HOME_CHANNEL"
# 返回错误：param invalid: incoming webhook access token invalid
```

✅ **正确做法**：使用开放API认证流程（见上方）

### 陷阱2：环境变量截断

```bash
# ❌ 直接 echo 可能显示截断值
echo $FEISHU_APP_SECRET  # 显示：Qk5dSn...f6N1

# ✅ 使用 printenv 获取完整值
FEISHU_SECRET=$(printenv | grep FEISHU_APP_SECRET | cut -d= -f2)
```

### 陷阱3：消息内容转义

```bash
# ✅ JSON content 需要双重转义
"content": "{\"text\":\"第一行\\n第二行\"}"
```

### 陷阱4：Hermes execute_code 环境变量问题

```python
# ❌ execute_code 中 os.environ 可能缺少环境变量
import os
token = os.environ["FEISHU_APP_SECRET"]  # 可能抛出 KeyError

# ✅ 使用 terminal 命令获取环境变量
from hermes_tools import terminal
result = terminal('python3 -c "import os; print(os.environ.get(\'FEISHU_APP_SECRET\'))"')
secret = result['output'].strip()
```

### 陷阱5：多行消息 JSON 格式错误

```bash
# ❌ 使用 jq 构建复杂 JSON 容易出错
CONTENT=$(echo "$MSG" | jq -Rs '{text: .}')  # 格式不符合飞书要求

# ✅ 直接硬编码 JSON 字符串（简单场景）
curl -d '{"msg_type":"text","content":"{\"text\":\"第一行\\n第二行\"}"}'

# ✅ 使用 Python json.dumps（复杂场景）
import json
content = json.dumps({"text": "第一行\n第二行"})
```

---

## Python 示例

```python
import os
import requests

def send_to_feishu(message: str) -> dict:
    """发送消息到飞书群组"""
    
    # 1. 获取 token
    token_resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={
            "app_id": os.environ["FEISHU_APP_ID"],
            "app_secret": os.environ["FEISHU_APP_SECRET"]
        }
    )
    token = token_resp.json()["tenant_access_token"]
    
    # 2. 发送消息
    send_resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": os.environ["FEISHU_HOME_CHANNEL"],
            "msg_type": "text",
            "content": f'{{"text":"{message}"}}'
        }
    )
    
    return send_resp.json()
```

---

## 验证成功

成功响应：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "message_id": "om_x100b5066e7ceeca4b2a9b9928433d69"
  }
}
```

---

## 使用场景

- MCN热点调研报告推送
- 内容发布通知
- 定时任务结果汇报
- 错误告警

---

*Created: 2026-05-02*
*Updated: 2026-05-05 - Added pitfalls 4 & 5 for Hermes environment and multi-line JSON*
