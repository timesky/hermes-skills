# Profile Symlink 共享模式

## 发现背景

2026-05-10 检查 Hermes v0.12.0 Profile 技能结构时发现 MCN profile 使用 symlink 共享技能池。

## 架构模式

```
~/.hermes/profiles/mcn/skills/
├── apple/              ← 复制（官方）
├── autonomous-ai-agents/ ← 复制（官方）
├── creative/           ← 复制（官方）
├── mcn/                ← 复制（自建 MCN 技能）
│   ├── my-mcn-manager/
│   ├── mcn-content-writer/
│   └── ...
├── baoyu-article-illustrator → ../.agents/skills/baoyu-article-illustrator  ← Symlink
├── baoyu-comic          → ../.agents/skills/baoyu-comic                    ← Symlink
├── baoyu-infographic    → ../.agents/skills/baoyu-infographic              ← Symlink
└── ...                  ← 其他 baoyu 系列均为 symlink

~/.hermes/profiles/mcn/.agents/skills/
├── baoyu-article-illustrator/  ← 实际存放目录
├── baoyu-comic/
├── baoyu-infographic/
└── ...                         ← 共享池
```

## 关键发现

| Profile | Skills 数量 | Symlink 共享 |
|---------|-------------|--------------|
| default | - | 主目录，无 symlink |
| code | 89 | 无 symlink |
| mcn | 91 | **有 symlink** (22个 baoyu 系列) |
| stock | - | 无 symlink |

## 查看命令

```bash
# 查看 profile 技能结构
hermes profile show mcn

# 查看 symlink
ls -la ~/.hermes/profiles/mcn/skills/ | grep "^l"

# 查看共享池
ls -la ~/.hermes/profiles/mcn/.agents/skills/
```

## 使用场景

适用于：
- 多 Profile 需要共享同一套技能（如 baoyu 图像生成系列）
- 技能更新只需修改一处，所有 Profile 自动同步
- 减少 Profile 目录体积

## 创建 symlink 共享

```bash
# 1. 创建共享池目录
mkdir -p ~/.hermes/profiles/<profile>/skills/.agents/skills

# 2. 放置共享技能
mv ~/.hermes/profiles/<profile>/skills/<skill> ~/.hermes/profiles/<profile>/skills/.agents/skills/<skill>

# 3. 创建 symlink
ln -s ../.agents/skills/<skill> ~/.hermes/profiles/<profile>/skills/<skill>
```

## 注意事项

- `.bundled_manifest` 记录技能 hash，symlink 技能的 hash 与原目录一致
- Profile 的 `skills/` 目录下可以有混合模式：部分复制 + 部分 symlink
- 共享池 `.agents/skills/` 不是 Hermes 官方目录结构，是用户自定义模式

---

*Created: 2026-05-10 by Luna*