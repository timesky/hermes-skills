#!/usr/bin/env python3
"""选题分析脚本"""

import glob
import json
import os
import re
import yaml
import argparse
from datetime import datetime

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = f"{KB_ROOT}/mcn"
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")

def load_config():
    with open(MCN_CONFIG) as f:
        return yaml.safe_load(f)

def load_hotspot_data(date: str) -> list:
    """从 mcn/hotspot/{date}/hotspot-aggregated.md 读取热点数据"""
    filepath = f"{MCN_ROOT}/hotspot/{date}/hotspot-aggregated.md"
    
    if not os.path.exists(filepath):
        print(f"⚠️ 未找到 {date} 的热搜数据: {filepath}")
        return []
    
    content = open(filepath, encoding='utf-8').read()
    all_items = []
    
    # 解析 Markdown 列表格式: 1. [title](url) [category] (热度:xxx)
    for line in content.split('\n'):
        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.', '12.', '13.', '14.', '15.', '16.', '17.', '18.', '19.', '20.')):
            # 提取标题和链接
            match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()
                
                # 提取热度 (热度:xxx)
                heat_match = re.search(r'热度[:\s]*(\d+)', line)
                heat = heat_match.group(1) if heat_match else 'N/A'
                
                # 提取来源（从分组标题推断）
                source = 'unknown'
                
                item = {
                    'rank': len(all_items) + 1,
                    'title': title,
                    'heat': heat,
                    'url': url,
                    'source': source
                }
                all_items.append(item)
    
    print(f"✓ 加载 {len(all_items)} 条热搜数据")
    return all_items

def score_topic(item: dict, domains: list) -> dict:
    title = item['title']
    title_lower = title.lower()
    
    heat_str = str(item.get('heat', '0'))
    heat = 0
    heat_str = heat_str.replace(',', '').replace('热度', '').replace(' ', '')
    
    if '万' in heat_str:
        try:
            heat = float(heat_str.replace('万', '')) * 10000
        except:
            heat = 0
    elif '亿' in heat_str:
        try:
            heat = float(heat_str.replace('亿', '')) * 100000000
        except:
            heat = 0
    else:
        try:
            heat = float(heat_str)
        except:
            heat = 0
    
    heat_score = min(100, heat / 100000 * 100)
    
    relevance_score = 0
    matched_domain = None
    
    # 关键词库：每个领域的匹配关键词
    domain_keywords = {
        '科技': ['科技', '芯片', 'ChatGPT', '大模型', '5G', '云计算', 'AI', '人工智能', '手机', '数码', '3C', '智能', '互联网'],
        '编程': ['编程', 'GitHub', '开源', '全栈', '前端', '后端', '开发', '代码', '技术', '软件', '算法', '掘金'],
        'AI应用': ['AI', 'GPT', '大模型', 'LLM', '深度学习', '机器学习', 'AI创业', 'AI软件', '智能助手', 'AI应用'],
        '机器人': ['机器人', '自动驾驶', '智能硬件', '无人机', '机器人', '宇树', '人形机器人', '机器狗'],
        '综合': []  # 综合领域不匹配关键词
    }
    
    for domain in domains:
        domain_name = domain['name']
        keywords = domain.get('keywords', domain_keywords.get(domain_name, [domain_name]))
        
        for keyword in keywords:
            if keyword.lower() in title_lower:
                relevance_score = max(relevance_score, 70 + len(keyword) * 3)
                matched_domain = domain_name
                break
    
    total_score = heat_score * 0.4 + relevance_score * 0.6
    
    return {
        'title': title,
        'heat': heat,
        'heat_display': item.get('heat', 'N/A'),
        'rank': item.get('rank', '?'),
        'source': item.get('source', 'unknown'),
        'url': item.get('url', ''),
        'matched_domain': matched_domain,
        'total_score': total_score
    }

def generate_report(scored_items: list, date: str, top_n: int = 5) -> str:
    sorted_items = sorted(scored_items, key=lambda x: x['total_score'], reverse=True)
    
    report = f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
type: topic-recommend
status: pending
date: {date}
---

# MCN 选题分析报告

## 推荐主题 (Top {top_n})

| 排名 | 主题 | 领域 | 热度 | 综合评分 | 来源 |
|------|------|------|------|----------|------|
"""
    
    for i, item in enumerate(sorted_items[:top_n], 1):
        domain = item['matched_domain'] or '未匹配'
        report += f"| {i} | {item['title']} | {domain} | {item['heat_display']} | {item['total_score']:.1f} | [查看]({item['url']}) |\n"
    
    report += f"""
## 选题建议

### 优先选择
- **评分高**：综合评分 > 70 的话题
- **领域匹配**：科技、编程、机器人相关
- **时效性强**：排名靠前、上升期话题

### 下一步

确认主题后执行：
```bash
python scripts/run-content-gen.py --topic "主题名" --style professional
```

## 原始数据

- 分析热搜：{len(scored_items)}条
- 匹配领域：{len([i for i in scored_items if i['matched_domain']])}条
"""
    
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='指定日期')
    parser.add_argument('--top', type=int, default=5, help='推荐数量')
    
    args = parser.parse_args()
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"选题分析 - {date}")
    print("=" * 60)
    
    config = load_config()
    domains = config['hotspot']['domains']
    print(f"\n关注领域：{', '.join(d['name'] for d in domains)}")
    
    hotspot_items = load_hotspot_data(date)
    if not hotspot_items:
        return
    
    print("\n分析话题...")
    scored_items = [score_topic(item, domains) for item in hotspot_items]
    
    report = generate_report(scored_items, date, args.top)
    
    output_dir = f"{MCN_ROOT}/topic/{date}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/recommend.md"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ 报告已保存：{output_path}")
    
    print("\n" + "=" * 60)
    print("Top 3 推荐")
    print("=" * 60)
    
    sorted_items = sorted(scored_items, key=lambda x: x['total_score'], reverse=True)
    for i, item in enumerate(sorted_items[:3], 1):
        domain = item['matched_domain'] or '未匹配'
        print(f"{i}. {item['title']}")
        print(f"   领域：{domain} | 热度：{item['heat_display']} | 评分：{item['total_score']:.1f}\n")

if __name__ == '__main__':
    main()
