#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点调研脚本 - 整合多平台热搜抓取

渠道优先级策略：
P1（最精准）：虎嗅科技/3C、36kr AI/技术、掘金（直接分类URL）
P2：微博（category过滤）
P3：知乎/抖音（关键词匹配）

OpenCLI 环境要求：Node v20
"""

import subprocess
import json
import os
import yaml
import re
from datetime import datetime


# 目录约定（自包含，不依赖其他技能模块）
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = f"{KB_ROOT}/mcn"

# 从外部配置读取 KB_ROOT（可选）
config_path = os.path.expanduser("~/.hermes/mcn_config.yaml")
if os.path.exists(config_path):
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        kb_root = config.get("paths", {}).get("kb_root", KB_ROOT)
        KB_ROOT = kb_root
        MCN_ROOT = f"{KB_ROOT}/mcn"
    except:
        pass
# 加载环境变量（terminal 不继承 Hermes 环境）
def load_env():
    env_path = os.path.expanduser('~/.hermes/.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_env()

MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = f"{KB_ROOT}/mcn"

def load_config():
    with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_opencli_cmd(cmd: str, timeout: int = 60) -> str:
    """执行 OpenCLI 命令（使用 Node 20）"""
    full_cmd = f"source ~/.nvm/nvm.sh && nvm use 20 && {cmd}"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout

def fetch_huxiu_tech() -> list:
    """抓取虎嗅前沿科技频道"""
    print("  [虎嗅前沿科技] 抓取...")
    
    output_dir = "/tmp/huxiu_tech_articles"
    cmd = f"opencli web read --url https://www.huxiu.com/channel/105.html --output {output_dir}"
    
    try:
        run_opencli_cmd(cmd, timeout=45)
        
        # 解析保存的文章
        articles = []
        md_file = f"{output_dir}/前沿科技/前沿科技.md"
        
        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            articles = []
            
            # 虎嗅格式：[\n\n### 标题\n\n](url)
            # 使用正则匹配标题和链接
            article_pattern = r'\[\s*\n\s*###\s+([^\n]+)\s*\n\s*\]\((https://www\.huxiu\.com/article/\d+\.html)\)'
            matches = re.findall(article_pattern, content)
            
            for title, url in matches[:20]:
                title = title.strip()
                if title and title != '前沿科技':  # 排除频道标题
                    articles.append({
                        'title': title,
                        'platform': '虎嗅',
                        'category': '前沿科技',
                        'url': url,
                        'source': 'huxiu_tech'
                    })
        
        print(f"    获取 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"    错误: {e}")
        return []

def fetch_huxiu_3c() -> list:
    """抓取虎嗅3C数码频道"""
    print("  [虎嗅3C数码] 抓取...")
    
    output_dir = "/tmp/huxiu_3c_articles"
    cmd = f"opencli web read --url https://www.huxiu.com/channel/121.html --output {output_dir}"
    
    try:
        run_opencli_cmd(cmd, timeout=45)
        
        articles = []
        md_file = f"{output_dir}/3C数码/3C数码.md"
        
        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            articles = []
            
            # 虎嗅格式：[\n\n### 标题\n\n](url)
            article_pattern = r'\[\s*\n\s*###\s+([^\n]+)\s*\n\s*\]\((https://www\.huxiu\.com/article/\d+\.html)\)'
            matches = re.findall(article_pattern, content)
            
            for title, url in matches[:15]:
                title = title.strip()
                if title and title != '3C数码':  # 排除频道标题
                    articles.append({
                        'title': title,
                        'platform': '虎嗅',
                        'category': '3C数码',
                        'url': url,
                        'source': 'huxiu_3c'
                    })
        
        print(f"    获取 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"    错误: {e}")
        return []

def fetch_36kr_news() -> list:
    """抓取36氪新闻"""
    print("  [36氪] 抓取...")
    
    cmd = "opencli 36kr news --limit 20 --format json"
    
    try:
        output = run_opencli_cmd(cmd, timeout=45)
        
        # 解析 JSON
        lines = output.strip().split('\n')
        json_str = ""
        for i, line in enumerate(lines):
            if line.startswith('['):
                json_str = '\n'.join(lines[i:])
                break
        
        if json_str:
            data = json.loads(json_str)
            
            articles = []
            for item in data[:20]:
                articles.append({
                    'title': item.get('title', ''),
                    'platform': '36氪',
                    'category': '科技',
                    'url': item.get('url', ''),
                    'summary': item.get('summary', '')[:100],
                    'source': '36kr'
                })
            
            print(f"    获取 {len(articles)} 条")
            return articles
    except Exception as e:
        print(f"    错误: {e}")
        return []
    
    return []

def fetch_juejin() -> list:
    """抓取掘金首页"""
    print("  [掘金] 抓取...")
    
    output_dir = "/tmp/juejin_articles"
    cmd = f"opencli web read --url https://juejin.cn/ --output {output_dir}"
    
    try:
        run_opencli_cmd(cmd, timeout=45)
        
        articles = []
        # 掘金的输出目录可能不同，需要检查
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if f.endswith('.md'):
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    # 提取文章标题
                    titles = re.findall(r'###?\s*(.*?)\n', content)
                    for title in titles[:20]:
                        if title and len(title) > 5:
                            articles.append({
                                'title': title.strip(),
                                'platform': '掘金',
                                'category': '开发',
                                'url': 'https://juejin.cn/',
                                'source': 'juejin'
                            })
        
        print(f"    获取 {len(articles)} 条")
        return articles[:20]
    except Exception as e:
        print(f"    错误: {e}")
        return []

def fetch_weibo_filtered() -> list:
    """抓取微博热搜（过滤互联网/民生新闻分类）"""
    print("  [微博] 抓取（过滤分类）...")
    
    cmd = "opencli weibo hot --limit 50 --format json"
    
    try:
        output = run_opencli_cmd(cmd, timeout=45)
        
        lines = output.strip().split('\n')
        json_str = ""
        for i, line in enumerate(lines):
            if line.startswith('['):
                json_str = '\n'.join(lines[i:])
                break
        
        if json_str:
            data = json.loads(json_str)
            
            # 过滤分类
            filtered = [d for d in data if d.get('category') in ['互联网', '民生新闻']]
            
            articles = []
            for item in filtered:
                articles.append({
                    'title': item.get('word', ''),
                    'platform': '微博',
                    'category': item.get('category', ''),
                    'url': item.get('url', ''),
                    'hot_value': item.get('hot_value', 0),
                    'source': 'weibo'
                })
            
            print(f"    获取 {len(articles)} 条（过滤后）")
            return articles
    except Exception as e:
        print(f"    错误: {e}")
        return []
    
    return []

def keyword_match(title: str, keywords: list) -> bool:
    """关键词匹配"""
    for kw in keywords:
        if kw.lower() in title.lower():
            return True
    return False

def filter_by_keywords(articles: list, keywords: list) -> list:
    """关键词过滤"""
    return [a for a in articles if keyword_match(a.get('title', ''), keywords)]

def save_hotspot(date: str, all_articles: list) -> str:
    """保存热点数据"""
    output_dir = f"{MCN_ROOT}/hotspot/{date}"
    os.makedirs(output_dir, exist_ok=True)
    
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    md = f"""---
created: {time_str}
total: {len(all_articles)}
---

# {date} 热点聚合

## 来源统计

| 来源 | 数量 |
|------|------|
"""

    # 统计各来源
    sources = {}
    for a in all_articles:
        src = a.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        md += f"| {src} | {count} |\n"
    
    md += "\n---\n\n## 热点列表\n\n"
    
    # 按来源分组展示
    for source in ['huxiu_tech', 'huxiu_3c', '36kr', 'juejin', 'weibo']:
        source_articles = [a for a in all_articles if a.get('source') == source]
        if source_articles:
            platform = source_articles[0].get('platform', source)
            md += f"### {platform}\n\n"
            
            for i, a in enumerate(source_articles[:15], 1):
                title = a.get('title', '')
                url = a.get('url', '')
                category = a.get('category', '')
                hot_value = a.get('hot_value', '')
                
                md += f"{i}. [{title}]({url})"
                if category:
                    md += f" [{category}]"
                if hot_value:
                    md += f" (热度:{hot_value})"
                md += "\n"
            
            md += "\n"
    
    filename = f"{output_dir}/hotspot-aggregated.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return filename

def main():
    date = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"热点调研 - {date}")
    print("=" * 60)
    print()
    
    # P1: 有分类URL的平台
    print("=== P1 渠道（分类URL）===")
    huxiu_tech = fetch_huxiu_tech()
    huxiu_3c = fetch_huxiu_3c()
    juejin = fetch_juejin()
    
    print()
    print("=== P2 渠道（分类过滤）===")
    weibo = fetch_weibo_filtered()
    
    print()
    print("=== P3 渠道（36kr补充）===")
    kr36 = fetch_36kr_news()
    
    # 合并所有热点
    all_articles = huxiu_tech + huxiu_3c + juejin + weibo + kr36
    
    print()
    print("=" * 60)
    print(f"总计: {len(all_articles)} 条热点")
    print("=" * 60)
    
    # 保存
    if all_articles:
        filename = save_hotspot(date, all_articles)
        print(f"\n✅ 已保存: {filename}")
    
    # 返回数据供后续使用
    return all_articles

if __name__ == '__main__':
    articles = main()
    print(f"\n热点数量: {len(articles)}")