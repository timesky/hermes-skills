---
name: wiki-ingest
description: 增量式 ingest 流程，将 raw 源文件转换为 wiki 结构化内容。支持单个文件 ingest 和批量 ingest 两种模式。当用户说"ingest"、"建立 wiki"、"处理 raw 目录"、"批量 ingest"、"raw 目录所有内容都要建立 wiki"时使用。优先优化此技能，不要创建重复技能。
version: 2.1
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
6. **不要创建重复技能**：发现流程缺陷时，优先优化现有技能（如 wiki-ingest），而不是创建新技能（如 batch-ingest）
7. **文件验证必须严格**：过滤 placeholder（<1KB）、缓存消息、无 frontmatter 的文件

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

## 相关

- `wiki-auto-save`: 自动保存到 tmp
- `wiki-curator`: 定时整理（tmp → raw）
- `llm-wiki`: Karpathy LLM Wiki 模式

---

*Inspired by Karpathy LLM Wiki*