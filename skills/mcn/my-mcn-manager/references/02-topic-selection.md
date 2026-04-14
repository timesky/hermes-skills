---
module: 02-topic-selection
type: reference
source: mcn-topic-selector (整合)
---

# 模块 2: 选题分析

分析热搜数据，结合用户关注领域，生成推荐主题列表。

---

## 输入输出

**输入**：`tmp/hotspot/{日期}/*.md` 热搜数据
**输出**：`tmp/topic/{日期}/recommend.md` 选题报告

---

## 分析维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 热度评分 | 30% | 平台热度数据（阅读量、讨论数） |
| 相关性评分 | 30% | 与关注领域关键词匹配度 |
| 时效性评分 | 20% | 话题新鲜度（上升速度） |
| 排重检查 | 20% | 近 30 天已发布主题过滤 |

---

## 执行流程

### 1. 读取热搜数据

```python
import glob
import yaml

def load_hotspot_data(date: str) -> list:
    """加载指定日期的热搜数据"""
    pattern = f"/Users/timesky/backup/知识库-Obsidian/tmp/hotspot/{date}/*.md"
    files = glob.glob(pattern)
    
    all_items = []
    for f in files:
        content = open(f, encoding='utf-8').read()
        # 解析 Markdown 表格提取热搜项
        items = parse_hotspot_table(content)
        all_items.extend(items)
    
    return all_items
```

### 2. 加载配置

```python
config = yaml.safe_load(open("/Users/timesky/.hermes/mcn_config.yaml"))

domains = config['hotspot']['domains']  # 科技、编程、机器人
exclude_keywords = config['hotspot']['exclude_published']['keywords']  # 已发布主题
```

### 3. 评分算法

```python
def score_topic(item: dict, domains: list) -> dict:
    """对热搜话题评分"""
    
    title = item['title'].lower()
    heat = item.get('heat', 0)
    
    # 热度评分 (0-100)
    heat_score = min(100, heat / 10000 * 100)
    
    # 相关性评分 (0-100)
    relevance_score = 0
    matched_domain = None
    for domain in domains:
        for keyword in domain['keywords']:
            if keyword.lower() in title:
                relevance_score = 80 + (len(keyword) * 5)  # 关键词越长权重越高
                matched_domain = domain['name']
                break
    
    # 时效性评分 (0-100)
    # 根据话题上升速度计算
    
    # 排重检查
    duplicate = False
    for kw in exclude_keywords:
        if kw.lower() in title:
            duplicate = True
            break
    
    total_score = heat_score * 0.3 + relevance_score * 0.3 + 20  # 简化版
    
    return {
        'title': item['title'],
        'heat': heat,
        'heat_score': heat_score,
        'relevance_score': relevance_score,
        'matched_domain': matched_domain,
        'duplicate': duplicate,
        'total_score': total_score,
        'source_url': item.get('url', '')
    }
```

### 4. 生成推荐报告

```python
def generate_recommend_report(scored_items: list, top_n: int = 5) -> str:
    """生成选题推荐报告"""
    
    # 过滤重复项，按分数排序
    unique_items = [item for item in scored_items if not item['duplicate']]
    sorted_items = sorted(unique_items, key=lambda x: x['total_score'], reverse=True)
    
    report = """---
created: YYYY-MM-DD HH:MM
type: topic-recommend
status: pending
---

# MCN 选题分析报告

## 推荐主题 (Top 5)

| 排名 | 主题 | 领域 | 热度 | 综合评分 | 来源 |
|------|------|------|------|----------|------|
"""
    
    for i, item in enumerate(sorted_items[:top_n], 1):
        report += f"| {i} | {item['title']} | {item['matched_domain']} | {item['heat']} | {item['total_score']:.1f} | [查看]({item['source_url']}) |\n"
    
    report += """
## 选题建议

1. **优先选择**：评分高 + 领域匹配的话题
2. **避免重复**：已排除近 30 天发布过的主题
3. **时效性**：优先选择上升期话题

## 下一步

确认主题后执行：`生成文章：主题名`
"""
    
    return report
```

---

## 输出格式

```markdown
---
created: 2026-04-14 17:30
type: topic-recommend
status: pending
---

# MCN 选题分析报告

## 推荐主题 (Top 5)

| 排名 | 主题 | 领域 | 热度 | 综合评分 | 来源 |
|------|------|------|------|----------|------|
| 1 | xxx | 科技 | 12345 | 85.5 | [查看](url) |
| 2 | xxx | 编程 | 6789 | 78.2 | [查看](url) |

## 选题建议
...
```

---

## Pitfalls

1. **排重检查**：必须检查近 30 天已发布主题
2. **领域匹配**：关键词匹配要区分大小写
3. **分数阈值**：低于 50 分的话题不建议推荐
4. **来源链接**：必须保留原始链接供用户参考

---

*整合自：mcn-topic-selector*
