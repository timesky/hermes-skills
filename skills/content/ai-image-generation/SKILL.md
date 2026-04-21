---
name: ai-image-generation
description: AI图片生成技能 - 支持多平台API（GrsAI/Nano Banana/DALL-E等），统一接口调用，用于MCN配图生成
tags: [ai, image, generation, grsai, dall-e, nano-banana, mcn]
version: 2.2.0
updated: 2026-04-17
---

# AI 图片生成技能

统一的多平台AI图片生成接口，支持配置不同提供商。

---

## ⭐ 配置文件

路径：`~/.hermes/mcn_config.yaml`

```yaml
image_generation:
  # 默认提供商
  default_provider: grsai
  
  # 提供商配置
  providers:
    grsai:
      name: GrsAI
      api_url: https://grsai.dakka.com.cn/v1/draw/nano-banana  # 国内直连
      api_key: sk-xxx  # 你的API Key
      models:
        fast: nano-banana-fast    # 440积分/张
        pro: nano-banana-pro      # 900积分/张
      default_model: fast
      timeout: 90
      response_format: stream     # 流式响应（data:行）
      cost_per_image: 440        # 积分消耗
    
    # 可添加其他提供商
    openai:
      name: OpenAI DALL-E
      api_url: https://api.openai.com/v1/images/generations
      api_key: YOUR_OPENAI_KEY
      models:
        dall-e-3: dall-e-3
      default_model: dall-e-3
      timeout: 60
      response_format: sync
    
    stability:
      name: Stability AI
      api_url: https://api.stability.ai/v1/generation
      api_key: YOUR_STABILITY_KEY
      models:
        sd-xl: stable-diffusion-xl-1024-v1-0
      default_model: sd-xl
      timeout: 30

  # 提示词模板（按领域）
  prompt_templates:
    科技: "Professional product photography of {}, minimalist background, clean design, high quality, 16:9"
    航天: "{} scene, cinematic shot, dramatic lighting, starry sky background, professional composition, 16:9"
    职场: "{} illustration, modern office style, warm colors, professional atmosphere, 16:9"
    AI: "{} concept art, digital technology style, blue gradient, futuristic, 16:9"
    时政: "{} news scene, professional photography, documentary style, 16:9"
```

---

## GrsAI 详细说明

### 积分消耗（重要！）

| 模型 | 积分消耗 | 人民币 |
|------|----------|--------|
| nano-banana-fast | **440积分/张** | ¥0.022 |
| nano-banana-pro | 900积分/张 | ¥0.09 |

**⚠️ 注意**：积分≠人民币，5000积分约可生成11张图片

### 生成耗时

30-50秒，建议 timeout 设置为 **120秒**（用户要求）

### API 调用方式（重要！）

**推荐方式：webHook="-1" + 轮询 result**

```python
# 1. 提交任务（webHook="-1" 立即返回 task_id）
POST /v1/draw/nano-banana
Body: {"model": "nano-banana-fast", "prompt": "...", "webHook": "-1"}
返回: {"code": 0, "data": {"id": "task_id"}}

# 2. 轮询结果（最多60次，每次间隔2秒）
POST /v1/draw/result
Body: {"id": "task_id"}
返回: {"code": 0, "data": {"status": "succeeded", "results": [{"url": "..."}]}}
```

**⚠️ 注意**：
- **不要用流式等待**：直接等待流式响应会超时（execute_code 中 urllib SSL 经常超时）
- **使用 terminal + curl**：比 Python urllib 更稳定
- **API 地址**：国内直连 `https://grsai.dakka.com.cn`

**推荐方式：subprocess + curl（更稳定）**

execute_code 中 urllib.request 经常 SSL 超时，推荐用 subprocess + curl：

```python
import subprocess
import json
import time
import os

def submit_and_poll_curl(prompt: str, api_key: str, max_polls: int = 60, interval: int = 2) -> str:
    """用 curl 提交任务并轮询结果（推荐方式）"""
    
    api_base = "https://grsai.dakka.com.cn"
    
    # 1. 提交任务（用 curl）
    submit_cmd = [
        'curl', '-s', '-X', 'POST', api_base + "/v1/draw/nano-banana",
        '-H', f'Authorization: Bearer {api_key}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({"model": "nano-banana-fast", "prompt": prompt, "webHook": "-1"}),
        '--max-time', '30'
    ]
    
    result = subprocess.run(submit_cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    if data.get('code') != 0:
        print(f"提交失败: {data}")
        return None
    
    task_id = data['data']['id']
    print(f"Task ID: {task_id}")
    
    # 2. 轮询结果（用 curl）
    for i in range(max_polls):
        poll_cmd = [
            'curl', '-s', '-X', 'POST', api_base + "/v1/draw/result",
            '-H', f'Authorization: Bearer {api_key}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({"id": task_id}),
            '--max-time', '30'
        ]
        
        result = subprocess.run(poll_cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        status = data.get('data', {}).get('status', 'unknown')
        progress = data.get('data', {}).get('progress', 0)
        
        if i % 5 == 0:
            print(f"进度: {progress}% ({i+1}/{max_polls})")
        
        if status == 'succeeded':
            url = data['data']['results'][0]['url']
            print(f"✅ 生成成功")
            return url
        elif status == 'failed':
            print(f"❌ 生成失败")
            return None
        
        time.sleep(interval)
    
    print(f"⚠️ 轮询超时")
    return None

def download_image_curl(url: str, save_path: str) -> bool:
    """用 curl 下载图片"""
    cmd = ['curl', '-s', '-o', save_path, url, '--max-time', '60']
    subprocess.run(cmd)
    
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
        print(f"✅ 已保存: {save_path} ({os.path.getsize(save_path)/1024:.1f} KB)")
        return True
    return False
```

**⚠️ urllib.request 方式（不推荐）**

execute_code 环境中 SSL handshake 经常超时，仅供参考：

---

## 核心函数

### generate_image()

```python
from pathlib import Path
import yaml
import json
import ssl
import urllib.request
import requests

CONFIG_PATH = Path.home() / ".hermes" / "mcn_config.yaml"

def get_config():
    """加载配置"""
    return yaml.safe_load(CONFIG_PATH.read_text())

def generate_image(
    prompt: str,
    provider: str = None,
    model: str = None,
    timeout: int = 90
) -> str:
    """
    生成单张图片
    
    Args:
        prompt: 图片描述（英文效果更好）
        provider: 提供商（grsai/openai/stability）
        model: 模型名称（fast/pro/dall-e-3等）
        timeout: 超时秒数
    
    Returns:
        图片URL 或 None
    """
    
    config = get_config()
    
    # 获取提供商配置
    provider_name = provider or config['image_generation']['default_provider']
    provider_cfg = config['image_generation']['providers'][provider_name]
    
    api_url = provider_cfg['api_url']
    api_key = provider_cfg['api_key']
    model_name = model or provider_cfg['default_model']
    
    # 构建请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": provider_cfg['models'].get(model_name, model_name),
        "prompt": prompt
    }
    
    print(f"提交任务: {prompt[:50]}...")
    print(f"提供商: {provider_cfg['name']}, 模型: {model_name}")
    
    # 根据响应格式处理
    if provider_cfg['response_format'] == 'stream':
        return handle_stream(api_url, headers, data, timeout)
    else:
        return handle_sync(api_url, headers, data, timeout)

def handle_stream(api_url, headers, data, timeout):
    """处理流式响应（GrsAI）"""
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(api_url, data=req_data, headers=headers)
    
    resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
    response_text = resp.read().decode('utf-8')
    
    # 解析最后一行
    lines = response_text.strip().split('\n')
    
    for line in reversed(lines):
        if line.startswith('data:'):
            json_str = line[5:].strip()
            if json_str:
                result = json.loads(json_str)
                
                if result.get('status') == 'succeeded':
                    url = result['results'][0]['url']
                    print(f"生成成功！")
                    return url
    
    print(f"生成失败或超时")
    return None

def handle_sync(api_url, headers, data, timeout):
    """处理同步响应（DALL-E等）"""
    
    response = requests.post(api_url, headers=headers, json=data, timeout=timeout)
    result = response.json()
    
    if result.get('data'):
        return result['data'][0]['url']
    
    return None

def download_image(image_url: str, save_path: str) -> bool:
    """下载图片（使用requests更稳定）"""
    
    try:
        response = requests.get(image_url, timeout=60, verify=False)
        
        if response.status_code == 200:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"已保存: {save_path} ({len(response.content)} bytes)")
            return True
        
        return False
    
    except Exception as e:
        print(f"下载错误: {e}")
        return False
```

---

### generate_article_images()

批量生成文章配图。

**规则**：每篇 3 张（首图 + 2 张段落图）

**流程**：先排版 → 确定段落图位置 → 根据段落内容摘要生成配图

```python
def generate_article_images(
    topic: str,
    article_path: str,  # 必须提供，用于段落差异化
    count: int = 3,  # 固定3张：cover + img_1 + img_2
    provider: str = "doubao",  # 默认豆包（支持中文）
    save_dir: str = "/tmp/article_images"
) -> list:
    """
    为文章生成专属配图
    
    Args:
        topic: 文章主题（用于文件命名）
        article_path: 文章路径（必须提供，用于段落差异化）
        count: 图片数量（默认3张）
        provider: 提供商（doubao/grsai）
        save_dir: 保存目录
    
    Returns:
        图片列表 [{url, path, name, paragraph}]
    
    分配：
        cover（首图）：主题概念，900x500px
        img_1：前半部分段落内容
        img_2：后半部分段落内容
    """
    
    import os
    os.makedirs(save_dir, exist_ok=True)
    
    config = get_config()
    
    # 获取提示词模板
    templates = config['image_generation']['prompt_templates']
    template = templates.get(domain, templates['科技'])
    
    images = []
    
    for i, keyword in enumerate(keywords[:count]):
        prompt = template.format(keyword)
        
        print(f"\n=== 生成图片 {i+1}/{count} ===")
        print(f"关键词: {keyword}")
        
        image_url = generate_image(prompt)
        
        if image_url:
            save_path = f"{save_dir}/{topic}_{i+1}.png"
            
            if download_image(image_url, save_path):
                images.append({
                    'url': image_url,
                    'path': save_path,
                    'keyword': keyword
                })
    
    print(f"\n完成: {len(images)} 张图片")
    
    return images
```

---

## 使用示例

### 单张图片

```python
# 使用默认提供商（GrsAI fast）
url = generate_image("Huawei foldable smartphone, tech blue, minimalist")

if url:
    download_image(url, "/tmp/test.png")
```

### 指定提供商和模型

```python
# 使用 GrsAI pro（高质量）
url = generate_image(
    prompt="OPPO Find X9 smartphone, premium design",
    provider="grsai",
    model="pro"
)

# 使用 DALL-E
url = generate_image(
    prompt="Space rocket launch scene",
    provider="openai",
    model="dall-e-3"
)
```

### 批量生成文章配图

```python
images = generate_article_images(
    topic="华为Pura",
    keywords=["华为折叠屏", "科技手机", "现代设计"],
    count=3,
    domain="科技",
    save_dir="/tmp/article_images/huawei"
)
```

---

## 测试图片（已下载）

用于排版测试，不消耗API：

```json
[
  {"url": "https://file2.aitohumanize.com/file/2f4da763148b49dea83fa9ca6c691c27.png", "name": "apple_simple"},
  {"url": "https://file1.aitohumanize.com/file/658a4317281640f9b2daf592e8637532.png", "name": "oppo_findx9"},
  {"url": "https://file2.aitohumanize.com/file/cda21bd9fcbf4a5aae4be7fcdbb86757.png", "name": "image_3"},
  {"url": "https://file2.aitohumanize.com/file/34bde84d085746e995a9c169e92c2d3d.png", "name": "image_4"},
  {"url": "https://file4.aitohumanize.com/file/81b5caa2257d44ce900ec865cbbb1f5a.png", "name": "huawei_pura"}
]
```

本地路径：`/tmp/test_images/`

---

## ⭐ 失败重试机制

**问题**：图片生成可能因网络、超时等原因失败，导致配图数量不足

**解决方案**：
```python
def generate_images_with_retry(
    topic: str,
    keywords: list,
    count: int = 4,
    max_retries: int = 2,
    save_dir: str = "/tmp/article_images"
) -> list:
    """带重试机制的批量图片生成"""
    
    import os
    os.makedirs(save_dir, exist_ok=True)
    
    images = []
    failed_indices = []
    
    # 首次生成
    print(f"=== 首次生成 {count} 张图片 ===")
    for i, keyword in enumerate(keywords[:count]):
        prompt = f"{topic} {keyword}, high quality, professional"
        url = generate_image(prompt, timeout=120)
        
        if url:
            save_path = f"{save_dir}/img_{i+1}.png"
            if download_image(url, save_path):
                images.append({'path': save_path, 'keyword': keyword, 'index': i})
                print(f"✓ 图片{i+1}: {keyword}")
            else:
                failed_indices.append(i)
                print(f"✗ 图片{i+1}下载失败")
        else:
            failed_indices.append(i)
            print(f"✗ 图片{i+1}生成失败")
    
    # 重试失败的
    for retry in range(max_retries):
        if not failed_indices:
            break
        
        print(f"\n=== 重试第{retry+1}次，剩余{len(failed_indices)}张 ===")
        still_failed = []
        
        for idx in failed_indices:
            keyword = keywords[idx]
            # 使用不同的prompt尝试
            prompt = f"{topic} {keyword} variant {retry+1}, creative design"
            url = generate_image(prompt, timeout=120)
            
            if url:
                save_path = f"{save_dir}/img_{idx+1}.png"
                if download_image(url, save_path):
                    images.append({'path': save_path, 'keyword': keyword, 'index': idx})
                    print(f"✓ 重试成功: 图片{idx+1}")
                else:
                    still_failed.append(idx)
            else:
                still_failed.append(idx)
        
        failed_indices = still_failed
    
    # 最终结果
    print(f"\n=== 生成完成 ===")
    print(f"成功: {len(images)}张")
    if failed_indices:
        print(f"⚠️ 失败: {len(failed_indices)}张（索引: {failed_indices}）")
        print(f"建议手动补充或使用备选关键词")
    
    return images
```

**使用示例**：
```python
images = generate_images_with_retry(
    topic="华为折叠屏",
    keywords=["科技手机", "现代设计", "商务场景", "产品展示"],
    count=4,
    max_retries=2,
    save_dir="/tmp/article_images/huawei"
)

# 验证数量
if len(images) < 3:
    print("⚠️ 配图不足，需要补充")
```

---

## ⭐ 配图提示词设计（重要！）

**问题**：只用主题标题+通用模板会导致配图雷同，缺乏差异化

**解决方案**：根据文章段落内容定制提示词

```python
def generate_contextual_prompts(article_paragraphs: list, topic: str) -> list:
    """
    根据文章段落生成差异化提示词
    
    Args:
        article_paragraphs: 段落摘要列表（如 ["微软OpenAI合作变化", "会计争议", "算力之争"]）
        topic: 整体主题
    
    Returns:
        提示词列表（封面+内容图）
    """
    
    # 封面图：整体主题，强调对比和冲突
    cover_prompt = f"{topic} concept art, professional digital illustration, dramatic lighting, contrasting elements, modern tech style"
    
    # 内容图：根据每个段落定制
    paragraph_prompts = {
        "合作变化": "business partnership evolving, handshake fading, tech companies strategic alliance, corporate relationship tension",
        "财务争议": "financial data controversy infographic, accounting numbers disputed, charts and graphs, modern business illustration",
        "算力之争": "AI computing power competition, GPU data centers, server farm infrastructure, technology hardware",
        "理念之争": "AI philosophy debate, two visions concept, technology ethics, contrasting ideologies",
        "竞争态势": "market competition battle, corporate rivals, business warfare, strategic positioning"
    }
    
    prompts = [{'name': 'cover', 'prompt': cover_prompt}]
    
    for i, para in enumerate(article_paragraphs[:3]):
        # 根据段落关键词匹配模板
        matched = False
        for key, template in paragraph_prompts.items():
            if key in para:
                prompts.append({'name': f'img_{i+1}', 'prompt': template})
                matched = True
                break
        
        if not matched:
            # 默认模板
            prompts.append({'name': f'img_{i+1}', 'prompt': f"{para}, professional illustration, modern design, tech atmosphere"})
    
    return prompts
```

**示例**：
```python
# 主题：OpenAI内部信泄露：手撕Anthropic数据造假
paragraphs = ["微软和OpenAI的塑料兄弟情", "手撕Anthropic会计方式", "算力之争", "理念之争"]

prompts = generate_contextual_prompts(paragraphs, "OpenAI versus Anthropic rivalry")

# 结果：
# cover: "OpenAI versus Anthropic rivalry concept art..."
# img_1: "business partnership evolving..."
# img_2: "financial data controversy infographic..."
# img_3: "AI computing power competition..."
```

---

## Pitfalls

1. **⚠️ GrsAI积分消耗**：实际是440积分/张，不是22积分！
2. **API调用方式**：使用 `webHook="-1"` + 轮询 result，不要直接等待流式响应
3. **⚠️ SSL超时问题**：execute_code 中 urllib.request 经常 SSL handshake 趨时，推荐用 terminal + curl
4. **API地址**：国内直连 `https://grsai.dakka.com.cn`，海外 `https://grsaiapi.com`
5. **生成耗时**：30-50秒，轮询最多60次（每次间隔2秒）
6. **下载稳定性**：使用requests而非urllib
7. **图片URL有效期**：可能有限期，建议及时下载保存
8. **⚠️ 配图数量验证**：生成后必须验证数量≥3张，不足则重试或补充
9. **命名规范**：使用 img_1, img_2, img_3... 连续命名，跳过索引说明失败
10. **⚠️ 配图提示词差异化**：必须根据文章段落内容定制提示词，不能只用主题标题+通用模板（会导致图片雷同）
11. **⚠️ API响应结构**：图片URL在 `data['results'][0]['url']`，不是 `imageUrl` 或 `url` 字段
12. **⚠️ GrsAI 中文乱码**：Nano Banana 不支持中文提示词，图片中的文字会是乱码！必须使用英文提示词，或接入豆包生图 API
13. **⚠️ task_id 复用**：一旦获得 task_id，就不要重新提交任务，直接轮询等待结果。重复提交会消耗额外积分
14. **⚠️ 内容审核失败**：`output_moderation` 表示提示词触发审核，需要修改提示词（避免敏感词，改用纯英文描述）
15. **⚠️ 封面图尺寸**：公众号封面要求 900×500px，需要用 PIL 调整：`img.resize((900, 500), Image.LANCZOS)`

---

## ⭐ 豆包生图 API（推荐用于中文场景）

**问题**：GrsAI/Nano Banana 不支持中文提示词，图片中的文字是乱码

**解决方案**：接入豆包（字节跳动）生图 API，支持中文提示词

### 基本信息

| 项目 | 内容 |
|------|------|
| 提供商 | 字节跳动 / 火山引擎方舟平台 |
| API Endpoint | `https://ark.cn-beijing.volces.com/api/v3/images/generations` |
| 模型 ID | `doubao-seedream-4-0-250828` 或 `doubao-seedream-5-0-lite` |
| 平台地址 | https://ark.cn-beijing.volces.com/ |
| 免费额度 | 每个模型 **200张** |

### 关键优势

1. **✅ 支持中文提示词** - 这是最大优势，可以直接用中文描述，文字渲染正确
2. **图片质量稳定** - 字节跳动的图像生成技术成熟
3. **调用简单** - 类似 OpenAI 格式，同步响应
4. **免费额度** - 每个模型 200 张免费额度

### API 调用示例

```python
import requests

API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
API_KEY = "your_api_key"
MODEL_ID = "doubao-seedream-4-0-250828"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

payload = {
    "model": MODEL_ID,
    "prompt": "雨后彩虹，一群鸟儿飞过，高质量插画",  # 支持中文！
    "size": "1024x1024",
    "response_format": "url",
    "stream": False,
    "watermark": False
}

resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
result = resp.json()

# 图片 URL 在 result['data'][0]['url']
image_url = result['data'][0]['url']
```

### 脚本调用

```bash
# 单张图片
python ~/.hermes/skills/content/ai-image-generation/scripts/doubao-image-gen.py \
    --prompt "科技概念插画，蓝色调，现代设计" \
    --output ./test.png

# 批量生成（配合 MCN）
python ~/.hermes/skills/content/ai-image-generation/scripts/doubao-image-gen.py \
    --topic "华为折叠屏" \
    --count 4 \
    --date 2026-04-19 \
    --article ./article.md
```

### 配置添加（mcn_config.yaml）

```yaml
image_generation:
  default_provider: doubao  # 改为豆包
  
  providers:
    doubao:
      name: 豆包生图
      api_url: https://ark.cn-beijing.volces.com/api/v3/images/generations
      api_key: YOUR_VOLCES_API_KEY  # 需要申请
      models:
        seedream-4.0: doubao-seedream-4-0-250828
        seedream-5.0-lite: doubao-seedream-5-0-lite
      default_model: seedream-4.0
      timeout: 60
      response_format: sync
      advantage: 中文提示词支持
    
    # 保留 grsai 作为备用（英文场景）
    grsai:
      name: GrsAI Nano Banana
      api_url: https://grsai.dakka.com.cn/v1/draw/nano-banana
      api_key: sk-xxx
      models:
        fast: nano-banana-fast
      timeout: 120
      response_format: stream
      cost_per_image: 440
```

### 申请步骤

1. **注册火山引擎账号**：https://www.volcengine.com
2. **实名认证**（需要身份证）
3. **开通方舟平台**：https://ark.cn-beijing.volces.com/
4. **开通文生图模型**：在模型广场找到 `Doubao-Seedream-4.0` 或 `5.0-lite`
5. **创建 API Key**：左侧菜单 → API Key 管理 → 创建 → 复制

### 对比

| 特性 | GrsAI/Nano Banana | 豆包生图 |
|------|-------------------|----------|
| 中文提示词 | ❌ 不支持（乱码） | ✅ 支持 |
| 图片质量 | 一般 | 较好 |
| 免费额度 | 无明确额度 | 每模型200张 |
| API 稳定性 | 轮询慢（30-50秒） | 同步快（~10秒） |
| 文字渲染 | ❌ 乱码 | ✅ 正确 |
| 调用方式 | webHook轮询 | 直接POST |

### 推荐

- **中文场景** → 豆包（公众号文章配图）
- **英文场景** → GrsAI（英文提示词时）

---

## 相关技能

- `mcn-content-writer`: 内容生成（调用本技能生成配图）
- `mcn-wechat-publisher`: 公众号发布（上传图片到素材库）
- `mcn-hotspot-research`: 热点调研（选题来源）

---

*Updated: 2026-04-17 by Luna*