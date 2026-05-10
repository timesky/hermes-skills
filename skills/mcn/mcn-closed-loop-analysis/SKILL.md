---
name: mcn-closed-loop-analysis
description: MCN 闭环反馈分析技能 v2.0 - 自演进版本。分析数据 → 更新特征库 → 调整策略参数 → 优化提示词。实现持续学习闭环。
version: 2.0.0
triggers:
  - 闭环分析
  - 反馈分析
  - MCN 闭环
  - 文章数据分析
  - 自演进
  - 模式学习
parent: my-mcn-manager
---

# MCN 闭环反馈分析

## 概述

闭环分析是 MCN 工作流的第 8-9 阶段，实现 **自演进闭环**：

```
数据采集 → 特征提取 → 模式学习 → 策略调整 → 效果验证
```

### 核心能力（v2.0 新增）

1. **自动特征提取** - 分析标题、内容、发布时间等特征
2. **模式学习** - 识别高阅读文章的共同特征
3. **策略自动调整** - 更新评分权重和提示词
4. **效果追踪** - 验证策略调整效果

## 数据结构（v2.0）

### 标题特征库

位置：`mcn/data/title_features.json`

```json
{
  "high_perform": [
    {
      "title": "标题",
      "features": ["吐槽", "情绪词"],
      "read_count": 45,
      "open_rate": 0.14,
      "success_score": 85
    }
  ],
  "low_perform": [...],
  "patterns": {
    "吐槽类平均阅读": 45,
    "教程类平均阅读": 4
  }
}
```

### 策略参数库

位置：`mcn/data/strategy_params.json`

```json
{
  "topic_scoring": {
    "type_bonus": {"吐槽避坑": 50},
    "deduction": {"系列文": -20}
  },
  "title_scoring": {
    "数字加分": 20,
    "阈值": 30
  }
}
```

## 自演进流程（v2.0 核心）

### Step 0: 加载当前策略

```python
import json
import os

def load_strategy_params():
    """加载当前策略参数"""
    path = "/Users/hy_timesky/Documents/My_Obsidian/mcn/data/strategy_params.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_title_features():
    """加载标题特征库"""
    path = "/Users/hy_timesky/Documents/My_Obsidian/mcn/data/title_features.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
```

### Step 1: 提取标题特征

```python
def extract_title_features(title):
    """提取标题特征"""
    features = []
    
    # 类型特征
    type_keywords = {
        "吐槽": ["吐槽", "避坑", "踩坑", "后悔", "上当", "玩不起"],
        "教程": ["教程", "指南", "如何", "怎么", "入门"],
        "分析": ["分析", "解读", "揭秘", "深度"]
    }
    
    for type_name, keywords in type_keywords.items():
        if any(kw in title for kw in keywords):
            features.append(type_name)
    
    # 结构特征
    if any(c.isdigit() for c in title):
        features.append("含数字")
    if "？" in title or "?" in title:
        features.append("疑问句")
    
    # 情绪特征
    emotion_words = ["震惊", "意外", "没想到", "竟然", "居然", "坑", "惨"]
    if any(ew in title for ew in emotion_words):
        features.append("情绪词")
    
    return features
```

### Step 2: 更新特征库

```python
def update_title_features(title, read_count, open_rate):
    """更新标题特征库"""
    features_data = load_title_features()
    
    # 提取特征
    features = extract_title_features(title)
    
    # 计算成功分数
    success_score = min(100, read_count * 2 + open_rate * 100)
    
    # 分类入库
    entry = {
        "title": title,
        "features": features,
        "read_count": read_count,
        "open_rate": open_rate,
        "success_score": success_score,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    if success_score >= 30:
        features_data["high_perform"].append(entry)
    else:
        features_data["low_perform"].append(entry)
    
    # 更新模式统计
    for feature in features:
        key = f"{feature}类平均阅读"
        # 移动平均更新
        old_avg = features_data["patterns"].get(key, 0)
        new_avg = old_avg * 0.8 + read_count * 0.2
        features_data["patterns"][key] = round(new_avg, 1)
    
    # 保存
    save_title_features(features_data)
    return features
```

### Step 3: 模式学习

```python
def learn_patterns():
    """模式学习 - 提取成功模式"""
    features_data = load_title_features()
    
    # 统计高表现文章特征
    feature_scores = {}
    for article in features_data["high_perform"]:
        for feature in article["features"]:
            if feature not in feature_scores:
                feature_scores[feature] = []
            feature_scores[feature].append(article["read_count"])
    
    # 计算平均阅读
    pattern_insights = {}
    for feature, reads in feature_scores.items():
        avg_read = sum(reads) / len(reads)
        pattern_insights[feature] = {
            "avg_read": round(avg_read, 1),
            "sample_count": len(reads),
            "recommendation": "增加权重" if avg_read > 20 else "保持"
        }
    
    return pattern_insights
```

### Step 4: 调整策略参数

```python
def adjust_strategy_params():
    """根据学习结果调整策略参数"""
    strategy = load_strategy_params()
    patterns = learn_patterns()
    
    # 调整选题评分权重
    for feature, data in patterns.items():
        if feature in ["吐槽", "避坑"]:
            if data["avg_read"] > 30:
                strategy["topic_scoring"]["type_bonus"]["吐槽避坑"] = 60
            elif data["avg_read"] > 20:
                strategy["topic_scoring"]["type_bonus"]["吐槽避坑"] = 55
        elif feature in ["教程"]:
            if data["avg_read"] < 10:
                strategy["topic_scoring"]["type_bonus"]["教程实践"] = 20
    
    # 调整标题评分阈值
    avg_success = strategy["stats"]["avg_read"]
    if avg_success < 10:
        strategy["title_scoring"]["阈值"] = 40  # 提高门槛
    elif avg_success > 50:
        strategy["title_scoring"]["阈值"] = 25  # 降低门槛
    
    save_strategy_params(strategy)
    return strategy
```

### Step 5: 效果验证

```python
def validate_effect():
    """验证策略调整效果"""
    strategy = load_strategy_params()
    
    # 计算最近7天平均阅读
    # (需要从 wechat-analytics 获取数据)
    recent_avg = get_recent_avg_read(days=7)
    
    target = strategy["stats"]["target"]
    gap = target - recent_avg
    
    report = {
        "current_avg": recent_avg,
        "target": target,
        "gap": gap,
        "status": "达标" if gap <= 0 else f"差距{gap}",
        "strategy_adjustment": "需要强化" if gap > 50 else "微调优化"
    }
    
    # 飞书通知
    if gap <= 0:
        push_to_feishu(f"🎉 目标达成！平均阅读 {recent_avg}，新目标 {target * 1.5}")
        strategy["stats"]["target"] = int(target * 1.5)
    
    return report
```

## 执行入口

### 每日闭环（24h 追踪）

```python
def daily_closed_loop(article_id, title):
    """每日闭环 - 发布后 24 小时执行"""
    
    # 1. 获取文章数据
    stats = fetch_article_stats(article_id)
    read_count = stats["read_count"]
    open_rate = stats["read_count"] / stats["send_count"] if stats["send_count"] > 0 else 0
    
    # 2. 更新特征库
    features = update_title_features(title, read_count, open_rate)
    
    # 3. 微调策略
    adjust_strategy_params()
    
    # 4. 记录日志
    log_entry = {
        "date": datetime.now().isoformat(),
        "article_id": article_id,
        "title": title,
        "read_count": read_count,
        "features": features
    }
    append_to_daily_log(log_entry)
    
    return {"status": "ok", "features": features}
```

### 每周闭环（模式学习）

```python
def weekly_closed_loop():
    """每周闭环 - 周一 21:00 执行"""
    
    # 1. 学习模式
    patterns = learn_patterns()
    
    # 2. 调整策略
    strategy = adjust_strategy_params()
    
    # 3. 更新提示词
    update_writer_template(patterns)
    
    # 4. 效果验证
    report = validate_effect()
    
    # 5. 飞书报告
    push_weekly_report(patterns, strategy, report)
    
    return report
```

## 数据依赖

### 必需数据源

| 数据源 | 位置 | 用途 |
|--------|------|------|
| 微信公众号数据 | wechat-analytics 技能 | 阅读数、点赞数、收藏数、转发数 |
| 原文数据 | `mcn/topic/{date}/sources/topic-{idx}/source.json` | 对比分析 |
| 竞品数据 | `mcn/topic/{date}/sources/topic-{idx}/competitors.json` | 竞品对比 |
| 已生成文章 | `mcn/content/{date}/{title}/article.md` | 内容分析 |

### 可选数据源（降级时使用）

| 数据源 | 位置 | 用途 |
|--------|------|------|
| 热点数据 | `mcn/hotspot/{date}/hotspots.json` | 热点趋势分析 |
| 选题推荐 | `mcn/topic/{date}/recommend.md` | 选题匹配 |

## 执行流程

### 完整流程（所有数据可用）

```
Step 1: 获取微信统计数据
  └─ 使用 wechat-analytics 技能
  └─ 获取最近 15 天文章数据

Step 2: 读取原文和竞品数据
  └─ 从 sources/ 目录读取预抓取数据

Step 3: 对比分析
  └─ vs 原文：阅读数、点赞率差距
  └─ vs 竞品：高表现文章成功因素

Step 4: 交叉分析（6 维度）
  └─ 标题、内容、写作风格、表达方式、排版、引流话术

Step 5: 输出优化建议
  └─ 生成飞书报告

Step 6: 更新提示词
  └─ 更新 content-template.md 和 style-guide.md
```

### 降级流程（数据不可用）

当 `wechat-analytics` 技能不可用或数据缺失时：

```
Step 1: 检查可用数据
  └─ 列出 mcn/content/ 下所有文章
  └─ 列出 mcn/hotspot/ 下所有热点数据
  └─ 检查 sources/ 目录是否存在

Step 2: 内容分析
  └─ 统计字数、段落数、章节数
  └─ 检测 AI 痕迹词频率
  └─ 分析口语化程度

Step 3: 热点趋势分析
  └─ 统计平台分布
  └─ 识别 AI/科技相关热点
  └─ 提取高热度选题

Step 4: 生成部分分析报告
  └─ 说明数据限制
  └─ 提供可执行的优化建议
  └─ 列出下一步行动

Step 5: 推送飞书通知
```

## 代码示例

### 检查数据可用性

```python
import os

def check_data_availability(base_path):
    """检查闭环分析所需数据是否可用"""
    
    availability = {
        "articles": False,
        "hotspots": False,
        "sources": False,
        "wechat_stats": False
    }
    
    # 检查文章
    content_dir = os.path.join(base_path, "content")
    if os.path.exists(content_dir):
        articles = [d for d in os.listdir(content_dir) if os.path.isdir(os.path.join(content_dir, d))]
        availability["articles"] = len(articles) > 0
    
    # 检查热点
    hotspot_dir = os.path.join(base_path, "hotspot")
    if os.path.exists(hotspot_dir):
        hotspots = [f for f in os.listdir(hotspot_dir) if os.path.isdir(os.path.join(hotspot_dir, f))]
        availability["hotspots"] = len(hotspots) > 0
    
    # 检查原文/竞品数据
    topic_dir = os.path.join(base_path, "topic")
    if os.path.exists(topic_dir):
        for date_dir in os.listdir(topic_dir):
            sources_dir = os.path.join(topic_dir, date_dir, "sources")
            if os.path.exists(sources_dir):
                availability["sources"] = True
                break
    
    return availability
```

### 内容分析

```python
import re

def analyze_article(content):
    """分析文章内容"""
    
    # 提取标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else "无标题"
    
    # 统计字数（排除 frontmatter 和 markdown 标记）
    text_content = re.sub(r'^---.*?---', '', content, flags=re.DOTALL)
    text_content = re.sub(r'[#*\-\s\n|>]', '', text_content)
    word_count = len(text_content)
    
    # 提取章节
    sections = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
    
    # 检测 AI 痕迹词
    ai_patterns = ['说实话', '怎么说呢', '值得一提的是', '总而言之', '综上所述', '不得不说']
    ai_trace_count = sum(content.count(p) for p in ai_patterns)
    
    # 检测口语化表达
    casual_patterns = ['你想想', '我觉得', '我发现']
    casual_count = sum(content.count(p) for p in casual_patterns)
    
    return {
        "title": title,
        "word_count": word_count,
        "sections": sections,
        "ai_trace_count": ai_trace_count,
        "casual_count": casual_count
    }
```

### 飞书推送

```python
import json
import urllib.request
import os

def push_to_feishu(report_content, channel_id=None):
    """推送报告到飞书群"""
    
    FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', '')
    FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', '')
    FEISHU_HOME_CHANNEL = channel_id or os.environ.get('FEISHU_HOME_CHANNEL', '')
    
    # 获取 token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'),
                                headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        token_result = json.loads(response.read().decode('utf-8'))
    
    if token_result.get('code') != 0:
        return {"error": "Failed to get token"}
    
    access_token = token_result['tenant_access_token']
    
    # 发送消息
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    data = {
        "receive_id": FEISHU_HOME_CHANNEL,
        "msg_type": "text",
        "content": json.dumps({"text": report_content}, ensure_ascii=False)
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'),
                                headers={
                                    'Content-Type': 'application/json',
                                    'Authorization': f'Bearer {access_token}'
                                })
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))
```

## 报告模板

```markdown
## MCN 闭环分析报告 - {日期}

### ⚠️ 数据获取限制（如有）

[列出不可用的数据源和原因]

### 📊 已生成文章概览

| 日期 | 标题 | 字数 | 状态 | 小节数 |
|------|------|------|------|--------|
| ... | ... | ... | ... | ... |

### 📈 热点数据统计

[热点趋势分析]

### 🔍 文章内容分析

[逐篇分析]

### 💡 优化建议

#### 标题优化
- **发现**: ...
- **建议**: ...

#### 内容优化
- **发现**: ...
- **建议**: ...

#### 风格优化
- **发现**: ...
- **建议**: ...

### 📝 提示词调整建议

[具体提示词修改]

### 🚀 下一步行动

[待处理事项]

---
报告时间: {时间}
```

## Pitfalls

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **wechat-analytics 技能缺失** | 未安装 | 使用降级流程，基于本地数据分析 |
| **微信 API IP 白名单** | 当前 IP 未配置 | 登录后台添加 IP 白名单 |
| **sources/ 目录不存在** | 选题阶段未预抓取 | 提醒启用数据预抓取 |
| **飞书推送失败** | 凭据无效或过期 | 检查环境变量 FEISHU_APP_ID/SECRET |
| **报告超长** | 飞书消息长度限制 | 分段发送或使用富文本卡片 |

## 环境变量

| 变量名 | 用途 | 必需 |
|--------|------|------|
| `FEISHU_APP_ID` | 飞书应用 ID | 是 |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 是 |
| `FEISHU_HOME_CHANNEL` | 默认推送群 | 是 |

## 下一步行动模板

当数据不可用时，报告中应包含：

1. **配置 IP 白名单**
   - 登录微信公众号后台
   - 设置 → 公众号设置 → 功能设置 → IP白名单
   - 添加当前 IP

2. **安装 wechat-analytics 技能**
   ```bash
   hermes skill install wechat-analytics
   ```

3. **启用数据预抓取**
   - 在选题阶段创建 sources/ 目录结构
   - 抓取原文和竞品数据

4. **手动获取统计数据**
   - 登录微信公众号后台
   - 导出最近 15 天文章数据
   - 手动更新分析报告

---

## 版本管理系统（v2.1 新增）

**要求**：每次参数调整必须记录版本，支持回退。

### 自动调整流程

```
1. 检测触发条件（平均阅读<5持续3天）
2. 加载当前策略版本
3. 计算调整参数
4. 创建新版本（调用 strategy_version_manager.py）
5. 更新技能文件（同步参数）
6. 观察3天效果
7. 若效果差 → 回退到上一版本
```

### 版本文件结构

```
mcn/data/
├── strategy_registry.json      # 版本索引
├── strategy_versions/          # 版本历史
│   ├── v1.0.0_20260501.json
│   ├── v1.1.0_20260508.json
│   └── ...
├── adjustment_log.json         # 调整日志
└── rollback_history.json       # 回退历史
```

### 回退命令

```bash
# 回退到指定版本
python scripts/strategy_version_manager.py --action rollback --version v1.0.0 --reason "效果不佳，平均阅读下降"

# 查看历史
python scripts/strategy_version_manager.py --action history

# 对比版本
python scripts/strategy_version_manager.py --action compare --v1 v1.0.0 --v2 v1.1.0
```

---

## 触发条件与调整动作

| 指标 | 阈值 | 触发动作 | 版本类型 |
|------|------|----------|----------|
| 平均阅读 < 5 | 连续3天 | 标题情绪词权重+10 | tune (v1.x) |
| 打开率 < 1% | 连续5篇 | 吐槽加分+10 | tune |
| 某类型阅读 > 50 | 连续3篇 | 该类型加分+20 | tune |
| 系列文打开率低 | 检测到 | 减分项权重+5 | tune |
| 核心指标持续下降 | 7天 | 回退上一版本 | rollback |

---

## 观察周期

| 版本类型 | 观察周期 | 效果评估 |
|---------|---------|---------|
| tune | 3天 | 对比调整前后平均阅读 |
| major | 7天 | 全指标对比 |
| rollback | 3天 | 确认回退有效 |

---

*Version: 2.1.0 - 新增版本管理系统，支持可追溯可回退*

*Created: 2026-04-29*
