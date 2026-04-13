---
name: mcn-hotspot-aggregator
description: 多平台热搜聚合技能 - 使用 OpenCLI 抓取知乎、微博、抖音、小红书等平台热搜，保存到知识库等待选题分析
tags: [mcn, hotspot, aggregator, opencli]
version: 1.1.0
updated: 2026-04-12
---

# MCN 热搜聚合技能

> ⚠️ **工具选择**
> - **推荐**: OpenCLI（87平台预定义，社区维护）
> - **备用**: web-fetcher（定制场景）
> - Hermes 内置 Playwright browser 不兼容 macOS 11.7

自动抓取多平台热搜/热榜，聚合保存到知识库 tmp 目录，等待选题分析。

---

## 支持平台

| 平台 | OpenCLI 命令 | 输出格式 |
|------|-------------|----------|
| 知乎 | `opencli zhihu hot` | JSON (rank, title, heat, answers, url) |
| 微博 | `opencli weibo hot` | JSON (rank, word, hot_value, category, url) |
| 抖音 | `opencli douyin hot` | JSON |
| 小红书 | `opencli xiaohongshu feed` | JSON |
| HackerNews | `opencli hackernews hot` | JSON |
| B站 | `opencli bilibili hot` | JSON |

---

## 知识库路径

```
KB_ROOT = /Users/timesky/backup/知识库-Obsidian
HOTSPOT_DIR = KB_ROOT/tmp/hotspot/
```

---

## ⭐ 领域配置（可自定义）

默认关注领域：
```yaml
# ~/.hermes/mcn_config.yaml
domains:
  - name: 科技
    keywords: [科技, 数码, 手机, AI, 互联网]
    platforms: [weibo, zhihu]
    limit: 10
  
  - name: 编程
    keywords: [编程, 代码, 开发, 程序员, Python]
    platforms: [zhihu, hackernews]
    limit: 10
  
  - name: 机器人
    keywords: [机器人, 宇树, 人形机器人, AI机器人]
    platforms: [weibo, zhihu]
    limit: 10
```

修改配置后重启定时任务生效。

---

## 使用流程

### 1. 启动 OpenCLI Daemon

```bash
source ~/.nvm/nvm.sh && nvm use 22
opencli doctor  # 检查连接状态
```

### 2. 抓取热搜列表

```bash
# 知乎热榜
opencli zhihu hot --limit 20 --format json

# 微博热搜
opencli weibo hot --limit 20 --format json

# 抽音热榜
opencli douyin hot --limit 20 --format json

# 小红书推荐
opencli xiaohongshu feed --limit 20 --format json

# HackerNews
opencli hackernews hot --limit 20 --format json

# B站热门
opencli bilibili hot --limit 20 --format json
```

### 3. ⭐ 新增：提取文章摘要（提升选题质量）

**⚠️ 重要发现**：OpenCLI browser 无法直接获取微博内容（需要登录）。

**解决方案**：使用 Hermes `web_search + web_extract` 工具获取文章内容，再生成摘要。

```python
from hermes_tools import web_search, web_extract

def extract_hotspot_summaries(hotspots: list) -> list:
    """提取热搜文章摘要"""
    
    summaries = []
    
    for item in hotspots[:5]:  # Top 5
        title = item['title']
        
        # 1. 搜索相关文章
        result = web_search(title, limit=3)
        
        if result['data']['web']:
            urls = [article['url'] for article in result['data']['web'][:2]]
            
            # 2. 提取文章内容
            articles = web_extract(urls)
            
            for article in articles['results']:
                if article.get('content') and not article.get('error'):
                    content = article['content'][:2000]
                    
                    # 3. 生成摘要（summarize-pro executive 格式）
                    summary = {
                        'title': title,
                        'source': article.get('title', '未知'),
                        'url': article.get('url', ''),
                        'content': content[:500],  # 核心内容
                        'heat': item['heat']
                    }
                    
                    summaries.append(summary)
                    break
    
    return summaries
```

**摘要输出格式**：
```markdown
### 话题摘要

| 排名 | 标题 | 热度 | 摘要（200字） | 链接 |
|------|------|------|---------------|------|
| 1 | xxx | 12345 | 核心观点：... 主要论点：... | [查看](url) |
```

**摘要输出格式**：
```markdown
### 话题摘要

| 排名 | 标题 | 热度 | 摘要（200字） | 链接 |
|------|------|------|---------------|------|
| 1 | xxx | 12345 | 核心观点：... 主要论点：... | [查看](url) |
```

### 4. 保存到知识库

生成文件格式：
```markdown
---
created: YYYY-MM-DD HH:MM
platform: zhihu/weibo/douyin/xiaohongshu/hackernews/bilibili
status: pending
type: hotspot
---

# YYYY-MM-DD 平台热搜榜

## Top 20

| 排名 | 标题 | 热度 | 链接 |
|------|------|------|------|
| 1 | ... | ... | [查看](url) |
| 2 | ... | ... | [查看](url) |

## 原始 JSON

```json
[完整 JSON 数据]
```

## Meta
- 抓取时间: YYYY-MM-DD HH:MM
- 平台: xxx
- 条数: 20
```

---

## Python 调用示例

```python
import subprocess
import json
import datetime
import os

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
HOTSPOT_DIR = f"{KB_ROOT}/tmp/hotspot"

def fetch_hotspot(platform: str, limit: int = 20) -> list:
    """抓取指定平台热搜"""
    cmd = f"source ~/.nvm/nvm.sh && nvm use 22 && opencli {platform} hot --limit {limit} --format json"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # 提取 JSON 部分（跳过 "Now using node..." 行）
    lines = result.stdout.strip().split('\n')
    json_start = 0
    for i, line in enumerate(lines):
        if line.startswith('['):
            json_start = i
            break
    
    json_str = '\n'.join(lines[json_start:])
    return json.loads(json_str)

def save_hotspot(platform: str, data: list):
    """保存热搜到知识库"""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 创建目录
    os.makedirs(f"{HOTSPOT_DIR}/{date_str}", exist_ok=True)
    
    # 生成 Markdown
    md_content = f"""---
created: {time_str}
platform: {platform}
status: pending
type: hotspot
---

# {date_str} {platform} 热搜榜

## Top {len(data)}

"""
    
    # 表格
    md_content += "| 排名 | 标题 | 热度 | 链接 |\n|------|------|------|------|\n"
    
    for item in data:
        rank = item.get('rank', item.get('position', '?'))
        title = item.get('title', item.get('word', item.get('name', '?')))
        heat = item.get('heat', item.get('hot_value', item.get('score', '?')))
        url = item.get('url', '')
        md_content += f"| {rank} | {title} | {heat} | [查看]({url}) |\n"
    
    md_content += f"""
## 原始 JSON

```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

## Meta
- 抓取时间: {time_str}
- 平台: {platform}
- 条数: {len(data)}
"""
    
    # 写入文件
    filename = f"{HOTSPOT_DIR}/{date_str}/{platform}-hotspot.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return filename

def aggregate_all_platforms():
    """抓取所有平台热搜"""
    platforms = ['zhihu', 'weibo', 'douyin', 'xiaohongshu', 'hackernews', 'bilibili']
    results = {}
    
    for platform in platforms:
        try:
            data = fetch_hotspot(platform)
            filename = save_hotspot(platform, data)
            results[platform] = {'count': len(data), 'file': filename}
        except Exception as e:
            results[platform] = {'error': str(e)}
    
    return results
```

---

## 输出目录结构

```
tmp/hotspot/
└── YYYY-MM-DD/
    ├── zhihu-hotspot.md
    ├── weibo-hotspot.md
    ├── douyin-hotspot.md
    ├── xiaohongshu-hotspot.md
    ├── hackernews-hotspot.md
    └── bilibili-hotspot.md
```

---

## Pitfalls

1. **OpenCLI Daemon 必须运行**: 抓取前检查 `opencli doctor`
2. **Browser Extension 必须连接**: 否则会超时
3. **JSON 提取要跳过前几行**: nvm 输出会混杂在结果中
4. **不同平台字段名不同**: title/word/name, heat/hot_value/score
5. **抖音可能超时**: 暂时跳过不影响其他平台

---

## 与入口技能的关系

**入口技能**：`wechat-mp-auto-publish`（MCN 唯一入口，定时任务 + 人工确认 + 一键执行）

**子技能**（可单独调用）：
- `mcn-hotspot-aggregator`: 热搜抓取
- `mcn-topic-selector`: 选题分析
- `mcn-content-rewriter`: 内容改写
- `mcn-wechat-publisher`: 公众号发布

---

## 相关技能

- `mcn-topic-selector`: 热搜 → 选题分析
- `mcn-content-rewriter`: 选题 → 内容改写
- `mcn-wechat-publisher`: 内容 → 公众号发布

---

*Last updated: 2026-04-12 by Luna*