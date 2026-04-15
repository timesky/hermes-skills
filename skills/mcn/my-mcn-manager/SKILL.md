---
name: my-mcn-manager
description: |
  MCN 公众号全自动工作流管理。当用户提到：公众号文章、自动发布、MCN 发布、
  热点调研、选题分析、内容改写、配图生成、发布草稿时使用此技能。
  支持完整流程（调研→选题→写作→配图→发布）或分阶段执行。
  配置在 ~/.hermes/mcn_config.yaml，输出到知识库 mcn/目录。
tags: [mcn, wechat, auto-publish, workflow, content]
version: 1.0.0
created: 2026-04-14
author: Luna
---

# MCN Manager - 公众号全自动工作流

统一入口的 MCN 内容管理工作流，整合热点调研、选题分析、内容改写、AI 配图、公众号发布于一体。

---

## ⭐ 2026-04-15 核心改进

### 改进 1：确定话题后才抓取原文

**设计原则**：节省资源，避免调研阶段大量下载原文

```
调研阶段（轻量）：
  → 只获取：标题 + 热度 + 平台分类
  → "摘要"来源：热点榜自带描述（如有）或标题本身
  → 不下载原文，不消耗大量 API 资源

选题阶段（关键词匹配）：
  → 基于标题关键词匹配领域
  → 基于热度排序
  → 排除近30天已发布话题

确定话题后（才抓取原文）：
  → 用 web_fetcher 抓取原文全文
  → 提取核心观点、数据、案例
  → 基于原文真实内容改写
  → 确保真实性，不凭空捏造
```

**原文抓取脚本**（确定话题后执行）：
```bash
# 抓取虎嗅/36氪原文
python scripts/fetch-source-article.py --topic "话题名" --urls "原文链接列表"

# 输出：mcn/content/{日期}/source_articles/
# 用于改写时参考，确保真实性
```

---

### 改进 2：多话题文章处理规则

**问题**：热点榜中存在混合标题，如"小米模型，高德机器人，银行xx调整"

**处理规则**：

```python
def is_mixed_topic(title: str) -> bool:
    """检测是否混合话题"""
    
    # 分隔符检测
    separators = ['，', ',', '、', '|', '；']
    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            # 检查各部分是否独立话题
            valid_parts = [p for p in parts if len(p.strip()) >= 4]
            if len(valid_parts) >= 2:
                return True
    
    return False

# 处理策略
if is_mixed_topic(title):
    # 忽略该文章，不纳入选题
    print(f"跳过混合话题: {title}")
    continue
```

**跳过规则**：
- 标题用逗号/顿号分隔多个话题 → 跳过
- 每部分长度 ≥4 字 → 视为独立话题 → 跳过
- 保证最终文章主题单一、聚焦

---

### 改进 3：不同类型改写模板

**模板文件位置**：`templates/content-templates.md`

**文章类型分类**：

| 类型 | 模板 | 特点 | 适用场景 |
|------|------|------|----------|
| 热点评论 | T-01 | 快速响应、观点鲜明 | 社会事件、科技新闻 |
| 干货教程 | T-02 | 实操性强、步骤清晰 | 技术分享、工具使用 |
| 行业分析 | T-03 | 数据支撑、深度解读 | 市场趋势、公司动态 |
| 故事叙述 | T-04 | 情感共鸣、代入感强 | 个人经历、创业故事 |
| 观点争议 | T-05 | 引发讨论、独特视角 | 行业争议、技术选型 |

**改写风格**：

| 风格 | 特征 | 去 AI 化要点 |
|------|------|-------------|
| professional | 客观分析、数据支撑 | 添加"我认为"、"从经验来看" |
| casual | 口语化、接地气 | 用"说实话"、"你想想" |
| story | 叙事感、情感起伏 | 第一人称/内心独白 |

**调用方式**：
```python
# 自动识别文章类型
article_type = detect_article_type(topic, source_content)

# 获取对应模板
template = get_template(article_type, style='casual')

# 基于模板和原文改写
article = rewrite_with_template(template, source_article)
```

详见：`templates/content-templates.md`

---

### 改进 4：配图数量计算公式

**配图结构**：首图（封面）+ 中间图 + 尾图

**计算公式**：
```python
word_count = 文章字数
middle_images = max(0, word_count // 500 - 1)  # 向下取整减1

# 示例：
# 1500字 → floor(1500/500)-1 = 3-1 = 2张中间图
# 1799字 → floor(1799/500)-1 = 3-1 = 2张中间图  
# 2000字 → floor(2000/500)-1 = 4-1 = 3张中间图

# 总配图数量
total_images = 1(封面) + middle_images + 1(尾图)
```

**配图位置规则**：
- 首图：文章开头前（封面）
- 中间图：每约500字一张，插入在段落结束处
- 尾图：文章结尾后（总结/引导图）

**具体位置计算**：
```python
def calculate_image_positions(word_count: int) -> list:
    """计算配图位置"""
    
    middle_count = max(0, word_count // 500 - 1)
    
    # 中间图均匀分布
    # 每 (word_count / (middle_count + 1)) 字一张
    positions = []
    interval = word_count // (middle_count + 1)
    
    for i in range(middle_count):
        # 位置：interval * (i+1) 字处
        # 实际插入：最近的段落结束处
        positions.append(interval * (i + 1))
    
    return positions
```

**字数与配图对照表**：

| 字数范围 | 中间图数量 | 总配图数量 |
|----------|------------|------------|
| 500-999 | 0张 | 2张（首+尾） |
| 1000-1499 | 1张 | 3张 |
| 1500-1999 | 2张 | 4张 |
| 2000-2499 | 3张 | 5张 |

**⚠️ 注意**：
- 计算结果是配图数量上限
- 实际配图还需考虑段落结构
- 配图应插入在段落结束处，而非句子中间

---

### 改进 5：配图异步处理（长时间任务）

**问题**：GrsAI 配图接口响应慢（可能 1800-2000秒），同步等待会阻塞主流程

**解决方案**：异步提交 + 定时轮询 + 自动排版

```
[阶段 1] 提交配图任务
    → 获取 task_id → 记录到 tasks.json → 返回（不阻塞）

[阶段 2] 后台定时任务（Cron，每5分钟）
    → 扫描 pending 任务 → 斐波那契轮询检查结果

[阶段 3] 自动触发排版
    → 检测完成 → 自动排版 → 飞书通知用户
```

#### 斐波那契轮询策略（从3秒开始，最多5次）

```python
def fibonacci_intervals() -> list:
    """斐波那契等待间隔（秒）
    
    从3秒开始，最多5次：
    - 第1次：3秒
    - 第2次：5秒
    - 第3次：8秒
    - 第4次：13秒
    - 第5次：21秒
    
    之后固定每120秒检查一次，直到2000秒超时
    """
    fib_intervals = [3, 5, 8, 13, 21]  # 累计50秒
    max_wait = 2000
    
    # 填充固定120秒间隔
    total = sum(fib_intervals)
    while total + 120 <= max_wait:
        fib_intervals.append(120)
        total += 120
    
    return fib_intervals
```

#### 触发排版条件

```python
def check_layout_ready(tasks: dict) -> tuple[bool, str]:
    """检查是否满足排版条件
    
    条件：
    1. 所有任务状态是 succeeded 或 failed（无 pending）
    2. 成功图片数 >= 3
    3. 必须包含：封面图(cover)、至少1张中间图(img_x)、尾图(end)
    
    返回：(是否满足, 缺少原因)
    """
    succeeded = {k: v for k, v in tasks.items() 
                 if v.get('status') == 'succeeded'}
    
    # 检查数量
    if len(succeeded) < 3:
        return False, f"图片不足：{len(succeeded)}/3"
    
    # 检查类型
    has_cover = any('cover' in k for k in succeeded.keys())
    has_middle = any(k.startswith('img_') for k in succeeded.keys())
    has_end = any('end' in k for k in succeeded.keys())
    
    if not has_cover:
        return False, "缺少封面图"
    if not has_middle:
        return False, "缺少中间图"
    if not has_end:
        return False, "缺少尾图"
    
    return True, "满足条件"
```

#### 不满足时的补图逻辑

```python
def supplement_images(tasks: dict, date: str, topic: str):
    """补足缺失图片
    
    流程：
    1. 计算缺少数量 = 3 - 成功数
    2. 重新生成缺失类型的图片
    3. 提交新任务 → 继续等待循环
    """
    succeeded = [k for k, v in tasks.items() 
                 if v.get('status'] == 'succeeded']
    
    # 检查缺失类型
    need_cover = not any('cover' in k for k in succeeded)
    need_end = not any('end' in k for k in succeeded)
    middle_count = sum(1 for k in succeeded if k.startswith('img_'))
    
    # 计算需要补充的中间图数量（最少1张）
    need_middle = max(0, 1 - middle_count)
    
    # 重新生成
    prompts = []
    if need_cover:
        prompts.append({'name': 'cover_new', 'prompt': f'{topic}封面图...'})
    for i in range(need_middle):
        prompts.append({'name': f'img_{middle_count + i + 1}_new', 
                        'prompt': f'{topic}中间图{i+1}...'})
    if need_end:
        prompts.append({'name': 'end_new', 'prompt': f'{topic}尾图...'})
    
    # 提交新任务（调用 generate-images.py）
    for p in prompts:
        submit_image_task(p['name'], p['prompt'], date)
    
    # 继续等待循环（不排版）
    return len(prompts)
```

#### Cron 配置

```bash
*/5 * * * * cd ~/.hermes/skills/mcn/my-mcn-manager && \
  eval "$(pyenv init -)" && python scripts/poll-image-tasks.py
```

**⚠️ 注意**：
- 每个 task_id 只提交一次（积分保护）
- 斐波那契最多5次（3→5→8→13→21），之后固定120秒
- 超过 2000 秒标记为 timeout
- **触发排版必须满足**：≥3张成功，含封面+中间+尾图
- **不满足则补图**：自动生成缺失图片继续循环

---

### 改进 6：选题排除已发布内容

**问题**：选题分析时未排除已发布文章，可能导致重复选题

**解决方案**：从公众号后台获取已发布文章列表，作为排除依据

```python
def fetch_published_articles():
    """获取公众号已发布文章列表
    
    通过公众号API获取已发布文章：
    1. 获取素材列表（news类型）
    2. 提取标题和发布时间
    3. 保存到 mcn/published_articles.json
    """
    import requests
    
    # 获取 access_token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    token_resp = requests.get(token_url)
    access_token = token_resp.json().get('access_token')
    
    # 获取素材列表
    materials_url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={access_token}"
    payload = {"type": "news", "offset": 0, "count": 20}
    resp = requests.post(materials_url, json=payload)
    
    # 提取标题
    articles = []
    for item in resp.json().get('item', []):
        for content in item.get('content', {}).get('news_item', []):
            articles.append({
                'title': content.get('title'),
                'publish_time': item.get('update_time')
            })
    
    return articles

def exclude_published_topics(hotspots: list, published: list) -> list:
    """排除已发布话题
    
    规则：排除近30天已发布的所有话题（不只是当天）
    """
    import time
    
    cutoff_time = time.time() - 30 * 24 * 3600  # 30天前
    
    # 提取已发布标题关键词
    published_keywords = set()
    for article in published:
        if article['publish_time'] > cutoff_time:
            # 提取标题核心关键词
            title = article['title']
            keywords = extract_keywords(title)
            published_keywords.update(keywords)
    
    # 过滤热点
    filtered = []
    for hotspot in hotspots:
        title = hotspot['title']
        keywords = extract_keywords(title)
        
        # 检查是否有重叠
        overlap = any(k in published_keywords for k in keywords)
        if not overlap:
            filtered.append(hotspot)
        else:
            print(f"排除已发布话题: {title}")
    
    return filtered
```

**执行时机**：选题分析开始时，先获取已发布列表，再进行排除

---

### 改进 7：内容生成后必须去AI化

**问题**：模板改写后的文章仍有AI痕迹（编号列表、抽象分析、结尾互动句）

**解决方案**：内容生成后强制执行去AI化处理

```python
# 工作流顺序
generate_article(topic) → humanize_article(article) → validate_word_count()

# 去 AI 化规则（基于 humanizer-zh 技能）
1. 删除编号列表 → 改为平铺叙述
2. 删除抽象分析句 → "我觉得这背后反映的问题很值得思考"
3. 删除自我定位语 → "作为一个关注科技领域的从业者"
4. 删除结尾互动句 → "你怎么看这件事？欢迎在评论区分享"
5. 变化句子长度 → 长短交错，避免机械重复
```

**触发时机**：模板改写完成后，字数验证前

---

### 改进 8：配图并发提交 + 积分保护

**问题**：串行提交导致等待时间长；重试浪费积分

**解决方案**：并发提交 + 创建拿到id就不重试

```python
# 配图工作流（并发版）
[Step 1] 并发提交所有任务
    → ThreadPoolExecutor(max_workers=count)
    → 每个任务独立提交
    → 拿到 task_id → 记录 → 不重试（绝对禁止）
    → 提交失败 → 记录状态 → 不重试

[Step 2] 并发轮询结果
    → ThreadPoolExecutor(max_workers=count)
    → 每个任务独立轮询
    → result 接口可以重试（不影响积分）
    → 成功 → 下载图片
    → 失败/超时 → 记录 task_id 供找回

# 关键原则
创建接口（/v1/draw/nano-banana）：
  ✅ 拿到 task_id → 成功，不重试
  ❌ 提交失败 → 记录，不重试（积分保护）

轮询接口（/v1/draw/result）：
  ✅ 可以反复查询（不影响积分）
  ⏳ 超时 → 记录 task_id，后续手动找回
```

**积分保护规则**：
- 创建接口成功 → task_id 有效，积分已扣除
- 创建接口失败 → 不重试，避免重复扣积分
- 轮询超时 → task_id 保存，用户可手动找回图片

---

*改进日期：2026-04-15*
*改进内容：原文抓取时机、多话题处理、改写模板、配图计算公式、配图异步处理、选题排除、去AI化、配图并发*

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
|| `调研今天热点` | 阶段 1：热点调研 | mcn/hotspot/{日期}/ |
|| `分析选题` | 阶段 2：选题分析 | mcn/topic/{日期}/recommend.md |
|| `生成文章：主题名` | 阶段 3-4：内容生成 | mcn/content/{日期}/article.md |
|| `生成配图` | 阶段 5：AI 配图 | mcn/images/{日期}/ |
|| `排版文章` | 阶段 6：排版整合 | mcn/content/{日期}/article_formatted.md |
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

**⚠️ 图片路径匹配问题**

配图脚本输出目录：`mcn/images/{date}/`
发布脚本期望目录：`mcn/content/{date}/images/`

发布前需要复制图片：
```bash
# 复制配图到正确位置
mkdir -p ~/backup/知识库-Obsidian/mcn/content/{日期}/images
cp ~/backup/知识库-Obsidian/mcn/images/{日期}/cover_new.png ~/backup/知识库-Obsidian/mcn/content/{日期}/images/cover.png
cp ~/backup/知识库-Obsidian/mcn/images/{日期}/img_*.png ~/backup/知识库-Obsidian/mcn/content/{日期}/images/
```

**建议**：在 publish-draft.py 中自动处理路径匹配，或统一输出目录。

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
mcn/hotspot/2026-04-14/
├── hotspot-aggregated.md
└── ...
```

详见：`references/01-hotspot-research.md`

---

### 模块 2：选题分析

**功能**：分析热搜数据，结合用户关注领域，生成推荐主题列表

**输入**：热点调研结果
**输出**：`mcn/topic/{日期}/recommend.md`

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

使用 **curl 命令** + **假地址 webHook** + 轮询 result 模式：

```
⚠️ 关键发现：requests 库会导致参数丢失（后台显示"无数据"），必须用 curl！

正确方式（curl）：
curl -s -X POST https://grsai.dakka.com.cn/v1/draw/nano-banana \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {API_KEY}" \
  -d '{"model":"nano-banana-fast","prompt":"...","webHook":"http://192.168.1.1","shutProgress":false}'
  
→ 返回 {"code":0,"data":{"id":"task_id"}}
→ 后台正确显示 prompt 和请求参数

错误方式（requests库）：
requests.post(url, headers=headers, json=payload)
→ 积分扣除，但后台显示"无数据"
→ 参数丢失，任务可能失败
```

**提交参数**：
```
1. POST /v1/draw/nano-banana 
   {"model": "nano-banana-fast", "prompt": "...", "webHook": "http://192.168.1.1", "shutProgress": false}
   → 返回 {"data": {"id": "task_id"}}
   
   ⚠️ webHook 必须是假地址（如 http://192.168.1.1），不能是 "-1" 或空！
   ⚠️ 必须用 curl 命令，不能用 requests 库！

2. POST /v1/draw/result {"id": "task_id"}  （轮询，最多60次，间隔5秒）
   → status: "running" → 继续等待
   → status: "succeeded" → 下载图片
   → status: "failed" → 换prompt重试
   → 超过5分钟仍running → 放弃不重试（避免积分浪费）
```

**积分节省要点**：
| 问题 | 解决方案 |
|------|----------|
| **requests库参数丢失** | **必须用 curl 命令提交** |
| 重复提交相同任务 | task_id持久化到tasks.json |
| 超时后重新提交所有 | 检查已有task_id，增量继续 |
| 相同prompt失败后继续 | 换prompt变体，不重复 |
| execute_code超时中断 | 用terminal+curl或subprocess.run(curl) |

**执行脚本**：
```bash
python scripts/generate-images.py --topic "主题名" --count 4 --date YYYY-MM-DD
```

**执行流程**：
1. 根据主题生成关键词列表
2. 批量生成图片（带重试机制，max_retries=2）
3. 验证数量 ≥ 3 张
4. 下载保存到 `mcn/content/{日期}/images/{主题}/`

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

### 领域关键词配置（2026-04-15 修复）

**⚠️ 配置文件 domains 缺少 keywords 字段时**，脚本会使用内置关键词库：

```python
domain_keywords = {
    '科技': ['科技', '芯片', 'ChatGPT', '大模型', '5G', '云计算', 'AI', '人工智能', '手机', '数码'],
    '编程': ['编程', 'GitHub', '开源', '全栈', '前端', '后端', '开发', '代码', '技术'],
    'AI应用': ['AI', 'GPT', '大模型', 'LLM', '深度学习', '机器学习', 'AI创业'],
    '机器人': ['机器人', '自动驾驶', '智能硬件', '无人机', '宇树', '人形机器人'],
    '综合': []
}
```

脚本会优先使用配置中的 keywords，若不存在则使用内置库。

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
| 9 | GrsAI API Key 截断 | 必须用完整原始值 patch，不能用显示截断值 | config |
| 10 | 配图超时无记录 | 提交后立即保存 Task ID 到 tasks.json，方便找回 | image |
| 11 | 公众号配置分散 | 整合到 mcn_config.yaml 的 publish.accounts.main | config |

---

## ⭐ GrsAI Task ID 记录机制

**关键经验**：配图提交后立即记录 Task ID，超时后不重试。

```bash
# 提交任务后立即记录
echo '{"task_id": "xxx", "status": "submitted"}' >> tasks.json

# 超时后用户可通过 Task ID 找回
curl -X POST 'https://grsai.dakka.com.cn/v1/draw/result' \
  -H 'Authorization: Bearer {API_KEY}' \
  -d '{"id": "{TASK_ID"}'
```

**用户明确要求**：超时后不要重试消耗积分，而是记录 ID 让用户自行找回。

---

## ⭐ 配置整合说明

所有配置整合到 `~/.hermes/mcn_config.yaml`：

```yaml
# GrsAI 图片生成
image_generation:
  providers:
    grsai:
      api_key: sk-0c6...完整369  # ⚠️ 必须完整值

# 公众号发布
publish:
  accounts:
    main:
      appid: wx...
      secret: ...
      author: TimeSky
```

⚠️ 旧配置文件 `wechat_mp_config.yaml` 已废弃，整合到主配置。

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

### 2026-04-15 发现的问题

**脚本路径不一致（已修复）**：
- `run-topic-analysis.py`：从 `tmp/hotspot/` 改为 `mcn/hotspot/`
- `push-to-feishu.py`：从 `tmp/topic/` 改为 `mcn/topic/`
- **原因**：早期脚本基于 tmp 目录，后来统一改为 mcn 目录但未同步更新

**正文配图数量硬编码（已修复）**：
- `publish-draft.py` 原只检查 `img_1.png`, `img_2.png`, `img_3.png`
- **修复**：改为动态扫描 `images_dir` 中所有 `img_*.png` 文件
- **影响**：配图数量灵活，无需手动修改脚本

**封面图路径兼容（已修复）**：
- 封面图可能在不同位置：`images_dir/cover.png` 或 `images_dir/cover/cover.png`
- **修复**：添加多候选路径检查，自动定位封面图

**图片插入位置硬编码（已修复）**：
- 原固定在第 3、5、8 段落插入，只支持 3 张图
- **修复**：改为按比例均匀分布（20%/40%/60%/80%），支持任意数量配图

**Python 编码声明缺失**：
- `run-content-gen.py` 缺少 `# -*- coding: utf-8 -*-`
- **修复**：添加编码声明到文件开头

**内容生成脚本占位问题**：
- `run-content-gen.py` 的 generate_titles 和 write_article 是占位实现
- **临时方案**：使用 delegate_task 调用 Hermes LLM 生成文章
- **TODO**：脚本需要集成实际 LLM API

**GrsAI API Key 缺失**：
- 配置文件 `mcn_config.yaml` 缺少 `image_generation` 配置块
- `.env` 文件缺少 `GRSAI_API_KEY`
- **需要配置**：添加到 `.env` 或 `mcn_config.yaml`

### 2026-04-15 Python 环境问题（新增）
- **pyenv 不自动加载**：terminal 执行脚本时需 `eval "$(pyenv init -)"` 初始化
- 默认 python 是系统 2.7，python3 是 3.8.9
- 正确版本：pyenv 3.11.13（`global_env`）
- **解决方案**：脚本执行前加初始化命令

### 2026-04-15 文章路径问题（新增）
- 工作流生成的文章在 `~/.hermes/hermes-agent/article.md`
- 知识库中的可能是占位符或旧版本
- **发布时确认**：检查文章字数是否达标（1500+），避免发布占位符

### 2026-04-14 已记录
- 正文配图必须用素材库 URL
- 配图数量验证机制
- 生成失败重试机制

详见：`~/.hermes/learnings/LRN-20260414-001.md`

---

## ⚠️ 重要注意事项（2026-04-15 更新）

### 1. 配置完整性检查

**技能合并后配置丢失问题**：
- 合并前各独立技能有自己的配置
- 合并后需要统一配置到 `~/.hermes/mcn_config.yaml`
- **必须包含**：
  - `image_generation.providers.grsai.api_key`（完整 key，非截断）
  - `publish.accounts.main.appid/secret`（公众号配置）

**验证配置**：
```bash
cat ~/.hermes/mcn_config.yaml | grep -A5 "image_generation:" | grep "api_key"
cat ~/.hermes/mcn_config.yaml | grep -A5 "publish:" | grep "appid"
```

### 2. 积分消耗任务的保护机制

**⚠️ 绝对禁止**：对消耗积分的任务（配图生成）执行重试

当配图生成失败或超时时：
1. **记录 Task ID** → 保存到 `tasks.json` 供后续找回
2. **不重试** → 避免积分浪费
3. **用户选择** → 使用已生成图片、手动配图、或跳过

**正确流程**：
```
提交任务 → 记录 Task ID → 等待完成 → 失败则停止，不重试
```

### 3. 问题诊断优先级

出现问题时应按以下顺序处理：
1. **检查脚本配置** → API Key、路径、依赖
2. **检查配置文件** → YAML 格式、完整值（非截断）
3. **人工介入** → 不用命令行重试消耗性任务

### 4. 配置修改注意事项

**⚠️ patch 时必须用完整原始值**：

错误示例（会破坏配置）：
```python
patch(old_string="api_key: sk-0c6...e369", new_string="...")  # 截断值
```

正确示例：
```python
# 必须从原始来源获取完整 key
api_key = "sk-0c6f0263a0d24861bf954f5a7154e369"  # 完整值
```

### 5. Python 执行环境

**⚠️ terminal 工具不自动加载 pyenv**：

```bash
# 正确执行方式
eval "$(pyenv init -)" && python scripts/publish-draft.py --article article.md --date 2026-04-15

# 错误方式（用系统 python3）
python3 scripts/publish-draft.py  # 会调用 3.8.9，缺少依赖
```

系统环境：pyenv 3.11.13（默认），需手动初始化。

### 6. 文章路径确认

**发布前必须确认文章来源**：
- 工作流生成的文章：`~/.hermes/hermes-agent/article.md`（正确）
- 知识库 tmp 目录：可能是占位符（错误）

```bash
# 检查文章字数
wc -w ~/.hermes/hermes-agent/article.md
# 应显示 1500+ 字，否则是占位符
```

---

*Last updated: 2026-04-15 by Luna*
*修复内容：路径统一(tmp→mcn)、API Key读取(环境变量→YAML)、积分保护机制、Python环境(pyenv)、文章路径确认*

---

*Last updated: 2026-04-15 by Luna*
*整合自：mcn-hotspot-aggregator, mcn-topic-selector, mcn-content-rewriter, mcn-wechat-publisher*
