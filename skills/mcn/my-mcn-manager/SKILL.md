---
name: my-mcn-manager
description: |
  MCN 内容工作流总引导 - 入口技能，管理工作流集合和子技能调度。
  
  职责：
  1. 引导必要技能安装
  2. 定义工作流集合（当前：微信公众号发布流程）
  3. 作为入口引导用户完成任务
  4. 变更管理（新技能/改名/流程变更先修改此技能）
  5. 调度子技能，确保功能闭环和产出交付
  
  触发词：MCN、公众号、热点调研、选题分析、内容生成、执行MCN流程
tags: [mcn, workflow, orchestrator, entry-point]
version: 3.1.0
created: 2026-04-10
updated: 2026-04-16
---

# MCN 内容工作流总引导

**定位**：入口技能，不执行具体功能，只负责调度和引导。

---

## 职责定义

| 职责 | 说明 |
|------|------|
| 技能依赖管理 | 列出必要子技能，引导安装缺失技能 |
| 工作流集合 | 定义可用工作流（当前：微信公众号） |
| 用户引导 | 根据用户意图选择工作流，引导完成 |
| 变更管理 | 新技能/改名/流程变更必须先修改此技能 |
| 调度协调 | 调用子技能，确保功能闭环和产出交付 |

---

## 必要子技能

**安装前检查**：执行 MCN 流程前，确保以下技能已安装：

| 子技能 | 职责 | 安装检查 |
|--------|------|----------|
| mcn-hotspot-research | 热点调研，抓取多平台数据 | `~/.hermes/skills/mcn/mcn-hotspot-research/SKILL.md` |
| mcn-topic-selector | 选题分析，排除已发布，推荐 Top 5 | `~/.hermes/skills/mcn/mcn-topic-selector/SKILL.md` |
| mcn-content-writer | 内容生成，去 AI 化，字数验证 | `~/.hermes/skills/mcn/mcn-content-writer/SKILL.md` |
| humanizer-zh | 去 AI 化处理（被 content-writer 调用） | `~/.hermes/skills/content/humanizer-zh/SKILL.md` |
| ai-image-generation | 配图生成（被本技能调用） | `~/.hermes/skills/content/ai-image-generation/SKILL.md` |
| mcn-wechat-publisher | 微信公众号草稿发布 | `~/.hermes/skills/mcn/mcn-wechat-publisher/SKILL.md` |
| mcn-zhihu-publisher | 知乎专栏草稿保存（仅草稿） | `~/.hermes/skills/mcn/mcn-zhihu-publisher/SKILL.md` |

**缺失处理**：如果子技能缺失，提示用户安装：
```
"检测到 {技能名} 未安装，请先安装该技能后再执行 MCN 流程"
```

---

## 环境依赖

**执行前检查**：

| 依赖 | 用途 | 检查命令 | 安装命令 |
|------|------|----------|----------|
| Playwright | 热点调研（OpenCLI 备用方案） | `python3 -c "import playwright"` | `pip3 install playwright && playwright install chromium` |
| Node.js v20+ | OpenCLI（可选） | `node --version` | `brew install node@20` |
| Python 3.8+ | 所有脚本 | `python3 --version` | 系统自带 |

**⚠️ 注意**：OpenCLI 可能未安装或存在兼容性问题，Playwright 是必需的备用方案。

---

## 工作流集合

### 工作流 1：微信公众号发布（当前）

```
热点调研 → 选题分析 → 飞书推送 → 用户选择 → 内容生成 → 配图 → 发布草稿
```

| 阶段 | 子技能 | 产出交付 |
|------|--------|----------|
| 1 | mcn-hotspot-research | `mcn/hotspot/{date}/hotspot.json` |
| 2 | mcn-topic-selector | `mcn/topic/{date}/recommend.md` + 飞书推送 |
| 3 | 用户选择 | 用户指定选题标题 |
| 4 | mcn-content-writer | `mcn/content/{date}/{slug}/article.md`（1500-2000字） |
| 5 | ai-image-generation | `mcn/content/{date}/{slug}/images/*.png`（4张） |
| 6 | publish-draft（本技能脚本） | 公众号草稿 media_id |

### 工作流 2：知乎专栏发布

```
热点调研 → 选题分析 → 飞书推送 → 用户选择 → 内容生成 → 知乎草稿
```

| 阶段 | 子技能 | 产出交付 |
|------|--------|----------|
| 1-4 | 同工作流1 | 同工作流1 |
| 5 | mcn-zhihu-publisher | 知乎草稿 URL（⚠️ 仅草稿，不发布） |

**⚠️ 知乎安全约束**：
- 知乎无官方 API，使用浏览器自动化
- 仅保存草稿，用户需手动检查后发布
- 需 OpenCLI daemon（端口 19825）+ Node v20

### 工作流 3：其他渠道（预留）

后续可扩展：
- 小红书发布流程
- 抖音短视频流程
- B站视频流程

---

## 子技能交付规范

**每个子技能必须：**

1. **功能闭环**：独立完成本阶段所有工作
2. **产出明确**：输出文件到约定位置
3. **状态返回**：返回执行结果（成功/失败/产出路径）
4. **不跨技能依赖**：不导入其他技能模块，通过约定位置衔接

**交付格式**：

```python
# 子技能执行完成后返回
{
    "status": "success|failed",
    "output_path": "产出文件路径",
    "message": "简要说明"
}
```

---

## 调度方式

### 自动完整流程

用户说 `"执行 MCN 流程"` → 按工作流顺序调度所有阶段

### 跨会话恢复（新增）

**触发场景**：用户在新会话回复「继续MCN」或「选题X」

**恢复逻辑**：
```
1. 读取 mcn/workflow.json（锚点文件）
2. 检查 status 字段：
   - pending_user_choice → 用户选择选题，继续内容生成
   - topic_selected → 读取已选选题，继续内容生成
   - content_done → 继续配图生成
   - images_done → 继续发布草稿
3. 根据状态继续执行对应阶段
```

**用户选择选题时的处理流程**（由 Luna 主 agent 执行）：
```
用户: 选题1

Luna:
1. [读取锚点] mcn/workflow.json → status: pending_user_choice
2. [获取选题] recommendations[0] → "AI让人越来越累"
3. [更新锚点] 更新 workflow.json:
   - selected_topic = "AI让人越来越累"
   - status = "topic_selected"
   - last_updated = 当前时间
4. [继续流程] 调用 mcn-content-writer → 生成文章
```

**Luna 更新 workflow.json 的代码**：
```python
import json
from datetime import datetime

workflow_path = "~/backup/知识库-Obsidian/mcn/workflow.json"
with open(workflow_path, 'r') as f:
    workflow = json.load(f)

# 用户选择选题 X
topic_idx = int(user_input.replace("选题", "")) - 1
selected = workflow["recommendations"][topic_idx]

workflow["selected_topic"] = selected["title"]
workflow["status"] = "topic_selected"
workflow["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(workflow_path, 'w') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)
```

**状态流转完整链路**：
```
run-topic-analysis.py → status: "pending_user_choice"
Luna (用户选择) → status: "topic_selected"
run-content-gen.py → status: "content_done"
generate-images.py → status: "images_done"
publish-draft.py → status: "published"
```

**示例**：
```
用户: 选题1

Luna:
1. [读取锚点] mcn/workflow.json → status: pending_user_choice
2. [获取选题] recommendations[0] → "AI让人越来越累"
3. [更新状态] selected_topic = "AI让人越来越累", status = "topic_selected"
4. [继续流程] 调用 mcn-content-writer → 生成文章
```

### 单阶段触发

| 用户输入 | 调度子技能 |
|----------|-----------|
| `"热点调研"` | mcn-hotspot-research |
| `"选题分析"` | mcn-topic-selector |
| `"内容生成 {选题}"` | mcn-content-writer |
| `"配图 {选题}"` | ai-image-generation |
| `"发布草稿"` | publish-draft.py |
| `"知乎草稿"` | mcn-zhihu-publisher |
| `"发布到知乎"` | mcn-zhihu-publisher |

### 阶段间衔接

**通过约定位置衔接，不传递路径参数：**

```
热点调研产出：mcn/hotspot/{date}/
                ↓
选题分析读取：同上位置（约定）
                ↓
选题分析产出：mcn/topic/{date}/recommend.md
                ↓
内容生成读取：用户指定选题标题
                ↓
内容生成产出：mcn/content/{date}/{slug}/article.md
                ↓
配图读取：用户指定选题标题
                ↓
配图产出：mcn/content/{date}/{slug}/images/
                ↓
发布读取：用户指定文章路径
```

---

## 变更管理流程

**规则**：任何变更必须先修改此技能，再处理具体技能。

### 新技能加入

1. 在 `必要子技能` 表添加新技能
2. 在 `工作流` 表添加新阶段
3. 定义新技能的产出交付位置
4. 更新 `目录约定` 文档
5. 创建新技能 SKILL.md

### 技能改名

1. 在此技能更新子技能名称引用
2. 重命名子技能目录
3. 更新子技能 SKILL.md name 字段
4. 更新 `目录约定` 文档

### 流程变更

1. 在此技能更新工作流阶段顺序
2. 更新各子技能的产出交付位置（如需）
3. 更新 `目录约定` 文档

---

## 本技能自有脚本

以下脚本属于入口技能，不属于任何子技能：

| 脚本 | 说明 |
|------|------|
| generate-images.py | 配图生成（调用 ai-image-generation API） |
| poll-image-tasks.py | 配图任务轮询 |
| publish-draft.py | 发布草稿到公众号 |
| push-to-feishu.py | 推送选题报告到飞书 |

**这些脚本是工作流的"胶水"，连接子技能产出和最终输出。**

---

## 目录约定

详见：`references/config.md`

**核心约定**（所有子技能遵循）：

```
mcn/
├── hotspot/{date}/              # 阶段1产出
├── topic/{date}/                # 阶段2产出
├── content/{date}/{slug}/       # 阶段4产出
│   ├── article.md
│   └── images/                  # 阶段5产出
└── publish/                     # 发布记录
```

---

## 执行示例

### 完整流程

```
用户: 执行 MCN 流程

Luna:
1. [检查技能依赖] ✓ 所有子技能已安装
2. [阶段1] 调用 mcn-hotspot-research → 产出热点数据
3. [阶段2] 调用 mcn-topic-selector → 产出选题报告
4. [阶段2.5] 调用 push-to-feishu → 推送飞书
5. [等待用户选择] 请用户指定选题
6. [阶段4] 调用 mcn-content-writer → 产出文章
7. [阶段5] 调用 generate-images.py → 产出配图
8. [阶段6] 调用 publish-draft.py → 发布草稿
9. [完成] 返回草稿链接
```

### 单阶段

```
用户: 内容生成 "OpenAI内部信曝光"

Luna:
1. [检查技能] mcn-content-writer 已安装 ✓
2. [调用] mcn-content-writer/scripts/run-content-gen.py --topic "OpenAI内部信曝光"
3. [返回] 文章已生成：mcn/content/2026-04-15/OpenAI内部信曝光/article.md
```

---

## Pitfalls

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 子技能缺失 | 用户未安装 | 提示安装，不继续执行 |
| 产出找不到 | 目录约定不一致 | 检查 `references/config.md` |
| 配图和文章分离 | 传递了错误 topic | 使用 slugify 确保路径一致 |
| 工作流中断 | 子技能执行失败 | 返回失败状态，不继续下一阶段 |

---

## References

| 文档 | 说明 |
|------|------|
| config.md | 目录约定、架构原则 |
| 01-hotspot-research.md | 热点调研详细流程 |
| 02-topic-selection.md | 选题分析详细流程 |
| 03-content-rewriting.md | 内容生成详细流程 |
| 04-image-generation.md | 配图生成详细流程 |
| 05-humanizer.md | 去 AI 化详细流程 |
| 06-publishing.md | 发布流程详细说明 |

---

*Version: 3.1.0*
*架构原则：总引导 + 子技能功能闭环 + 约定衔接*