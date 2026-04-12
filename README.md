# Hermes Skills

Hermes Agent 技能仓库 - 自建技能 + 必备开源技能推荐

参考：[anthropics/skills](https://github.com/anthropics/skills)

---

## 目录结构

```
hermes-skills/
├── README.md                 # 本说明文件
├── THIRD_PARTY_SKILLS.md     # 必备开源技能列表
├── skills/                   # 技能目录
│   ├── note-taking/          # 知识库管理
│   │   ├── wiki-ingest/      # 增量式 ingest 流程
│   │   ├── wiki-auto-save/   # 自动保存到知识库
│   │   └── obsidian/         # Obsidian 集成
│   ├── mcn/                  # MCN 内容系统
│   │   ├── mcn-workflow/     # 完整工作流
│   │   ├── mcn-hotspot-aggregator/  # 热搜聚合
│   │   ├── mcn-topic-selector/      # 选题分析
│   │   ├── mcn-content-rewriter/    # 内容改写
│   │   └── mcn-wechat-publisher/    # 公众号发布
│   ├── content/              # 内容生成
│   │   └── wechat-mp-auto-publish/  # 公众号全自动发布
│   ├── software-development/ # 软件开发
│   │   ├── skill-optimizer/  # Skill 自动优化
│   │   └── skill-creator/    # Skill 创建工具
│   └── devops/               # 运维部署
│       └── hermes-backup/    # Hermes 备份恢复
└── templates/                # 技能模板
    └── SKILL.md.template     # 技能模板文件
```

---

## 自建技能

### note-taking (知识库管理)

| 技能 | 说明 | 状态 |
|------|------|------|
| `wiki-ingest` | 增量式 ingest 流程，将 raw 源文件转换为 wiki 结构化内容 | ✅ 维护中 |
| `wiki-auto-save` | 自动保存搜索内容到知识库 tmp 目录 | ✅ 维护中 |
| `obsidian` | Obsidian 集成，读取/搜索/创建笔记 | ✅ 稳定 |

### mcn (内容系统)

| 技能 | 说明 | 状态 |
|------|------|------|
| `mcn-workflow` | MCN 完整工作流 - 热搜聚合、选题分析、内容改写、发布 | ✅ 维护中 |
| `mcn-hotspot-aggregator` | 多平台热搜聚合（知乎、微博、抖音、小红书） | ✅ 维护中 |
| `mcn-topic-selector` | 选题分析，结合用户关注领域生成选题建议 | ✅ 维护中 |
| `mcn-content-rewriter` | 内容改写，生成适合公众号的多版本文章 | ✅ 维护中 |
| `mcn-wechat-publisher` | 公众号发布，浏览器自动化登录后台发草稿 | ✅ 维护中 |

### content (内容生成)

| 技能 | 说明 | 状态 |
|------|------|------|
| `wechat-mp-auto-publish` | 微信公众号全自动发布流程 | ✅ 维护中 |

### software-development (开发工具)

| 技能 | 说明 | 状态 |
|------|------|------|
| `skill-optimizer` | 使用 Autoresearch 方法自动优化 Hermes Skills | ✅ 维护中 |
| `skill-creator` | 创建/修改技能，运行 evals 测试 | ✅ 稳定 |

### devops (运维部署)

| 技能 | 说明 | 状态 |
|------|------|------|
| `hermes-backup` | Hermes Agent 完整备份与恢复 | ✅ 稳定 |

---

## 必备开源技能

详见 [THIRD_PARTY_SKILLS.md](./THIRD_PARTY_SKILLS.md)

推荐技能来源：
- [anthropics/skills](https://github.com/anthropics/skills) - Anthropic 官方技能
- [hermes-agent/skills](https://github.com/hermes-agent/skills) - Hermes 社区技能
- 其他高质量开源技能

---

## 使用方法

### 1. 克隆仓库

```bash
cd /Users/timesky/backup/hermes_agent_bak
git clone git@github.com:timesky/hermes-skills.git
```

### 2. 创建软连接

```bash
# 备份原有 skills 目录
mv ~/.hermes/skills ~/.hermes/skills.bak

# 创建软连接
ln -s /Users/timesky/backup/hermes_agent_bak/hermes-skills/skills ~/.hermes/skills
```

### 3. 验证

```bash
ls -la ~/.hermes/skills
# 应该看到指向 hermes-skills/skills 的软连接
```

---

## 开发流程

### 添加新技能

1. 在 `skills/<category>/<skill-name>/` 创建技能目录
2. 创建 `SKILL.md` 文件（参考模板）
3. 添加脚本/模板/资源文件
4. 测试技能功能
5. 提交到 GitHub

### 优化现有技能

1. 修改技能文件
2. 测试功能
3. 更新 `CHANGELOG.md`（如果有）
4. 提交到 GitHub：
   ```bash
   git add .
   git commit -m "优化：<技能名> - <改动说明>"
   git push
   ```

### 更新必备技能列表

1. 编辑 `THIRD_PARTY_SKILLS.md`
2. 添加新发现的优质技能
3. 提交到 GitHub

---

## 技能模板

参考 `templates/SKILL.md.template`

```markdown
---
name: skill-name
description: 清晰描述技能功能和触发条件
version: 1.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
author: 作者名
---

# 技能名称

技能说明和核心原则

---

## 完整流程

```
流程图或步骤说明
```

---

## Pitfalls

- 常见错误和注意事项

---

## 相关

- [[相关技能]]

---

*Created: YYYY-MM-DD*
```

---

## 许可证

- 自建技能：MIT License
- 第三方技能：遵循各自许可证

---

## 更新日志

### 2026-04-12

- 初始版本
- 迁移 note-taking 分类技能（wiki-ingest, wiki-auto-save, obsidian）
- 迁移 mcn 分类技能（完整工作流）
- 迁移 software-development 分类技能（skill-optimizer, skill-creator）
- 创建必备技能列表

---

*Last updated: 2026-04-12*