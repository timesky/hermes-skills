# Skill Optimization Changelog Template

## 优化任务

- Skill: {skill_name}
- 类型: {skill_type}
- 起始分数: {baseline_score}%
- 最终分数: {final_score}%
- 总轮数: {total_rounds}

---

## [Round N] 改动标题

**改动内容**:
在 SKILL.md 中做了什么修改

```diff
- 原内容
+ 新内容
```

**测试分数**: {prev_score}% → {new_score}%
**效果**: ✅ 保留 / ❌ 回退
**原因**: 为什么保留或回退

---

## 总结

| 改动类型 | 保留 | 回退 |
|----------|------|------|
| 规则添加 | N | N |
| Pitfall添加 | N | N |
| 禁用模式 | N | N |
| 范例添加 | N | N |
| 其他 | N | N |

**有效改动**: {列出保留的改动类型}
**无效改动**: {列出回退的改动类型}

---

## 可迁移经验

以下经验可应用于同类 Skill：

1. {经验1}
2. {经验2}
3. {经验3}

---

*此 Changelog 可迁移到其他 Skill 或交给更强模型*
*Created by skill-optimizer on {date}*