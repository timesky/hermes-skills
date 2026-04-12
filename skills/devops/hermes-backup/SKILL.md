---
name: hermes-backup
description: Hermes Agent 完整备份与恢复技能，支持快速恢复和跨机器迁移
version: 1.0
created: 2026-04-12
author: Luna
---

# hermes-backup

Hermes Agent 完整备份与恢复技能，确保可以快速恢复或迁移到新机器。

---

## 备份范围

| 类型 | 路径 | 备份 | 说明 |
|------|------|------|------|
| 配置文件 | config.yaml | ✅ | 核心配置（模型、工具集等） |
| 环境变量 | .env | ✅ | API keys（备份时脱敏显示） |
| Persona | SOUL.md | ✅ | Luna 人格定义 |
| 认证凭证 | auth.json | ✅ | OAuth 凭证 |
| 自研技能 | skills/* | ✅ | 用户开发的技能 |
| 开源技能 | skills/* | ❌ | 恢复时通过 `hermes skills install` 重装 |
| 长期记忆 | memories/ | ✅ | MEMORY.md, USER.md |
| 自定义脚本 | scripts/ | ✅ | backup_hermes.py 等 |
| Cron 任务 | cron/ | ✅ | 定时任务配置 |
| 会话历史 | sessions/ | ❌ | 可选（太大） |

---

## 备份目录结构

```
/Users/timesky/backup/hermes_agent_bak/
├── YYYY-MM-DD/                    # 每日备份
│   ├── manifest.json              # 备份清单
│   ├── config.yaml                # 配置
│   ├── .env                       # 环境变量
│   ├── SOUL.md                    # Persona
│   ├── auth.json                  # OAuth 凭证
│   ├── memories/                  # 记忆
│   │   ├── MEMORY.md
│   │   └── USER.md
│   ├── scripts/                   # 脚本
│   ├── skills/                    # 自研技能
│   │   └── note-taking/wiki-auto-save/
│   │   └── web/web-fetcher/
│   └── cron/                      # Cron 任务
└── latest/                        # 最新备份软链接
└── restore_guide.md               # 恢复指南
```

---

## 备份流程

### 1. 执行备份脚本

```bash
python3 ~/.hermes/scripts/backup_hermes.py
```

### 2. 备份脚本功能

1. **创建备份目录**：`YYYY-MM-DD/`
2. **复制配置文件**：config.yaml, .env, SOUL.md, auth.json
3. **备份自研技能**：扫描 skills 目录，备份非官方技能
4. **备份记忆**：复制 memories/ 目录
5. **备份脚本**：复制 scripts/ 目录
6. **备份 Cron 配置**：复制 cron/ 目录
7. **生成 manifest.json**：记录备份内容清单
8. **生成 restore_guide.md**：恢复指南
9. **更新 latest 软链接**
10. **清理旧备份**：保留最近 7 天

### 3. 自研技能识别

通过以下规则识别自研技能：

- 技能目录中存在 `scripts/` 子目录
- 技能目录中存在自定义文件
- 不在官方技能列表中

---

## 恢复流程

### 本机恢复

```bash
python3 ~/.hermes/scripts/restore_hermes.py --backup latest
```

### 新机器迁移

1. **安装 Hermes Agent**
   ```bash
   pip install hermes-agent
   hermes setup
   ```

2. **复制备份文件**
   ```bash
   # 从备份位置复制到 ~/.hermes/
   scp backup/hermes_agent_bak/latest/* ~/.hermes/
   ```

3. **执行恢复脚本**
   ```bash
   python3 ~/.hermes/scripts/restore_hermes.py --backup latest --migrate
   ```

4. **重装开源技能**
   ```bash
   # 查看原机器的技能列表
   cat ~/.hermes/manifest.json | jq '.skills.installed'
   
   # 安装所需技能
   hermes skills install <skill-name>
   ```

5. **环境检测**
   ```bash
   python3 ~/.hermes/scripts/restore_hermes.py --check-env
   ```

---

## 恢复脚本功能

### --backup <path>
指定备份路径（默认 latest）

### --migrate
新机器迁移模式，会：
- 创建必要的目录结构
- 设置权限
- 不覆盖已存在的文件

### --check-env
环境检测，检查：
- Python 版本
- 必要的依赖包
- 技能依赖的外部工具
- API keys 是否配置

### --skills-only
只恢复技能（用于技能单独恢复）

---

## 环境检测清单

恢复后需要检测的环境：

| 依赖 | 检查方式 | 说明 |
|------|----------|------|
| Python 3.10+ | `python3 --version` | Hermes 运行基础 |
| hermes CLI | `hermes --version` | 主程序 |
| curl/jq | `curl --version` | 技能常用工具 |
| git | `git --version` | GitHub 技能 |
| ffmpeg | `ffmpeg -version` | 音视频技能 |
| pandoc | `pandoc --version` | 文档转换 |
| pyfiglet | `pip show pyfiglet` | ASCII 艺术技能 |
| faster-whisper | `pip show faster-whisper` | STT 技能 |

---

## Pitfalls

1. **API keys 安全**：
   - .env 文件包含敏感信息，备份时注意存储安全
   - 不要将备份上传到公开位置

2. **技能依赖**：
   - 自研技能可能有外部依赖（Python 包、CLI 工具）
   - 恢复时需要检测并安装这些依赖

3. **Cron 任务**：
   - Cron 任务恢复后需要重启 Gateway
   - `hermes gateway restart`

4. **会话历史**：
   - 会话历史默认不备份（太大）
   - 如需备份，使用 `--include-sessions`

5. **开源技能**：
   - 开源技能不备份，只记录列表
   - 恢复时需要重新安装

---

## 自建技能软连接架构

自建技能通过软连接管理，确保修改自动同步到 Git 仓库。

### 目录结构

```
/Users/timesky/backup/hermes_agent_bak/hermes-skills/  # Git 仓库（技能源文件）
├── skills/
│   ├── mcn/                     # 分类目录
│   │   ├── wechat-mp-auto-publish/  # 技能源文件
│   │   ├── mcn-hotspot-aggregator/
│   │   └── ...
│   ├── note-taking/
│   ├── devops/
│   └── software-development/

~/.hermes/skills/                 # Hermes 技能目录
├── mcn/
│   ├── wechat-mp-auto-publish → 软连接 → hermes-skills/skills/mcn/wechat-mp-auto-publish
│   ├── mcn-hotspot-aggregator → 软连接
│   └── ...
├── research/                     # 官方技能（普通目录，不是软连接）
│   ├── arxiv/
│   └── llm-wiki/
```

### 创建新技能流程

1. **在 Git 仓库中创建**：
   ```bash
   cd /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills
   mkdir -p <category>/<skill-name>
   # 编写 SKILL.md 和相关文件
   ```

2. **创建软连接**（只链接单个技能目录，不是整个分类）：
   ```bash
   ln -s /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills/<category>/<skill-name> ~/.hermes/skills/<category>/<skill-name>
   ```

3. **提交到 Git**：
   ```bash
   cd /Users/timesky/backup/hermes_agent_bak/hermes-skills
   git add skills/<category>/<skill-name>
   git commit -m "添加新技能: <skill-name>"
   git push
   ```

### 重要注意事项

| 规则 | 说明 |
|------|------|
| **只链接单个技能目录** | `ln -s .../skills/<category>/<skill-name>` 不是 `ln -s .../skills` |
| **不要删除整个分类** | 官方技能在分类目录中，删除整个分类会丢失官方技能 |
| **恢复备份** | 官方技能丢失时可从 `skills.local.bak` 恢复 |
| **备份仓库清理** | Git 仓库只保留自建技能，不包含官方技能 |

### 当前自建技能软连接列表（共 9 个）

| 技能 | 软连接状态 |
|------|------------|
| mcn/wechat-mp-auto-publish | ✅ 入口技能 |
| mcn/mcn-hotspot-aggregator | ✅ 热搜抓取 |
| mcn/mcn-topic-selector | ✅ 选题分析 |
| mcn/mcn-content-rewriter | ✅ 内容改写 |
| mcn/mcn-wechat-publisher | ✅ 公众号发布 |
| note-taking/wiki-auto-save | ✅ 自动保存 |
| note-taking/wiki-ingest | ✅ 增量式 ingest |
| devops/hermes-backup | ✅ 备份恢复 |
| software-development/skill-optimizer | ✅ Skill 优化 |

---

## 相关

- `wiki-auto-save`: 知识库自动保存
- `hermes-agent`: Hermes 使用指南