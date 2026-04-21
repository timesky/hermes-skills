#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点调研 Playwright 备用方案 - 当 OpenCLI 不可用时使用

OpenCLI 在 Node v20/v22 都有 undici 版本兼容问题，此脚本提供备用方案。
"""

import asyncio
import json
import os
import yaml
from datetime import datetime
from playwright.async_api import async_playwright

# 目录约定
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

# 从配置读取（可选覆盖）
config_path = os.path.expanduser("~/.hermes/mcn_config.yaml")
if os.path.exists(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)
    kb_root = config.get("paths", {}).get("kb_root", KB_ROOT)
    KB_ROOT = kb_root
    MCN_ROOT = KB_ROOT + "/mcn"

async def fetch_weibo_hot(page):
    """抓取微博热搜"""
    print("  [微博热搜] 抓取...")
    articles = []
    
    try:
        await page.goto("https://s.weibo.com/top/summary", timeout=20000)
        await page.wait_for_timeout(3000)
        
        items = await page.evaluate("""() => {
            const results = [];
            const trs = document.querySelectorAll('tbody tr');
            for (const tr of trs) {
                const td = tr.querySelector('td:nth-child(2)');
                if (td) {
                    const a = td.querySelector('a');
                    if (a) {
                        results.push({
                            title: a.innerText.trim(),
                            url: a.href
                        });
                    }
                }
            }
            return results;
        }""")
        
        keywords = ['科技', 'AI', '互联网', '手机', '华为', '苹果', '小米', '芯片', '机器人', '编程', '大模型', '数码']
        for item in items[:50]:
            title = item.get('title', '')
            if any(kw in title for kw in keywords):
                articles.append({
                    'title': title,
                    'platform': '微博',
                    'category': '互联网',
                    'url': item.get('url', ''),
                    'source': 'weibo'
                })
        
        print(f"    获取 {len(articles)} 条")
    except Exception as e:
        print(f"    错误: {e}")
    
    return articles

async def fetch_zhihu_hot(page):
    """抓取知乎热榜"""
    print("  [知乎热榜] 抓取...")
    articles = []
    
    try:
        await page.goto("https://www.zhihu.com/hot", timeout=20000)
        await page.wait_for_timeout(3000)
        
        items = await page.evaluate("""() => {
            const results = [];
            const items = document.querySelectorAll('.HotList-item, .HotItem');
            for (const item of items) {
                const titleEl = item.querySelector('.HotItem-title, .title');
                const excerptEl = item.querySelector('.HotItem-excerpt, .excerpt');
                const linkEl = item.querySelector('a[href*="/question/"]');
                
                if (titleEl) {
                    results.push({
                        title: titleEl.innerText.trim(),
                        excerpt: excerptEl ? excerptEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href : ''
                    });
                }
            }
            return results;
        }""")
        
        keywords = ['科技', 'AI', '人工智能', '编程', '机器人', '芯片', '大模型', '华为', '苹果', '小米', '互联网', '数码']
        
        for item in items[:50]:
            title = item.get('title', '')
            excerpt = item.get('excerpt', '')
            
            if any(kw in title for kw in keywords) or any(kw in excerpt for kw in keywords):
                articles.append({
                    'title': title,
                    'platform': '知乎',
                    'category': '科技',
                    'url': item.get('url', ''),
                    'excerpt': excerpt[:100] if excerpt else '',
                    'source': 'zhihu'
                })
        
        print(f"    获取 {len(articles)} 条")
    except Exception as e:
        print(f"    错误: {e}")
    
    return articles

async def fetch_36kr_tech(page):
    """抓取36氪科技频道"""
    print("  [36氪科技] 抓取...")
    articles = []
    
    try:
        await page.goto("https://36kr.com/information/technology/", timeout=20000)
        await page.wait_for_timeout(3000)
        
        items = await page.evaluate("""() => {
            const results = [];
            const links = document.querySelectorAll('a[href*="/information/technology/detail"], a[href*="/p/"]');
            for (const link of links) {
                const title = link.innerText.trim();
                if (title && title.length > 5) {
                    results.push({
                        title: title,
                        url: link.href
                    });
                }
            }
            return results;
        }""")
        
        seen = set()
        for item in items[:20]:
            title = item.get('title', '')
            if title and title not in seen:
                seen.add(title)
                articles.append({
                    'title': title,
                    'platform': '36氪',
                    'category': '科技',
                    'url': item.get('url', ''),
                    'source': '36kr'
                })
        
        print(f"    获取 {len(articles)} 条")
    except Exception as e:
        print(f"    错误: {e}")
    
    return articles

async def fetch_huxiu_tech(page):
    """抓取虎嗅科技频道"""
    print("  [虎嗅科技] 抓取...")
    articles = []
    
    try:
        await page.goto("https://www.huxiu.com/channel/105.html", timeout=20000)
        await page.wait_for_timeout(3000)
        
        items = await page.evaluate("""() => {
            const results = [];
            const links = document.querySelectorAll('a[href*="/article/"]');
            for (const link of links) {
                const title = link.innerText.trim();
                if (title && title.length > 5 && !title.includes('更多') && !title.includes('登录') && !title.match(/^\d+分钟前/)) {
                    results.push({
                        title: title,
                        url: link.href
                    });
                }
            }
            return results;
        }""")
        
        seen = set()
        for item in items[:15]:
            title = item.get('title', '')
            if title and title not in seen:
                seen.add(title)
                articles.append({
                    'title': title,
                    'platform': '虎嗅',
                    'category': '前沿科技',
                    'url': item.get('url', ''),
                    'source': 'huxiu'
                })
        
        print(f"    获取 {len(articles)} 条")
    except Exception as e:
        print(f"    错误: {e}")
    
    return articles

def save_hotspot_data(date, all_articles):
    """保存热点数据"""
    output_dir = MCN_ROOT + "/hotspot/" + date
    os.makedirs(output_dir, exist_ok=True)
    
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 保存 JSON
    json_file = output_dir + "/hotspot.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    # 构建 MD
    md_lines = [
        "---",
        "created: " + time_str,
        "total: " + str(len(all_articles)),
        "---",
        "",
        "# " + date + " 热点聚合",
        "",
        "## 来源统计",
        "",
        "| 来源 | 数量 |",
        "|------|------|"
    ]
    
    sources = {}
    for a in all_articles:
        src = a.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        md_lines.append("| " + src + " | " + str(count) + " |")
    
    md_lines.extend(["", "---", "", "## 热点列表", ""])
    
    for source in ['weibo', 'zhihu', '36kr', 'huxiu']:
        source_articles = [a for a in all_articles if a.get('source') == source]
        if source_articles:
            platform = source_articles[0].get('platform', source)
            md_lines.extend(["### " + platform, ""])
            
            for i, a in enumerate(source_articles[:15], 1):
                title = a.get('title', '')
                url = a.get('url', '')
                hot_value = a.get('hot_value', '')
                
                line = str(i) + ". [" + title + "](" + url + ")"
                if hot_value:
                    line += " (热度:" + str(hot_value) + ")"
                md_lines.append(line)
            
            md_lines.append("")
    
    md_file = output_dir + "/hotspot-aggregated.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    return md_file, json_file

async def main(date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("热点调研 (Playwright) - " + date)
    print("=" * 60)
    print()
    
    all_articles = []
    
    async with async_playwright() as p:
        # 使用 chromium（系统已有 chromium-1217）
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        weibo = await fetch_weibo_hot(page)
        zhihu = await fetch_zhihu_hot(page)
        kr36 = await fetch_36kr_tech(page)
        huxiu = await fetch_huxiu_tech(page)
        
        all_articles = weibo + zhihu + kr36 + huxiu
        
        await browser.close()
    
    print()
    print("=" * 60)
    print("总计: " + str(len(all_articles)) + " 条热点")
    print("=" * 60)
    
    if all_articles:
        md_file, json_file = save_hotspot_data(date, all_articles)
        print()
        print("已保存: " + md_file)
        print("已保存: " + json_file)
        
        return {"status": "success", "md_file": md_file, "json_file": json_file, "total": len(all_articles)}
    else:
        print()
        print("警告: 未获取到热点数据")
        return {"status": "failed", "message": "未获取到热点数据"}

if __name__ == '__main__':
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    result = asyncio.run(main(date))
    print(json.dumps(result, ensure_ascii=False))