# 飞书推送工作流程

## 环境变量配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `FEISHU_APP_ID` | 飞书应用ID | `cli_a9667db8f0385bdf` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 32位完整字符串 |
| `FEISHU_HOME_CHANNEL` | 目标群组chat_id | `oc_cee6bee35ad7089425553188ffc09014` |

**⚠️ 注意**: `FEISHU_HOME_CHANNEL` 是 **chat_id**，不是 webhook token！

---

## 认证流程（两步）

### 步骤1：获取 tenant_access_token

```python
import requests

token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
token_data = {
    "app_id": "cli_a9667db8f0385bdf",
    "app_secret": "r2h7VQZyMv4BdxaSpRb5CBP5T0lopOtw"  # 完整密钥
}

response = requests.post(token_url, json=token_data)
token_result = response.json()

# 成功响应: {'code': 0, 'tenant_access_token': 't-g10457...', 'expire': 7200}
tenant_token = token_result['tenant_access_token']
```

### 步骤2：发送消息

```python
import json

send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
headers = {
    "Authorization": f"Bearer {tenant_token}",
    "Content-Type": "application/json"
}
params = {"receive_id_type": "chat_id"}

# 富文本卡片格式
message_content = {
    "zh_cn": {
        "title": "📈 市场阶段判定报告 (2026-05-07)",
        "content": [
            [{"tag": "text", "text": "【市场阶段】", "style": ["bold"]},
             {"tag": "text", "text": " 牛市 🐂"}],
            [{"tag": "text", "text": "【置信度】", "style": ["bold"]},
             {"tag": "text", "text": " 67%"}],
            [{"tag": "text", "text": ""}],  # 空行
            [{"tag": "text", "text": "【推荐策略】", "style": ["bold"]}],
            [{"tag": "text", "text": "进攻策略（首选）"}],
            [{"tag": "text", "text": "• 预期收益: +22.62%"}]
        ]
    }
}

data = {
    "receive_id": "oc_cee6bee35ad7089425553188ffc09014",
    "msg_type": "post",  # 富文本消息
    "content": json.dumps(message_content)
}

response = requests.post(send_url, headers=headers, params=params, json=data)
result = response.json()

# 成功响应: {'code': 0, 'data': {'message_id': 'om_x100b...'}}
```

---

## ⚠️ 常见错误（Pitfalls）

### 1. 使用 Webhook 端点（错误）

```python
# ❌ 错误做法：FEISHU_HOME_CHANNEL 不是 webhook token
url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_HOME_CHANNEL}"
# 返回: "param invalid: incoming webhook access token invalid"

# ✅ 正确做法：使用 Open API 认证流程
# 先获取 tenant_access_token，再调用 im/v1/messages
```

### 2. 环境变量截断显示

```python
# ❌ Python execute_code 可能无法读取环境变量
import os
secret = os.environ.get('FEISHU_APP_SECRET')  # 可能返回空字符串

# ✅ 使用 terminal 命令获取完整值
# echo $FEISHU_APP_SECRET
# 或直接硬编码完整密钥（脚本内部）
```

### 3. 密钥不完整

```python
# ❌ 截断的密钥
"app_secret": "r2h7VQ...pOtw"  # 这会返回 "app secret invalid"

# ✅ 完整密钥
"app_secret": "r2h7VQZyMv4BdxaSpRb5CBP5T0lopOtw"
```

### 4. 消息格式错误

```python
# ❌ 错误：content 不是 JSON 字符串
data = {"content": message_content}  # 直接传对象

# ✅ 正确：content 需要序列化为 JSON 字符串
data = {"content": json.dumps(message_content)}
```

---

## 消息类型

| msg_type | 说明 | content格式 |
|----------|------|-------------|
| `text` | 纯文本 | `{"text": "消息内容"}` |
| `post` | 富文本卡片 | 见上方示例 |
| `interactive` | 交互卡片 | 更复杂的按钮/表单 |

---

## 成功响应示例

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "message_id": "om_x100b508ac6296914c3a271dbf4846a5",
    "create_time": "1778116750457"
  }
}
```

---

## Bash 版本（备用）

```bash
# 1. 获取 token
TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_a9667db8f0385bdf","app_secret":"r2h7VQZyMv4BdxaSpRb5CBP5T0lopOtw"}' \
  | jq -r '.tenant_access_token')

# 2. 发送消息
curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"receive_id":"oc_cee6bee35ad7089425553188ffc09014","msg_type":"text","content":"{\"text\":\"测试消息\"}"}'
```

---

## 验证状态

- ✅ 已验证成功（2026-05-07）
- 消息ID: `om_x100b508ac6296914c3a271dbf4846a5`
- 目标群: `oc_cee6bee35ad7089425553188ffc09014`

---

*Created: 2026-05-07*