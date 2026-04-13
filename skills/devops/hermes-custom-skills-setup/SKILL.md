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

*Created: 2026-04-13 by Luna*