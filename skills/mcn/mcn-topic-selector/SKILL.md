---
name: mcn-topic-selector
description: |
  MCN 选题分析技能 - 分析热点数据，推荐选题，排除已发布内容。
  
  触发词：选题分析、选题推荐、热点选题、mcn选题
  
  可独立调用，也可被 my-mcn-manager 在阶段2调度。
parent: my-mcn-manager
tags: [mcn, topic, selector, analysis, recommendation]
version: 1.1.0
created: 2026-04-15
updated: 2026-04-15
---

# MCN 选题分析

分析热点数据，推荐 Top 5 选题，排除已发布内容（相似度比较）。

---

## 功能闭环与产出交付

**职责**：独立完成选题分析阶段所有工作。

| 项目 | 说明 |
|------|------|
| 输入 | `--date {日期}`（从约定位置读取热点数据） |
| 输入位置 | `mcn/hotspot/{date}/`（上游产出） |
| 产出位置 | `mcn/topic/{date}/recommend.md` |
| 状态返回 | `{"status": "success", "output_path": "...", "date": "..."}` |

**衔接机制**：
- 上游技能 `mcn-hotspot-research` 产出到约定位置
- 本技能从约定位置读取，不需要参数传递
- 下游用户选择选题后，传递给 `mcn-content-writer`

---

## 配置来源

**约定优于配置 + 技能独立性**

- 配置文件：`~/.hermes/mcn_config.yaml`（唯一外部依赖）
- 目录约定：脚本内联解析，不依赖其他技能模块
- 输入目录：`mcn/hotspot/{date}/`
- 输出目录：`mcn/topic/{date}/`

脚本不导入其他技能目录下的模块。详见入口技能 `references/config.md`。

---

## 触发场景

| 用户输入 | 响应 |
|----------|------|
| "选题分析" | 分析今日热点并推荐 |
| "选题推荐" | 推荐可选主题 |
| "热点选题" | 从热点中选主题 |

---

## 核心功能

### 1. 加载热点数据

从约定位置读取：`mcn/hotspot/{date}/hotspot-aggregated.md`

### 2. 排除已发布内容

使用**余弦相似度**（字符级分词 + 技术词匹配）：

```python
# 余弦相似度阈值
COSINE_SIMILARITY_THRESHOLD = 0.35  # 35% 以上排除

# 分词方式：字符级 + 技术词库
- 字符级拆分（中文字符）
- 技术词匹配（AI、机器人、芯片、算力等）

# 检查方式
余弦相似度 >= 35% → 排除
```

**排除列表格式**（完整记录）：
| 新话题标题 | 相似标题 | 相似度 | 原因 |
|------------|----------|--------|------|
| 具身模型Scaling Law... | 高德首款具身机器人 | **35.6%** | 余弦相似 |
| | 宇树机器人 | 29.2% | 次相似 |

### 3. 推荐评分

| 评分因素 | 权重 |
|----------|------|
| 热度值 | 40% |
| 领域相关性 | 30% |
| 发布优先级 | 20% |
| 内容可操作性 | 10% |

---

## 输出

```
~/backup/知识库-Obsidian/mcn/topic/{日期}/
├── recommend.md    # Top 5 推荐主题
├── excluded.md     # 已排除主题（含原因）
└── analysis.json   # 详细分析数据

~/backup/知识库-Obsidian/mcn/
└── workflow.json   # ⚓ 锚点文件（跨会话衔接）
```

**⚠️ 锚点文件机制（新增）**：

选题分析完成后，自动写入 `mcn/workflow.json`，记录当前工作流状态。
用于跨会话衔接：用户在新会话回复「选题X」时，读取此文件恢复上下文。

---

## Terminal 执行

```bash
eval "$(pyenv init -)" && python3 ~/.hermes/skills/mcn/mcn-topic-selector/scripts/run-topic-analysis.py --date 2026-04-15
```

**脚本目录**：`mcn-topic-selector/scripts/`
- `run-topic-analysis.py` - 主脚本
- `fetch-published-articles.py` - 获取已发布文章列表

---

## 已发布文章列表

位置：`~/.hermes/mcn_published.json`

格式：
```json
[
  {
    "title": "文章标题",
    "publish_date": "2026-04-15",
    "keywords": ["关键词1", "关键词2"]
  }
]
```

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| 排除不生效 | 1. 检查 mcn_published.json 是否更新；2. 关键词提取改用核心实体词拆分（而非连续子串）；3. 降低 KEYWORD_OVERLAP_THRESHOLD=1 |
| 相似度误判 | 调整 SIMILARITY_THRESHOLD（默认0.5）；语义相似度阈值降低到0.5 |
| 评分显示0.0 | 可能是热度数据缺失（N/A）导致评分计算失败。检查热点数据是否有 `heat_score` 字段；领域匹配失败时评分权重分配异常 |
| 热点数据缺失 | 先执行 mcn-hotspot-research |
| 话题排除但用户仍选 | 用户可能远程操作，排除逻辑需验证；核心实体词匹配要覆盖常见词（机器人、AI、芯片等） |
| 草稿未被排除 | 排重仅检查 `mcn_published.json`（已发布），草稿未发布不会被排除。**解决方案**：可选参数 `--check-drafts` 检查 `mcn/content/{date}/` 目录下已有草稿，避免重复选题 |
| publish_date 缺失导致排除失效 | 当文章 `publish_date` 和 `publish_time` 为空时，`'' >= cutoff_date` 返回 False，所有文章被过滤掉。**解决方案**：`check_topic_excluded()` 已修复，空日期文章默认纳入比较（不按日期过滤） |

---

## 相关技能

- **mcn-hotspot-research** - 上游技能，产出到约定位置
- **mcn-content-writer** - 下游技能，接收用户选择的选题
- **my-mcn-manager** - 父技能，调度和引导

---

*Version: 1.1.0 - 功能闭环 + 产出交付规范*