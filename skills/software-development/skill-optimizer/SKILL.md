---
name: skill-optimizer
description: |
  Hermes 技能全生命周期管理。使用 Autoresearch 方法优化技能，支持合并、拆分、废弃管理。
  当用户提到：优化技能、合并技能、拆分技能、废弃技能、技能健康检查时使用此技能。
  定期执行健康检查（每周），问题触发自动优化。
version: 2.0
created: 2026-04-12
updated: 2026-04-15
author: Luna
inspired_by: Karpathy Autoresearch
---

## 技能管理决策框架

### 优化时机选择

| 方式 | 适用场景 |
|------|----------|
| **问题触发（立即）** | 用户纠正、执行失败、参数错误、环境变更 |
| **定期检查（每周）** | 废弃技能检测、一致性检查、使用频率统计 |

**结论**：问题触发 + 每周健康检查（非每日）

### 技能粒度判断

| 合并条件 | 拆分条件 |
|----------|----------|
| 流程必须按顺序执行 | 功能可独立使用 |
| 共享配置/状态 | 无依赖关系 |
| 用户不关心中间步骤 | 用户可能单独调用某个功能 |

**分层架构**：
- L1 入口技能（调度器）
- L2 功能技能（领域相关，可独立）
- L3 通用技能（跨领域复用）

### 合并/拆分安全流程

**核心原则**：增量迁移 + 保留备份，**不重写**

```
合并流程：
  Step 1: 创建骨架（只有调度逻辑）
  Step 2: 逐个迁移子技能（复制，验证）
  Step 3: 原技能标记 deprecated（保留30天）
  Step 4: 验证完整流程
  Step 5: 删除旧技能（30天后）

拆分流程：
  Step 1: 分析拆分点
  Step 2: 创建子技能目录
  Step 3: 编写子技能 SKILL.md（标记 parent）
  Step 4: 原技能改为入口（删除已拆分实现）
  Step 5: 验证双向调用
```

---

# skill-optimizer

使用 Karpathy 的 Autoresearch 方法自动优化 Hermes Skills。

---

## 核心公式

```
Autoresearch = 改一小步 + 测试 + 保留/回退 × N 次
```

---

## 工作流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Skill Autoresearch 优化流程                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 选择目标 Skill                                                  │
│  ├─ 读取 skill_view(name) 获取当前 SKILL.md                             │
│  ├─ 分析 Skill 类型：内容生成/工具调用/工作流                            │
│  └─ 选择合适的 Checklist 模板                                           │
│                                                                         │
│  Step 2: 定义测试输入                                                    │
│  ├─ 提供典型使用场景的输入                                               │
│  ├─ 可以是：具体任务、URL、文件路径                                      │
│  └─ 用于后续每次测试                                                    │
│                                                                         │
│  Step 3: 获取基线分数                                                    │
│  ├─ 用当前 Skill 处理测试输入                                           │
│  ├─ 用 Checklist 评估输出质量                                           │
│  └─ 记录起始分数和失败项                                                 │
│                                                                         │
│  Step 4: 进入优化循环                                                    │
│  ├─ 分析失败的 Checklist 项                                             │
│  ├─ 做一个小改动（修改 SKILL.md）                                        │
│  ├─ 重新运行测试，用 Checklist 评分                                     │
│  ├─ 分数上升 → 保留改动，更新 changelog                                  │
│  ├─ 分数下降 → 回退改动，记录失败原因                                    │
│  └─ 循环直到：连续3次95%+ 或 达到最大轮数                                │
│                                                                         │
│  Step 5: 输出结果                                                        │
│  ├─ 优化后的 Skill（保存为新版本或更新）                                 │
│  ├─ Changelog（记录所有改动和效果）                                      │
│  ├─ 原始 Skill 备份                                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Checklist 模板库

### 内容生成类 Skill

适用于：文案生成、文章改写、摘要生成等

```yaml
checklist:
  - id: title_quality
    question: 标题是否包含具体数字或具体结果？
    weight: 1
    type: content
    
  - id: no_buzzword
    question: 是否避免了"革命性""颠覆性""协同效应"等 buzzword？
    weight: 1
    type: content
    
  - id: specific_cta
    question: CTA 是否使用了具体的动词短语（而非"了解更多"）？
    weight: 1
    type: content
    
  - id: pain_point_first
    question: 第一行是否指出了具体痛点（而非废话开场）？
    weight: 1
    type: content
    
  - id: length_control
    question: 总字数是否在指定范围内？
    weight: 1
    type: content
```

### 工具调用类 Skill

适用于：API调用、数据处理、文件操作等

```yaml
checklist:
  - id: correct_tool
    question: 是否使用了正确的工具/命令？
    weight: 2
    type: tool
    
  - id: error_handling
    question: 是否有错误处理机制（try/except 或 fallback）？
    weight: 1
    type: tool
    
  - id: correct_output
    question: 输出格式是否正确（JSON/Markdown/等）？
    weight: 2
    type: tool
    
  - id: pitfall_covered
    question: 是否处理了已知的 Pitfall？
    weight: 1
    type: tool
```

### 工作流类 Skill

适用于：多步骤流程、自动化任务等

```yaml
checklist:
  - id: step_order
    question: 步骤顺序是否正确？
    weight: 2
    type: workflow
    
  - id: verification_step
    question: 关键步骤后是否有验证/检查？
    weight: 1
    type: workflow
    
  - id: fallback_defined
    question: 每个步骤是否有失败后的处理方案？
    weight: 1
    type: workflow
    
  - id: clear_output
    question: 最终输出是否清晰说明了结果？
    weight: 1
    type: workflow
```

---

## Changelog 格式

优化过程的完整记录，保存在 `skill-name/CHANGELOG.md`：

```markdown
# Skill Optimization Changelog

## 优化任务

- Skill: wiki-auto-save
- 类型: 内容生成
- 起始分数: 56%
- 最终分数: 92%
- 总轮数: 4

---

## [Round 1] 增加标题规则

**改动内容**:
在 SKILL.md 中添加：
> 标题必须包含具体信息，不要使用"让你的业务增长"这种模糊表达。

**测试分数**: 56% → 68%
**效果**: ✅ 保留
**原因**: 解决最常见的失败原因——标题太虚

---

## [Round 2] 禁用 Buzzword

**改动内容**:
添加黑名单：
> 永远不要使用：革命性、颠覆性、协同效应、利用、解锁

**测试分数**: 68% → 80%
**效果**: ✅ 保留
**原因**: 这些词让内容像 AI 废话

---

## [Round 3] 添加范例

**改动内容**:
在 templates/ 添加高质量范例文件，标注关键点

**测试分数**: 80% → 92%
**效果**: ✅ 保留
**原因**: 让 Skill 看到什么是"好"，而不是瞎猜

---

## [Round 4] 压缩字数限制

**改动内容**:
收紧字数限制到 100 字以内

**测试分数**: 92% → 75%
**效果**: ❌ 回退
**原因**: 内容太薄，关键信息丢失

---

## 总结

| 改动类型 | 保留 | 回退 |
|----------|------|------|
| 规则添加 | 2 | 0 |
| 黑名单 | 1 | 0 |
| 范例添加 | 1 | 0 |
| 限制收紧 | 0 | 1 |

**有效改动**: 增加规则、添加范例
**无效改动**: 过度限制

---

*此 Changelog 可迁移到其他 Skill 或交给更强模型*
```

---

## 操作命令

### 启动优化

```
run skill-optimizer on wiki-auto-save
```

### 指定参数

```
run skill-optimizer on wiki-auto-save with:
  - test_input: "抓取知乎文章 https://zhuanlan.zhihu.com/p/xxx"
  - checklist: content-generation
  - max_rounds: 10
```

### 查看结果

```
skill_view(name=wiki-auto-save, file_path=CHANGELOG.md)
```

---

## 小改动策略

每次只改一小步，常见改动类型：

| 改动类型 | 示例 | 适用场景 |
|----------|------|----------|
| 增加规则 | "标题必须包含数字" | 解决具体失败项 |
| 添加 Pitfall | "不要覆盖已存在文件" | 防止常见错误 |
| 禁用模式 | "永远不要使用xxx" | 消除负面特征 |
| 添加范例 | templates/example.md | 让 Skill 看到什么是好 |
| 调整顺序 | 重新排列步骤 | 工作流优化 |
| 添加验证 | "执行后检查结果" | 提高可靠性 |

---

## Pitfalls

### 优化流程

1. **不要一次改太多**：每次只改一个小点，否则无法判断哪个改动有效
2. **Checklist 不能太模糊**：必须是 Yes/No 问题，否则评分不一致
3. **测试输入要稳定**：每次测试用相同的输入，否则分数不可比
4. **保留原始版本**：优化开始前备份原始 Skill
5. **Changelog 是资产**：记录每个改动和效果，这是可迁移的知识

### 健康检查脚本 (skill_health_check.py)

6. **YAML 日期自动解析**：`yaml.safe_load()` 会将 `'2026-04-15'` 这样的日期字符串自动转换为 `datetime.date` 对象，而非字符串。脚本需同时处理两种类型：
   ```python
   if isinstance(deprecated_date, date):
       dep_date = deprecated_date
   else:
       dep_date = datetime.strptime(deprecated_date, '%Y-%m-%d').date()
   ```

7. **异常时间戳过滤**：复制文件可能导致 DOS 时间戳（1980-01-01），造成 "16911 天未使用" 的误报。需过滤早于 2020 年的时间戳：
   ```python
   if last_used.year >= 2020:
       # 正常处理
   ```

8. **SKILL.md 中的示例代码会被解析**：如果 SKILL.md 的代码块中包含 `status: deprecated` 等 YAML 格式，脚本可能误解析。健康检查应只解析 frontmatter（文件开头 `---` 之间的部分）。

---

## 与 LLM Wiki 的关系

| 方法 | 目标 | 积累 |
|------|------|------|
| LLM Wiki | 知识库 | wiki 页面 |
| Skill Autoresearch | Skill 优化 | Changelog |

两者都强调 **可测量 + 可积累**。

---

## 相关

- `autoresearch-skill-evolution`: 原始方法论（wiki 页面）
- `skill_manage`: 技能管理工具
- `hermes-backup`: 技能备份（优化前备份）

---

## 技能生命周期管理（扩展功能）

### 优化时机策略

**推荐：问题触发 + 每周健康检查**

```
触发优化（立即执行）：
  - 用户纠正操作方式
  - 执行失败或超时
  - 发现脚本参数错误
  - 配置/环境变更导致失效

每周健康检查（Cron）：
  - 扫描所有自建技能的 last_used 时间
  - 超过30天未使用 → 评估是否废弃
  - 检查 SKILL.md 与实际脚本的一致性
  - 生成技能健康报告
```

### 技能粒度原则

**分层架构**：

```
L1 - 入口技能（统一调度）
  → my-mcn-manager（调度器）
  → my-favorites-sync（调度器）

L2 - 功能技能（独立可复用）
  → mcn-hotspot-research
  → mcn-topic-selector
  → mcn-content-rewriter

L3 - 通用技能（跨领域复用）
  → humanizer-zh
  → ai-image-generation
```

**判断标准**：

| 合并条件 | 拆分条件 |
|----------|----------|
| 流程必须按顺序执行 | 功能可独立使用 |
| 共享配置/状态 | 无依赖关系 |
| 用户不关心中间步骤 | 用户可能单独调用某个功能 |

### 安全合并/拆分流程

**核心原则：增量迁移 + 保留备份，禁止重写**

```
合并流程：
Step 1: 创建新入口技能（骨架，只有调度逻辑）
Step 2: 逐个迁移子技能（复制原有内容到 references/）
Step 3: 原技能标记 deprecated（保留7天）
Step 4: 验证完整流程
Step 5: 删除旧技能

拆分流程：
Step 1: 创建子技能目录（复制相关部分）
Step 2: 原技能改为入口（保留调度逻辑）
Step 3: 添加 redirect 标记
Step 4: 验证双向调用（入口调用 + 独立调用）
```

**⚠️ 禁止做法**：
- 直接重写整个技能 → 原有功能丢失
- 合并后立即删除旧技能 → 无回退方案
- 新技能依赖调用旧技能 → 形成耦合

### 废弃管理

```yaml
# SKILL.md frontmatter
status: deprecated
deprecated_date: 2026-04-15
redirect_to: new-skill-name
reason: "功能已整合到 new-skill-name"
```

- deprecated 标记后保留 30 天
- 每周健康检查提醒用户删除

---

## 自建技能架构说明

**软连接结构**：
```
~/.hermes/skills → /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills/
```

**自建技能位置**：
- `software-development/skill-optimizer/` - 本技能
- `skill-creator/skill-consolidation-pattern/` - 合并技能模式
- `mcn/my-mcn-manager/` - MCN 工作流
- `my-favorites-sync/` - 知识收藏同步

---

*Inspired by Karpathy Autoresearch*
*Extended: 2026-04-15 by Luna (lifecycle management)*