# MCN 架构原则与目录约定

**版本**: 2026-04-15 v3.0

---

## 架构原则

### 1. 入口技能职责

`my-mcn-manager` 作为总引导，负责：
- 技能依赖管理（列出必要子技能，引导安装）
- 工作流集合定义
- 用户引导和任务调度
- 变更管理（新技能/改名/流程变更先修改入口技能）
- 子技能协调（确保功能闭环和产出交付）

**入口技能不执行具体功能，只调度和引导。**

### 2. 子技能独立性

每个子技能必须：
- **功能闭环**：独立完成本阶段所有工作
- **产出明确**：输出文件到约定位置
- **状态返回**：返回执行结果
- **不跨技能依赖**：不导入其他技能模块

### 3. 约定优于配置

衔接机制：通过约定位置，而非共享模块或参数传递。

```
下游技能知道约定位置 → 直接去读取 → 不需要参数传递
```

---

## 子技能交付规范

### 功能闭环要求

| 子技能 | 输入 | 产出 | 状态返回 |
|--------|------|------|----------|
| mcn-hotspot-research | --date | `hotspot/{date}/hotspot.json` | success + path |
| mcn-topic-selector | --date（读取热点） | `topic/{date}/recommend.md` | success + path |
| mcn-content-writer | --topic | `content/{date}/{slug}/article.md` | success + path |
| ai-image-generation | --topic --date | `content/{date}/{slug}/images/*.png` | success + paths |

### 产出交付位置

每个子技能产出必须放入约定位置：

```
mcn/
├── workflow.json              # ⚓ 锚点文件（跨会话衔接）
│
├── hotspot/{date}/              # mcn-hotspot-research 产出
│   ├── hotspot.json             # 热点数据
│   └── sources/                 # 原始数据备份
│
├── topic/{date}/                # mcn-topic-selector 产出
│   ├── recommend.md             # 选题报告（Top 5）
│   └── analysis.json            # 分析数据
│
├── content/{date}/{slug}/       # mcn-content-writer 产出
│   ├── article.md               # 文章（1500-2000字）
│   └── images/                  # ai-image-generation 产出
│       ├── cover.png            # 封面（900x500）
│       ├── img_*.png            # 正文配图
│       └── tasks.json           # 任务记录
│
└── publish/                     # my-mcn-manager 产出
    └── drafts.json              # 草稿记录
```

---

## 锚点文件机制（新增）

### 位置

`mcn/workflow.json` - 固定位置，任何会话都能找到

### 用途

**跨会话衔接**：当用户在新会话回复「选题X」或「继续MCN」时，读取此文件恢复上下文。

### 结构

```json
{
  "date": "2026-04-19",
  "current_step": "topic_selection",
  "status": "pending_user_choice",
  
  "data_paths": {
    "hotspot": "mcn/hotspot/2026-04-19/hotspot.json",
    "topic": "mcn/topic/2026-04-19/analysis.json",
    "recommend": "mcn/topic/2026-04-19/recommend.md"
  },
  
  "recommendations": [...],  // Top 5 选题
  "selected_topic": null,
  "article_path": null,
  "images_path": null,
  "media_id": null,
  "published": false,
  
  "updated_at": "2026-04-19T14:19:00"
}
```

### 状态流转

| 阶段完成 | workflow.json 更新 |
|----------|-------------------|
| hotspot_research | `status: "hotspot_done"` |
| topic_selector | `status: "pending_user_choice"` |
| 用户选择选题 | `status: "topic_selected", selected_topic: "..."` |
| content_writer | `status: "content_done", article_path: "..."` |
| image_gen | `status: "images_done", images_path: "..."` |
| publish_draft | `status: "published", published: true` |

### 与约定位置的关系

```
                    ┌─────────────────┐
                    │  workflow.json  │ ← 锚点文件（跨会话）
                    │   (固定位置)    │
                    └─────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ hotspot/{date} │  │ topic/{date}  │  │ content/{date}│ ← 约定位置（同会话）
└───────────────┘  └───────────────┘  └───────────────┘

同会话：直接用约定位置（下游技能知道去哪读）
跨会话：先读 workflow.json → 获取 data_paths → 导航到约定位置
```

---

每个子技能执行完成后返回：

```python
{
    "status": "success|failed",
    "output_path": "产出文件路径",
    "output_files": ["多个文件路径"],  # 可选
    "message": "简要说明",
    "date": "执行日期",
    "topic_slug": "选题slug"  # 如果有
}
```

---

## 目录约定（所有技能遵循）

### 路径拼接规则

```python
# 每个脚本内联此逻辑，不依赖共享模块
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

def slugify(text):
    import re
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【»]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
# MCN 内容工作流配置

## 文章排版规范

**结束语模板**：
```
你怎么看当前的算力市场？欢迎在评论区分享你的观点和经验。

---

**关注「{公众号名称}」，一起洞察技术趋势，共同成长。**
```

**⚠️ 注意**：
- 公众号名称要使用正确的存稿公众号，不是原文来源
- **标签不要放在文章底部**，标签是给编辑参考，不是正文内容
- 结束语目的是提高互动（评论区引导 + 关注引导）

---

## 目录约定
hotspot_dir = f"{MCN_ROOT}/hotspot/{date}"
topic_dir = f"{MCN_ROOT}/topic/{date}"
article_dir = f"{MCN_ROOT}/content/{date}/{slugify(topic)}"
images_dir = f"{MCN_ROOT}/content/{date}/{slugify(topic)}/images"
article_file = f"{MCN_ROOT}/content/{date}/{slugify(topic)}/article.md"
```

### 从外部配置读取 KB_ROOT（可选覆盖）

```yaml
# ~/.hermes/mcn_config.yaml
paths:
  kb_root: /Users/timesky/backup/知识库-Obsidian
```

脚本可读取此配置覆盖默认 KB_ROOT，但目录结构约定不变。

---

## 衔接机制

### 热点 → 选题

```
mcn-hotspot-research 产出：mcn/hotspot/{date}/hotspot.json
mcn-topic-selector 读取：同上（约定位置）
```

### 选题 → 内容

```
mcn-topic-selector 产出：mcn/topic/{date}/recommend.md
用户选择：指定选题标题
mcn-content-writer 输入：--topic "用户选择的标题"
```

### 内容 → 配图

```
mcn-content-writer 产出：mcn/content/{date}/{slug}/article.md
ai-image-generation 输入：--topic "同一标题" --date
ai-image-generation 产出：mcn/content/{date}/{slug}/images/*.png
```

### 配图 → 发布

```
ai-image-generation 产出：mcn/content/{date}/{slug}/images/
publish-draft 输入：--article "文章路径"
publish-draft 读取：同目录下的 images/
```

---

## 变更管理流程

**规则**：任何变更必须先修改 `my-mcn-manager`，再处理具体技能。

### 新技能加入

```
1. my-mcn-manager SKILL.md → 添加必要子技能
2. my-mcn-manager SKILL.md → 添加工作流阶段
3. references/config.md → 添加产出位置约定
4. 创建新技能 SKILL.md
5. 创建新技能脚本
```

### 技能改名

```
1. my-mcn-manager SKILL.md → 更新子技能名称引用
2. 重命名子技能目录
3. 子技能 SKILL.md → 更新 name 字段
4. references/config.md → 更新名称
```

### 流程变更

```
1. my-mcn-manager SKILL.md → 更新工作流阶段顺序
2. 子技能 SKILL.md → 更新产出位置（如需）
3. references/config.md → 更新目录约定
4. 子技能脚本 → 更新输出路径
```

---

## 技能独立性验证

每个子技能应满足：

| 检查项 | 要求 |
|--------|------|
| 不导入其他技能模块 | ✅ |
| 脚本内联目录解析 | ✅ |
| 配置从外部 YAML 读取 | ✅ |
| 目录遵循约定 | ✅ |
| 产出放入约定位置 | ✅ |
| 返回状态信息 | ✅ |

---

## 工作流集合

### 当前：微信公众号发布

| 阶段 | 子技能 | 产出 |
|------|--------|------|
| 1 | mcn-hotspot-research | hotspot/{date}/ |
| 2 | mcn-topic-selector | topic/{date}/recommend.md |
| 3 | push-to-feishu（入口技能脚本） | 飞书消息 |
| 4 | 用户选择 | 选题标题 |
| 5 | mcn-content-writer | content/{date}/{slug}/article.md |
| 6 | ai-image-generation | content/{date}/{slug}/images/ |
| 7 | publish-draft（入口技能脚本） | 公众号草稿 |

### 预留：其他渠道

- 小红书发布流程
- 抖音短视频流程
- B站视频流程

---

*架构原则：入口引导 + 子技能闭环 + 约定衔接*