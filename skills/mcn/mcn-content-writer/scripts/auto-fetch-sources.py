#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动抓取原文数据 - 用于深度保持验证的原文数据源

用法:
    python scripts/auto-fetch-sources.py --date 2026-04-25
    python scripts/auto-fetch-sources.py --topic "黄仁勋GPT-5.5全员用"
    
功能:
    1. 从选题报告读取今日选题
    2. 根据来源 URL 抓取原文内容
    3. 保存到 sources/source_articles.json
"""

import sys
import os
import re
import json
import yaml
import argparse
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# 配置
# Profile隔离：使用HERMES_HOME环境变量
HERMES_HOME = os.environ.get('HERMES_HOME', '/Users/hy_timesky/.hermes')
MCN_CONFIG = os.path.join(HERMES_HOME, 'mcn_config.yaml')

try:
    with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
        _config = yaml.safe_load(f)
    KB_ROOT = _config.get('paths', {}).get('kb_root', os.path.expanduser("~/Documents/My_Obsidian"))
except:
    KB_ROOT = os.path.expanduser("~/Documents/My_Obsidian")

MCN_ROOT = KB_ROOT + "/mcn"
SOURCES_FILE = os.path.join(MCN_ROOT, "sources/source_articles.json")

# web-fetcher 服务地址
WEB_FETCHER_URL = "http://127.0.0.1:9234"


def read_topic_report(date: str) -> list:
    """读取选题报告，提取选题和来源 URL"""
    filename = f"{MCN_ROOT}/topic/{date}/recommend.md"
    
    if not os.path.exists(filename):
        print(f"✗ 选题报告不存在：{filename}")
        return []
    
    content = open(filename, encoding='utf-8').read()
    
    topics = []
    # 解析推荐主题表格
    table_match = re.search(r'\| 排名 \| 主题 \| 领域 \| 热度 \| 综合评分 \| 来源 \|(.*?)\n##', content, re.DOTALL)
    
    if table_match:
        table_content = table_match.group(1)
        for line in table_content.strip().split('\n'):
            if line.strip().startswith('|'):
                parts = line.split('|')
                if len(parts) >= 6:
                    # 提取来源链接
                    source_link = parts[6].strip()
                    source_url = re.search(r'\((https?://[^)]+)\)', source_link)
                    
                    topics.append({
                        'rank': parts[1].strip(),
                        'title': parts[2].strip(),
                        'domain': parts[3].strip(),
                        'source_url': source_url.group(1) if source_url else ''
                    })
    
    return topics


def fetch_via_web_fetcher(url: str) -> dict:
    """通过 web-fetcher 服务抓取页面"""
    
    try:
        # 创建抓取任务
        response = requests.post(
            f"{WEB_FETCHER_URL}/api/fetch",
            json={
                "url": url,
                "extract_content": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'content': result.get('content', ''),
                'title': result.get('title', ''),
                'status': 'success'
            }
        else:
            return {'status': 'error', 'message': f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def fetch_36kr_article(url: str) -> dict:
    """抓取 36kr 文章"""
    
    # 优先使用 web-fetcher
    result = fetch_via_web_fetcher(url)
    
    if result['status'] == 'success' and result['content']:
        return result
    
    # 备用：直接 HTTP 请求
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 36kr 文章内容区域
            article_div = soup.find('div', class_='article-content') or soup.find('div', class_='rich-text')
            
            if article_div:
                content = article_div.get_text(separator='\n', strip=True)
                return {
                    'content': content,
                    'title': soup.find('h1').get_text(strip=True) if soup.find('h1') else '',
                    'status': 'success'
                }
    except Exception as e:
        print(f"  ⚠️ 36kr 抓取失败: {e}")
    
    return {'status': 'error', 'message': '无法获取内容'}


def detect_platform(url: str) -> str:
    """检测来源平台"""
    if '36kr.com' in url:
        return '36kr'
    if 'weibo.com' in url or 's.weibo.com' in url:
        return '微博热搜'
    if 'huxiu.com' in url:
        return '虎嗅'
    if 'thepaper.cn' in url:
        return '澎湃新闻'
    if 'zhihu.com' in url:
        return '知乎'
    return '其他'


def fetch_source_content(url: str) -> dict:
    """根据平台选择抓取方法"""
    
    platform = detect_platform(url)
    
    if platform == '36kr':
        return fetch_36kr_article(url)
    elif platform == '微博热搜':
        # 微博需要登录，标记为需要 web-fetcher
        return {'status': 'needs_login', 'message': '微博需要登录态'}
    else:
        # 其他平台尝试 web-fetcher
        return fetch_via_web_fetcher(url)


def load_existing_sources() -> list:
    """加载已有的原文数据"""
    if os.path.exists(SOURCES_FILE):
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_sources(sources: list):
    """保存原文数据"""
    os.makedirs(os.path.dirname(SOURCES_FILE), exist_ok=True)
    with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)
    print(f"✓ 原文数据已保存：{SOURCES_FILE}")


def main():
    parser = argparse.ArgumentParser(description='自动抓取原文数据')
    parser.add_argument('--date', type=str, help='从选题报告读取（指定日期）')
    parser.add_argument('--topic', type=str, help='指定主题名称')
    parser.add_argument('--url', type=str, help='直接指定来源 URL')
    
    args = parser.parse_args()
    
    sources = load_existing_sources()
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    
    if args.url:
        # 直接抓取指定 URL
        print(f"抓取：{args.url}")
        result = fetch_source_content(args.url)
        
        if result['status'] == 'success':
            sources.append({
                'date': date_str,
                'my_title': args.topic or result['title'],
                'source_platform': detect_platform(args.url),
                'source_url': args.url,
                'source_content': result['content'],
                'source_length': len(result['content'])
            })
            save_sources(sources)
        else:
            print(f"✗ 抓取失败：{result['message']}")
            
    elif args.date:
        # 从选题报告批量抓取
        topics = read_topic_report(date_str)
        
        if not topics:
            print("✗ 无选题数据")
            sys.exit(1)
        
        print(f"发现 {len(topics)} 个选题")
        
        for topic in topics[:5]:  # 只处理前5个
            print(f"\n[{topic['rank']}] {topic['title']}")
            
            if not topic['source_url']:
                print("  ⚠️ 无来源 URL，跳过")
                continue
            
            # 检查是否已抓取
            existing = [s for s in sources if s['my_title'] == topic['title']]
            if existing:
                print("  ✓ 已存在，跳过")
                continue
            
            result = fetch_source_content(topic['source_url'])
            
            if result['status'] == 'success':
                sources.append({
                    'date': date_str,
                    'my_title': topic['title'],
                    'source_platform': detect_platform(topic['source_url']),
                    'source_url': topic['source_url'],
                    'source_content': result['content'],
                    'source_length': len(result['content'])
                })
                print(f"  ✓ 抓取成功：{result['content'][:50]}...")
            else:
                print(f"  ⚠️ 抓取失败：{result['message']}")
        
        save_sources(sources)
    
    else:
        print("用法：")
        print("  python scripts/auto-fetch-sources.py --date 2026-04-25")
        print("  python scripts/auto-fetch-sources.py --url https://36kr.com/p/xxx")
        sys.exit(1)


if __name__ == '__main__':
    main()