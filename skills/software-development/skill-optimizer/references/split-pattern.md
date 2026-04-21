---
module: split-pattern
type: reference
version: 1.0.0
---

# 技能拆分流程

将臃肿技能拆分为独立可复用的子技能。

---

## 拆分判断标准

| 应拆分 | 不应拆分 |
|--------|----------|
| 功能可独立使用 | 流程必须按顺序执行 |
| 无依赖关系 | 共享配置/状态 |
| 用户可能单独调用某个功能 | 用户不关心中间步骤 |
| SKILL.md 超过 500 行 | 领域高度相关 |

---

## 详细流程

### Step 1: 分析拆分点

**识别可独立的功能模块**：

```
原技能分析：
- 功能 A：热点调研 → 可独立，无依赖
- 功能 B：选题分析 → 依赖 A 的输出，但有独立价值
- 功能 C：内容生成 → 依赖 B 的选题，不可独立
- 功能 D：配图生成 → 可独立，通用功能
```

**拆分决策**：
- 功能 A → 拆分为独立技能
- 功能 D → 拆分为通用技能（L3）
- 功能 B/C → 保留在入口技能

---

### Step 2: 创建子技能目录

```bash
# 复制相关部分到新目录
mkdir -p ~/.hermes/skills/new-sub-skill/

# 复制相关脚本
cp scripts/run-module.py ~/.hermes/skills/new-sub-skill/scripts/

# 复制相关模板
cp templates/module-template.md ~/.hermes/skills/new-sub-skill/templates/
```

---

### Step 3: 编写子技能 SKILL.md

```yaml
---
name: new-sub-skill
description: |
  [子技能的触发词和场景]
  可独立调用，也可被父技能调度。
parent: parent-skill-name  # 标记来源
tags: [独立关键词]
---

# 子技能名称

独立功能描述。

---

## 独立调用

用户直接触发：[触发词]

## 父技能调度

被 parent-skill-name 在阶段 N 调用。
```

---

### Step 4: 修改原技能为入口

**保留调度逻辑，删除已拆分的实现**：

```markdown
## 阶段 N: [功能名称]

调用子技能：new-sub-skill

详见：new-sub-skill/SKILL.md
```

---

### Step 5: 添加 redirect 标记

**在子技能中标记来源**：

```yaml
redirect_from: parent-skill-name/module-n
```

**在父技能中标记去向**：

```yaml
redirect_to: new-sub-skill
```

---

### Step 6: 验证双向调用

| 测试 | 方法 | 状态 |
|------|------|------|
| 入口调用 | 执行父技能完整流程 | [ ] |
| 独立调用 | 直接触发子技能 | [ ] |
| 配置共享 | 两边都能读取配置 | [ ] |
| 输出一致 | 输出格式不变 | [ ] |

---

## 分层架构建议

```
L1 - 入口技能（调度器）
  → 统一触发，调度各阶段

L2 - 功能技能（领域相关）
  → 可独立，也可被调度

L3 - 通用技能（跨领域）
  → 完全独立，多处复用
```

**示例**：

```
L1: my-mcn-manager
L2: mcn-hotspot-research, mcn-topic-selector
L3: humanizer-zh, ai-image-generation
```

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| 拆分后功能丢失 | 先复制，再删除，每步验证 |
| 配置分散 | 保留统一配置，两边都能读取 |
| 触发词冲突 | 子技能 description 明确独立触发场景 |
| 过度拆分 | 评估独立价值，不要拆分太细 |

---

*Created: 2026-04-15 by Luna*