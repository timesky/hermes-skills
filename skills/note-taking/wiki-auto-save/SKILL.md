---
name: wiki-auto-save
description: 自动保存搜索内容到知识库 tmp 目录，抓取阅读/点赞/收藏指标，等待定时整理任务评估
triggers:
  - web_search 执行后
  - web_extract 执行后
version: 1.1
created: 2026-04-12
updated: 2026-04-12
author: Luna
---

# wiki-auto-save

自动保存搜索内容到知识库 tmp 目录的技能。

---

## 知识库路径

```
KB_ROOT = /Users/timesky/backup/知识库-Obsidian
```

---

## 保存流程

### 1. 生成文件名

```python
import datetime
import re

date_str = datetime.datetime.now().strftime("%Y-%m-%d")
slug = re.sub(r'[^\w\s-]', '', title).lower().replace(' ', '-')[:50]
filename = f"tmp/{date_str}/{slug}.md"
```

### 2. 抓取文章指标（重要！）

在 `web_extract` 时，必须同时抓取以下指标：

| 平台 | 指标获取方式 |
|------|-------------|
| 知乎 | 阅读量（页面显示）、点赞数、收藏数 |
| 微信公众号 | 阅读数（底部显示）、点赞数 |
| CSDN | 阅读量、点赞数、收藏数 |
| GitHub | Stars、Forks、Watchers |
| 其他 | 尽可能抓取可见的互动数据 |

**指标抓取方法**：
- 使用 `browser_vision` 分析页面获取可见指标
- 或使用 `browser_console` 执行 JS 获取数据
- 如果无法获取，标记为 `未知`

### 3. 文件格式

```markdown
---
created: YYYY-MM-DD HH:MM
source: URL
session_id: 当前会话ID
tags: [初步标签]
status: pending
---

# 标题

## 原文指标
- 阅读量: N（或"未知"）
- 点赞数: N（或"未知"）
- 收藏数: N（或"未知"）

## 搜索查询
原始搜索关键词

## 搜索结果摘要
[搜索结果列表 - title, url, description]

## 提取内容
[web_extract 的完整内容]

## Meta
- 保存时间: YYYY-MM-DD HH:MM
- 保存原因: 自动保存
- 平台: 知乎/公众号/CSDN/GitHub/其他
```

---

## 目录结构

```
tmp/
└── YYYY-MM-DD/           # 按日期分目录
    ├── 文章标题-slug.md
    └── 另一文章-slug.md
```

**不使用 web/user 子目录**，所有内容统一按日期存放。

---

## 标签自动推断

根据内容关键词自动添加标签：

| 关键词 | 标签 |
|--------|------|
| API, SDK, 开发 | tech/dev |
| AI, LLM, model | tech/ai |
| 投资, 理财, 股票 | finance |
| 公司, 项目, 业务 | work |
| 研究, 论文, arxiv | research |
| 知乎 | platform/zhihu |
| GitHub | platform/github |

---

## 触发条件

**自动触发**：
- 执行 `web_search` 后 → 保存搜索结果摘要
- 执行 `web_extract` 后 → 保存提取的完整内容 + 抓取指标

**不触发**：
- 用户明确说"不要保存"
- 内容已存在于 `raw/` 或 `wiki/`

---

## Pitfalls

1. **必须抓取指标**：阅读/点赞/收藏是整理评估的关键依据
2. **不要覆盖已存在文件**：先检查同名文件
3. **按日期分目录**：不要使用 web/user 子目录
4. **session_id 必须记录**：用于后续引用追踪
5. **指标无法获取时标记"未知"**：不要跳过指标字段

---

## 验证

保存后检查：
```
search_files(path=KB_ROOT/tmp/YYYY-MM-DD/, pattern="*.md")
```

---

## 完整整理流程

```
tmp/YYYY-MM-DD/ → 定时整理 → raw/sources/ → ingest → wiki/
     ↓                    ↓           ↓          ↓
  自动保存            评估决策      移入raw     更新wiki
                         ↓
                    delete.log（删除记录）
```

### 流程步骤

| 阶段 | 操作 | 说明 |
|------|------|------|
| 自动保存 | web_search/web_extract 后 | 存入 tmp，包含指标 |
| 定时整理 | 8-22点每2小时 | 评估总分，决定保留/删除 |
| 移入 raw | 总分 >= 5 | shutil.move 到 raw/sources/ |
| Ingest | 移入后触发 | 创建 wiki 页面，更新索引 |
| 删除记录 | 总分 < 3 或过期 | 追加到 wiki/delete.log |

### Raw 来源

| 来源 | 说明 |
|------|------|
| tmp | 自动保存的搜索内容 |
| 知乎收藏夹 | 定期同步的文章 |
| 用户指定 | 用户要求抓取的内容 |

---

## 相关

- `llm-wiki`: Wiki 结构化整理（ingest 流程）
- `wiki-curator`: 定时整理脚本（评估+移入raw+删除）
- `zhihu-collection-fetcher`: 知乎收藏夹抓取