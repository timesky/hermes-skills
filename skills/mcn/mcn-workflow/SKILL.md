---
name: mcn-workflow
description: MCN 完整工作流技能 - 整合热搜聚合、选题分析、内容改写、公众号发布的全流程自动化
tags: [mcn, workflow, automation]
version: 1.0.0
created: 2026-04-12
author: Luna
---

# MCN 完整工作流

整合热搜聚合 → 选题分析 → 内容改写 → 公众号发布的全流程。

---

## 工作流架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MCN 自动化工作流                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: 热搜聚合                                                    │
│  ├─ opencli zhihu hot    → 知乎热榜                                  │
│  ├─ opencli weibo hot    → 微博热搜                                  │
│  ├─ opencli douyin hot   → 抖音热榜                                  │
│  ├─ opencli xiaohongshu feed → 小红书推荐                            │
│  └─ 保存到 tmp/hotspot/YYYY-MM-DD/                                   │
│                                                                     │
│  Step 2: 选题分析                                                    │
│  ├─ 读取热搜聚合结果                                                 │
│  ├─ 计算相关性评分（AI/技术/金融领域）                                 │
│  ├─ 生成选题报告                                                     │
│  └─ 保存到 tmp/topic/YYYY-MM-DD/topic-report.md                     │
│                                                                     │
│  Step 3: 内容改写                                                    │
│  ├─ 读取选题报告                                                     │
│  ├─ 获取原文内容                                                     │
│  ├─ 生成多版本文章（专业版/轻松版/故事版）                             │
│  └─ 保存到 tmp/content/YYYY-MM-DD/                                   │
│                                                                     │
│  Step 4: 公众号发布                                                  │
│  ├─ 打开公众号后台                                                   │
│  ├─ 等待用户扫码登录                                                 │
│  ├─ 自动填写文章内容                                                 │
│  └─ 保存为草稿                                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 知识库路径

```
KB_ROOT = /Users/timesky/backup/知识库-Obsidian
HOTSPOT_DIR = KB_ROOT/tmp/hotspot/
TOPIC_DIR = KB_ROOT/tmp/topic/
CONTENT_DIR = KB_ROOT/tmp/content/
PUBLISH_DIR = KB_ROOT/tmp/publish/
```

---

## 执行流程

### 方式一：手动分步执行

```bash
# Step 1: 热搜聚合
hermes
> 加载技能 mcn-hotspot-aggregator
> 执行热搜聚合

# Step 2: 选题分析
> 加载技能 mcn-topic-selector
> 执行选题分析

# Step 3: 内容改写
> 加载技能 mcn-content-rewriter
> 执行内容改写

# Step 4: 公众号发布
> 加载技能 mcn-wechat-publisher
> 执行公众号发布
```

### 方式二：一键执行完整工作流

```python
async def run_mcn_workflow():
    """执行完整 MCN 工作流"""
    
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print(f"=== MCN 工作流开始 ===")
    print(f"日期: {date}")
    
    # Step 1: 热搜聚合
    print("\n[Step 1] 热搜聚合...")
    hotspots = await aggregate_hotspots()
    print(f"抓取完成: {len(hotspots)} 个平台")
    
    # Step 2: 选题分析
    print("\n[Step 2] 选题分析...")
    topics = await analyze_topics(hotspots)
    print(f"推荐选题: {len(topics['recommended'])} 个")
    
    # Step 3: 内容改写
    print("\n[Step 3] 内容改写...")
    articles = await rewrite_content(topics['recommended'][:3])
    print(f"生成文章: {len(articles)} 篇")
    
    # Step 4: 公众号发布
    print("\n[Step 4] 公众号发布...")
    print("请在浏览器中扫码登录公众号...")
    results = await publish_to_wechat(articles)
    print(f"发布结果: {results}")
    
    print(f"\n=== MCN 工作流完成 ===")
    
    return {
        'hotspots': hotspots,
        'topics': topics,
        'articles': articles,
        'publish_results': results
    }
```

---

## 使用指南

### 启动工作流

在 Hermes 中执行：

```
加载技能 mcn-workflow
执行 MCN 工作流
```

### 查看工作流状态

```
查看 MCN 工作流进度
```

### 跳过某步骤

```
执行 MCN 工作流，跳过热搜聚合
执行 MCN 工作流，只做选题分析
```

---

## Cron 定时任务

设置每日自动执行：

```bash
# 每天 8:00 执行热搜聚合
hermes cron create --schedule "0 8 * * *" \
  --name "mcn-hotspot-daily" \
  --prompt "加载技能 mcn-hotspot-aggregator，执行热搜聚合"

# 每天 9:00 执行选题分析
hermes cron create --schedule "0 9 * * *" \
  --name "mcn-topic-daily" \
  --prompt "加载技能 mcn-topic-selector，执行选题分析"

# 每天 10:00 执行内容改写（手动触发）
# 公众号发布需要用户交互，不适合定时任务
```

---

## 输出目录结构

```
tmp/
├── hotspot/
│   └── YYYY-MM-DD/
│       ├── zhihu-hotspot.md
│       ├── weibo-hotspot.md
│       └── ...
├── topic/
│   └── YYYY-MM-DD/
│       └── topic-report.md
├── content/
│   └── YYYY-MM-DD/
│       ├── 选题1-professional.md
│       ├── 选题1-casual.md
│       ├── 选题1-story.md
│       └── ...
└── publish/
    └── YYYY-MM-DD/
        └── publish-log.md
```

---

## 相关技能

- `mcn-hotspot-aggregator`: 热搜聚合
- `mcn-topic-selector`: 选题分析
- `mcn-content-rewriter`: 内容改写
- `mcn-wechat-publisher`: 公众号发布

---

## Pitfalls

1. **OpenCLI Daemon 必须运行**: 热搜聚合依赖 OpenCLI
2. **Browser Extension 必须连接**: 公众号发布依赖浏览器控制
3. **登录需要用户交互**: 公众号发布需要扫码
4. **敏感话题跳过**: 选题分析时过滤敏感内容
5. **改写保持原创**: 不能直接复制原文

---

*Last updated: 2026-04-12 by Luna*