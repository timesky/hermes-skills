#!/usr/bin/env python3
"""
Hermes Web Fetcher - Universal Content Fetcher

Python integration for Hermes Web Fetcher extension
Fetches content from any website using chrome.scripting API
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
EXT_PATH = Path.home() / '.hermes/browser-extension/web-fetcher'
PROCESSED_FILE = Path('/tmp/web_fetcher_processed.json')
KB_ROOT = Path('/Users/timesky/backup/知识库-Obsidian/04-外部资源/网络转载')

# Site-specific configurations
SITE_CONFIGS = {
    'zhihu_collection': {
        'name': '知乎收藏夹',
        'url_pattern': r'zhihu\.com/collection/(\d+)',
        'collection_id': '797328373',
        'id_pattern': r'/p/(\d+)|/question/(\d+)',
        'category_map': {
            'AI': 'AI 工具',
            '编程': 'AI 编程',
            '投资': '投资',
            '创业': 'AI 创业'
        }
    },
    'github_trending': {
        'name': 'GitHub Trending',
        'url_pattern': r'github\.com/trending',
        'id_pattern': r'github\.com/([^/]+/[^/]+)',
        'category_map': {}
    }
}


def load_processed():
    """Load processed IDs"""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'ids': [], 'last_id': None, 'by_site': {}}


def save_processed(data):
    """Save processed IDs"""
    with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def categorize_article(title, content, site='default'):
    """Categorize article based on content"""
    text = (title + ' ' + content).lower()
    
    # Site-specific rules
    if site == 'zhihu_collection':
        if any(kw in text for kw in ['ai', 'agent', '模型', 'llm', 'claude']):
            if any(kw in text for kw in ['编程', '代码', '开发', 'github']):
                return 'AI 编程'
            return 'AI 工具'
        elif any(kw in text for kw in ['投资', '理财', '股票', '量化']):
            return '投资'
        elif any(kw in text for kw in ['创业', '副业', '赚钱']):
            return 'AI 创业'
    
    # Default rules
    if any(kw in text for kw in ['python', 'javascript', 'code', '编程']):
        return '编程'
    elif any(kw in text for kw in ['ai', 'machine learning', 'ml']):
        return 'AI'
    else:
        return '其他'


def main():
    print("=" * 60)
    print("Hermes Web Fetcher - 通用网页抓取工具")
    print("=" * 60)
    
    # Check extension
    if not EXT_PATH.exists():
        print(f"\n❌ 扩展路径不存在：{EXT_PATH}")
        return 1
    
    print(f"\n✅ 扩展路径：{EXT_PATH}")
    
    # Load processed
    processed = load_processed()
    print(f"📊 已处理：{len(processed.get('ids', []))} 篇文章")
    print(f"📌 上次 ID: {processed.get('last_id', '无')}")
    
    print("\n" + "=" * 60)
    print("使用方法:")
    print("=" * 60)
    print("""
1. 在 Chrome 中加载扩展:
   chrome://extensions/ → 开发者模式 → 加载已解压的扩展程序
   选择：~/.hermes/browser-extension/web-fetcher/

2. 打开要抓取的网站:
   - 知乎收藏夹：https://www.zhihu.com/collection/797328373
   - GitHub Trending: https://github.com/trending
   - 或其他任何网站

3. 点击扩展图标抓取内容

4. 或通过 Hermes Agent 调用:
   - fetch_list(tabId, options) - 抓取列表
   - fetch_article(tabId) - 抓取文章
    """)
    
    print("\n支持的网站:")
    for key, config in SITE_CONFIGS.items():
        print(f"  - {config['name']}: {key}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
