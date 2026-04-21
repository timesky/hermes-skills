---
module: deprecation-pattern
type: reference
version: 1.0.0
---

# 技能废弃管理

安全废弃不再使用的技能，避免误删和数据丢失。

---

## 废弃触发条件

| 条件 | 说明 |
|------|------|
| 功能已整合 | 被新技能完全替代 |
| 30天未使用 | last_used 超过 30 天 |
| 用户确认废弃 | 用户明确表示不再需要 |
| 功能过时 | 技术环境变化导致失效 |

---

## 废弃流程

### Step 1: 标记 deprecated

**修改 SKILL.md frontmatter**：

```yaml
---
name: old-skill-name
status: deprecated
deprecated_date: 2026-04-15
redirect_to: new-skill-name  # 如果有替代
reason: "功能已整合到 new-skill-name"
keep_days: 30  # 保留天数
---
```

---

### Step 2: 创建备份

```bash
# 备份到 .backup 目录
mkdir -p ~/.hermes/skills/.backup/2026-04-15/
cp -r ~/.hermes/skills/old-skill-name ~/.hermes/skills/.backup/2026-04-15/
```

---

### Step 3: 健康检查提醒

**每周健康检查会报告**：

```
废弃技能提醒：
- old-skill-name (deprecated 15天，还剩15天)
  → 替代：new-skill-name
  → 原因：功能已整合
```

---

### Step 4: 删除（到期后）

**条件**：
- deprecated_days >= keep_days
- 无用户反对

```bash
# 删除技能目录
rm -rf ~/.hermes/skills/old-skill-name

# 保留备份（不删除）
# ~/.hermes/skills/.backup/2026-04-15/old-skill-name
```

---

## redirect_to 用法

**当技能有替代时**：

```yaml
redirect_to: new-skill-name
```

**Luna 行为**：
- 用户提到旧触发词 → 自动加载新技能
- 提示用户："此功能已迁移到 new-skill-name"

**当技能无替代时**：

```yaml
redirect_to: null
reason: "功能已过时，不再使用"
```

---

## 定时任务处理

**废弃技能关联的 Cron 任务**：

```bash
# 查看关联任务
/cron list | grep old-skill-name

# 更新或删除任务
/cron update job_id --prompt "使用 new-skill-name ..."
# 或
/cron remove job_id
```

---

## 备份保留策略

| 时间 | 操作 |
|------|------|
| 0-30天 | 技能标记 deprecated，备份创建 |
| 30-60天 | 技能删除，备份保留 |
| 60天后 | 备份可手动清理（用户决定） |

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| 立即删除 | 必须保留 30 天 |
| 备份丢失 | 备份目录不随技能删除 |
| Cron 任务遗忘 | 废弃时同步检查关联任务 |
| redirect_to 无效 | 确保新技能已存在并稳定 |

---

*Created: 2026-04-15 by Luna*