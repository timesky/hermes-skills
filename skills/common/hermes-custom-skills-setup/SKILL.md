---
name: hermes-custom-skills-setup
description: Hermes 自建技能管理架构 - 按 Profile 分离技能目录（common/mcn/stock/third-party），实现职责清晰和版本控制
version: 3.0.0
author: Luna
category: common
---

# Hermes 自建技能管理架构

## 核心思路（v3.0 - Profile 分离目录）

使用官方 `external_dirs` 配置，按 Profile 分离技能目录：

```
~/.hermes/skills/           # Bundled skills（官方管理）
├── apple/
├── github/
├── creative/
└── ...（24个官方分类）

Git 仓库 (external_dirs):   # 自建技能（Git 版本控制）
/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills/
├── common/                 # 公共技能（所有Profile共享）
│   ├── web-fetcher/
│   ├── hermes-backup/
│   ├── hermes-custom-skills-setup/
│   ├── wiki-auto-save/
│   └── wiki-ingest/
├── mcn/                    # MCN 专用技能
│   ├── my-mcn-manager/
│   ├── mcn-content-writer/
│   ├── humanizer-zh/
│   ├── ai-image-generation/
│   └── ...（15个）
├── stock/                  # Stock 专用技能
│   ├── autonomous-trading/
│   ├── bear-market-strategy/
│   └── ...（6个）
└── third-party/            # 第三方技能（预留）
```

## 各 Profile external_dirs 配置

| Profile | external_dirs | 说明 |
|---------|---------------|------|
| **default** | common + third-party | 仅公共技能 |
| **mcn** | common + mcn + third-party | 公共 + MCN专用 |
| **stock** | common + stock + third-party | 公共 + Stock专用 |
| **code** | common + third-party | 仅公共技能 |

## 好处

1. **Profile 隔离**：各 Profile 只加载需要的技能，职责清晰
2. **公共共享**：common 目录一次更新，所有 Profile 同步
3. **专用独立**：mcn/stock 专用技能不污染其他 Profile
4. **第三方预留**：third-party 目录存放外部技能
5. **官方原生支持**：Hermes v0.13.0+ 的 external_dirs 机制

---

## 架构搭建流程（v2.0 - external_dirs）

### Step 1: 备份自建技能

```bash
mkdir -p ~/.hermes/backup_skills
cd /Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills
cp -r mcn ~/.hermes/backup_skills/
cp -r content ~/.hermes/backup_skills/
cp -r stock ~/.hermes/backup_skills/
cp -r devops/hermes-backup ~/.hermes/backup_skills/
cp -r devops/hermes-custom-skills-setup ~/.hermes/backup_skills/
cp -r note-taking/wiki-auto-save ~/.hermes/backup_skills/
cp -r note-taking/wiki-ingest ~/.hermes/backup_skills/
cp -r web/web-fetcher ~/.hermes/backup_skills/
```

### Step 2: 解除 symlink（如果有）

```bash
rm ~/.hermes/skills
```

### Step 3: 恢复标准 bundled skills

```bash
mkdir -p ~/.hermes/skills
# 从本地备份恢复或运行 hermes update
cp -r ~/.hermes/skills.local.bak/* ~/.hermes/skills/
```

### Step 4: 清理 Git 仓库

```bash
cd /Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills
# 移除所有 bundled skills 目录
git rm -r --cached software-development/ productivity/ yuanbao/ ...
rm -rf apple autonomous-ai-agents creative github ...  # 删除所有官方分类
# 只保留自建技能目录
```

### Step 5: 补全自建技能到 Git

```bash
cd ~/.hermes/backup_skills
cp -r mcn /Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills/
cp -r stock /Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills/
# ... 复制所有自建技能
```

### Step 6: 简化 .gitignore

```gitignore
# 系统文件
.DS_Store
**/*.pyc

# 运行时文件
skills/.usage.json
skills/.bundled_manifest
skills/.curator_state
```

### Step 7: 配置 external_dirs

```bash
# default profile
hermes config set skills.external_dirs '["/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills"]'

# mcn profile
hermes config set skills.external_dirs '["/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills"]' --profile mcn

# code profile
hermes config set skills.external_dirs '["/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills"]' --profile code

# stock profile
hermes config set skills.external_dirs '["/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills"]' --profile stock
```

### Step 8: 重启 Gateway 并验证

```bash
hermes gateway restart
hermes skills list | grep -E "mcn|stock|web-fetcher"
```

### Step 9: Git 提交

```bash
cd /Users/hy_timesky/backup/hermes_agent_bak/hermes-skills
git add -A
git commit -m "refactor: 重构技能库架构，仅保留自建技能"
git push origin master
```

---

## 自建技能列表（v3.0 - 按 Profile 分离）

### 公共技能（common/）- 5个

| 技能 | 说明 | 所有 Profile 共享 |
|------|------|------------------|
| web-fetcher | Web 抓取扩展 | ✓ |
| hermes-backup | Hermes 备份恢复 | ✓ |
| hermes-custom-skills-setup | 技能管理架构 | ✓ |
| wiki-auto-save | 知识库自动保存 | ✓ |
| wiki-ingest | 增量式 ingest | ✓ |

### MCN 专用技能（mcn/）- 15个

| 技能 | 说明 |
|------|------|
| my-mcn-manager | MCN 工作流总引导 |
| mcn-content-writer | 内容生成 |
| mcn-hotspot-research | 热点调研 |
| mcn-topic-selector | 选题分析 |
| mcn-wechat-publisher | 公众号发布 |
| mcn-zhihu-publisher | 知乎发布 |
| mcn-closed-loop-analysis | 闭环反馈分析 |
| mcn-feishu-push | 飞书推送 |
| mcn-workflow-fallback | 工作流降级 |
| mcn-multi-platform | 多平台分发 |
| wechat-analytics | 公众号数据分析 |
| wechat-analytics-browser | Browser 方式数据分析 |
| humanizer-zh | 去除 AI 写作痕迹 |
| ai-image-generation | AI 图片生成 |
| zhihu-favorites-sync | 知乎收藏夹同步 |

### Stock 专用技能（stock/）- 6个

| 技能 | 说明 |
|------|------|
| autonomous-trading | 自动交易系统 |
| bear-market-strategy | 空头市场策略 |
| portfolio-strategy-combination | 组合策略 |
| risk-monitoring-system | 风控系统 |
| financial-cache-operations | 金融缓存操作 |
| strategy-auto-test | 策略自动测试 |

**总计**：26个自建技能（common:5, mcn:15, stock:6）

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
category: common
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

### 1. external_dirs YAML 格式问题

`hermes config set` 命令有时会将列表存储为字符串而非 YAML 列表：

```yaml
# ❌ 错误格式（字符串）
external_dirs: '["/path/to/skills"]'

# ✅ 正确格式（列表）
external_dirs:
  - /path/to/skills
```

修复方法：
```bash
sed -i '' 's/external_dirs:.*$/external_dirs:\n    - \/path\/to\/skills/' ~/.hermes/config.yaml
```

### 2. 不要用 symlink 替代 external_dirs

v0.13.0+ 有官方 external_dirs 支持，不要再用 symlink：

```bash
# ❌ 旧方案（已废弃）
ln -s /backup/skills ~/.hermes/skills

# ✅ 新方案
hermes config set skills.external_dirs '["/backup/skills"]'
```

### 3. Git 仓库不要包含 bundled skills

Git 仓库只保留自建技能，不要跟踪官方技能：

```bash
# ❌ 错误 - 会污染 Git 仓库
git add skills/github/
git add skills/creative/

# ✅ 正确 - 只提交自建技能
git add skills/mcn/
git add skills/stock/
```

### 4. 多 Profile 需各自配置 external_dirs

每个 Profile 都需要单独配置 external_dirs：

```bash
hermes config set skills.external_dirs '["/path"]' --profile mcn
hermes config set skills.external_dirs '["/path"]' --profile code
hermes config set skills.external_dirs '["/path"]' --profile stock
```

### 5. 备份脚本调整

备份脚本 (`backup_hermes.py`) 需要调整路径：

```python
# 旧方案：备份 symlink 目录
# 新方案：直接备份 Git 仓库
GIT_SKILLS = "/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills"
```

### 6. Gateway 重启后验证

每次架构变更后都要重启 Gateway 并验证技能加载：

```bash
hermes gateway restart
hermes skills list | grep -E "mcn|stock|web-fetcher"
```

### 7. 技能 category 字段必须与目录匹配

v3.0 后技能 category 必须与所在目录匹配：

```yaml
# common/web-fetcher/SKILL.md
category: common

# mcn/humanizer-zh/SKILL.md
category: mcn

# stock/autonomous-trading/SKILL.md
category: stock
```

### 8. 新建技能需确认归属目录

创建新技能时需确定归属：

| 技能类型 | 归属目录 | 可见 Profile |
|----------|----------|--------------|
| 所有 Profile 共享 | common/ | default, mcn, stock, code |
| MCN 专用 | mcn/ | 仅 mcn |
| Stock 专用 | stock/ | 仅 stock |
| 第三方 | third-party/ | 需配置的 Profile |

### 9. default Profile 不含专用技能

default 和 code Profile 只有 common + third-party，无专用技能：

```bash
# 验证 default 不含 mcn/stock 专用技能
hermes skills list | grep -E "mcn-content|autonomous-trading"
# 应为 0 个匹配
```

---

## 相关文件（v3.0）

- Git 仓库：`/Users/hy_timesky/backup/hermes_agent_bak/hermes-skills/skills/`
- Bundled skills：`~/.hermes/skills/`（24个官方分类）
- external_dirs 配置：各 Profile 的 `config.yaml`
  - default: `common/ + third-party/`
  - mcn: `common/ + mcn/ + third-party/`
  - stock: `common/ + stock/ + third-party/`
  - code: `common/ + third-party/`
- 备份目录：`~/.hermes/backup_skills_v3/`
- GitHub：`git@github.com:timesky/hermes-skills.git`

---

## 架构版本历史

| 版本 | 日期 | 方案 | 说明 |
|------|------|------|------|
| v1.0 | 2026-04-13 | Symlink 整体方案 | `~/.hermes/skills` symlink 到 Git 仓库 |
| v2.0 | 2026-05-10 | external_dirs 方案 | Bundled skills + Git 仓库分离，官方原生支持 |
| v3.0 | 2026-05-10 | **Profile 分离目录** | 按 common/mcn/stock/third-party 分离，各 Profile 独立配置 |

---

*Created: 2026-04-13 by Luna*  
*Updated: 2026-04-30 - 添加官方 Overlay 方案调研、Profile 隔离架构*  
*Updated: 2026-05-10 - v2.0 架构重构，切换到 external_dirs 方案*  
*Updated: 2026-05-10 - v3.0 架构重构，按 Profile 分离技能目录*