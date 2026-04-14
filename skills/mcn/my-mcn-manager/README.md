# my-mcn-manager 使用指南

## 快速开始

### 方式 1：自动触发（推荐）

技能描述已配置触发词，提到以下关键词会自动触发：
- 公众号文章
- 自动发布
- MCN 发布
- 热点调研
- 选题分析

### 方式 2：命令行执行

```bash
cd ~/.hermes/skills/mcn/my-mcn-manager

# 完整流程
python scripts/run-full-workflow.py

# 只调研热点（整合多渠道）
python scripts/run-hotspot-research.py

# 分析选题
python scripts/run-topic-analysis.py --date 2026-04-14 --top 5

# 生成并发布文章
python scripts/publish_after_confirm.py "主题名" --style professional

# 验证文章
python scripts/validate-article.py --article article.md
```

---

## 渠道优先级策略（重要更新）

热点抓取已整合多渠道，按精准度分级：

| 优先级 | 平台 | 分类方式 | 抓取方式 |
|--------|------|----------|----------|
| **P1（最精准）** | 虎嗅前沿科技 | 直接分类URL | `opencli web read` |
| **P1** | 虎嗅3C数码 | 直接分类URL | `opencli web read` |
| **P1** | 掘金 | 整站开发 | `opencli web read` |
| **P2** | 微博 | category过滤 | 过滤 `互联网`/`民生新闻` |
| **P3** | 36氪 | API | `opencli 36kr news` |
| **P4** | 知乎/抖音 | 关键词匹配 | 无分类 |

**OpenCLI 环境要求**：
- **Node版本**：必须用 v20（v22有undici兼容问题，v18不支持styleText）
- 安装：`nvm use 20 && npm install -g @jackwener/opencli@1.6.0`
- 验证：`opencli weibo hot --limit 10 --format json`

---

## 工作流说明

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  阶段 1      │ → │  阶段 2      │ → │  阶段 3      │ → │  阶段 4      │
│  热点调研   │   │  选题分析   │   │  内容生成   │   │  发布草稿   │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
     ↓                   ↓                   ↓                   ↓
mcn/hotspot/      mcn/topic/          mcn/content/        公众号草稿箱
YYYY-MM-DD/       recommend.md        article.md          media_id: xxx
```

---

## 任务清理机制（新增）

### 发布完成后归档

```bash
# 归档已完成的任务
python scripts/task_manager.py archive --task-id 20260414_170000
```

### 选题前检查未完成任务

```bash
# 检查是否有未完成的任务
python scripts/task_manager.py reset

# 如果有未完成任务，会推送飞书人工确认
# 退出码 2 表示需要人工确认
```

---

## 脚本说明

### run-hotspot-research.py（已更新）

**功能**：整合抓取虎嗅/36kr/掘金/微博等多平台热搜

**渠道优先级**：
- P1: 虎嗅科技/3C、掘金（直接分类URL）
- P2: 微博（category过滤）
- P3: 36kr（API）
- P4: 知乎/抖音（关键词匹配）

**示例**：
```bash
# 抓取今天的所有渠道热点
python scripts/run-hotspot-research.py
```

**输出**：
```
mcn/hotspot/2026-04-14/
└── hotspot-aggregated.md  # 所有渠道聚合
```

---

### run-topic-analysis.py

**功能**：分析热搜数据，生成推荐主题

**参数**：
- `--date`: 指定日期
- `--top`: 推荐主题数量（默认 5）
- `--output`: 输出文件路径

**示例**：
```bash
python scripts/run-topic-analysis.py --date 2026-04-14 --top 5
```

---

### task_manager.py（已更新）

**功能**：任务生命周期管理

**新增命令**：
- `archive`: 归档已完成的任务
- `reset`: 检查未完成任务，推送飞书确认

**示例**：
```bash
# 初始化任务
python scripts/task_manager.py init --topic "今日热点"

# 更新步骤状态
python scripts/task_manager.py update --task-id xxx --step research

# 归档任务
python scripts/task_manager.py archive --task-id xxx

# 检查未完成任务（选题前调用）
python scripts/task_manager.py reset
```

---

### generate-images.py（已优化）

**功能**：AI 配图生成（优化积分使用）

**关键改进**：
- webHook 使用假地址（避免 -1 问题）
- task_id 持久化（避免重复提交）
- 轮询 5秒间隔，最多 5 分钟
- 超时放弃不重试（节省积分）

**示例**：
```bash
python scripts/generate-images.py --topic "AI软件" --count 4 --date 2026-04-14
```

---

### publish-draft.py

**功能**：公众号草稿发布

**关键注意**：
- 封面图用永久素材 API
- 正文配图用 uploadimg API
- JSON 中文用 ensure_ascii=False

**示例**：
```bash
python scripts/publish-draft.py --article article.md --images-dir images/
```

---

## 配置文件

### 主配置：~/.hermes/mcn_config.yaml

```yaml
hotspot:
  channels:
    # 有分类URL的平台（优先）
    huxiu_tech:
      url: https://www.huxiu.com/channel/105.html
      type: channel_direct
      domain: 科技
      
    # 微博分类过滤
    weibo:
      cmd: opencli weibo hot --limit 50
      type: opencli_filter
      filter:
        categories: [互联网, 民生新闻]

article:
  min_chars: 1500
  max_chars: 2000
  
image_generation:
  providers:
    grsai:
      api_url: https://grsai.dakka.com.cn/v1/draw/nano-banana
```

---

## 输出目录结构（已更新）

```
~/backup/知识库-Obsidian/
├── mcn/                        # MCN 专用目录（不参与 wiki-ingest）
│   ├── hotspot/YYYY-MM-DD/     # 热搜聚合数据
│   ├── topic/YYYY-MM-DD/       # 选题分析报告
│   ├── content/YYYY-MM-DD/     # 文章 + 配图
│   ├── images/YYYY-MM-DD/      # AI 生成的配图
│   └── publish/YYYY-MM-DD/     # 发布记录
│
└── tmp/                        # 其他临时文件
    └── tasks/                  # 任务跟踪
        ├── archive/            # 已归档任务
        └── *_task.json         # 进行中的任务
```

---

## 常见问题

### Q1: OpenCLI 热搜抓取失败

**原因**：Node 版本不兼容

**解决**：
```bash
# 必须使用 Node 20
source ~/.nvm/nvm.sh && nvm use 20
opencli weibo hot --limit 10 --format json
```

### Q2: 配图生成积分浪费

**原因**：重复提交相同任务

**解决**：
- task_id 已持久化到 tasks.json
- 超时后检查已有 task_id，增量继续
- 不重新提交所有任务

### Q3: 公众号发布报错 40164

**原因**：IP 白名单未配置

**解决**：
1. 登录公众号后台
2. 设置与开发 → 基本配置
3. IP 白名单 → 添加当前机器 IP

### Q4: 未完成任务冲突

**解决**：
```bash
# 检查未完成任务
python scripts/task_manager.py reset

# 如果飞书推送确认，回复：
# - "重新开始" 继续执行
# - "放弃" 归档旧任务
```

---

## 定时任务配置

```bash
# 编辑 crontab
crontab -e

# MCN 调研（使用 my-mcn-manager）
0 17 * * 1-5 cd ~/.hermes/skills/mcn/my-mcn-manager && source ~/.nvm/nvm.sh && nvm use 20 && python scripts/run-hotspot-research.py
```

---

## 版本历史

| 版本 | 更新内容 | 日期 |
|------|----------|------|
| 2.0 | 整合多渠道、任务清理机制、Node 20 | 2026-04-14 |
| 1.0 | 初始版本 | 2026-04-13 |

---

*Last updated: 2026-04-14*