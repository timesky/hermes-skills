#!/usr/bin/env python3
"""
手动更新已发布文章列表

用法:
    python update-published-list.py --title "文章标题" --date 2026-04-20
    python update-published-list.py --from-content  # 从 content 目录扫描
    python update-published-list.py --list          # 显示当前列表
"""

import os
import json
import argparse
from datetime import datetime

PUBLISHED_FILE = os.path.expanduser("~/.hermes/mcn_published.json")
MCN_ROOT = "/Users/timesky/backup/知识库-Obsidian/mcn"

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        with open(PUBLISHED_FILE) as f:
            return json.load(f)
    return []

def save_published(articles):
    with open(PUBLISHED_FILE, 'w') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print(f"✓ 已保存 {len(articles)} 篇文章")

def add_article(title, date, media_id=None):
    articles = load_published()
    
    # 检查是否已存在
    existing_titles = {a['title'] for a in articles}
    if title in existing_titles:
        print(f"⚠️ 文章已存在: {title}")
        return
    
    articles.append({
        'title': title,
        'publish_date': date,
        'publish_time': int(datetime.strptime(date, '%Y-%m-%d').timestamp()) if date else 0,
        'media_id': media_id or ''
    })
    
    # 按日期排序（最新在前）
    articles.sort(key=lambda x: x.get('publish_time', 0), reverse=True)
    
    save_published(articles)
    print(f"✓ 已添加: {title} ({date})")

def scan_from_content():
    """从 content 目录扫描所有草稿作为已发布候选"""
    articles = []
    content_dir = os.path.join(MCN_ROOT, "content")
    
    if not os.path.exists(content_dir):
        print(f"⚠️ content 目录不存在")
        return
    
    for date_dir in sorted(os.listdir(content_dir), reverse=True):
        date_path = os.path.join(content_dir, date_dir)
        if not os.path.isdir(date_path):
            continue
        
        for slug_dir in sorted(os.listdir(date_path)):
            slug_path = os.path.join(date_path, slug_dir)
            if not os.path.isdir(slug_path):
                continue
            
            article_file = os.path.join(slug_path, "article.md")
            if os.path.exists(article_file):
                with open(article_file) as f:
                    first_line = f.readline()
                title = first_line.replace('#', '').strip() if first_line.startswith('#') else slug_dir
                
                articles.append({
                    'title': title,
                    'publish_date': date_dir,
                    'publish_time': int(datetime.strptime(date_dir, '%Y-%m-%d').timestamp()),
                    'media_id': '',
                    'slug': slug_dir
                })
    
    if articles:
        save_published(articles)
        print(f"\n已添加的文章:")
        for a in articles[:10]:
            print(f"  - {a['title']} ({a['publish_date']})")
    else:
        print("未找到任何文章")

def list_published():
    articles = load_published()
    print(f"\n已发布文章列表 ({len(articles)} 篇):")
    for a in articles:
        print(f"  - {a['title']} ({a.get('publish_date', 'N/A')})")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--title', type=str, help='文章标题')
    parser.add_argument('--date', type=str, help='发布日期')
    parser.add_argument('--media-id', type=str, help='media_id')
    parser.add_argument('--from-content', action='store_true', help='从 content 目录扫描')
    parser.add_argument('--list', action='store_true', help='显示当前列表')
    parser.add_argument('--clear', action='store_true', help='清空列表')
    
    args = parser.parse_args()
    
    if args.list:
        list_published()
    elif args.clear:
        save_published([])
        print("✓ 已清空")
    elif args.from_content:
        scan_from_content()
    elif args.title and args.date:
        add_article(args.title, args.date, args.media_id)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()