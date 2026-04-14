---
module: config
type: reference
---

# 配置汇总

## 配置文件位置

| 文件 | 路径 | 作用 |
|------|------|------|
| 主配置 | `~/.hermes/mcn_config.yaml` | 热点领域、文章要求、配图配置 |
| 公众号 | `~/.hermes/wechat_mp_config.yaml` | AppID、Secret、作者名 |

---

## 主配置详解

### 文章要求

```yaml
article:
  min_chars: 1500          # 最少字数
  max_chars: 2000          # 最多字数
  min_images: 3            # 最少配图
  max_images: 5            # 最多配图
  cover_size: 900x500      # 封面尺寸
  humanization_threshold: 45  # 去 AI 化评分阈值
```

### 热点领域

```yaml
hotspot:
  domains:
    - name: 科技
      keywords: [科技，数码，手机，AI, 互联网，华为，苹果]
      platforms: [weibo, zhihu, toutiao, huxiu]
      top_n: 10
    - name: 编程
      keywords: [编程，代码，开发，程序员，Python]
      platforms: [zhihu, juejin, hackernews]
      top_n: 10
    - name: 机器人
      keywords: [机器人，宇树，人形机器人，AI 机器人]
      platforms: [weibo, zhihu, toutiao]
      top_n: 10
  
  exclude_published:
    days: 30  # 排除近 30 天已发布主题
    keywords: [宇树机器人，小米 MiMo, 华为 Pura]  # 已发布关键词
```

### 配图生成

```yaml
image_generation:
  default_provider: grsai
  providers:
    grsai:
      api_url: https://api.grsai.com/v1/draw/nano-banana
      api_key: sk-xxx
      cost_per_image: 440  # 积分/张
      timeout: 120
  prompt_templates:
    科技："Professional product photography of {}, minimalist, 16:9"
    AI: "{} concept art, digital technology, blue gradient, 16:9"
```

---

## 公众号配置

```yaml
appid: wx47533ce9c8854fb5
secret: 2b990fc5...eb2f
author: TimeSky

cover_prompts:
  科技：tech cover, blue gradient, minimalist
  商业：business cover, dark blue, professional
  生活：lifestyle cover, warm colors
  热点：news cover, bold colors, dynamic
```

---

## 修改配置

### 方式 1：直接编辑

```bash
nano ~/.hermes/mcn_config.yaml
```

### 方式 2：脚本修改

```bash
# 修改关注领域
python scripts/update-config.py --set "hotspot.domains=[科技，AI,投资]"

# 修改字数要求
python scripts/update-config.py --set "article.min_chars=1800"
```

---

*配置说明汇总*
