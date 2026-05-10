---
name: hermes-custom-skills-setup
description: Hermes 自建技能管理架构 - 软连接整个 skills 目录到 Git 仓库，实现修改自动同步和版本控制
version: 1.0.0
author: Luna
category: devops
---

# Hermes 自建技能管理架构

## 核心思路

将整个 `~/.hermes/skills` 目录软连接到 Git 仓库，自建技能用 Git 管理，官方技能用 `.gitignore` 排除。

```
~/.hermes/skills → 软连接 → hermes-skills/skills
                                    ↓
                              Git 仓库管理
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
            自建技能（Git跟踪）              官方技能（.gitignore排除）
```

## 好处

1. **软连接简单**：只链接一个目录
2. **修改自动同步**：Git 仓库中修改立即生效
3. **版本控制**：所有自建技能有 Git 历史
4. **官方技能隔离**：通过 .gitignore 排除，不影响 Git

---

## 架构搭建流程

### Step 1: 备份当前状态

```bash
cp -r ~/.hermes/skills ~/.hermes/skills.local.bak.v2
```

### Step 2: 解除现有软连接（如果有）

```bash
# 检查现有软连接
find ~/.hermes/skills -type l -maxdepth 3

# 删除软连接，复制文件回来
for skill in "mcn/wechat-mp-auto-publish" ...; do
  if [ -L ~/.hermes/skills/$skill ]; then
    rm ~/.hermes/skills/$skill
    cp -r /path/to/backup/$skill ~/.hermes/skills/$skill
  fi
done
```

### Step 3: 删除过时技能

检查过时技能是否已整合到现有技能中：
- `batch-ingest` → 功能与 wiki-ingest 重复
- `mcn-workflow` → 功能合并到 wechat-mp-auto-publish
- `zhihu-collection-*` → 功能整合到 mcn-hotspot-aggregator

```bash
rm -rf ~/.hermes/skills/note-taking/batch-ingest
rm -rf ~/.hermes/skills/mcn/mcn-workflow
rm -rf ~/.hermes/skills/web/zhihu-collection-*
```

### Step 4: 移动 skills 目录到 Git 仓库

```bash
GIT_SKILLS="/Users/timesky/backup/hermes_agent_bak/hermes-skills/skills"

# 删除 Git 仓库中现有的 skills 目录
rm -rf "$GIT_SKILLS"

# 移动 hermes 的 skills 目录到 Git 仓库
mv ~/.hermes/skills "$GIT_SKILLS"
```

### Step 5: 创建 .gitignore

排除所有官方/第三方技能：

```gitignore
# 官方分类目录
skills/apple/
skills/autonomous-ai-agents/
skills/creative/
skills/data-science/
skills/github/
skills/research/
...（列出所有官方分类）

# .hub 目录（官方）
skills/.hub/

# 系统文件
.DS_Store
skills/.bundled_manifest

# 注意：新安装官方技能后需要添加到此文件
```

### Step 6: 创建软连接

```bash
ln -s /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills ~/.hermes/skills
```

### Step 7: Git 提交自建技能

```bash
cd /Users/timesky/backup/hermes_agent_bak/hermes-skills
git add .gitignore
git add skills/mcn/
git add skills/note-taking/wiki-auto-save/
git add skills/note-taking/wiki-ingest/
git add skills/devops/hermes-backup/
git add skills/software-development/skill-optimizer/
git add skills/web/web-fetcher/
git commit -m "整合技能管理架构"
git push
```

---

## 自建技能列表

| 分类 | 技能 | 说明 |
|------|------|------|
| **mcn** | wechat-mp-auto-publish | 公众号入口技能 |
| **mcn** | mcn-hotspot-aggregator | 热搜抓取 |
| **mcn** | mcn-topic-selector | 选题分析 |
| **mcn** | mcn-content-rewriter | 内容改写 |
| **mcn** | mcn-wechat-publisher | 公众号发布 |
| **note-taking** | wiki-auto-save | 知识库自动保存 |
| **note-taking** | wiki-ingest | 增量式 ingest |
| **devops** | hermes-backup | Hermes 备份恢复 |
| **software-development** | skill-optimizer | Skill 自动优化 |
| **web** | web-fetcher | Web 抓取扩展 |

---

## 创建新技能流程

### Step 1: 在 Git 仓库对应分类创建

```bash
cd /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills/<category>
mkdir <skill-name>
```

### Step 2: 创建 SKILL.md

```markdown
---
name: <skill-name>
description: ...
version: 1.0.0
author: Luna
category: <category>
---

# 技能内容...
```

### Step 3: 提交到 Git

```bash
git add skills/<category>/<skill-name>/
git commit -m "添加新技能: <skill-name>"
git push
```

**注意**：由于是软连接，新技能自动在 `~/.hermes/skills` 中可见。

---

## 新安装官方技能后更新 .gitignore

```bash
# 编辑 .gitignore
vim /Users/timesky/backup/hermes_agent_bak/hermes-skills/.gitignore

# 添加新官方技能目录
skills/<新分类>/

# 提交
git add .gitignore
git commit -m "更新 .gitignore: 排除新官方技能"
git push
```

---

## 安装第三方技能流程

### 方法1：从 GitHub 克隆

```bash
cd /Users/timesky/backup/hermes_agent_bak/hermes-skills

# 克隆到对应分类
git clone https://github.com/xxx/skill-name.git skills/<category>/skill-name --depth 1

# 删除嵌套的 .git 目录（避免 Git 仓库冲突）
rm -rf skills/<category>/skill-name/.git

# 更新 .gitignore 添加排除
echo "skills/<category>/skill-name/" >> .gitignore

# 或使用反排除（如果该分类已整体排除）
sed -i '' '/skills\/<category>\//a\
!skills/<category>/skill-name/
' .gitignore

git add .gitignore
git commit -m "安装第三方技能: skill-name"
git push
```

### 方法2：从压缩包下载

```bash
# 下载并解压
curl -L "<download-url>" -o /tmp/skill.zip
unzip /tmp/skill.zip -d /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills/<category>/skill-name

# 更新 .gitignore（同上）
```

### 第三方技能示例

| 技能 | 分类 | 功能 |
|------|------|------|
| humanizer-zh | content | 去除 AI 写作痕迹 |
| summarize-pro | productivity | 20种摘要格式 |

---

## Pitfalls

### 1. 不要链接单个技能目录

错误做法：链接单个技能目录会导致循环引用
```bash
# ❌ 错误
ln -s /backup/skills/mcn/wechat-mp-auto-publish ~/.hermes/skills/mcn/wechat-mp-auto-publish
```

正确做法：链接整个 skills 目录
```bash
# ✅ 正确
ln -s /backup/skills ~/.hermes/skills
```

### 2. 不要删除整个分类目录

删除过时技能时，只删除单个技能目录，不删除整个分类：
```bash
# ❌ 错误 - 会删除分类下所有技能
rm -rf ~/.hermes/skills/mcn/

# ✅ 正确 - 只删除单个技能
rm -rf ~/.hermes/skills/mcn/mcn-workflow
```

### 3. 官方技能丢失后恢复

如果官方技能目录丢失，从备份恢复：
```bash
cp -r ~/.hermes/skills.local.bak ~/.hermes/skills
# 然后重新执行架构搭建流程
```

### 4. 备份脚本调整

备份脚本 (`backup_hermes.py`) 中的 `CUSTOM_SKILLS` 列表需要与此架构同步：
```python
CUSTOM_SKILLS = [
    "mcn/wechat-mp-auto-publish",
    "mcn/mcn-hotspot-aggregator",
    ...  # 与 .gitignore 保留的技能一致
]
```

---

## 相关文件

- Git 仓库：`/Users/timesky/backup/hermes_agent_bak/hermes-skills`
- 软连接：`~/.hermes/skills → hermes-skills/skills`
- .gitignore：`hermes-skills/.gitignore`
- 备份脚本：`~/.hermes/scripts/backup_hermes.py`

---

## Curator 技能治理系统（v0.12.0+）

Hermes v0.12.0 引入了 **Curator** 自动治理机制，定期审查、清理、归档技能。

### 查看状态

```bash
hermes curator status
```

输出示例：
```
curator: ENABLED
  runs:           0
  last run:       4d ago
  interval:       every 7d
  stale after:    30d unused
  archive after:  90d unused
```

### Curator 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 运行间隔 | 7 天 | 自动审查周期 |
| 标记 stale | 30 天未用 | 超时未使用的技能标记为 stale |
| 归档 | 90 天未用 | 超时未使用的技能自动归档 |
| 自动删除 | **永不** | 只归档不删除，可恢复 |

### Curator 命令

```bash
hermes curator status          # 查看状态和统计
hermes curator run             # 立即执行审查
hermes curator run --dry-run   # 预览（不实际操作）
hermes curator pause           # 暂停自动审查
hermes curator resume          # 恢复自动审查
hermes curator pin <skill>     # 固定技能（curator 不处理）
hermes curator unpin <skill>   # 解除固定
hermes curator restore <skill> # 从归档恢复技能
hermes curator backup          # 手动备份 skills 目录
hermes curator rollback        # 从备份恢复
```

### 保护规则

- **Bundled 技能**：永不被 curator 修改
- **Hub 安装技能**：永不被 curator 修改
- **Agent 创建技能**：唯一被 curator 处理的对象
- **Pinned 技能**：用户固定后永不被处理

### 与自建技能的关系

自建技能如果通过 Git 仓库管理（软连接方案），不会被 curator 视为 "agent-created"，因此不会被自动归档。

**建议**：
- 重要自建技能用 `hermes curator pin <skill>` 固定，防止误操作
- 定期运行 `hermes curator run --dry-run` 检查技能健康度

---

## 官方 Overlay 方案（进行中）

GitHub Issue #16852 提出了官方解决方案，预计在 v0.11+ 实现（注：v0.12.0 已有 Curator，但 Overlay 未实现）：

### 架构设计

```bash
~/.hermes/skills/
├── bundled/          ← 系统自带，只读，更新时完全替换
│   ├── mlops/
│   ├── media/
│   └── ...
├── custom/           ← 用户自建，更新时不动
│   ├── mcn/
│   └── youtube-content.diff  ← 给 bundled 打补丁
└── .bundled_manifest
```

### 核心特性

1. **分层加载**：运行时优先 `custom/`，再 `bundled/`
2. **补丁支持**：可以给 bundled skill 打 `.diff` 补丁
3. **冲突检测**：上游更新时检测与用户补丁冲突
4. **新增 CLI**：
   - `hermes skills diff <name>` - 查看与上游差异
   - `hermes skills patch <name>` - 创建补丁
   - `hermes skills conflicts` - 检测冲突
   - `hermes skills merge <name>` - 合并上游更新

### 当前方案的问题

| 问题 | 影响 |
|------|------|
| 所有技能混在 `~/.hermes/skills/` | 无法区分系统/自建/第三方 |
| 用户修改 bundled skill → hash 不匹配 | 上游更新被永久跳过 |
| `.gitignore` 需要维护所有官方分类 | 新装官方技能要手动排除 |
| 无法给官方技能打补丁 | 修改即丢失更新 |

### 建议

- **短期**：继续使用当前软连接方案
- **中期**：等待官方 Overlay 方案（Issue #16852）
- **替代**：用 Profile 隔离，每个 profile 独立 skills/

---

## Profile 隔离架构（替代方案）

适用于多 Agent 分工场景，每个 Profile 完全独立管理自己的技能。

### 架构示例

```bash
~/.hermes/profiles/
├── mcn/
│   ├── config.yaml
│   └── skills/
│       └── mcn/              ← Git 仓库（独立管理）
│           ├── my-mcn-manager/
│           ├── mcn-content-writer/
│           └── ...
│
├── coder/
│   └── skills/
│       └── custom/           ← Git 仓库
│           ├── skill-optimizer/
│           └── ...
│
└── luna/                     ← 主 Luna（共享基础技能）
    └── skills → ~/Workspace/hermes-skills/luna-skills
```

### 技能按 Profile 归属分析

| Profile | 数量 | 技能列表 | 特点 |
|---------|------|----------|------|
| **MCN 专用** | 11个 | my-mcn-manager, mcn-content-writer, mcn-hotspot-research, mcn-topic-selector, mcn-wechat-publisher, mcn-zhihu-publisher, mcn-closed-loop-analysis, mcn-feishu-push, mcn-workflow-fallback, wechat-analytics, ai-image-generation | 完整内容闭环，依赖公众号/飞书 API |
| **Luna 共用** | 7个 | wiki-auto-save, wiki-ingest, web-fetcher, twitter-bookmarks-sync, zhihu-favorites-sync, hermes-backup, hermes-custom-skills-setup | 知识管理 + 基础设施，通用性强 |
| **Coder 专用** | 2个 | skill-optimizer, macos-fs-timeout-troubleshoot | 技能开发调试专用 |

### 核心依赖关系

```
web-fetcher (核心基础技能)
     ↓
  ┌──┴──┐
  ↓     ↓
MCN   知识库
(知乎发布、公众号分析)  (wiki-auto-save)
```

**注意**：web-fetcher 是多 Profile 共享依赖，需在每个 Profile 中可用。

### Profile 隔离 vs 软连接方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **软连接（当前）** | 简单，一个连接解决，修改立即生效 | 所有技能混杂，需维护 .gitignore |
| **Profile 独立 Git** | 职责清晰，每个领域独立管理 | 分散多个仓库，共享技能需复制 |
| **中央仓库+引用** | 统一管理 + Profile 隔离 | 需维护软连接，目录结构复杂 |

### 选择建议

- **单一 Agent + 少量自建技能** → 软连接方案
- **多 Agent 分工 + 大量自建技能** → Profile 隔离方案
- **等待官方方案** → Issue #16852 Overlay 架构

## Profile 技能共享方案对比

### 方案A：external_dirs（官方推荐 v0.13.0+）

**原理**：通过 config.yaml 配置共享目录

```yaml
# ~/.hermes/profiles/mcn/config.yaml
skills:
  external_dirs: ["../skills"]  # 相对路径指向 ~/.hermes/skills/
```

**优点**：
- 官方原生支持，无需手动 symlink
- 一次更新，所有 Profile 自动同步
- Git 仓库可放在 `~/.hermes/skills/`
- Curator 不会治理 `external_dirs` 的技能

**缺点**：
- 需要每个 Profile 配置 external_dirs
- 相对路径解析依赖 Profile 目录结构

详见：[autonomous-ai-agents/hermes-agent/references/multi-profile-skill-governance.md](../../autonomous-ai-agents/hermes-agent/references/multi-profile-skill-governance.md)

### 方案B：Symlink 共享池（当前使用）

MCN profile 使用 `.agents/skills/` 目录 + symlink 实现技能共享。详见 [references/profile-symlink-sharing.md](references/profile-symlink-sharing.md)。

### 方案C：完整复制

Profile 创建时复制所有技能，独立管理。

---

### 推荐方案

| 场景 | 推荐 |
|------|------|
| 多 Profile + 自建技能共享 | **external_dirs**（官方支持） |
| 现有 symlink 已稳定 | 保持现状，逐步迁移到 external_dirs |
| 单 Profile | 无需共享 |

---

## Profile Symlink 共享模式

---

*Created: 2026-04-13 by Luna*  
*Updated: 2026-04-30 - 添加官方 Overlay 方案调研、Profile 隔离架构*  
*Updated: 2026-05-10 - 添加 Curator 治理系统、Profile Symlink 共享模式*