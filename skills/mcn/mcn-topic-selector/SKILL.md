---
name: mcn-topic-selector
description: MCN 选题分析技能 - 分析热搜聚合结果，结合用户关注领域，生成选题建议报告
tags: [mcn, topic, selector, analysis]
version: 1.0.0
created: 2026-04-12
author: Luna
---

# MCN 选题分析技能

分析热搜聚合结果，结合用户关注领域，生成选题建议报告。

---

## 知识库路径

```
KB_ROOT = /Users/timesky/backup/知识库-Obsidian
HOTSPOT_DIR = KB_ROOT/tmp/hotspot/
TOPIC_DIR = KB_ROOT/tmp/topic/
USER_INTERESTS = KB_ROOT/raw/notes/MCN运营调研/
```

---

## 用户关注领域

TimeSky 的关注领域（从知识库分析）：
- AI 工具和 AI 研究
- 后端架构
- 量化研究
- 投资理财
- 环境与运维

---

## 选题分析流程

### 1. 读取热搜聚合

```python
import os
import glob
import json
from datetime import datetime

def read_hotspot_files(date: str):
    """读取指定日期的热搜文件"""
    pattern = f"{KB_ROOT}/tmp/hotspot/{date}/*.md"
    files = glob.glob(pattern)
    
    hotspots = {}
    for f in files:
        platform = os.path.basename(f).replace('-hotspot.md', '')
        # 解析 Markdown 中的 JSON
        content = open(f).read()
        json_match = re.search(r'```json\n(.+?)\n```', content, re.DOTALL)
        if json_match:
            hotspots[platform] = json.loads(json_match.group(1))
    
    return hotspots
```

### 2. 相关性评分

根据用户关注领域评分：

| 领域 | 关键词 | 权重 |
|------|--------|------|
| AI/LLM | AI, LLM, model, GPT, Claude, 机器学习, 大模型 | 10 |
| 后端架构 | 架构, 分布式, 微服务, Docker, K8s, 云原生 | 8 |
| 量化研究 | 量化, 交易, 算法交易, 回测, 因子 | 8 |
| 投资理财 | 投资, 股票, 基金, 理财, 金融 | 7 |
| 环境运维 | 运维, DevOps, CI/CD, Linux, 部署 | 6 |
| 通用热点 | 高热度话题（>100万） | 基础分 + 热度/10万 |

### 3. 生成选题报告

```markdown
---
created: YYYY-MM-DD HH:MM
status: pending
type: topic-report
---

# YYYY-MM-DD 选题分析报告

## 热搜概览

- 知乎: 20 条
- 微博: 20 条
- 抖音: 20 条
- 小红书: 20 条
- HackerNews: 20 条
- B站: 20 条

## 推荐选题

### 🔥 高相关性选题

| 来源 | 标题 | 相关领域 | 热度 | 推荐指数 |
|------|------|----------|------|----------|
| 知乎 | 小米推出 MiMo 大模型订阅套餐 | AI/LLM | 140万 | ⭐⭐⭐⭐⭐ |
| 知乎 | 公众号批量删除AI写作文章 | AI/LLM | 111万 | ⭐⭐⭐⭐⭐ |

### 💡 中相关性选题

| 来源 | 标题 | 相关领域 | 热度 | 推荐指数 |
|------|------|----------|------|----------|

### 📈 高热度选题（可能适合）

| 来源 | 标题 | 热度 | 改写难度 |
|------|------|------|----------|

## 选题建议

### 今日推荐（Top 5）

1. **小米推出 MiMo 大模型订阅套餐**
   - 相关性: AI/LLM ✅
   - 热度: 140万（高）
   - 改写方向: 从技术角度分析大模型定价策略
   
2. **公众号批量删除AI写作文章**
   - 相关性: AI/LLM ✅
   - 热度: 111万（中高）
   - 改写方向: AI写作合规性探讨

3. ...

## Meta
- 分析时间: YYYY-MM-DD HH:MM
- 热搜来源: 6 个平台
- 推荐选题: 5 个
```

---

## 评分算法

```python
def calculate_relevance(title: str, heat: int) -> dict:
    """计算选题相关性"""
    
    # 关键词匹配
    ai_keywords = ['AI', 'LLM', 'model', 'GPT', 'Claude', '机器学习', '大模型', '人工智能', '算法']
    tech_keywords = ['架构', '分布式', '微服务', 'Docker', 'K8s', '云原生', '后端', '代码', '开发']
    finance_keywords = ['投资', '股票', '基金', '理财', '金融', '量化', '交易']
    
    relevance_score = 0
    matched_domain = None
    
    # AI 相关
    for kw in ai_keywords:
        if kw.lower() in title.lower():
            relevance_score = 10
            matched_domain = 'AI/LLM'
            break
    
    # 技术相关
    if not matched_domain:
        for kw in tech_keywords:
            if kw.lower() in title.lower():
                relevance_score = 8
                matched_domain = '技术架构'
                break
    
    # 金融相关
    if not matched_domain:
        for kw in finance_keywords:
            if kw.lower() in title.lower():
                relevance_score = 7
                matched_domain = '投资理财'
                break
    
    # 热度加分
    heat_bonus = min(heat / 100000, 5)  # 最高加 5 分
    
    final_score = relevance_score + heat_bonus
    
    return {
        'score': final_score,
        'domain': matched_domain,
        'heat_bonus': heat_bonus
    }
```

---

## 输出目录结构

```
tmp/topic/
└── YYYY-MM-DD/
    └── topic-report.md
```

---

## ⭐ 排除已发布文章（必须执行）

**规则**：排除近1个月已发布的所有话题（不只是当天）

```python
def get_published_articles(days: int = 30) -> list:
    """获取近N天已发布文章列表"""
    
    from datetime import datetime, timedelta
    
    # 来源1：公众号后台抓取（需定期更新）
    # 来源2：MCN配置中的记录
    config_path = Path.home() / ".hermes" / "mcn_config.yaml"
    config = yaml.safe_load(config_path.read_text())
    
    published = config.get('published_articles', [])
    
    # 过滤近N天
    cutoff_date = datetime.now() - timedelta(days=days)
    
    recent_published = []
    for article in published:
        article_date = datetime.strptime(article['date'], '%Y-%m-%d')
        if article_date >= cutoff_date:
            recent_published.append(article)
    
    return recent_published

def extract_exclude_keywords(article_topic: str) -> list:
    """提取有效排除关键词（过滤单字母、型号后缀）"""
    
    # 常见型号后缀（不应作为排除关键词）
    stopwords = ['X', 'Max', 'Pro', 'Mini', 'Ultra', 'Plus', 'SE', 'Lite']
    
    keywords = []
    parts = article_topic.split() if ' ' in article_topic else [article_topic]
    
    for part in parts:
        # 过滤单字母和停用词
        if len(part) > 1 and part not in stopwords:
            keywords.append(part)
    
    return keywords

def filter_published_topics(hotspots: list, published_articles: list) -> list:
    """过滤已发布话题"""
    
    # 提取排除关键词
    exclude_keywords = []
    for article in published_articles:
        keywords = extract_exclude_keywords(article['topic'])
        exclude_keywords.extend(keywords)
    
    # 过滤热点
    new_hotspots = []
    for hotspot in hotspots:
        is_excluded = False
        title = hotspot.get('title', '').lower()
        
        for kw in exclude_keywords:
            if kw.lower() in title:
                is_excluded = True
                print(f"排除: {hotspot['title']} (关键词: {kw})")
                break
        
        if not is_excluded:
            new_hotspots.append(hotspot)
    
    return new_hotspots
```

**配置已发布文章列表**：
```yaml
# ~/.hermes/mcn_config.yaml
published_articles:
  - title: "宇树机器人10米每秒：博尔特记录要被破了"
    date: "2026-04-12"
    topic: "宇树机器人"
  - title: "小米 MiMo 定价：为何不想贱卖 token"
    date: "2026-04-12"
    topic: "小米MiMo"
  # ... 定期更新
```

---

## Pitfalls

1. **热度值单位不同**: 知乎用"万热度"，微博用数字，需要统一
2. **重复话题去重**: 不同平台可能有相同话题
3. **避免负面话题**: 跳过敏感/负面内容
4. **保持多样性**: 不要只选 AI 相关，适当混合高热度通用话题
5. **⚠️ 排除近1个月**: 不只是当天，要排除近30天已发布的所有话题
6. **关键词过滤**: 避免单字母误排除（如"X"、"Max"等型号后缀）

---

## 与入口技能的关系

**入口技能**：`wechat-mp-auto-publish`（MCN 唯一入口，定时任务 + 人工确认 + 一键执行）

**子技能**（可单独调用）：
- `mcn-hotspot-aggregator`: 热搜抓取
- `mcn-topic-selector`: 选题分析
- `mcn-content-rewriter`: 内容改写
- `mcn-wechat-publisher`: 公众号发布

---

## 相关技能

- `mcn-hotspot-aggregator`: 热搜聚合（前置）
- `mcn-content-rewriter`: 内容改写（后置）
- `wiki-auto-save`: 知识库保存

---

*Last updated: 2026-04-12 by Luna*