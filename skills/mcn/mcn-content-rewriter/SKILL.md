---
name: mcn-content-rewriter
description: MCN 内容改写技能 - 根据选题生成适合公众号的多版本文章，支持不同风格和长度
tags: [mcn, content, rewriter, wechat]
version: 1.0.0
created: 2026-04-12
author: Luna
---

# MCN 内容改写技能

根据选题生成适合公众号的多版本文章。

---

## 知识库路径

```
KB_ROOT = /Users/timesky/backup/知识库-Obsidian
TOPIC_DIR = KB_ROOT/tmp/topic/
CONTENT_DIR = KB_ROOT/tmp/content/
TEMPLATE_FILE = KB_ROOT/raw/notes/MCN运营调研/MCN运营-内容模板库.md
```

---

## 公众号文章模板

参考知识库中的内容模板库，主要使用：

### 标题公式

1. **数字 + 结果 + 方法**
   - 示例：3 个方法，让我半年存款翻倍

2. **人群 + 痛点 + 方案**
   - 示例：30 岁还没存款？这个理财计划适合你

3. **对比 + 反差 + 原因**
   - 示例：同样工作 5 年，为什么他存款是你的 10 倍？

### 开头模板

- 场景引入式
- 数据冲击式
- 故事叙述式

### 结尾模板

- 总结升华式
- 互动引导式

---

## 改写流程

### 1. 读取选题报告

```python
def read_topic_report(date: str):
    """读取选题报告"""
    filename = f"{KB_ROOT}/tmp/topic/{date}/topic-report.md"
    content = open(filename).read()
    # 解析推荐选题
    return parse_recommended_topics(content)
```

### 2. 获取原文内容

使用 OpenCLI 或 web-fetcher 获取原文：

```bash
# 知乎问题详情
opencli zhihu question <id>

# 微博帖子详情
opencli weibo post <id>

# 公众号文章下载
opencli weixin download <url>
```

### 3. 生成改写版本

```python
def generate_wechat_article(topic: dict, style: str = 'professional'):
    """生成公众号文章"""
    
    prompt = f"""
请根据以下热点话题，生成一篇适合微信公众号的文章。

话题：{topic['title']}
热度：{topic['heat']}
来源：{topic['source']}
相关领域：{topic['domain']}

要求：
1. 标题使用「数字 + 结果 + 方法」公式，吸引读者
2. 开头使用「场景引入式」，300 字内抓住读者
3. 正文 1500-2000 字，分 3-5 个要点阐述
4. 结尾使用「总结升华式 + 互动引导」
5. 风格：{style}（专业/轻松/故事）
6. 避免敏感内容，保持客观中立

输出格式：
## 标题
[生成的标题]

## 正文
[完整正文内容]

## 标签建议
#AI #技术 #干货 #思考
"""
    
    # 调用 LLM 生成
    return llm_generate(prompt)
```

### 4. 保存改写结果

```markdown
---
created: YYYY-MM-DD HH:MM
source_topic: 原话题标题
source_url: 原话题链接
platform: wechat-mp
status: draft
style: professional/casual/story
---

# 改写标题

[生成的标题]

## 正文

[完整正文内容]

## 标签建议

#AI #技术 #干货

## Meta

- 原话题: [链接](url)
- 改写时间: YYYY-MM-DD HH:MM
- 字数: N
- 风格: xxx
```

---

## 改写风格选项

| 风格 | 适用场景 | 特点 |
|------|----------|------|
| professional | 技术分析、行业解读 | 专业术语、数据支撑、逻辑严密 |
| casual | 生活话题、轻松内容 | 口语化、emoji、亲切感 |
| story | 人物故事、案例分析 | 叙事性强、情感共鸣 |

---

## 多版本生成

对于每个选题，生成 3 个版本：

1. **专业版**: 适合技术类读者
2. **轻松版**: 适合大众传播
3. **故事版**: 适合情感共鸣

```python
def generate_multi_versions(topic: dict):
    """生成多版本文章"""
    versions = {}
    
    for style in ['professional', 'casual', 'story']:
        versions[style] = generate_wechat_article(topic, style)
    
    return versions
```

---

## 输出目录结构

```
tmp/content/
└── YYYY-MM-DD/
    ├── 选题1-professional.md
    ├── 选题1-casual.md
    ├── 选题1-story.md
    ├── 选题2-professional.md
    ├── 选题2-casual.md
    ├── 选题2-story.md
    └── content-summary.md
```

---

## Pitfalls

1. **避免照搬原文**: 必须改写，不能直接复制
2. **保持原创性**: 改写后要有新的观点或角度
3. **敏感话题跳过**: 政治、负面、争议话题不改写
4. **字数控制**: 公众号文章建议 1500-2500 字
5. **标题长度**: 公众号标题建议 15-25 字

---

## 相关技能

- `mcn-topic-selector`: 选题分析（前置）
- `mcn-wechat-publisher`: 公众号发布（后置）
- `web-fetcher`: 获取原文内容

---

*Last updated: 2026-04-12 by Luna*