---
module: consolidation-pattern
type: reference
source: skill-consolidation-pattern (整合)
version: 1.0.0
---

# 技能合并流程

将多个分散技能整合为单一入口技能的详细步骤。

---

## 核心原则

| 原则 | 说明 |
|------|------|
| **代码复制而非调用** | 新技能独立完整，不依赖旧技能 |
| **旧技能保留备份** | 标记 deprecated，保留 30 天 |
| **增量迁移** | 逐个功能迁移，每步验证 |

---

## 详细流程

### Step 1: 设计架构

```
新技能目录结构：
skill-name/
├── SKILL.md                    # 统一入口 + 工作流说明
├── references/                 # 模块化文档（原技能代码）
│   ├── 01-module-a.md
│   ├── 02-module-b.md
│   └── ...
├── scripts/                    # 统一执行脚本
│   ├── run-full-workflow.py
│   └── validate-xxx.py
└── assets/                     # 资源文件（可选）
```

**命名规范**：
- `references/` 文件：`NN-module-name.md`（数字前缀表示顺序）
- `scripts/` 文件：`run-module-name.py`（动词前缀表示动作）

---

### Step 2: 创建骨架 SKILL.md

**只写调度逻辑，不实现具体功能**：

```yaml
---
name: new-skill-name
description: |
  [完整列出所有触发词]
  当用户提到：A、B、C、D 时使用此技能。
  支持完整流程或分阶段执行。
tags: [关键词1, 关键词2]
---

# 技能名称

一句话描述核心功能。

---

## 工作流概览

| 阶段 | 功能 | 调用模块 | 自动化 |
|------|------|----------|--------|
| 1 | xxx | references/01-xxx.md | 全自动 |
| 2 | xxx | references/02-xxx.md | 半自动 |

---

## 详细模块

详见各 references 文档。
```

---

### Step 3: 逐个迁移子技能

**对每个旧技能执行**：

```bash
# 读取旧技能
skill_view(name=old-skill-a)

# 提取核心逻辑
# 简化为 references/01-module-a.md

# 删除旧技能特有的上下文（如"本技能调用 xxx"）
# 只保留核心功能和配置
```

**验证每个模块**：
- 独立执行是否正常
- 配置是否正确加载
- 输出格式是否符合预期

---

### Step 4: 标记旧技能 deprecated

**修改旧技能 SKILL.md**：

```yaml
---
name: old-skill-a
status: deprecated
deprecated_date: 2026-04-15
redirect_to: new-skill-name
reason: "功能已整合到 new-skill-name references/01-module-a.md"
---
```

---

### Step 5: 验证完整流程

**测试清单**：

| 测试项 | 方法 | 状态 |
|--------|------|------|
| 触发词测试 | 提到关键词是否触发 | [ ] |
| 完整流程测试 | 端到端执行 | [ ] |
| 分阶段测试 | 单独执行各阶段 | [ ] |
| 配置读取测试 | 加载配置文件 | [ ] |
| 错误处理测试 | 异常情况处理 | [ ] |

---

### Step 6: 删除旧技能（30天后）

**条件**：
- 新技能稳定运行 30 天
- 无用户反馈问题
- 定时任务已切换到新脚本

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| 新技能依赖旧技能 | 代码复制到 references/，不调用 |
| 触发词不够全面 | description 列出所有触发场景 |
| 配置文件分散 | 统一到单一配置文件 |
| 立即删除旧技能 | 保留 30 天作为备份 |
| references/照搬旧技能 | 简化为模块说明，删除上下文 |

---

## 示例：MCN 整合

**整合前**：
```
mcn-hotspot-aggregator/
mcn-topic-selector/
mcn-content-rewriter/
mcn-image-generator/
mcn-wechat-publisher/
```

**整合后**：
```
my-mcn-manager/
├── SKILL.md
├── references/
│   ├── 01-hotspot-research.md
│   ├── 02-topic-selection.md
│   ├── 03-content-rewriting.md
│   ├── 04-image-generation.md
│   └── 05-publishing.md
├── scripts/
│   ├── run-topic-analysis.py
│   ├── run-content-gen.py
│   ├── generate-images.py
│   ├── publish-draft.py
│   └── fetch-published-articles.py
└── templates/
    ├── content-templates.md
    └── prompt-templates.md
```

---

*Source: skill-consolidation-pattern*
*Created: 2026-04-14 by Luna*