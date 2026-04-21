---
name: zhihu-collection-scraper
status: deprecated
deprecated_date: 2026-04-15
redirect_to: zhihu-favorites-sync
reason: "已改名并升级，输出路径改为 raw/zhihu/"
description: |
  [已废弃] 请使用 zhihu-favorites-sync
  输出路径已从 tmp/ 改为 raw/，方便 wiki-ingest 自动整理
tags: [zhihu, collection, scraper, deprecated]
version: 1.0.0
updated: 2026-04-15
---

# 知乎收藏夹增量抓取技能

定期抓取知乎收藏夹的新增文章，保存到 Obsidian 知识库。用于 MCN 内容素材积累。

---

## 配置

| 配置项 | 值 |
|--------|-----|
| 收藏夹 URL | `https://www.zhihu.com/collection/797328373` |
| 脚本路径 | `~/.hermes/scripts/opencli-zhihu-collection.js` |
| 进度文件 | `/tmp/zhihu_collection_progress.json` |
| 输出目录 | `~/backup/知识库-Obsidian/tmp/zhihu/{日期}/` |

---

## 执行方式

### 方式 1: OpenCLI (首选)

```bash
node ~/.hermes/scripts/opencli-zhihu-collection.js
```

### 方式 2: web-fetcher (备选，OpenCLI 未运行时)

```bash
curl -s http://localhost:9234/health && node ~/.hermes/scripts/webfetcher-zhihu-backup.js
```

---

## 工作流程

1. **导航** - OpenCLI navigate 到收藏夹页面
2. **等待** - 5 秒页面加载
3. **获取列表** - 使用 `.ContentItem` selector 获取文章列表
4. **对比进度** - 读取进度文件，过滤已处理的文章 ID
5. **抓取内容** - 对新增文章逐个 navigate + exec 抓取
6. **保存文件** - 保存为 Markdown 到 `{日期}/article-{id}.md`
7. **更新进度** - 写入新的 processed_ids 到进度文件

---

## 运行模式

- **每次最多抓取 5 篇** - 脚本限制 `slice(0, 5)` 避免超时
- **多篇需多次运行** - 如有 20 篇新增，需运行 4 次
- **幂等性** - 重复运行不会重复抓取（通过 ID 去重）

---

## 输出格式

```
=== OpenCLI 知乎收藏夹增量抓取 ===

已处理：32 篇

导航到收藏夹...
等待 5 秒...

获取文章列表...
收藏夹文章：20 篇
新增文章：11 篇

抓取文章内容...
  抓取：https://zhuanlan.zhihu.com/p/20263312597
  已保存：article-2026331259756920982.md
  ...

=== 完成 ===
新增：5 篇
位置：/Users/timesky/backup/知识库-Obsidian/tmp/zhihu/2026-04-14
```

---

## 故障排查

### 问题 1: 脚本超时 (120s)

**现象**: 输出显示部分文章已保存，但命令以 exit code 124 结束

**处理**:
1. 检查已保存的文件：`ls ~/backup/知识库-Obsidian/tmp/zhihu/{日期}/`
2. 检查进度文件是否更新：`cat /tmp/zhihu_collection_progress.json`
3. 如进度文件未更新，手动补充已抓取的文章 ID
4. 重新运行脚本继续抓取剩余文章

### 问题 2: OpenCLI daemon 未运行

**现象**: 连接错误 `ECONNREFUSED`

**处理**:
1. 启动 OpenCLI daemon
2. 或切换到 web-fetcher 备选方案

### 问题 3: 进度文件 ID 格式不一致

**现象**: 同一篇文章被重复抓取

**原因**: 脚本中文章 ID 提取逻辑可能产生不同格式（短 ID vs 完整 ID）

**处理**:
1. 检查进度文件中的 ID 格式
2. 手动清理重复的 ID 条目
3. 考虑修复脚本中的 ID 提取逻辑

---

## 文章文件结构

```markdown
# 文章标题

作者：xxx
日期：2026-04-14
来源：https://zhuanlan.zhihu.com/p/xxxxx

---

文章内容正文...
```

---

## Cron 调度示例

```bash
# 每天上午 9 点抓取
0 9 * * * node ~/.hermes/scripts/opencli-zhihu-collection.js >> ~/logs/zhihu-scraper.log 2>&1
```

---

## 后续整理

抓取的 articles 保存在 `tmp/zhihu/` 目录，等待定期整理任务评估后移动到正式知识库目录。

---

## 相关文件

- 脚本：`~/.hermes/scripts/opencli-zhihu-collection.js`
- 进度：`/tmp/zhihu_collection_progress.json`
- 输出：`~/backup/知识库-Obsidian/tmp/zhihu/`

---

## Pitfalls

1. **⚠️ 超时处理**：脚本限制 5 篇/次，超时后需手动更新进度文件
2. **ID 格式**：文章 ID 可能为短格式（如 `20263312597`）或完整格式（如 `2026331259756920982`），去重时需统一
3. **多次运行**：大量新增文章时需多次运行脚本，每次 5 篇
4. **进度文件位置**：`/tmp/` 可能重启清空，重要进度需备份

---

*Updated: 2026-04-14 by Luna*
