---
name: wiki-ingest
description: 增量式 ingest 流程，将 raw 源文件转换为 wiki 结构化内容。支持单个文件 ingest 和批量 ingest 两种模式。当用户说"ingest"、"建立 wiki"、"处理 raw 目录"、"批量 ingest"时使用。
version: 2.0
created: 2026-04-12
updated: 2026-04-12
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
│                         Wiki Ingest 流程                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 检查 processed.log                                              │
│  ├─ 读取 wiki/processed.log                                             │
│  ├─ 检查源文件是否已处理过                                              │
│  └─ 已处理 → 跳过；未处理 → 继续                                        │
│                                                                         │
│  Step 2: 读取源文件                                                      │
│  ├─ 从 raw/sources/ 或 raw/notes/ 读取                                  │
│  ├─ 解析 frontmatter（created, source, tags）                           │
│  └─ 提取正文内容                                                        │
│                                                                         │
│  Step 3: 提取关键信息                                                    │
│  ├─ 识别实体：人物、项目、工具、组织                                    │
│  ├─ 识别概念：技术、方法论、理论                                        │
│  └─ 识别关系：A 与 B 的关系、A 是 B 的一种                                │
│                                                                         │
│  Step 4: 创建/更新 Wiki 页面                                             │
│  ├─ 新实体 → wiki/entities/实体名.md                                    │
│  ├─ 新概念 → wiki/concepts/概念名.md                                    │
│  ├─ 已有页面 → 增量更新（追加来源，添加 cross-reference）               │
│  └─ 相关文件 → 合并到一个页面                                           │
│                                                                         │
│  Step 5: 增量更新 index.md                                               │
│  ├─ 使用 patch 添加新行到表格                                           │
│  ├─ 更新 Statistics 数字                                                │
│  └─ 不要重写整个文件！                                                  │
│                                                                         │
│  Step 6: 追加 log.md                                                     │
│  ├─ 格式：## [YYYY-MM-DD HH:MM] ingest | 标题                           │
│  └─ 记录处理内容、关键洞察                                              │
│                                                                         │
│  Step 7: 追加 processed.log                                              │
│  ├─ 格式：source_path | ingest_date | wiki_pages | status               │
│  └─ 标记源文件已处理，避免重复                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 增量更新规则

### 实体页面

**新实体**:
```markdown
---
created: YYYY-MM-DD
sources: [源文件路径]
tags: [标签]
---

# 实体名

## 概述
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

---

## 相关

- `wiki-auto-save`: 自动保存到 tmp
- `wiki-curator`: 定时整理（tmp → raw）
- `llm-wiki`: Karpathy LLM Wiki 模式

---

*Inspired by Karpathy LLM Wiki*