#!/usr/bin/env python3
"""
Hermes Web Fetcher - 通过扩展 API 抓取知乎收藏夹
使用 chrome.scripting.executeScript，复用用户 cookies
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

# 配置
COLLECTION_ID = '797328373'
KB_ROOT = Path('/Users/timesky/backup/知识库-Obsidian/04-外部资源/网络转载')
TO_PROCESS_FILE = Path('/tmp/collection_to_process.json')
PROCESSED_FILE = Path('/tmp/zhihu_processed_ids.json')
CONCURRENCY = 2

def load_articles_to_process():
    """读取待处理文章列表"""
    if TO_PROCESS_FILE.exists():
        with open(TO_PROCESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_processed_ids():
    """读取已处理 ID"""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('ids', []))
    return set()

def categorize_article(title, content):
    """分类文章"""
    text = (title + ' ' + content).lower()
    
    if any(kw in text for kw in ['ai', 'agent', '模型', 'llm', 'claude', 'gemma', 'qwen']):
        if any(kw in text for kw in ['编程', '代码', '开发', 'github', '开源']):
            return 'AI 编程'
        return 'AI 工具'
    elif any(kw in text for kw in ['投资', '理财', '股票', '量化', '信用卡', '资本']):
        return '投资'
    elif any(kw in text for kw in ['创业', '副业', '赚钱', '一人公司', 'mcn']):
        return 'AI 创业'
    elif any(kw in text for kw in ['设计', 'ui', 'figma', '画布']):
        return '设计工具'
    else:
        return 'AI 工具'

def save_article(article):
    """保存文章到知识库"""
    title = article.get('title', '无标题')
    content = article.get('content', '')
    author = article.get('author', '')
    post_date = article.get('date', '').split('T')[0] if article.get('date') else datetime.now().strftime('%Y-%m-%d')
    url = article.get('url', '')
    article_id = article.get('id', '')
    
    if len(post_date) != 10:
        post_date = datetime.now().strftime('%Y-%m-%d')
    
    # 分类
    category = categorize_article(title, content)
    
    # 创建分类目录
    category_dir = KB_ROOT / category
    category_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    safe_title = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', title)[:80]
    filename = f"知乎 - {safe_title}.md"
    filepath = category_dir / filename
    
    # 生成 YAML 头
    yaml_header = f"""---
title: {title}
original_url: {url}
post_date: {post_date}
author: {author}
category: {category}
source: 知乎收藏夹 {COLLECTION_ID}
article_id: {article_id}
collected_date: {datetime.now().strftime('%Y-%m-%d')}
tags: [知乎，{category.replace(' ', ', ')}]
---

"""
    
    # 完整内容
    full_content = yaml_header + content
    
    # 保存文件
    filepath.write_text(full_content, encoding='utf-8')
    return filepath, category

def fetch_article_via_extension(article_url):
    """
    通过扩展 API 抓取文章
    使用 AppleScript 调用扩展
    """
    # 这里需要通过 AppleScript 或 Python 的 selenium/pyppeteer 调用扩展
    # 简化方案：直接使用 CDP 但通过扩展的 content.js 逻辑
    
    # TODO: 实现扩展调用
    # 目前返回 None 表示需要使用扩展
    return None

def main():
    print("=" * 60)
    print("Hermes Web Fetcher - 知乎收藏夹抓取")
    print("=" * 60)
    
    # 加载数据
    articles = load_articles_to_process()
    processed_ids = load_processed_ids()
    
    print(f"\n待抓取文章：{len(articles)} 篇")
    print(f"已处理 ID: {len(processed_ids)} 个")
    
    if not articles:
        print("\n✅ 没有待抓取的文章！")
        return 0
    
    print("\n" + "=" * 60)
    print("⚠️  注意：扩展 API 调用需要额外配置")
    print("=" * 60)
    print("""
当前扩展已加载，但 Python 无法直接调用 chrome.runtime API。

有两种方案：

方案 A: 使用 Node.js 脚本通过 CDP + 扩展 content.js 逻辑
  - 优点：快速，已测试
  - 缺点：不是纯扩展调用

方案 B: 使用 Selenium/Playwright 加载扩展
  - 优点：真实模拟扩展调用
  - 缺点：需要额外依赖

方案 C: 手动使用扩展 Popup
  - 打开收藏夹页面
  - 点击扩展图标
  - 点击"抓取当前收藏夹"

请选择方案 (A/B/C) 或直接按 Enter 使用方案 A: """)
    
    choice = input().strip().lower()
    
    if choice == 'b':
        print("\n方案 B 需要安装 selenium 和配置 ChromeDriver")
        print("建议使用方法 A 或 C")
        return 1
    elif choice == 'c':
        print("\n请在 Chrome 中:")
        print("1. 打开 https://www.zhihu.com/collection/797328373?page=1")
        print("2. 点击扩展图标")
        print("3. 点击'抓取当前收藏夹'")
        return 0
    else:
        # 方案 A: 使用 Node.js 脚本
        print("\n使用方法 A (Node.js + CDP + 扩展逻辑)...")
        print("执行抓取脚本...\n")
        
        result = subprocess.run(
            ['node', '/tmp/grab_articles.js'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print("错误:", result.stderr)
        
        # 保存抓取结果到知识库
        grabbed_file = Path('/tmp/articles_grabbed.json')
        if grabbed_file.exists():
            grabbed_articles = json.loads(grabbed_file.read_text(encoding='utf-8'))
            print(f"\n保存 {len(grabbed_articles)} 篇文章到知识库...")
            
            saved_count = 0
            for article in grabbed_articles:
                if article.get('content') and len(article['content']) > 0:
                    try:
                        filepath, category = save_article(article)
                        saved_count += 1
                        print(f"  ✅ {category}/{filepath.name[:40]}...")
                    except Exception as e:
                        print(f"  ❌ 保存失败：{e}")
            
            print(f"\n✅ 已保存 {saved_count} 篇文章")
            
            # 更新进度
            new_ids = set(a['id'] for a in grabbed_articles if a.get('content'))
            all_ids = processed_ids | new_ids
            last_id = grabbed_articles[-1]['id'] if grabbed_articles else None
            
            with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'ids': list(all_ids),
                    'last_id': last_id,
                    'total_saved': saved_count,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            print(f"📌 已更新进度：{len(all_ids)} 篇")
        
        return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
