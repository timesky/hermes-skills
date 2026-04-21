#!/usr/bin/env python3
"""选题分析脚本 - 增加排除已发布内容"""

import glob
import json
import os
import re
import yaml
import argparse
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import Counter
import math

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = f"{KB_ROOT}/mcn"
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
PUBLISHED_FILE = os.path.expanduser("~/.hermes/mcn_published.json")

# 从外部配置读取 KB_ROOT（可选）
if os.path.exists(MCN_CONFIG):
    try:
        with open(MCN_CONFIG) as f:
            config = yaml.safe_load(f)
        kb_root = config.get("paths", {}).get("kb_root", KB_ROOT)
        KB_ROOT = kb_root
        MCN_ROOT = f"{KB_ROOT}/mcn"
    except:
        pass

def slugify(text: str) -> str:
    """将文本转换为目录名安全的 slug"""
    import re
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【】\n\r\t]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s[:50].strip('-')

# 排除时间范围（天）
EXCLUDE_DAYS = 30

# 余弦相似度阈值（百分比）
COSINE_SIMILARITY_THRESHOLD = 0.35  # 35% 以上排除

# 技术词库（用于分词）
TECH_WORDS = [
    'AI', '机器人', '算力', '芯片', '模型', '内存', '手机', '编程', '代码', 'GPU', 
    '英伟达', '苹果', '小米', '具身', 'HBM', 'HBF', '并购', '罗技', '数据', '战事',
    'Scaling', 'Law', '人形', '财商', '农村', '老人', '诈骗', '大学生', '造谣',
    '视频', '导航', '高德', '涉黄', '软件', '手写', '古法', '助手', '实战', 
    'Hermes', '机器狗', '宇树', 'MiMo', '定价', '安卓', '供应链', '折叠', 'iPhone',
    '华为', 'OPPO', 'vivo', '三星', '微软', '谷歌', 'OpenAI', 'Anthropic',
    '自动驾驶', '无人机', '智能硬件', '大模型', 'LLM', 'GPT', '深度学习'
]


def tokenize(text):
    """分词：字符级 + 技术词"""
    # 中文字符拆分
    chars = [c for c in text if c.strip()]
    # 匹配技术词
    tokens = chars + [w for w in TECH_WORDS if w in text or w.lower() in text.lower()]
    return tokens


def cosine_similarity(title1, title2):
    """计算余弦相似度（0-1）"""
    tokens1 = tokenize(title1)
    tokens2 = tokenize(title2)
    
    # 词频向量
    vec1 = Counter(tokens1)
    vec2 = Counter(tokens2)
    
    # 所有词
    all_words = set(vec1.keys()) | set(vec2.keys())
    
    # 计算点积和模
    dot_product = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)
    norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v**2 for v in vec2.values()))
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    return dot_product / (norm1 * norm2)


def find_most_similar(title, published_titles):
    """找出最相似的已发布文章"""
    sims = [(pub, cosine_similarity(title, pub)) for pub in published_titles]
    sims.sort(key=lambda x: x[1], reverse=True)
    return sims[:3]  # 返回前3个最相似的


def load_config():
    with open(MCN_CONFIG) as f:
        return yaml.safe_load(f)


def load_published_articles():
    """加载已发布文章列表"""
    if not os.path.exists(PUBLISHED_FILE):
        print("⚠️ 未找到已发布文章列表，请先运行: python fetch-published-articles.py")
        return []
    
    with open(PUBLISHED_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_keywords_from_title(title):
    """从标题提取关键词（拆分核心词）"""
    # 去掉标点和特殊字符
    clean_title = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
    
    # 核心实体词（公司名、产品名、技术名）
    entities = [
        "苹果", "华为", "小米", "OPPO", "vivo", "三星", "英伟达", "微软", "谷歌", "OpenAI", "Anthropic",
        "机器人", "人形", "具身", "机器狗", "宇树", "自动驾驶",
        "AI", "GPT", "大模型", "LLM", "芯片", "算力", "GPU", "CPU",
        "折叠", "手机", "iPhone", "内存", "闪存",
        "财商课", "诈骗", "造谣", "涉黄"
    ]
    
    keywords = []
    
    # 优先匹配核心实体词
    for entity in entities:
        if entity.lower() in title.lower() or entity in clean_title:
            if entity not in keywords:
                keywords.append(entity)
    
    # 补充：提取2-4字的词组
    for length in range(4, 1, -1):
        for i in range(len(clean_title) - length + 1):
            word = clean_title[i:i+length]
            if word and word not in keywords and len(word) >= 2:
                keywords.append(word)
    
    return keywords[:15]


def check_topic_excluded(title, published_articles, cutoff_time, cutoff_date):
    """检查话题是否已发布（使用余弦相似度）"""
    
    # 当 publish_date 缺失时，默认检查所有文章（不按日期过滤）
    published_titles = [a.get('title', '') for a in published_articles 
                        if (not a.get('publish_date') and not a.get('publish_time')) or
                           a.get('publish_date', '') >= cutoff_date or 
                           a.get('publish_time', 0) >= cutoff_time]
    
    # 找出最相似的
    top_similar = find_most_similar(title, published_titles)
    
    if top_similar and top_similar[0][1] >= COSINE_SIMILARITY_THRESHOLD:
        best_match, best_sim = top_similar[0]
        # 返回完整的相似列表
        similar_list = [(pub, round(sim*100, 1)) for pub, sim in top_similar if sim > 0]
        return True, best_match, f"{round(best_sim*100, 1)}%", similar_list
    
    return False, None, None, []


def load_hotspot_data(date: str) -> list:
    """从 mcn/hotspot/{date}/hotspot-aggregated.md 读取热点数据"""
    filepath = f"{MCN_ROOT}/hotspot/{date}/hotspot-aggregated.md"
    
    if not os.path.exists(filepath):
        print(f"⚠️ 未找到 {date} 的热搜数据: {filepath}")
        return []
    
    content = open(filepath, encoding='utf-8').read()
    all_items = []
    
    # 解析 Markdown 列表格式
    for line in content.split('\n'):
        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', 
                                     '11.', '12.', '13.', '14.', '15.', '16.', '17.', '18.', '19.', '20.',
                                     '21.', '22.', '23.', '24.', '25.', '26.', '27.', '28.', '29.', '30.')):
            match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()
                
                heat_match = re.search(r'热度[:\s]*(\d+)', line)
                heat = heat_match.group(1) if heat_match else 'N/A'
                
                item = {
                    'rank': len(all_items) + 1,
                    'title': title,
                    'heat': heat,
                    'url': url,
                    'source': 'unknown'
                }
                all_items.append(item)
    
    print(f"✓ 加载 {len(all_items)} 条热搜数据")
    return all_items


def is_mixed_topic(title: str) -> bool:
    """检测是否混合话题（逗号分隔多个话题）"""
    
    separators = ['，', ',', '、', '|', '；']
    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            valid_parts = [p for p in parts if len(p.strip()) >= 4]
            if len(valid_parts) >= 2:
                return True
    
    return False


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
    
    domain_keywords = {
        '科技': ['科技', '芯片', 'ChatGPT', '大模型', '5G', '云计算', 'AI', '人工智能', '手机', '数码', '3C', '智能', '互联网'],
        '编程': ['编程', 'GitHub', '开源', '全栈', '前端', '后端', '开发', '代码', '技术', '软件', '算法', '掘金'],
        'AI应用': ['AI', 'GPT', '大模型', 'LLM', '深度学习', '机器学习', 'AI创业', 'AI软件', '智能助手', 'AI应用'],
        '机器人': ['机器人', '自动驾驶', '智能硬件', '无人机', '机器人', '宇树', '人形机器人', '机器狗'],
        '综合': []
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


def generate_report(scored_items: list, date: str, excluded_items: list, top_n: int = 5) -> str:
    sorted_items = sorted(scored_items, key=lambda x: x['total_score'], reverse=True)
    
    report = f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
type: topic-recommend
status: pending
date: {date}
excluded_count: {len(excluded_items)}
---

# MCN 选题分析报告

## 推荐主题 (Top {top_n})

|| 排名 | 主题 | 领域 | 热度 | 综合评分 | 来源 ||
||------|------|------|------|----------|------||
"""
    
    for i, item in enumerate(sorted_items[:top_n], 1):
        domain = item['matched_domain'] or '未匹配'
        report += f"| {i} | {item['title']} | {domain} | {item['heat_display']} | {item['total_score']:.1f} | [查看]({item['url']}) |\n"
    
    # 添加排除记录（完整列表）
    if excluded_items:
        report += f"""
## 已排除话题 ({len(excluded_items)}条)

以下话题因近{EXCLUDE_DAYS}天已发布或混合话题被排除：

| 新话题标题 | 相似标题 | 相似度 | 原因 |
|------------|----------|--------|------|
"""
        for item in excluded_items:
            title = item.get('title', '')
            similar_list = item.get('similar_list', [])
            reason = item.get('reason', '')
            
            if similar_list:
                # 取最相似的
                best_similar, best_pct = similar_list[0]
                report += f"| {title[:40]}... | {best_similar[:30]}... | **{best_pct}%** | 余弦相似 |\n"
                # 如果有多个相似，列出其他
                for sim_title, sim_pct in similar_list[1:]:
                    if sim_pct > 10:  # 只记录10%以上的
                        report += f"| | {sim_title[:30]}... | {sim_pct}% | 次相似 |\n"
            else:
                report += f"| {title[:40]}... | - | - | {reason} |\n"
    
    report += f"""
## 相似度阈值说明

- 当前阈值：**{COSINE_SIMILARITY_THRESHOLD*100:.0f}%**（余弦相似度）
- 高相似（>35%）：自动排除
- 中相似（10-35%）：记录供人工确认
- 低相似（<10%）：保留

## 统计

- 分析热搜：{len(scored_items) + len(excluded_items)}条
- 排除话题：{len(excluded_items)}条
- 有效候选：{len(scored_items)}条
- 匹配领域：{len([i for i in scored_items if i['matched_domain']])}条
"""
    
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='指定日期')
    parser.add_argument('--top', type=int, default=5, help='推荐数量')
    parser.add_argument('--refresh-published', action='store_true', help='重新获取已发布列表')
    
    args = parser.parse_args()
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"选题分析 - {date}")
    print("=" * 60)
    
    # 获取已发布文章列表（可选刷新）
    if args.refresh_published or not os.path.exists(PUBLISHED_FILE):
        print("\n[刷新已发布文章列表]")
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fetch_script = os.path.join(script_dir, 'fetch-published-articles.py')
        
        if os.path.exists(fetch_script):
            subprocess.run(['python3', fetch_script], check=True)
        else:
            print(f"⚠️ 未找到脚本: {fetch_script}")
    
    config = load_config()
    domains = config['hotspot']['domains']
    print(f"\n关注领域：{', '.join(d['name'] for d in domains)}")
    
    # 加载已发布文章
    published_articles = load_published_articles()
    cutoff_time = time.time() - EXCLUDE_DAYS * 24 * 3600
    cutoff_date_dt = datetime.now() - timedelta(days=EXCLUDE_DAYS)
    cutoff_date = cutoff_date_dt.strftime("%Y-%m-%d")  # 字符串格式，兼容时间戳错误
    print(f"排除范围：近{EXCLUDE_DAYS}天已发布 ({len(published_articles)}篇)")
    
    hotspot_items = load_hotspot_data(date)
    if not hotspot_items:
        return
    
    print("\n筛选话题...")
    valid_items = []
    excluded_items = []
    
    for item in hotspot_items:
        title = item['title']
        
        # 检查混合话题
        if is_mixed_topic(title):
            excluded_items.append({
                'title': title,
                'heat': item['heat'],
                'reason': '混合话题'
            })
            continue
        
        # 检查已发布（使用余弦相似度）
        excluded, similar_article, reason, similar_list = check_topic_excluded(title, published_articles, cutoff_time, cutoff_date)
        if excluded:
            excluded_items.append({
                'title': title,
                'heat': item['heat'],
                'reason': f'已发布({reason})',
                'similar_article': similar_article,
                'similar_list': similar_list
            })
            print(f"  排除: {title} → {reason} 《{similar_article}》")
            continue
        
        valid_items.append(item)
    
    print(f"✓ 有效话题: {len(valid_items)}条")
    print(f"✓ 排除话题: {len(excluded_items)}条")
    
    print("\n分析话题...")
    scored_items = [score_topic(item, domains) for item in valid_items]
    
    report = generate_report(scored_items, date, excluded_items, args.top)
    
    output_dir = f"{MCN_ROOT}/topic/{date}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/recommend.md"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ 报告已保存：{output_path}")
    
    # 写入 workflow.json（锚点文件）
    workflow = {
        "date": date,
        "current_step": "topic_selection",
        "status": "pending_user_choice",
        "data_paths": {
            "hotspot": f"mcn/hotspot/{date}/hotspot.json",
            "topic": f"mcn/topic/{date}/analysis.json",
            "recommend": f"mcn/topic/{date}/recommend.md"
        },
        "recommendations": [],
        "selected_topic": None,
        "article_path": None,
        "images_path": None,
        "media_id": None,
        "published": False,
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    # 提取 Top 5 推荐写入 workflow.json
    sorted_items = sorted(scored_items, key=lambda x: x['total_score'], reverse=True)
    for i, item in enumerate(sorted_items[:args.top], 1):
        workflow["recommendations"].append({
            "rank": i,
            "title": item['title'],
            "source": item['source'],
            "hot": item['heat_display'],
            "domain": item['matched_domain'],
            "score": round(item['total_score'] / 100, 2)  # 转为 0-1 范围
        })
    
    workflow_path = f"{MCN_ROOT}/workflow.json"
    with open(workflow_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)
    
    print(f"✓ workflow.json 已更新：{workflow_path}")
    
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