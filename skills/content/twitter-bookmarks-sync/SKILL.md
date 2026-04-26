---
name: twitter-bookmarks-sync
description: |
  Twitter/X 书签收藏增量同步技能 - 定期抓取书签列表新增推文，直接保存到 raw 目录供 wiki-ingest 整理。
  当用户提到"Twitter收藏"、"X书签"、"书签同步"、"同步推文"时使用此技能。
tags: [twitter, x, bookmarks, sync, opencli, obsidian, knowledge-base, raw, wiki-ingest]
version: 1.0.0
created: 2026-04-24
author: Luna
---

# Twitter/X 书签收藏增量同步

定期抓取 Twitter/X 书签列表的新增推文，直接保存到知识库 raw 目录。

---

## 配置

| 配置项 | 值 |
|--------|-----|
| 书签 URL | `https://x.com/i/bookmarks` |
| 脚本路径 | `~/.hermes/scripts/twitter-bookmarks-sync.py` |
| 进度文件 | `/tmp/twitter_bookmarks_progress.json` |
| 输出目录 | `~/Documents/My_Obsidian/raw/sources/twitter/{日期}/` |

**输出路径说明**：直接输出到 `raw/sources/`，方便 wiki-ingest 自动发现和整理。

---

## 执行方式

### Python + OpenCLI (推荐)

```bash
# 使用 Python 脚本
python3 ~/.hermes/scripts/twitter-bookmarks-sync.py

# 限制每次抓取数量
python3 ~/.hermes/scripts/twitter-bookmarks-sync.py --max 10

# 仅查看缺失列表（不抓取）
python3 ~/.hermes/scripts/twitter-bookmarks-sync.py --dry-run
```

### 前置要求

1. **已登录 Twitter/X**：Chrome 中需登录账号
2. **OpenCLI 已安装**：
   ```bash
   npm install -g @jackwener/opencli@latest
   ```
3. **Node.js >= 21**：
   ```bash
   /opt/homebrew/bin/node --version  # 应显示 v21+
   ```

---

## 工作流程

1. **导航** - OpenCLI 打开书签页面
2. **等待** - 3 秒页面加载
3. **滚动加载** - 循环滚动到底部，加载所有书签（最多 200 条）
4. **获取完整列表** - 使用 `[data-testid=tweet]` selector 获取所有推文
5. **对比进度** - 读取进度文件，过滤已处理的推文 ID
6. **抓取内容** - 对新增推文逐个抓取（最多 10 条/次）
7. **保存文件** - 保存为 Markdown 到 `raw/twitter/{日期}/`
8. **更新进度** - 写入新的 processed_ids + total_bookmarks

---

## 推文内容格式

```markdown
# 推文标题（或首句摘要）

## 元信息

| 属性 | 值 |
|------|-----|
| 作者 | 用户名 (@handle) |
| 来源 | X/Twitter |
| URL | https://x.com/user/status/{id} |
| 抓取时间 | 2026-04-24 10:30:00 |
| 类型 | 推文/长推文 |
| 回复 | N |
| 转帖 | N |
| 喜欢 | N |

---

## 正文

推文内容...
```

---

## 与 wiki-ingest 的关系

```
twitter-bookmarks-sync（抓取）
    ↓
raw/twitter/{日期}/{handle}-{id}.md
    ↓
wiki-ingest（定时整理）
    ↓
wikiLLM/结构化知识
```

---

## Cron 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| Twitter 书签同步 | 每日 09:00, 18:00 | 早晚两次 |

---

## 故障排查

### OpenCLI 未安装

```bash
export PATH="/opt/homebrew/bin:$PATH"
npm install -g @jackwener/opencli@latest
opencli browser open "https://x.com"  # 测试
```

### 未登录 Twitter

Chrome 中访问 `https://x.com` 并登录账号。书签页面需要登录才能访问。

### 脚本限制

脚本每次最多处理 10 条推文（默认）。如果新增超过限制：
- 第一次运行抓取前 10 条
- 再次运行抓取剩余推文
- Cron 任务会自动处理

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| **OpenCLI eval 语法错误** | ⚠️ 选择器中的特殊字符（如 `href*=/status/`）会导致 SyntaxError。需用转义或简化选择器 |
| 进度文件丢失 | 重新抓取会重复，需手动清理 raw 中重复文件 |
| Node.js 未安装 | OpenCLI 依赖 Node.js：`brew install node` |
| Node.js PATH 问题 | macOS Homebrew 安装的 Node 在 `/opt/homebrew/bin/node`，需显式设置 PATH |
| Chrome 未登录 | 书签页面需要登录才能访问 |
| 推文内容获取失败 | 长推文需要特殊处理 `[data-testid=twitterArticleRichTextView]` |

**当前状态**: 脚本框架已完成，但 OpenCLI eval 问题待修复。获取书签列表的 JavaScript 选择器需要调整。

---

## 支持的内容类型

| 类型 | 特征 | 处理方式 |
|------|------|----------|
| 普通推文 | `data-testid=tweet` | 直接获取文本 |
| 长推文文章 | `data-testid=twitterArticleRichTextView` | 获取完整文章内容 |
| 带图片推文 | `data-testid=tweetPhoto` | 记录图片 URL |
| 转帖 | `role=link` 引用原文 | 标记为转帖 |

---

*Created: 2026-04-24*