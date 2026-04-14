# 文档摄取报告

## 元数据

| 属性 | 值 |
|------|-----|
| 创建日期 | 2026-01-23 |
| 来源 | 鲸林向海 |
| 作者 | 鲸栖 |
| 原始链接 | https://www.itsolotime.com/archives/19109 |
| 标签 | AI技能, GitHub开源, 文本处理, 自动化工具, 视频剪辑 |
| 原始文件 | 2026-01-23-4款GitHub开源AI技能视频剪辑文本去AI化小红书发布与技能管理工具.md |
| 处理时间 | 2026-04-13 |

---

## 文档摘要

本文介绍了4款GitHub开源的AI技能工具，涵盖视频剪辑、文本去AI化、小红书自动发布和技能管理等功能。这些工具旨在帮助内容创作者提高工作效率，实现自动化流程。

---

## 核心内容

### 1. 视频剪辑 Skill (videocut-skills)

**功能特点：**
- 自动识别视频中的口误、静音片段、语气词等冗余内容
- AI自动处理这些片段，提高剪辑效率
- 集成Whisper模型生成字幕，支持词典纠错
- 使用FFmpeg进行底层视频剪辑
- 具备自我更新能力，可根据使用习惯优化规则

**适用场景：** 口播类视频创作者

**使用方法：**
```bash
# 克隆仓库
git clone https://github.com/Ceeon/videocut-skills.git ~/.claude/skills/videocut

# 在Claude Code中安装
/videocut:安装
```

---

### 2. 文本去AI化 Skill

**核心特点：**
- 基于维基百科的"AI写作特征"研究
- 识别并消除AI生成文本的特征
- 使文本更自然、更像人类书写
- 支持多种文本类型处理

**应用场景：** 需要降低文本AI痕迹的场景

---

### 3. 小红书发布 Skill

**主要功能：**
- 自动化登录小红书
- 内容格式化适配
- 图片上传
- 发布流程全自动化

**目标：** 实现从小红书登录到发布的完整自动化

---

### 4. 技能管理工具

**功能列表：**
- 创建新的Skills
- 更新现有Skills
- 删除不需要的Skills
- Skills版本管理
- Skills依赖管理

---

## 关键信息提取

### GitHub仓库
- **videocut-skills**: https://github.com/Ceeon/videocut-skills

### 技术栈
- **Whisper**: 语音识别模型，用于生成字幕
- **FFmpeg**: 视频处理工具
- **Claude Code**: AI开发环境

### 关键词
- AI Skills
- 自动化工作流
- 视频剪辑自动化
- 文本处理
- 社交媒体发布
- 开源工具

---

## 结构化数据

```yaml
tools:
  - name: 视频剪辑 Skill
    repo: videocut-skills
    github: https://github.com/Ceeon/videocut-skills
    features:
      - 口误识别
      - 静音片段处理
      - 字幕生成
      - 自我优化
    tech_stack:
      - Whisper
      - FFmpeg
      - Claude Code
    use_case: 口播类视频制作
    
  - name: 文本去AI化 Skill
    basis: 维基百科AI写作特征研究
    features:
      - AI特征识别
      - 文本人性化
      - 多类型文本支持
      
  - name: 小红书发布 Skill
    features:
      - 自动登录
      - 内容格式化
      - 图片上传
      - 自动发布
      
  - name: 技能管理工具
    features:
      - Skills创建
      - Skills更新
      - Skills删除
      - 版本管理
      - 依赖管理
```

---

## 使用建议

1. **视频创作者**：优先关注videocut-skills，可大幅提升口播视频剪辑效率
2. **内容营销人员**：小红书发布Skill可实现批量自动化发布
3. **AI内容优化**：文本去AI化工具适合需要降低AI痕迹的场景
4. **开发者**：技能管理工具便于维护和迭代多个Skills

---

*本报告由无技能baseline自动生成*