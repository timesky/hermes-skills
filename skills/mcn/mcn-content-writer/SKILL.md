---
name: mcn-content-writer
description: |
  MCN 内容生成技能 - 根据选题生成公众号文章，自动去 AI 化。
  
  触发词：内容生成、文章生成、mcn文章、写公众号文章
  
  可独立调用，也可被 my-mcn-manager 在阶段3调度。
parent: my-mcn-manager
tags: [mcn, content, writer, article, humanizer]
version: 1.3.0
created: 2026-04-15
updated: 2026-04-16
---

# MCN 内容生成

根据选题生成公众号文章（1500-2000字），自动调用 humanizer-zh 去 AI 化。

---

## 功能闭环与产出交付

**职责**：独立完成内容生成阶段所有工作。

| 项目 | 说明 |
|------|------|
| 输入 | `--topic {选题标题}` |
| 产出位置 | `mcn/content/{date}/{slug}/article.md` |
| 产出要求 | 1500-2000字，去AI化完成 |
| 状态返回 | `{"status": "success", "output_path": "...", "topic_slug": "...", "word_count": ...}` |

**衔接机制**：
- 下游技能 `ai-image-generation` 使用相同 `topic` → 配图产出到同目录 `images/`
- 不需要参数传递，约定优于配置

**验证要求**：
- 字数达标（1500-2000）
- 去 AI 化完成
- 文件路径正确

---

## 配置来源

**约定优于配置 + 技能独立性**

- 配置文件：`~/.hermes/mcn_config.yaml`（唯一外部依赖）
- 目录约定：脚本内联解析，不依赖其他技能模块
- 模板文件：本技能目录 `templates/content-templates.md`
- 输出目录：`mcn/content/{date}/{slug}/article.md`

脚本不导入其他技能目录下的模块。详见入口技能 `references/config.md`。

---

## 触发场景

| 用户输入 | 响应 |
|----------|------|
| "内容生成" | 根据选题生成文章 |
| "写公众号文章" | 生成并去 AI 化 |
| "生成文章" | 生成文章内容 |

---

## 核心流程

```
选题 → 内容生成 → 去 AI 化 → 排版 → 配图 → 发布
```

### 完整工作流（用户要求）

| 步骤 | 脚本 | 功能 |
|------|------|------|
| **1. 内容生成** | `run-content-gen.py` | 根据选题生成文章（1500-2000字） |
| **2. 去 AI 化** | `humanize-article.py` | 自动调用，评分≥45为达标 |
| **3. 排版** | `layout-article.py` | 标题竞选 → 美化 → 图片锚点 → 固定尾部 |
| **4. 配图** | `generate-images.py` | 首图 + 2张段落图（豆包API） |
| **5. 发布** | `publish-draft.py` | 上传到公众号草稿箱 |

---

### 1. 内容生成

- 字数要求：1500-2000 字
- 人设：科技从业者视角
- 风格：客观分析 + 口语化表达
- **自动调用去 AI 化**（无需用户提醒）

### 2. 去 AI 化（自动执行）

**流程**：生成文章后自动调用 `humanize-article.py`

**评分标准**：
- ≥45分：达标，可直接发布
- <45分：建议人工审核

**处理内容**：
- 删除：编号列表、抽象分析句、结尾互动句、模板化表达
- 变化：句子长度（长短交替）、添加个人观点、口语化表达

### 3. 排版流程（layout-article.py）

| 功能 | 说明 |
|------|------|
| **标题竞选** | 生成5个候选标题，自动评估选择最佳 |
| **美化样式** | 转换为公众号 HTML 格式（标题、正文、引用） |
| **图片锚点** | 自动去掉标签建议，3张图均匀分布 |
| **固定尾部** | 添加关注公众号模板（在总结语之后） |

**图片分布规则**（均匀分布）：
- 封面图（IMG_0）：标题后作为首图（双重用途：公众号封面 + 文章首图）
- 段落图1（IMG_1）：文章前 1/3 位置
- 段落图2（IMG_2）：文章后 1/3 位置（总结段落之前）

**自动处理**：
- 自动去掉文章末尾的 `## 标签建议` 部分
- 过滤空段落和分隔线
- 根据段落总数动态计算图片位置

**固定尾部模板**：
```
如果觉得有用，点个「在看」支持一下 👇
关注「{公众号名称}」
分享技术干货 · 聊聊行业观察 · 记录成长思考
```

### 4. 配图生成（generate-images.py）

**数量**：每篇 3 张（封面图 + 2 张段落图）

**⚠️ 配图保护机制**：
- **已有配图时自动跳过**，不会覆盖
- 使用 `--force` 参数强制重新生成
- 配图目录：`mcn/content/{date}/{slug}/images/`

**图片用途**：
- cover.png（900x500px）：公众号封面 + 文章首图（双重用途）
- img_1.png：段落图1（前 1/3）
- img_2.png：段落图2（后 1/3）

**提示词设计**：
- 豆包用中文提示词（解决 GrsAI 乱码问题）
- 段落图从段落内容提取关键词，生成差异化提示词

### 5. 字数验证

如果字数 < 1500：
- 自动补充内容（最多 2 次）
- 报告最终字数

---

## 输出

```
文章保存到：mcn/content/{date}/{slug}/article.md

同时创建空目录：mcn/content/{date}/{slug}/images/
（供下游配图技能使用）
```

---

## 配图规则（重要）

**数量**：每篇 3 张（封面图 + 2 张段落图）

**流程**：
```
先排版 → 确定段落图位置 → 根据段落内容摘要生成配图
```

**图片分布**（均匀分布）：
- cover.png（900x500px）：公众号封面 + 文章首图（双重用途）
- img_1.png：文章前 1/3 位置，根据段落内容摘要生成
- img_2.png：文章后 1/3 位置（总结段落之前），根据段落内容摘要生成

**提示词设计**：
- 封面图：`{主题} 概念插画，科技氛围，专业设计，高质量`
- 段落图：从段落提取关键词，生成差异化提示词

---

## 模板系统

**模板文件**：`templates/content-templates.md`（本技能目录）

包含5种文章类型的改写模板：

| 类型 | 模板编号 | 适用场景 |
|------|----------|----------|
| 热点评论 | T-01 | 社会事件、科技新闻 |
| 干货教程 | T-02 | 技术分享、工具使用 |
| 行业分析 | T-03 | 市场趋势、公司动态 |
| 故事叙述 | T-04 | 个人经历、创业故事 |
| 观点争议 | T-05 | 行业争议、技术选型 |

**自动识别逻辑**（`detect_article_type()`）：
- 包含「教程、方法、如何、步骤」→ 干货教程
- 包含「分析、市场、趋势、估值」→ 行业分析
- 包含「争议、质疑、之争、撕」→ 观点争议
- 包含「经历、故事、创业、背后」→ 故事叙述
- 默认 → 热点评论

---

## 执行方式

**脚本目录**：`mcn-content-writer/scripts/`
- `run-content-gen.py` - 主脚本（使用模板系统）
- `generate-images.py` - 配图生成（调用 ai-image-generation API）
- `humanize-article.py` - 去 AI 化处理
- `validate-article.py` - 文章验证

```bash
# Terminal 直接执行 - 内容生成
eval "$(pyenv init -)" && python3 ~/.hermes/skills/mcn/mcn-content-writer/scripts/run-content-gen.py --topic "选题标题"

# Terminal 直接执行 - 配图生成
eval "$(pyenv init -)" && python3 ~/.hermes/skills/mcn/mcn-content-writer/scripts/generate-images.py --topic "选题标题" --date 2026-04-15 --count 4
```

---

## 文章结构

```markdown
---
title: 文章标题（15-25字）
created: 2026-04-15
source: 原文链接
---

# 标题

开头：引出话题（2-3句）

正文：分析现象、案例、观点（自然分段）

结尾：总结观点（不使用互动句）
```

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| ~~run-content-gen.py 是占位实现~~ | ✅ **已修复**(2026-04-21)：脚本现已调用 DashScope API（glm-5）。注意：`coding.dashscope.aliyuncs.com` **只支持 glm-5**，不支持通义系列 |
| **DashScope API 模型限制** | `coding.dashscope.aliyuncs.com` endpoint 只支持 `glm-5`，不支持 qwen-plus/qwen-turbo。如需用通义，需申请标准 DashScope API Key |
| **f-string JSON 转义** | f-string 中 JSON 花括号需双写：`{{\"key\": \"value\"}}`，否则报 `Invalid format specifier` |
| 字数不足 | 自动补充功能失效时，需人工补充到1500-2000字 |
| 去 AI 化不彻底 | 检查 humanizer-zh 是否正确调用 |
| 原文抓取失败 | **推荐 web-fetcher**（OpenCLI 有 Node undici 错误）。用法：`client.fetch_article(tab_id)` 返回 `{title, content}`。参见 web-fetcher 技能 |
| **publish-draft 图片命名** | 必须使用特定格式：`cover.png`（封面）+ `img_1.png`, `img_2.png`（段落图）。脚本自动在20%、40%位置插入图片。文章内不需要 `![]` 图片引用，脚本处理图片插入 |
| **配图提示词雷同** | generate-images.py 必须传 `--article` 参数，否则配图只用主题标题导致雷同。正确调用：`generate-images.py --topic "X" --article ARTICLE_PATH --date DATE --count 4` |
| **publish-draft topic 参数** | `--topic` 参数必须使用 slugify 后的目录名（如 `特斯拉-Optimus-机器人最新进展曝光`），而非原始标题（含空格）。否则路径匹配失败，封面图找不到 |
| **layout-article.py 覆盖标题** | 排版脚本会用 slug 名称生成模板标题（如「3个关键点，让你看懂ai-tutor-globalization」），覆盖原标题。**解决方案**：排版后手动用 sed 修改 HTML + patch 恢复 article.md 标题，或脚本需增加 `--skip-title-election` 参数 |
| **generate-images.py 目录名** | 配图脚本用 `--topic` 参数值（中文主题名）创建目录，而非 slug。导致图片保存到 `AI导师全球化浪潮/images/` 而非 `ai-tutor-globalization/images/`。**解决方案**：生成后手动移动图片到正确目录 |
| **参数命名不一致** | `humanize-article.py` 用 `--input`，其他脚本用 `--article`。调用时需注意区分 |
| GrsAI 生成慢 | 每张图片需 2-5 分钟，4 张并发可能超时（轮询300s）。task_id 已记录，可用 `curl -X POST grsai/v1/draw/result -d '{"id":"TASK_ID"}'` 找回 |
| OpenCLI Node 版本 | 必须用 Node v20（v22 有 undici 错误），执行前先 `nvm use 20` |

## 备用方案（脚本失效时）

```bash
# 1. 用 OpenCLI 抓取原文
opencli web read --url "https://www.huxiu.com/article/XXX.html" --output /tmp/article

# 2. 读取原文
cat /tmp/article/*/content.md

# 3. 人工撰写文章（1500-2000字，科技从业者视角）
# 4. 发布草稿
python scripts/publish-draft.py --article ARTICLE_PATH --date DATE --images IMAGE_PATHS
```

---

## 相关技能

- **mcn-topic-selector** - 上游技能，提供选题
- **humanizer-zh** - 去 AI 化（L3 通用技能）
- **ai-image-generation** - 下游技能，从同目录 images/ 产出配图
- **my-mcn-manager** - 父技能

---

*Version: 1.1.0 - 功能闭环 + 产出交付规范*