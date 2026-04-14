---
module: 04-image-generation
type: reference
source: ai-image-generation (整合)
---

# 模块 4: AI 配图生成

为文章生成 3-5 张专属配图。

---

## 配置

路径：`~/.hermes/mcn_config.yaml`

```yaml
image_generation:
  default_provider: grsai
  providers:
    grsai:
      api_url: https://api.grsai.com/v1/draw/nano-banana
      api_key: sk-xxx
      models:
        fast: nano-banana-fast    # 440 积分/张
        pro: nano-banana-pro      # 900 积分/张
      default_model: fast
      timeout: 120
      cost_per_image: 440
  
  prompt_templates:
    科技："Professional product photography of {}, minimalist background, clean design, 16:9"
    AI: "{} concept art, digital technology style, blue gradient, futuristic, 16:9"
```

---

## 执行流程

### 1. 生成单张图片

```python
import json
import urllib.request
import ssl

def generate_image(prompt: str, timeout: int = 120) -> str:
    """生成单张图片"""
    
    config = yaml.safe_load(open("~/.hermes/mcn_config.yaml"))
    provider = config['image_generation']['providers']['grsai']
    
    api_url = provider['api_url']
    api_key = provider['api_key']
    model = provider['default_model']
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {"model": model, "prompt": prompt}
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(api_url, data=json.dumps(data).encode(), headers=headers)
    resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
    response_text = resp.read().decode()
    
    # 解析流式响应（最后一行）
    lines = response_text.strip().split('\n')
    for line in reversed(lines):
        if line.startswith('data:'):
            result = json.loads(line[5:].strip())
            if result.get('status') == 'succeeded':
                return result['results'][0]['url']
    
    return None
```

### 2. 批量生成（带重试）

```python
def generate_images_with_retry(topic: str, keywords: list, count: int = 4, max_retries: int = 2) -> list:
    """带重试的批量生成"""
    
    images = []
    failed_indices = []
    
    # 首次生成
    for i, keyword in enumerate(keywords[:count]):
        prompt = f"{topic} {keyword}, high quality"
        url = generate_image(prompt)
        
        if url and download_image(url, f"/tmp/img_{i+1}.png"):
            images.append({'url': url, 'keyword': keyword})
        else:
            failed_indices.append(i)
    
    # 重试
    for retry in range(max_retries):
        if not failed_indices:
            break
        
        for idx in failed_indices:
            prompt = f"{topic} {keywords[idx]} variant {retry+1}"
            url = generate_image(prompt)
            if url:
                images.append({'url': url, 'keyword': keywords[idx]})
    
    return images
```

### 3. 下载图片

```python
import requests

def download_image(image_url: str, save_path: str) -> bool:
    """下载图片"""
    
    try:
        response = requests.get(image_url, timeout=60, verify=False)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        print(f"下载错误：{e}")
        return False
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

## Pitfalls

1. **积分消耗**：440 积分/张（fast 模型）
2. **生成耗时**：30-50 秒，timeout 设 120 秒
3. **失败重试**：max_retries=2
4. **数量验证**：生成后必须验证≥3 张
5. **命名规范**：img_1, img_2, img_3... 连续命名

---

*整合自：ai-image-generation*
