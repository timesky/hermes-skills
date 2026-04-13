---
name: ai-image-generation
description: AI图片生成技能 - 使用 Gemini Nano Banana、DALL-E 等生成主题配图
tags: [ai, image, generation, gemini, nano-banana, dalle]
version: 1.0.0
created: 2026-04-13
author: Luna
---

# AI图片生成技能

为公众号、博客等内容自动生成主题相关配图。

---

## Gemini Nano Banana（推荐）

Google Gemini 内置图片生成功能，免费额度充足。

### 额度对比

| 功能 | 免费用户 | Google AI Pro | Google AI Ultra |
|------|----------|--------------|-----------------|
| Nano Banana | 100张/天 | **1000张/天** | 1000张/天 |
| Nano Banana Pro | 3张/天 | **100张/天** | 1000张/天 |

### API 额度（独立计算）

| 渠道 | 额度 | 说明 |
|------|------|------|
| Gemini App | 订阅额度 | 手动使用网页 |
| Gemini API | 250请求/天 | 免费 API Key |
| AI Studio | 500-1000张/天 | 网页界面 |

**关键**：订阅额度 ≠ API 额度，两者独立。

---

## 使用方式

### 方案 A：Gemini App（手动，安全）

```
1. 访问 https://gemini.google.com
2. 输入图片生成提示词
3. 下载生成图片
4. 上传到素材库
```

**优点**：
- 使用订阅额度（1000张/天）
- 无封号风险
- 效果好，支持中文

### 方案 B：API 调用（自动化）

**Python 示例**：
```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

prompt = "华为折叠屏手机，科技感，蓝色调，产品摄影风格"

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt],
)

for part in response.parts:
    if part.inline_data is not None:
        image = part.as_image()
        image.save("output.png")
```

---

## 提示词模板

### 产品/科技类
```
A photorealistic shot of [产品名称], premium design, 
tech blue color theme, modern minimalist background, 
product photography style, 16:9 aspect ratio
```

### 新闻/事件类
```
[事件描述] scene, dramatic lighting, 
cinematic shot, professional news style, 16:9
```

### 商业/职场类
```
Modern office setting, [场景描述], 
professional atmosphere, business casual style, 16:9
```

---

## 封号风险与安全使用

### 风险行为

| 行为 | 风险等级 |
|------|----------|
| IP国家不一致 | 高 |
| 多设备短时间登录 | 高 |
| 使用公共代理/VPN | 高 |
| 生成违规内容 | 高 |
| 高频突破限制 | 中 |

### 安全建议

| 建议 | 说明 |
|------|------|
| 固定IP | 使用稳定网络环境 |
| 合理频率 | 不超过每日限制 |
| 自然间隔 | 每次请求间隔1-2秒 |
| 合规内容 | 不生成暴力/仇恨内容 |
| 单设备使用 | 长期在一个环境 |

---

## 其他方案

### DALL-E（OpenAI）

| 项目 | 说明 |
|------|------|
| API Key | platform.openai.com |
| 费用 | $0.02-0.04/张 |
| 模型 | DALL-E 3 |

**调用示例**：
```python
import openai
client = openai.OpenAI(api_key="YOUR_KEY")

response = client.images.generate(
    model="dall-e-3",
    prompt="华为折叠屏手机，科技感",
    size="1024x1024",
    n=1
)

image_url = response.data[0].url
```

### Stable Diffusion（免费）

| 项目 | 说明 |
|------|------|
| 本地部署 | 需要 GPU |
| 模型 | 约 4GB |
| 费用 | 免费 |

---

## 公众号配图限制

- ❌ 外部图片 URL 不被接受（Unsplash 等）
- ✅ 需要先上传到素材库
- ✅ 每篇文章配图必须专属，不能交叉使用
- ✅ 封面尺寸：900x500px

---

## ⚠️ 浏览器自动化限制

**OpenCLI browser 在 Gemini 页面不稳定**：
- 测试发现页面会崩溃（变成 about:blank）
- 原因：Gemini 的复杂 JS 状态管理
- 结论：**不推荐用浏览器自动化**

**替代方案**：
```
用户手动生成 → 复制图片URL/下载 → 我自动上传素材库
```

---

## 配图工作流

```
文章主题 → AI生成图片 → 下载 → 上传素材库 → 文章引用
```

**自动化流程**：
```python
def generate_and_upload(topic: str, access_token: str):
    # 1. AI生成
    image = generate_with_gemini(topic)
    
    # 2. 保存本地
    image.save(f"/tmp/{topic}.png")
    
    # 3. 上传素材库
    media_id = upload_to_wechat(f"/tmp/{topic}.png", access_token)
    
    return media_id
```

---

## 参考资料

- Gemini API: https://ai.google.dev
- 获取 API Key: https://ai.google.dev/gemini-api/docs/rate-limits
- 图片生成文档: https://ai.google.dev/gemini-api/docs/image-generation

---

*Last updated: 2026-04-13*