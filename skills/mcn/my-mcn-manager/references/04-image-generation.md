---
module: 04-image-generation
type: reference
source: ai-image-generation (整合)
---

# 模块 4: AI 配图生成

为文章生成 3-5 张专属配图。

---

## ⚠️ 重要：API 正确用法（2026-04-14 更新）

### 关键参数

| 参数 | 正确值 | 说明 |
|------|--------|------|
| `webHook` | `"http://192.168.1.1"` | **假地址**，不能是 `-1` 或空 |
| API 地址 | `https://grsai.dakka.com.cn/v1/draw/nano-banana` | 国内直连地址 |
| 轮询频率 | 5 秒 | 避免频繁请求 |
| 最大等待 | 5 分钟（60次） | 给长任务足够时间 |
| 超时处理 | **放弃不重试** | 避免积分浪费 |

### 常见错误

```
❌ 错误用法：
webHook: "-1" 或 webHook: ""

✅ 正确用法：
webHook: "http://192.168.1.1"（任意假地址）
```

---

## 配置

路径：`~/.hermes/mcn_config.yaml`

```yaml
image_generation:
  default_provider: grsai
  providers:
    grsai:
      api_url: https://grsai.dakka.com.cn/v1/draw/nano-banana
      api_key: sk-xxx
      models:
        fast: nano-banana-fast    # 440 积分/张
        pro: nano-banana-pro      # 900 积分/张
      default_model: fast
      cost_per_image: 440
```

---

## 执行流程（优化版）

### 1. 提交任务

```python
import requests
import json

def submit_task(prompt: str) -> str:
    """提交图片生成任务，返回 task_id"""
    
    api_url = "https://grsai.dakka.com.cn/v1/draw/nano-banana"
    api_key = "sk-xxx"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "nano-banana-fast",
        "prompt": prompt,
        "webHook": "http://192.168.1.1",  # 关键：假地址
        "shutProgress": False
    }
    
    resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
    result = resp.json()
    
    if result.get('code') == 0 and result.get('data'):
        task_id = result['data']['id']
        # 持久化 task_id（避免超时丢失）
        save_task_id(task_id, prompt)
        return task_id
    
    return None
```

### 2. 轮询结果（5秒间隔，最多5分钟）

```python
def poll_result(task_id: str, max_polls: int = 60, interval: int = 5) -> str:
    """轮询获取结果，最多 5 分钟"""
    
    result_url = "https://grsai.dakka.com.cn/v1/draw/result"
    
    for i in range(max_polls):
        resp = requests.post(
            result_url,
            headers={"Authorization": "Bearer sk-xxx"},
            json={"id": task_id},
            timeout=30
        )
        
        data = resp.json().get('data', {})
        status = data.get('status')
        
        if status == 'succeeded':
            return data['results'][0]['url']
        
        elif status == 'failed':
            print(f"失败: {data.get('failure_reason')}")
            return None
        
        elif status == 'running':
            if i % 5 == 0:
                print(f"进度: {data.get('progress', 0)}% ({i+1}/{max_polls})")
            time.sleep(interval)
    
    # 超时：放弃不重试（避免积分浪费）
    print(f"超时 ({max_polls * interval}s)，放弃此任务")
    return None
```

### 3. Task ID 持久化

```python
def save_task_id(task_id: str, prompt: str, output_dir: str):
    """保存 task_id 到文件，避免超时丢失"""
    
    tasks_file = os.path.join(output_dir, "tasks.json")
    
    tasks = {}
    if os.path.exists(tasks_file):
        tasks = json.load(open(tasks_file))
    
    tasks[task_id] = {
        'prompt': prompt,
        'status': 'running',
        'submit_time': time.time()
    }
    
    json.dump(tasks, open(tasks_file, 'w'), indent=2)
```

---

## 完整示例

```python
import requests
import time
import os
import json

# 参数
POLL_INTERVAL = 5  # 5秒间隔
MAX_POLL_COUNT = 60  # 60次 = 5分钟
FAKE_WEBHOOK = "http://192.168.1.1"  # 假地址

def generate_image(prompt: str, name: str, output_dir: str) -> bool:
    """生成单张图片的完整流程"""
    
    # 检查是否已存在
    output_path = os.path.join(output_dir, f"{name}.png")
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"[{name}] 已存在，跳过")
        return True
    
    # 提交任务
    print(f"[{name}] 提交任务...")
    
    resp = requests.post(
        "https://grsai.dakka.com.cn/v1/draw/nano-banana",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-xxx"
        },
        json={
            "model": "nano-banana-fast",
            "prompt": prompt,
            "webHook": FAKE_WEBHOOK,
            "shutProgress": False
        },
        timeout=30
    )
    
    result = resp.json()
    if result.get('code') != 0:
        print(f"  提交失败: {result}")
        return False
    
    task_id = result['data']['id']
    print(f"  Task ID: {task_id}")
    
    # 持久化
    save_task_id(task_id, prompt, output_dir)
    
    # 轮询结果
    image_url = poll_result(task_id)
    if not image_url:
        return False
    
    print(f"  URL: {image_url[:50]}...")
    
    # 下载
    resp = requests.get(image_url, timeout=60)
    with open(output_path, 'wb') as f:
        f.write(resp.content)
    
    print(f"  ✅ 完成 ({os.path.getsize(output_path)/1024:.1f} KB)")
    return True
```

---

## 配图要求

| 要求 | 说明 |
|------|------|
| 数量 | 3-5 张（硬性要求） |
| 尺寸 | 封面 900x500，正文比例不限 |
| 内容 | 与主题强相关，无商标 |
| 专属 | 每篇文章配图不能交叉使用 |

---

## Pitfalls（重要！）

### 积分浪费问题

| 问题 | 后果 | 解决方案 |
|------|------|----------|
| webHook="-1" | 任务异常失败 | 用假地址 |
| task_id 未持久化 | 超时后丢失，重新提交 | 保存到 tasks.json |
| 全量重试 | 重复提交所有任务 | 只处理失败的 |
| 相同 prompt 重试 | 失败的继续失败 | 换 prompt 变体 |
| 轮询超时过短 | 任务还在运行就放弃 | 延长到 5 分钟 |

### 积分消耗

- fast 模型：440 积分/张
- pro 模型：900 积分/张
- 余额 5000 积分 ≈ 11 张图

### 生成耗时

| 类型 | 耗时 |
|------|------|
| 简单 prompt | 8-30 秒 |
| 复杂 prompt | 90-200 秒 |
| 失败 prompt | 可能超过 200 秒 |

---

## Prompt 模板

```python
TEMPLATES = {
    "cover": [
        "{topic} concept art, professional digital illustration, modern tech style, blue gradient",
        "{topic} visual design, futuristic concept, clean composition",
    ],
    "content": [
        "{topic} illustration, modern minimalist design, tech atmosphere",
        "{topic} diagram, professional infographic style, digital art",
        "{topic} scene, technology theme, warm lighting",
    ]
}

def get_prompt(topic: str, type: str, variant: int = 0) -> str:
    """获取 prompt，失败后用变体"""
    prompts = TEMPLATES.get(type, TEMPLATES["content"])
    if variant < len(prompts):
        return prompts[variant].format(topic)
    return prompts[0].format(topic) + f", variant {variant}"
```

---

## 调整封面尺寸

```python
import subprocess

def resize_cover(input_path: str, output_path: str, width: int = 900, height: int = 500):
    """使用 sips 调整封面图尺寸"""
    
    subprocess.run([
        'sips', '-z', str(height), str(width),
        input_path, '--out', output_path
    ], capture_output=True)
```

---

*整合自：ai-image-generation + 实际使用经验（2026-04-14）*
*Last updated: 2026-04-14*