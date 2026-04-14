---
created: 2026-04-13
sources:
  - raw/sources/2026-04-13/4款github开源ai技能视频剪辑文本去ai化小红书发布与技能管理工具.md
  - raw/sources/2026-01-23-4款GitHub开源AI技能视频剪辑文本去AI化小红书发布与技能管理工具.md
tags: [ai-skills, github, automation, content-creation]
---

# AI Skills Toolkit 2026

## 概述

2026 年流行的 4 款 GitHub 开源 AI 技能工具，涵盖视频剪辑、文本去 AI 化、小红书发布和技能管理。

## 工具列表

### 1. videocut-skills（视频剪辑）

**开源地址**: https://github.com/Ceeon/videocut-skills

自动识别视频中的口误、静音片段、语气词等冗余内容，通过简单指令自动处理。

**功能特点**:
- Whisper 模型生成字幕 + 词典纠错
- FFmpeg 底层剪辑操作
- 自我更新能力，优化剪辑规则

**安装**:
```bash
git clone https://github.com/Ceeon/videocut-skills.git ~/.claude/skills/videocut
```

**使用**:
打开 Claude Code，输入 `/videocut:安装`，AI 会自动安装依赖并下载模型。

---

### 2. Humanizer-zh（去除 AI 味道）

**开源地址**: https://github.com/op7418/Humanizer-zh

基于维基百科 AI 写作特征指南，消除文本中的 AI 生成痕迹。

**检测维度**: 内容、语言语法、风格、交流模式

**核心特点**:
- 基于维基百科的"AI 写作特征"研究
- 识别并消除 AI 生成文本的特征
- 使文本听起来更自然、更像人类书写
- 支持多种文本类型处理

**安装**:
```bash
git clone https://github.com/op7418/Humanizer-zh.git ~/.claude/skills/humanizer-zh
```

> 📝 Hermes Agent 已集成此技能，可直接使用 `/humanizer-zh` 命令。

---

### 3. Auto-Redbook-Skills（小红书发布）

**开源地址**: https://github.com/comeonzhj/Auto-Redbook-Skills

辅助撰写、制作并发布小红书笔记，结合内容生成与视觉渲染技术。

**功能特点**:
- 自动化登录小红书
- 内容格式化适配
- 图片上传
- 发布流程自动化
- Playwright 渲染 Markdown 为精美图片
- 支持自定义背景渐变和封面样式

---

### 4. add-skill（技能安装工具）

**开源地址**: https://github.com/vercel-labs/add-skill

Vercel Labs 开发的命令行工具，用于将 Skill 安装到 Claude Code、Codex、Cursor 等编程 AI 助手。

**功能特点**:
- 从 GitHub 项目提取并配置 Skill 文件
- 自动识别标准化配置文件
- 一行命令完成安装
- 创建新的 Skills
- 更新现有 Skills
- 删除不需要的 Skills
- Skills 版本管理
- Skills 依赖管理

---

## 相关

- [[humanizer-zh]] - Hermes 已集成的文本去 AI 化技能
- [[claude-code]] - Claude Code CLI 编程助手
- [[hermes-agent]] - Hermes Agent 技能系统
- [[ai-programming-tools]] - AI 编程工具综述

## 来源

- [4款GitHub开源AI技能](../../raw/sources/2026-04-13/4款github开源ai技能视频剪辑文本去ai化小红书发布与技能管理工具.md) - 鲸林向海 (2026-04-13)
- [4款GitHub开源AI技能](../../raw/sources/2026-01-23-4款GitHub开源AI技能视频剪辑文本去AI化小红书发布与技能管理工具.md) - 鲸林向海 (2026-01-23)