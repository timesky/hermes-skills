---
name: my-mcn-manager
description: |
  MCN 公众号全自动工作流管理。当用户提到：公众号文章、自动发布、MCN 发布、
  热点调研、选题分析、内容改写、配图生成、发布草稿时使用此技能。
  支持完整流程（调研→选题→写作→配图→发布）或分阶段执行。
  配置在 ~/.hermes/mcn_config.yaml，输出到知识库 tmp/目录。
tags: [mcn, wechat, auto-publish, workflow, content]
version: 1.0.0
created: 2026-04-14
author: Luna
---

# MCN Manager - 公众号全自动工作流

统一入口的 MCN 内容管理工作流，整合热点调研、选题分析、内容改写、AI 配图、公众号发布于一体。

---

## ⭐ 快速开始

### 模式 1：完整流程（推荐）

```
用户：执行 MCN 工作流 / 自动发布公众号文章

→ 热点调研 → 选题分析 → 推送飞书 → 等待确认 → 生成文章 → 配图 → 排版 → 发布草稿
```

### 模式 2：分阶段执行

| 命令 | 执行阶段 | 输出 |
|------|----------|------|
|| `调研今天热点` | 阶段 1：热点调研 | tmp/hotspot/{日期}/ |
|| `分析选题` | 阶段 2：选题分析 | tmp/topic/{日期}/recommend.md |
|| `生成文章：主题名` | 阶段 3-4：内容生成 | tmp/content/{日期}/article.md |
|| `生成配图` | 阶段 5：AI 配图 | tmp/images/{日期}/ |
|| `排版文章` | 阶段 6：排版整合 | tmp/content/{日期}/article_formatted.md |
|| `发布草稿` | 阶段 7：公众号发布 | 草稿 media_id |

### 模式 3：配置管理

| 命令 | 作用 |
|------|------|
| `查看 MCN 配置` | 显示当前配置 |
| `修改关注领域为：科技，AI, 投资` | 更新领域列表 |
| `查看已发布文章` | 显示 Memory 记录 |

---

## 工作流概览

```
┌─────────────────────────────────────────────────────────────────┐
│  定时任务 17:00 或 用户手动触发                                   │
│     ↓                                                           │
│  [阶段 1] 热点调研 → mcn-hotspot-aggregator 逻辑                   │
│     ↓                                                           │
│  [阶段 2] 选题分析 → mcn-topic-selector 逻辑                      │
│     ↓                                                           │
│  [阶段 3] 推送飞书 → 等待用户确认（唯一交互点）                     │
│     ↓                                                           │
│  [阶段 4] 内容改写 → mcn-content-rewriter 逻辑                    │
│     ↓                                                           │
│  [阶段 5] AI 配图 → ai-image-generation 逻辑                       │
│     ↓                                                           │
│  [阶段 6] 排版整合 → 将配图插入文章合适位置                         │
│     ↓                                                           │
│  [阶段 7] 发布草稿 → mcn-wechat-publisher 逻辑                    │
│     ↓                                                           │
│  [阶段 8] 推送结果通知                                            │
└─────────────────────────────────────────────────────────────────┘
```

**⚠️ 重要：排版是独立步骤**

配图生成后必须先排版（将图片插入文章合适位置），再发布草稿。
不要跳过排版直接发布，否则配图无法正确显示在文章中。

### 阶段详细说明

| 阶段 | 功能 | 调用模块 | 自动化 |
|------|------|----------|--------|
| 1 | 多平台热搜抓取 | `references/01-hotspot-research.md` | 全自动 |
| 2 | 选题分析推荐 | `references/02-topic-selection.md` | 全自动 |
| 3 | 推送飞书 | scripts/push-to-feishu.py | 全自动 |
| 4 | 内容改写生成 | `references/03-content-rewriting.md` | 全自动 |
| 5 | AI 配图生成 | `references/04-image-generation.md` | 全自动 |
| 6 | 排版整合 | scripts/layout-article.py | 全自动 |
| 7 | 公众号发布 | `references/06-publishing.md` | 全自动 |

---

## 核心功能模块

### 模块 1：热点调研

**功能**：抓取知乎、微博、抖音、虎嗅、掘金等平台热搜

**⚠️ 渠道优先级策略（重要）**：

| 优先级 | 平台 | 分类方式 | 抓取方式 |
|--------|------|----------|----------|
| **P1（最精准）** | 虎嗅前沿科技 | 直接分类URL | `opencli web read --url https://www.huxiu.com/channel/105.html` |
| **P1** | 虎嗅3C数码 | 直接分类URL | `opencli web read --url https://www.huxiu.com/channel/121.html` |
| **P1** | 掘金 | 整站开发 | `opencli web read --url https://juejin.cn/` |
| **P2** | 微博 | category过滤 | `opencli weibo hot` + 过滤 `category="互联网"` |
| **P3** | 知乎/抖音 | 关键词匹配 | 无分类，只能关键词筛选 |

**OpenCLI 环境要求**：
- **Node版本**：必须用 v20（v22有undici兼容问题，v18不支持styleText）
- 安装：`nvm use 20 && npm install -g @jackwener/opencli@1.6.0`
- 验证：`opencli weibo hot --limit 10 --format json`

**分类URL抓取示例**：
```bash
# 虎嗅前沿科技（最精准）
opencli web read --url https://www.huxiu.com/channel/105.html --output /tmp/huxiu_articles

# 输出文章列表（Markdown格式）
# 包含标题、作者、发布时间、链接
```

**微博分类过滤示例**：
```bash
# 获取热搜，过滤特定分类
opencli weibo hot --limit 50 --format json | python3 -c "
import json, sys
data = json.load(sys.stdin)
filtered = [d for d in data if d.get('category') in ['互联网', '民生新闻']]
for d in filtered: print(d.get('word'))
"
```

**配置**（`~/.hermes/mcn_config.yaml`）：
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
        
  domains:
    - name: 科技
    - name: 编程
    - name: AI应用
```

**执行**：
```bash
python scripts/run-hotspot-research.py --date 2026-04-14
```

**输出**：
```
tmp/hotspot/2026-04-14/
├── weibo-hotspot.md
├── zhihu-hotspot.md
└── toutiao-hotspot.md
```

详见：`references/01-hotspot-research.md`

---

### 模块 2：选题分析

**功能**：分析热搜数据，结合用户关注领域，生成推荐主题列表

**输入**：热点调研结果
**输出**：`tmp/topic/{日期}/recommend.md`

**分析维度**：
- 热度评分（平台热度数据）
- 相关性评分（与关注领域匹配度）
- 时效性评分（话题新鲜度）
- 排重检查（近 30 天已发布主题）

**执行**：
```bash
python scripts/run-topic-analysis.py --date 2026-04-14
```

详见：`references/02-topic-selection.md`

---

### 模块 3：内容改写

**功能**：根据选题生成公众号文章（1500-2000 字）

**核心要求**：
| 项目 | 要求 |
|------|------|
| 字数 | 1500-2000 字（硬性） |
| 结构 | 5-8 段落 + 开头 + 总结 |
| 标题 | 15-25 字，吸引力公式 |
| 风格 | professional/casual/story |

**执行流程**：
1. 生成 5 个候选标题 → 评估选择最佳
2. 撰写正文（1500+ 字）
3. 字数验证 → 不足则自动补充（最多 2 次）
4. 品牌名称替换（豆包→某 AI，具体地名→不提及）

**执行**：
```bash
python scripts/run-content-gen.py --topic "主题名" --style professional
```

详见：`references/03-content-rewriting.md`

---

### 模块 4：AI 配图

**功能**：为文章生成 3-5 张专属配图

**配置**：
```yaml
image_generation:
  default_provider: grsai
  providers:
    grsai:
      api_url: https://grsai.dakka.com.cn/v1/draw/nano-banana  # 国内直连
      cost_per_image: 440  # 积分/张
      timeout: 120
```

**⚠️ API 调用方式（重要 - 已优化）**：

使用 **假地址 webHook** + 轮询 result 模式（避免超时浪费积分）：

```
1. POST /v1/draw/nano-banana 
   {"model": "nano-banana-fast", "prompt": "...", "webHook": "http://192.168.1.1"}
   → 返回 {"data": {"id": "task_id"}}
   
   ⚠️ 关键：webHook 必须是假地址（如 http://192.168.1.1），不能是 "-1" 或空！

2. POST /v1/draw/result {"id": "task_id"}  （轮询，最多60次，间隔5秒）
   → status: "running" → 继续等待
   → status: "succeeded" → 下载图片
   → status: "failed" → 换prompt重试
   → 超过5分钟仍running → 放弃不重试（避免积分浪费）
```

**积分节省要点**：
| 问题 | 解决方案 |
|------|----------|
| 重复提交相同任务 | task_id持久化到tasks.json |
| 超时后重新提交所有 | 检查已有task_id，增量继续 |
| 相同prompt失败后继续 | 换prompt变体，不重复 |
| SSL超时触发重试 | 用terminal+curl而非execute_code |

**执行脚本**：
```bash
python scripts/generate-images.py --topic "主题名" --count 4 --date YYYY-MM-DD
```

**执行流程**：
1. 根据主题生成关键词列表
2. 批量生成图片（带重试机制，max_retries=2）
3. 验证数量 ≥ 3 张
4. 下载保存到 `tmp/content/{日期}/images/{主题}/`

**执行**：
```bash
python scripts/generate-images.py --topic "主题名" --count 4
```

详见：`references/04-image-generation.md`

---

### 模块 5：去 AI 化

**功能**：去除 AI 写作痕迹，提升阅读体验

**评分阈值**：≥ 45 分（满分 50）

**检查项**：
- ✓ 删除"作为...的证明"
- ✓ 替换"此外"为直接陈述
- ✓ 打破三段式列举
- ✓ 添加个人观点（"我觉得""在我看来"）
- ✓ 变化句子节奏

**执行**：
```bash
python scripts/humanize-article.py --input article.md --output humanized.md
```

详见：`references/05-humanizer.md`

---

### 模块 6：公众号发布

**功能**：通过官方 API 发布文章到草稿箱

**配置**（`~/.hermes/wechat_mp_config.yaml`）：
```yaml
appid: wx47533ce9c8854fb5
secret: 2b990fc5...eb2f
author: TimeSky
```

**完整发布流程**：

```
Step 1: 获取 access_token
   GET /cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}
   → access_token（有效期2小时）

Step 2: 上传封面图（900x500）到永久素材库
   POST /cgi-bin/material/add_material?access_token={token}&type=image
   → thumb_media_id（封面图 media_id）

Step 3: 上传正文配图（获取素材库 URL）
   POST /cgi-bin/media/uploadimg?access_token={token}
   → 图片 URL（http://mmbiz.qpic.cn/...）

Step 4: 构建 HTML 内容（插入配图）
   公众号支持：<p>, <br/>, <strong>, <img src="...">
   注意：图片 src 必须是素材库 URL！

Step 5: 创建草稿
   POST /cgi-bin/draft/add
   Body: {"articles": [{"title", "thumb_media_id", "author", "content"}]}
   → media_id（草稿 ID）
```

**⚠️ 关键注意事项**：
- **封面图**：必须用永久素材 API（`/material/add_material`）
- **正文配图**：必须用 `uploadimg` API 获取素材库 URL（外部链接不被接受）
- **JSON 编码**：中文必须用 `ensure_ascii=False`
- **标题**：≤64 字符
- **排版顺序**：配图 → 排版 → 发布（不要跳过排版）

**正文配图上传流程（重要）**：
```python
# 1. 使用 uploadimg API（不是 material/add_material）
url = "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"

# 2. 上传图片返回 URL
result = {"url": "http://mmbiz.qpic.cn/mmbiz_png/xxx/0?from=appmsg"}

# 3. URL 直接用于 HTML content
content = f'<p><img src="{url}"/></p>'

# ⚠️ 注意：外部图片 URL（如 Unsplash）不被公众号接受！
# ⚠️ 只有素材库 URL 才能正确显示在文章中
```

**执行**：
```bash
python scripts/publish-draft.py --article article.md
```

详见：`references/06-publishing.md`

---

## ⭐ 配置管理

### 配置文件位置

| 文件 | 路径 | 作用 |
|------|------|------|
| 主配置 | `~/.hermes/mcn_config.yaml` | 热点领域、文章要求、配图配置 |
| 公众号 | `~/.hermes/wechat_mp_config.yaml` | AppID、Secret、作者名 |

### 查看配置

```bash
# 查看完整配置
cat ~/.hermes/mcn_config.yaml

# 查看公众号配置（脱敏）
cat ~/.hermes/wechat_mp_config.yaml | grep -v secret
```

### 修改配置

**方式 1：直接编辑**
```bash
nano ~/.hermes/mcn_config.yaml
```

**方式 2：命令行**
```bash
# 修改关注领域
python scripts/update-config.py --set "hotspot.domains=[科技，AI,投资]"

# 修改文章字数要求
python scripts/update-config.py --set "article.min_chars=1800"
```

详见：`references/config.md`

---

## 输出目录结构

```
/Users/timesky/backup/知识库-Obsidian/
├── mcn/                        # MCN 基础目录（人工定期整理）
│   ├── hotspot/                # 热搜原始数据
│   │   └── YYYY-MM-DD/
│   │       ├── weibo-hotspot.md
│   │       ├── zhihu-hotspot.md
│   │       └── ...
│   │
│   ├── topic/                  # 选题分析报告
│   │   └── YYYY-MM-DD/
│   │       └── recommend.md
│   │
│   ├── content/                # 生成的文章
│   │   └── YYYY-MM-DD/
│   │       ├── article-name.md
│   │       └── images/
│   │           ├── cover.png
│   │           ├── img_1.png
│   │           └── ...
│   │
│   └── publish/                # 发布记录
│       └── YYYY-MM-DD/
│           └── publish-log.md
│
└── tmp/                        # auto-save（不用于 MCN）
    └── ...
```

**⚠️ 目录变更说明**：
- MCN 输出目录从 `tmp/` 改为 `mcn/`
- `mcn/` 目录内容不参与 wiki-ingest 流程
- 人工定期整理 `mcn/` 目录内容
- 配置文件：`~/.hermes/mcn_config.yaml` 的 `kb_paths.mcn_root`

---

## 定时任务配置

| 时间 | 任务 | 脚本 | 说明 |
|------|------|------|------|
| 11:00 | 文章数据分析 | `scripts/analyze-articles.py` | 分析 15 天阅读数据 |
| 17:00 | 热点调研 + 选题 | `scripts/run-full-workflow.py --stage research` | 抓取热搜 + 分析 |
| 17:30 | 推送飞书 | `scripts/push-to-feishu.py` | 推送选题报告 |

**Cron 配置示例**：
```bash
# 编辑定时任务
crontab -e

# 添加任务
0 17 * * * cd ~/.hermes/skills/mcn/my-mcn-manager && python scripts/run-hotspot-research.py
30 17 * * * cd ~/.hermes/skills/mcn/my-mcn-manager && python scripts/push-to-feishu.py
```

---

## ⭐ 文章质量验证

### 发布前检查清单

```python
# scripts/validate-article.py
checks = {
    'word_count': {'min': 1500, 'max': 2000, 'status': 'pass'},
    'image_count': {'min': 3, 'max': 5, 'status': 'pass'},
    'humanization_score': {'min': 45, 'status': 'pass'},
    'title_length': {'max': 64, 'status': 'pass'},
    'digest_length': {'max': 120, 'status': 'pass'},
    'brand_names': {'replaced': True, 'status': 'pass'}
}
```

### 执行验证

```bash
python scripts/validate-article.py --article article.md
```

**输出**：
```
=== 文章验证报告 ===
✓ 字数：1856 字 (1500-2000)
✓ 配图：4 张 (3-5)
✓ 去 AI 化：47/50 (≥45)
✓ 标题：22 字 (≤64)
✓ 摘要：98 字 (≤120)
✓ 品牌名：已替换

结论：✅ 符合发布标准
```

---

## ⭐ 重要注意事项

### 远程操作支持

**⚠️ 远程操作时无法查看本地文件**，所有通知必须直接发送内容：

```python
# ❌ 错误：只给文件路径
print(f"选题报告：tmp/topic/{date}/recommend.md")

# ✅ 正确：直接发送内容到飞书
python scripts/push-to-feishu.py --topic-report {date}
# 发送完整 Top 5 推荐主题到飞书
```

**飞书推送必须包含**：
- Top 5 推荐主题（标题 + 领域 + 热度 + 评分）
- 每个主题的可点击链接
- 选题建议
- 下一步操作指引

**飞书推送必须包含**：
- Top 5 推荐主题（标题 + 领域 + 热度 + 评分）
- 每个主题的可点击链接
- 选题建议
- 下一步操作指引

### 飞书推送配置（重要）

**⚠️ 独立脚本不会自动加载 .env**，必须手动加载：

```python
# scripts/push-to-feishu.py 开头必须包含
def load_env():
    """从 .env 文件加载环境变量"""
    env_path = os.path.expanduser('~/.hermes/.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_env()  # 必须调用！
```

**必需环境变量**（`~/.hermes/.env`）：

| 变量 | 作用 | 获取方式 |
|------|------|----------|
| `FEISHU_APP_ID` | 飞书应用 ID | 飞书开放平台创建应用 |
| `FEISHU_APP_SECRET` | 应用密钥 | 同上 |
| `FEISHU_CHAT_ID` | 推送目标会话 | 从飞书对话 URL 或 API 获取 |

**获取 app_access_token 流程**：

```python
# 1. 调用飞书内部 API
url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"

# 2. 发送 app_id + app_secret
data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}

# 3. 返回 token（有效期 2 小时）
# 建议缓存，提前 5 分钟刷新
```

**推送消息 API**：

```python
url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

data = {
    "receive_id": FEISHU_CHAT_ID,  # chat_id 类型
    "msg_type": "text",
    "content": json.dumps({"text": message}, ensure_ascii=False)  # 中文必须 ensure_ascii=False
}
headers = {"Authorization": "Bearer " + token}
```

**常见问题**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 脚本找不到环境变量 | terminal() 不继承 Hermes 环境 | 添加 load_env() 函数 |
| 推送失败 code!=0 | token 过期或无效 | 检查 app_id/secret，重新获取 token |
| 中文乱码 | JSON 编码问题 | 使用 `ensure_ascii=False` |
| CHAT_ID 未配置 | 缺少环境变量 | 添加到 ~/.hermes/.env |

### 热度解析

不同平台热度格式不同，必须兼容：
- 微博：纯数字 `1103348`
- 知乎：带单位 `1547 万热度 `、`274 万热度`
- 处理：去掉 `,`、`热度 `、` ` 空格，再解析数字

### Task.md 集成

每个脚本执行后必须更新 task.md：
```python
# 更新步骤状态
task_data['steps']['research'] = {
    'status': 'completed',
    'data': {'platforms': results, 'total_count': 40},
    'updated': datetime.now().isoformat()
}
```

### 去重机制

发布前检查 30 天内是否发布过相同主题：
```python
python scripts/task_manager.py check --topic "主题名"
# 返回 True 表示已发布，应跳过
```
| 8 | IP 白名单未配 | 公众号后台 → 基本配置 → 添加 IP | publishing |

---

## 与旧技能的关系

本技能是**完整独立整合版本**，不依赖原有分散技能：

| 旧技能 | 整合状态 | 建议 |
|--------|----------|------|
| wechat-mp-auto-publish | ✅ 整合到主工作流 | 可废弃 |
| mcn-hotspot-aggregator | ✅ → references/01 | 可废弃 |
| mcn-topic-selector | ✅ → references/02 | 可废弃 |
| mcn-content-rewriter | ✅ → references/03 | 可废弃 |
| ai-image-generation | ✅ → references/04 | 保留（通用） |
| humanizer-zh | ✅ → references/05 | 保留（第三方） |
| mcn-wechat-publisher | ✅ → references/06 | 可废弃 |

**迁移步骤**：
1. 测试新技能完整流程
2. 确认定时任务切换到新脚本
3. 删除旧技能（可选）

---

## 相关技能

- `humanizer-zh`: 去 AI 化处理（第三方技能）
- `ai-image-generation`: AI 图片生成（通用技能，可选）
- `summarize-pro`: 热搜摘要提取
- `wiki-auto-save`: 知识收集保存

---

## 学习记录

今日问题（2026-04-14）已记录：
- 正文配图必须用素材库 URL
- 配图数量验证机制
- 生成失败重试机制

详见：`~/.hermes/learnings/LRN-20260414-001.md`

---

*Last updated: 2026-04-14 by Luna*
*整合自：mcn-hotspot-aggregator, mcn-topic-selector, mcn-content-rewriter, mcn-wechat-publisher*
