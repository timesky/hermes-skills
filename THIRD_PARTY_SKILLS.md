# 必备第三方技能列表

精选高质量的开源 Hermes/Claude Agent 技能，按类别整理。

---

## 官方技能

### Anthropic Skills (anthropics/skills)

| 技能 | 分类 | 说明 | 链接 |
|------|------|------|------|
| `docx` | Document | Word 文档创建和编辑 | [GitHub](https://github.com/anthropics/skills/tree/main/skills/docx) |
| `pdf` | Document | PDF 文件处理和内容提取 | [GitHub](https://github.com/anthropics/skills/tree/main/skills/pdf) |
| `pptx` | Document | PowerPoint 演示文稿创建 | [GitHub](https://github.com/anthropics/skills/tree/main/skills/pptx) |
| `xlsx` | Document | Excel 电子表格处理 | [GitHub](https://github.com/anthropics/skills/tree/main/skills/xlsx) |
| `skill-creator` | Development | 技能创建和优化工具 | [GitHub](https://github.com/anthropics/skills/tree/main/skills/skill-creator) |

**安装方式**:
```bash
# Claude Code
/plugin install document-skills@anthropic-agent-skills
```

---

## 社区技能

### Hermes Agent Skills

| 技能 | 分类 | 说明 | 链接 |
|------|------|------|------|
| `web-fetcher` | Web | Chrome 扩展 + WebSocket 抓取网页内容 | [GitHub](https://github.com/hermes-agent/skills) |
| `zhihu-collection-fetcher` | Web | 知乎收藏夹文章抓取 | [GitHub](https://github.com/hermes-agent/skills) |
| `opencli-browser-api` | Web | OpenCLI browser HTTP API | [GitHub](https://github.com/hermes-agent/skills) |

---

## 推荐技能

### 文档处理

| 技能 | 说明 | 来源 |
|------|------|------|
| `nano-pdf` | PDF 自然语言编辑 | Hermes 内置 |
| `ocr-and-documents` | OCR 和文档文本提取 | Hermes 内置 |

### 开发工具

| 技能 | 说明 | 来源 |
|------|------|------|
| `github-pr-workflow` | GitHub PR 完整流程 | Hermes 内置 |
| `github-code-review` | GitHub 代码审查 | Hermes 内置 |
| `test-driven-development` | TDD 开发流程 | Hermes 内置 |
| `systematic-debugging` | 系统化调试流程 | Hermes 内置 |

### 数据科学

| 技能 | 说明 | 来源 |
|------|------|------|
| `jupyter-live-kernel` | Jupyter 实时内核执行 | Hermes 内置 |

### MLOps

| 技能 | 说明 | 来源 |
|------|------|------|
| `huggingface-hub` | HuggingFace Hub CLI | Hermes 内置 |
| `peft-fine-tuning` | 参数高效微调 | Hermes 内置 |
| `llama-cpp` | llama.cpp GGUF 量化 | Hermes 内置 |

### 生产力

| 技能 | 说明 | 来源 |
|------|------|------|
| `notion` | Notion API 集成 | Hermes 内置 |
| `linear` | Linear 问题追踪 | Hermes 内置 |
| `google-workspace` | Google Workspace 集成 | Hermes 内置 |

### 研究

| 技能 | 说明 | 来源 |
|------|------|------|
| `arxiv` | arXiv 论文搜索 | Hermes 内置 |
| `llm-wiki` | Karpathy LLM Wiki 模式 | Hermes 内置 |
| `blogwatcher` | 博客/RSS 监控 | Hermes 内置 |

### 媒体

| 技能 | 说明 | 来源 |
|------|------|------|
| `youtube-content` | YouTube 字幕提取和转换 | Hermes 内置 |
| `gif-search` | Tenor GIF 搜索 | Hermes 内置 |

### 社交网络

| 技能 | 说明 | 来源 |
|------|------|------|
| `xitter` | X/Twitter CLI 集成 | Hermes 内置 |

---

## 技能发现渠道

1. **anthropics/skills** - 官方技能仓库，112k+ stars
   - https://github.com/anthropics/skills

2. **Hermes Agent Skills** - Hermes 社区技能
   - https://github.com/hermes-agent/skills

3. **Awesome Claude Code** - Claude Code 资源集合
   - https://github.com/jtremback/awesome-claude-code

4. **agentskills.io** - Agent Skills 规范和信息
   - https://agentskills.io/

---

## 添加标准

添加到本列表的技能应满足：

- ✅ 高质量实现，经过测试
- ✅ 清晰的文档和使用说明
- ✅ 活跃的维护状态
- ✅ 对 Hermes 用户有实际价值
- ✅ 开源许可证明确

---

## 更新记录

### 2026-04-12

- 初始版本
- 添加 Anthropic 官方技能
- 添加 Hermes 内置推荐技能
- 添加技能发现渠道

---

*Last updated: 2026-04-12*
*维护者：TimeSky*