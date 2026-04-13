---
name: ai-image-generation
description: AI图片生成技能 - 支持多平台API（GrsAI/Nano Banana/DALL-E等），统一接口调用，用于MCN配图生成
tags: [ai, image, generation, grsai, dall-e, nano-banana, mcn]
version: 2.0.0
updated: 2026-04-13
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
      api_url: https://api.grsai.com/v1/draw/nano-banana
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

30-50秒，建议 timeout 设置为 90秒

### 响应格式

流式响应，多行 `data:` 格式：

```
data: {"id":"xxx","progress":1,"status":"running",...}
data: {"id":"xxx","progress":50,"status":"running",...}
data: {"id":"xxx","progress":100,"status":"succeeded","results":[{"url":"https://..."}]}
```

**解析方法**：提取最后一行 `status="succeeded"` 的 `results[0].url`

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

批量生成文章配图：

```python
def generate_article_images(
    topic: str,
    keywords: list,
    count: int = 4,
    domain: str = "科技",
    save_dir: str = "/tmp/article_images"
) -> list:
    """
    为文章生成专属配图
    
    Args:
        topic: 文章主题（用于文件命名）
        keywords: 关键词列表（生成不同角度图片）
        count: 图片数量
        domain: 领域（科技/航天/职场/AI）
        save_dir: 保存目录
    
    Returns:
        图片列表 [{url, path, keyword}]
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

## Pitfalls

1. **⚠️ GrsAI积分消耗**：实际是440积分/张，不是22积分！
2. **流式响应解析**：必须提取最后一行 `data:` 的JSON
3. **生成耗时**：30-50秒，timeout需设90秒
4. **下载稳定性**：使用requests而非urllib
5. **图片URL有效期**：可能有限期，建议及时下载保存

---

## 相关技能

- `mcn-content-rewriter`: 内容改写（调用本技能生成配图）
- `mcn-wechat-publisher`: 公众号发布（上传图片到素材库）
- `mcn-hotspot-aggregator`: 热点调研（选题来源）

---

*Updated: 2026-04-13 by Luna*