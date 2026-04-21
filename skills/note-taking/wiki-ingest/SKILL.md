---
name: wiki-ingest
description: 增量式 ingest 流程，将 raw 源文件转换为 wiki 结构化内容。支持单个文件 ingest 和批量 ingest 两种模式。当用户说"ingest"、"建立 wiki"、"处理 raw 目录"、"批量 ingest"、"raw 目录所有内容都要建立 wiki"时使用。优先优化此技能，不要创建重复技能。
version: 2.2
created: 2026-04-12
updated: 2026-04-13
author: Luna
inspired_by: Karpathy LLM Wiki
---

# wiki-ingest

增量式 ingest 流程，将 raw 源文件转换为 wiki 结构化内容。

---

## 核心原则

**Ingest 是增量式的，不是覆盖式！**

---

## 完整流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Wiki 知识库流程                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【阶段 1】wiki-auto-save（自动）                                        │
│  ├─ 触发：web_search / web_extract 执行后                              │
│  ├─ 输出：tmp/YYYY-MM-DD/文章名.md                                      │
│  └─ 内容：搜索结果 + 提取内容 + 指标                                    │
│                                                                         │
│  【阶段 2】wiki-curator（定时整理）                                      │
│  ├─ 触发：8-22点每2小时                                                 │
│  ├─ 输入：tmp/YYYY-MM-DD/*.md                                          │
│  ├─ 评估：总分 >= 5 保留，< 3 删除                                      │
│  ├─ 输出：raw/sources/保留文件.md                                       │
│  └─ 删除记录：wiki/delete.log                                           │
│                                                                         │
│  【阶段 3】wiki-ingest（增量处理）                                       │
│  ├─ 触发：raw 有新文件时                                                │
│  ├─ 输入：raw/sources/*.md                                              │
│  ├─ 处理：提取实体/概念 → 创建/更新 wiki 页面                          │
│  ├─ 输出：wiki/entities/ 或 wiki/concepts/                             │
│  └─ 记录：wiki/processed.log + wiki/log.md                             │
│                                                                         │
│  【MCN 目录】人工定期整理                                                │
│  ├─ 位置：mcn/                                                          │
│  ├─ 内容：热点调研、选题、文章、配图、发布记录                          │
│  └─ 管理：不参与 wiki-ingest 流程，人工整理                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 流程步骤

| 阶段 | 操作 | 说明 |
|------|------|------|
| 自动保存 | web_search/web_extract 后 | 存入 tmp，包含指标 |
| 定时整理 | 8-22点每2小时 | 评估总分，决定保留/删除 |
| 移入 raw | 总分 >= 5 | shutil.move 到 raw/sources/ |
| 知乎同步 | 定时 Cron | 抓取收藏夹 → raw/sources/zhihu/{日期}/ |
| Ingest | 移入后触发 | 扫描 raw/sources/**/*.md，创建 wiki 页面 |
| 删除记录 | 总分 < 3 或过期 | 追加到 wiki/delete.log |

**扫描范围**：`raw/**/*.md`（包含所有子目录）

| 子目录 | 来源 | 文件数 | 说明 |
|--------|------|--------|------|
| `raw/sources/{日期}/` | wiki-auto-save → curator | ~173 | 搜索内容整理 |
| `raw/sources/zhihu/{日期}/` | zhihu-favorites-sync | — | 知乎收藏夹同步 |
| `raw/sources/网络转载/` | 手动保存 | — | 外部文章 |
| `raw/notes/AI工具/` | 手动笔记 | — | AI 工具研究 |
| `raw/notes/量化/` | 手动笔记 | — | 量化交易笔记 |
| `raw/notes/投资理财/` | 手动笔记 | — | 投资理财笔记 |
| `raw/notes/微信/` | MCN 草稿 | — | 公众号相关 |
| `raw/notes/博客/` | 手动笔记 | — | 博客草稿/发布 |
| `raw/assets/` | — | 0 | 资源文件（不扫描） |

**注意**：`raw/assets/` 不包含 md 文件，无需扫描。
[一句话定义]

## 关键信息
[主体内容]

## 相关
- [[相关页面]]

## 来源
- [来源 1](../../raw/sources/xxx.md)
```

**已有实体**（增量更新）:
```markdown
# 修改 frontmatter
sources: [原来源列表，新来源]  ← 追加新来源

# 追加到 ## 来源 节
- [新来源](../../raw/sources/xxx.md)  ← 添加新行

# 可选：更新 ## 关键信息
[合并新内容，不删除旧内容]
```

### 概念页面

**新概念**: 创建完整页面

**已有概念**（增量更新）:
- 合并相似内容
- 添加 cross-reference
- 更新 sources frontmatter

### 相关文件合并

多篇相关文章 → 一个 Wiki 页面：

| 源文件 | 合并到 |
|--------|--------|
| 小米 MiMo-公众号完整版.md | entities/xiaomi-mimo.md |
| 小米推出-MiMo-大模型订阅套餐.md | entities/xiaomi-mimo.md |
| GLM-5 上下文窗口.md | entities/glm-5.md |
| Hermes 配置.md | entities/glm-5.md (作为相关配置) |

---

## 输出文件与反查

| 文件 | 用途 | 说明 |
|------|------|------|
| `wiki/processed.log` | 已处理记录 | 反查哪些 raw 文件已 wiki 化 |
| `wiki/unprocessed.log` | 未处理记录 | 反查哪些 raw 文件尚未处理 |
| `wiki/duplicates.md` | 重复内容建议 | 列出关联 wiki 页和 raw 文件，建议合并删除 |
| `wiki/log.md` | 执行日志 | 每次 ingest 执行情况 |
| `wiki/index.md` | Wiki 索引 | 所有 wiki 页面分类索引 |

### 反查未处理内容

```bash
# 查看未处理列表
cat wiki/unprocessed.log

# 查看处理状态统计
python3 scripts/wiki_ingest.py --status
```

### 重复内容处理

`wiki/duplicates.md` 自动检测并记录：

| 检测规则 | 说明 |
|----------|------|
| 关键词重叠 | 相同关键词在 3+ 文件中出现 |
| 主题相似 | 相同主题在不同目录有多个文件 |
| 文件名相似 | 去除日期后缀后文件名相同 |

**处理建议**：
- 合并：多篇相关文章 → 一个 Wiki 页面
- 删除：明显过时/重复内容
- 保留：内容完整、时间最新的版本

---

## processed.log 格式

```markdown
# Processed Log

知识库源文件处理记录，append-only。

格式：`source_path | ingest_date | wiki_pages_created | status`

---

## 已处理文件

| 源文件 | Ingest 时间 | 生成的 Wiki 页面 | 状态 |
|--------|-------------|------------------|------|
| raw/sources/xxx.md | 2026-04-12 | entities/xxx.md | ✅ |

---

## 待处理文件

| 源文件 | 移入时间 | 原因 |
|--------|----------|------|
| raw/sources/yyy.md | 2026-04-12 | 等待 ingest |

---

## 处理规则

1. **每个文件只 ingest 一次** - 通过检查此 log 避免重复
2. **相关文件合并处理** - 如多篇 MiMo 文章 → 一个实体页
3. **批量归档文件** - 热搜聚合等不生成 wiki 页面，标记为"已归档"
4. **append-only** - 只追加新记录，不修改已有记录
```

---

## index.md 增量更新

**不要重写整个文件！** 使用 patch：

### 添加新页面到表格

```python
# 找到表格位置，添加新行
old_string = "|| [[existing-page\\|Page]] | Description | 1 ||"
new_string = """|| [[existing-page\\|Page]] | Description | 1 ||
|| [[new-page\\|New Page]] | New description | 1 ||"""

patch(path="wiki/index.md", old_string=old_string, new_string=new_string)
```

### 更新 Statistics

```python
# 找到统计数字，递增
old_count = "- **Wiki 页面数**: 5"
new_count = "- **Wiki 页面数**: 6"

patch(path="wiki/index.md", old_string=old_count, new_count=new_count)
```

---

## Pitfalls

1. **不要覆盖 index.md**：使用 patch 增量更新
2. **检查 processed.log**：避免重复处理同一文件
3. **相关文件合并**：多篇同主题文章 → 一个 Wiki 页面
4. **append-only 日志**：log.md 和 processed.log 只追加
5. **保留原始内容**：增量更新时不删除已有内容
6. **不要创建重复技能**：发现流程缺陷时，优先优化现有技能（如 wiki-ingest），而不是创建新技能（如 batch-ingest）
7. **处理所有类型文件**：不跳过无 frontmatter 或短文件，按类型分类处理

---

## 实战经验（2026-04-12 批量 ingest）

### 文件验证规则

```python
def validate_file_content(filepath: Path) -> Tuple[bool, str]:
    """验证文件内容是否有效"""
    # 1. 文件大小 >= 1KB（过滤 placeholder）
    if size < 1000:
        return False, "文件过小"
    
    # 2. 不是缓存消息
    cache_messages = ["File unchanged since last read", ...]
    if any(msg in content for msg in cache_messages):
        return False, "文件内容是缓存消息"
    
    # 3. 有 frontmatter
    if not content.strip().startswith('---'):
        return False, "文件格式不正确"
    
    # 4. 正文字数 >= 50
    if len(body) < 50:
        return False, "正文内容过短"
    
    return True, "验证通过"
```

**实战结果**：127 个文件中过滤掉 18 个无效文件（14.2%）

### index.md 更新实现

```python
def update_index_md(new_pages: List[dict]):
    content = INDEX_MD.read_text()
    
    # 1. 更新 Statistics（使用 regex）
    content = re.sub(r'page_count: (\d+)', f'page_count: {new_count}', content)
    content = re.sub(r'\*\*Wiki 页面数\*\*: (\d+)', f'**Wiki 页面数**: {new_count}', content)
    
    # 2. 添加新页面到表格（需要智能插入到对应分类表格）
    # ...
    
    INDEX_MD.write_text(content)
```

### 批量处理流程

1. 扫描 raw/sources/**/*.md
2. 验证每个文件内容
3. 检查 processed.log 过滤已处理
4. 按主题分组（关键词匹配）
5. 创建/更新 wiki 页面
6. 更新 index.md Statistics
7. 追加 processed.log 和 log.md

**实战结果**：109 个有效文件 → 36 个 wiki 页面

---

## 硬指标验证（测试必需）

**定义**: 所有 raw 文件必须有对应的真实 wiki 页面

### 验证脚本

```python
from pathlib import Path
import re

KB_ROOT = Path("/Users/timesky/backup/知识库-Obsidian")
RAW_DIR = KB_ROOT / "raw" / "sources"
PROC_LOG = KB_ROOT / "wiki" / "processed.log"

# 1. 统计 raw 文件
raw_files = list(RAW_DIR.glob("*.md"))

# 2. 读取 processed.log 提取已处理文件
processed_files = set()
if PROC_LOG.exists():
    content = PROC_LOG.read_text()
    for line in content.split('\n'):
        if '|' in line and '.md' in line:
            match = re.search(r'raw/sources/([^|]+\.md)', line)
            if match:
                processed_files.add(match.group(1))

# 3. 对比 - 找未处理文件
unprocessed = [f.name for f in raw_files if f.name not in processed_files]

# 4. 验证 wiki 页面有实质内容
empty_pages = []
for page in wiki_pages:
    content = page.read_text()
    body_lines = [l for l in content.split('\n') 
                  if l.strip() and not l.startswith('---') 
                  and not l.startswith('#') and not l.startswith('|')]
    if len(body_lines) < 3:
        empty_pages.append(page.name)

# 5. 结论
if len(unprocessed) == 0 and len(empty_pages) == 0:
    print("✅ 硬指标达标")
else:
    print(f"❌ 未处理: {len(unprocessed)}, 空 wiki: {len(empty_pages)}")
```

### 达标标准

| 指标 | 要求 |
|------|------|
| 未处理文件 | 0 |
| 空 wiki 页面 | 0 |
| Wiki 页面内容 | ≥3 行实质内容 |

---

## 处理所有类型文件

Wiki Ingest 处理 raw 目录下的**所有文件**，不跳过"无效"文件：

| 文件类型 | 定义 | 处理策略 | 输出位置 |
|----------|------|----------|----------|
| **完整文章** | 有 frontmatter，正文 ≥ 200 字 | 直接创建 Wiki 页面 | `wiki/entities/` 或 `wiki/concepts/` |
| **无frontmatter文章** | 无 frontmatter，正文 ≥ 200 字 | 自动生成 frontmatter，创建 Wiki 页面 | `wiki/entities/` |
| **短笔记** | 正文 < 200 字但有 frontmatter | 合并到相关主题 Wiki 页面 | 作为补充内容 |
| **碎片笔记** | 正文 < 100 字 | 记录到 `wiki/fragments.md` | 待人工整理或合并 |

### 无frontmatter文章处理

自动生成 frontmatter：

```yaml
---
title: {从文件名或首行提取}
created: {当前日期}
source: raw/notes/xxx.md
type: auto-generated
tags: {从内容提取关键词}
---
```

### 碎片笔记收集

`wiki/fragments.md` 记录所有碎片笔记：

```markdown
# 碎片笔记收集

记录未形成完整内容的碎片笔记，等待合并或扩展。

| 来源 | 内容 | 字数 | 建议合并到 |
|------|------|------|------------|
| raw/notes/速记.md | 快速记录内容 | 29 | 待定 |
| raw/notes/投资理财/龙头战法.md | 龙头战法要点 | 53 | wiki/concepts/龙头战法.md |
```

---

## 相关

- `wiki-auto-save`: 自动保存到 tmp
- `wiki-curator`: 定时整理（tmp → raw）
- `llm-wiki`: Karpathy LLM Wiki 模式

---

*Inspired by Karpathy LLM Wiki*