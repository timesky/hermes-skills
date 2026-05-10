---
name: ralph-loop
description: Ralph Loop 任务循环控制器 - 自动执行任务直到达标
tags: [automation, task-orchestration, multi-agent]
version: 1.0.0
---

# Ralph Loop

自动执行任务队列中的任务，验证结果，循环直到全部完成。

## 快速开始

### 执行任务队列

```bash
# 在 Hermes 中直接执行
bash ~/.hermes/ralph/ralph-loop.sh 10
```

### 查看当前任务

```bash
python3 ~/.hermes/ralph/task-state-manager.py list
```

### 手动添加任务

编辑 `~/.hermes/ralph/task-queue.yaml`:

```yaml
queue:
  - id: "TASK-001"
    title: "你的任务标题"
    priority: 1
    complexity: simple  # 或 complex
    status: pending
    criteria:
      - type: file_exists
        target: /path/to/file
```

## 工作原理

```
1. 读取 task-queue.yaml
2. 取出优先级最高的 pending 任务
3. 标记为 in_progress
4. 执行任务（集成 Hermes delegate_task）
5. 验证结果（运行 validators/*.py）
6. 更新状态为 completed 或 failed
7. 循环直到队列为空
```

## 验证器

| 验证器 | 用途 | 示例 |
|--------|------|------|
| `file_exists` | 检查文件是否存在 | `target: /tmp/test.txt` |
| `test_pass` | 运行 pytest | `target: tests/` |
| `coverage` | 检查覆盖率 | `target: 80` |

## 定时任务配置

```yaml
# 在 Hermes cronjob 中添加
- name: "夜间任务执行"
  schedule: "0 2 * * *"
  prompt: "执行 ralph-loop 技能"
  skills: ["ralph-loop"]
```

## 注意事项

- 默认最大迭代 10 次，防止死循环
- 使用锁文件防止重复执行
- 每次执行前会检查任务队列

---

*Last updated: 2026-05-05*
