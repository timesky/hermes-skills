---
name: zhihu-favorites-sync
description: |
  知乎收藏夹增量同步技能 - 定期抓取收藏夹新增文章，直接保存到 raw 目录供 wiki-ingest 整理。
  当用户提到"知乎收藏"、"收藏同步"、"同步知乎"时使用此技能。
tags: [zhihu, collection, sync, opencli, obsidian, knowledge-base, raw, wiki-ingest]
version: 3.0.0
created: 2026-04-14
updated: 2026-04-20
author: Luna
---

# 知乎收藏夹增量同步

定期抓取知乎收藏夹的新增文章，直接保存到知识库 raw 目录。

---

## 配置

| 配置项 | 值 |
|--------|-----|
|| 收藏夹 URL | `https://www.zhihu.com/collection/797328373` |
|| 脚本路径 (v3.0) | `~/.hermes/scripts/zhihu-collection-sync-v3.py` |
|| 进度文件 (v3.0) | `/tmp/zhihu_collection_progress_v3.json` |
|| 脚本路径 (v2.0) | `~/.hermes/scripts/opencli-zhihu-collection-v2.js`（已废弃） |
|| 脚本路径 (v1.x) | `~/.hermes/scripts/opencli-zhihu-collection.js`（已废弃） |
|| 输出目录 | `~/backup/知识库-Obsidian/raw/sources/zhihu/{日期}/` |

**输出路径说明**：直接输出到 `raw/sources/`，方便 wiki-ingest 自动发现和整理。

---

## 输出路径变更

**之前**：`tmp/zhihu/`（临时目录，需手动整理）

**现在**：`raw/zhihu/`（直接进入 wiki-ingest 流程）

```
raw/zhihu/2026-04-15/
├── article-{id}.md    → wiki-ingest 自动处理
└── ...
```

---

## 执行方式

### Python + web-fetcher (v3.0，推荐)

```bash
# 使用 Python 脚本（支持所有类型 + URL 集合对比）
python ~/.hermes/scripts/zhihu-collection-sync-v3.py

# 限制每次抓取数量
python ~/.hermes/scripts/zhihu-collection-sync-v3.py --max 5

# 仅查看缺失列表（不抓取）
python ~/.hermes/scripts/zhihu-collection-sync-v3.py --dry-run
```

**v3.0 修复**：
- ✅ 支持所有类型：文章 `/p/`、想法 `/pin/`、问答 `/question/`
- ✅ 增量逻辑：URL 集合对比（每次先获取完整列表，过滤已抓取）
- ✅ 不再用 ID 做结束标记（ID 是发布时间，不反映收藏顺序）

### 检查 OpenCLI 状态

```bash
opencli daemon status    # 检查 daemon 状态
opencli doctor           # 完整诊断（推荐）
```

---

## 工作流程 (v2.0)

1. **导航** - OpenCLI navigate 到收藏夹页面
2. **等待** - 5 秒页面加载
3. **滚动加载** - 循环滚动到底部，加载所有文章（最多 100 篇）
4. **获取完整列表** - 使用 `.ContentItem` selector 获取所有文章
5. **对比进度** - 读取进度文件，过滤已处理的 URL（而非 ID）
6. **抓取内容** - 对新增文章逐个抓取（最多 10 篇/次）
7. **保存文件** - 保存为 Markdown 到 `raw/zhihu/{日期}/`
8. **更新进度** - 写入新的 processed_urls + total_articles

### v1.x/v2.0 的问题（v3.0 已修复）

| 问题 | 影响 | 修复方式 |
|------|------|----------|
| 只抓首页 20 篇 | 收藏夹 >20 篇时遗漏 | 滚动加载完整列表 |
| 只支持文章类型 | 遗漏想法 `/pin/` 和问答 `/question/` | **v3.0 支持所有类型** |
| 用 ID 做结束标记 | ID 是发布时间，不反映收藏顺序 | **v3.0 用 URL 集合对比** |
| 无总数校验 | 无法发现收藏被删除 | 记录 total_articles |

---

## 与 wiki-ingest 的关系

```
zhihu-favorites-sync（抓取）
    ↓
raw/zhihu/{日期}/article-{id}.md
    ↓
wiki-ingest（定时整理）
    ↓
wikiLLM/结构化知识
```

**优势**：
- 无需手动移动文件
- wiki-ingest 自动发现新内容
- 统一的整理流程

---

## Cron 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| 知乎收藏-工作日 | 11:00/13:00/15:00/17:00 | 每2小时 |
| 知乎收藏-周末 | 10:00-22:00 每2小时 | 更频繁 |

---

## 故障排查

### OpenCLI daemon 未运行

错误：`ECONNREFUSED 127.0.0.1:19825`

解决：
```bash
# 1. 检查 daemon 状态
opencli daemon status

# 2. 如果未运行，直接运行脚本会自动启动 daemon
# 或者使用 doctor 诊断
opencli doctor

# 注意：没有 `opencli browser start` 命令，daemon 会在需要时自动启动
```

**常见情况**：
- Daemon 显示 "running" 但脚本报连接错误 → 检查 Chrome 扩展是否已加载
- 扩展未连接 → 重新加载 `chrome://extensions/` 中的 OpenCLI 扩展

### 脚本限制

脚本每次最多处理 5 篇文章。如果新增超过 5 篇：
- 第一次运行抓取前 5 篇
- 再次运行抓取剩余文章
- Cron 任务会自动处理（下次定时触发时完成）

### 超时处理

脚本限制 5 篇/次，超时后：
1. 检查已保存文件
2. 检查进度文件 `/tmp/zhihu_collection_progress.json`
3. 重新运行继续抓取

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| 进度文件丢失 | 重新抓取会重复，需手动清理 raw 中重复文件 |
| OpenCLI 版本 | **推荐 Node v22 + OpenCLI v1.7.4**（官方要求 >=21） |
| 输出路径错误 | 检查脚本配置，确保输出到 raw/zhihu/ |

---

## 历史变更

| 版本 | 变更 |
|------|------|
| 1.0.0 | 原名 zhihu-collection-scraper，输出到 tmp/，只支持文章类型 |
| 1.1.0 | 改名 zhihu-favorites-sync，输出改为 raw/ |
| 2.0.0 | 添加滚动加载 + URL 唯一标识，但仍只支持文章类型 |
| 3.0.0 | **重大修复**：支持所有类型（文章、想法、问答）+ URL 集合对比增量逻辑 |

---

## 增量同步逻辑对比

| 版本 | 增量方式 | 问题 |
|------|----------|------|
| v1.x | 用 ID 做结束标记 | ❌ ID 是发布时间戳，不反映收藏顺序，会遗漏 |
| v2.0 | 用 URL 作为唯一标识 | ❌ 只支持文章类型，遗漏想法和问答 |
| v3.0 | **URL 集合对比** | ✅ 每次先获取完整列表，过滤已抓取的 URL |

### v3.0 工作流程

```
1. 获取收藏夹完整列表（web-fetcher + 滚动加载）
2. 对比 processed_urls 集合
3. 找出所有未抓取的 URL（包括想法、问答）
4. 批量抓取缺失内容
5. 更新进度文件
```

**优势**：
- 不依赖 ID 排序
- 支持所有内容类型
- 不会遗漏任何收藏内容

---

## 迁移到 v3.0

首次使用 v3.0 脚本：

```bash
# 1. 手动迁移进度（从已有文件提取 URL）
python ~/.hermes/scripts/zhihu-migrate-progress.py

# 2. 运行同步脚本
python ~/.hermes/scripts/zhihu-collection-sync-v3.py --dry-run  # 先查看缺失
python ~/.hermes/scripts/zhihu-collection-sync-v3.py            # 正式抓取
```

---

*Created: 2026-04-14*
*Updated: 2026-04-20 (v3.0 支持所有类型 + URL 集合对比)*