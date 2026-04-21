#!/usr/bin/env python3
"""
微信公众号发布历史抓取脚本 v2.0

功能：
1. 抓取发布历史页面，获取文章列表和关键指标（送达/阅读/点赞/分享/收藏）
2. 检测登录状态，token 过期时截屏二维码
3. 检测当前公众号账号，避免多账号错乱
4. 生成分析报告

数据顺序（公众号后台）:
   第1列: 送达人数
   第2列: 阅读数
   第3列: 点赞数
   第4列: 分享数
   第5列: 收藏数

使用：
    python fetch-published-stats.py
    python fetch-published-stats.py --analyze  # 仅分析已保存数据
"""

import asyncio
import sys
import os
import re
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.expanduser('~/.hermes/skills/web/web-fetcher/server'))
from hermes_web_fetcher import HermesWebFetcher

STATS_FILE = os.path.expanduser("~/mcn/published_stats.json")
PUBLISHED_FILE = os.path.expanduser("~/.hermes/mcn_published.json")
SCREENSHOT_DIR = os.path.expanduser("~/mcn/screenshots/")

async def check_login_and_account(client: HermesWebFetcher):
    """
    检测登录状态和当前账号
    
    返回:
        (is_logged_in, account_name, token)
    """
    url = "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN"
    tab = await client.create_agent_tab(url)
    tab_id = tab['id']
    await asyncio.sleep(3)
    
    result = await client.fetch_article(tab_id)
    content = result.get('content', '')
    
    is_logged_in = '程序员的开发手册' in content or '设置与开发' in content
    
    if is_logged_in:
        account_match = re.search(r'程序员的开发手册', content)
        account_name = account_match.group(0) if account_match else "未知账号"
        
        token_match = re.search(r'token=(\d+)', content)
        token = token_match.group(1) if token_match else None
        
        print(f"✅ 已登录: {account_name}")
        print(f"   Token: {token}")
    else:
        print("❌ 未登录或 token 已过期")
        
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"login_qrcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        
        try:
            result = await client.screenshot_to_file(tab_id, screenshot_path)
            print(f"📸 二维码截图已保存: {screenshot_path}")
            print("   请扫码登录后重新运行脚本")
        except Exception as e:
            print(f"⚠️ 截屏失败: {e}")
            print("   请手动打开 https://mp.weixin.qq.com 扫码登录")
    
    await client.close_agent_tab(tab_id)
    
    return is_logged_in, account_name if is_logged_in else None, token if is_logged_in else None


async def fetch_all_stats(client: HermesWebFetcher, token: str):
    """抓取所有文章统计数据"""
    all_articles = []
    
    for page in range(7):
        begin = page * 20
        url = f"https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin={begin}&count=20&token={token}&lang=zh_CN"
        
        print(f"📖 第 {page+1} 页...")
        
        tab = await client.create_agent_tab(url)
        tab_id = tab['id']
        await asyncio.sleep(4)
        
        result = await client.fetch_article(tab_id)
        content = result.get('content', '')
        
        articles = parse_stats(content)
        all_articles.extend(articles)
        print(f"  ✅ {len(articles)} 篇")
        
        await client.close_agent_tab(tab_id)
        await asyncio.sleep(1)
    
    return all_articles


def parse_stats(content: str):
    """解析统计数据"""
    articles = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if '原创' in line and 'mp.weixin.qq.com/s/' in line:
            match = re.search(r'\[([^\]]+)\s*原创\]\((https://mp\.weixin\.qq\.com/s/[^\)]+)\)', line)
            if match:
                title = match.group(1).strip()
                url = match.group(2)
                
                nums = []
                for j in range(i+1, min(i+10, len(lines))):
                    next_line = lines[j].strip()
                    if re.match(r'^[\d,]+$', next_line):
                        num = int(next_line.replace(',', ''))
                        nums.append(num)
                    elif next_line and not next_line.startswith('['):
                        continue
                    else:
                        break
                
                articles.append({
                    'title': title,
                    'url': url,
                    '送达': nums[0] if len(nums) > 0 else 0,
                    'read_count': nums[1] if len(nums) > 1 else 0,
                    'like_count': nums[2] if len(nums) > 2 else 0,
                    'share_count': nums[3] if len(nums) > 3 else 0,
                    'fav_count': nums[4] if len(nums) > 4 else 0,
                })
    
    return articles


def analyze_articles(articles: list):
    """生成分析报告"""
    by_read = sorted(articles, key=lambda x: x['read_count'], reverse=True)
    by_like = sorted(articles, key=lambda x: x['like_count'], reverse=True)
    with_send = [a for a in articles if a['送达'] > 100]
    by_open_rate = sorted(with_send, key=lambda x: x['read_count']/x['送达'] if x['送达']>0 else 0, reverse=True)
    
    print("\n" + "="*60)
    print("微信公众号数据分析报告")
    print("="*60)
    
    print(f"\n📊 总计: {len(articles)} 篇文章")
    
    print("\n=== TOP 10 阅读数 ===")
    for i, a in enumerate(by_read[:10], 1):
        print(f"{i}. {a['title'][:40]}")
        print(f"   送达:{a['送达']} 读:{a['read_count']} 赞:{a['like_count']}")
    
    print("\n=== TOP 10 点赞数 ===")
    for i, a in enumerate(by_like[:10], 1):
        print(f"{i}. {a['title'][:40]}")
        print(f"   赞:{a['like_count']} 分:{a['share_count']} 藏:{a['fav_count']}")
    
    print("\n=== TOP 10 打开率（送达>100）===")
    for i, a in enumerate(by_open_rate[:10], 1):
        open_rate = a['read_count']/a['送达']*100 if a['送达']>0 else 0
        print(f"{i}. {a['title'][:40]}")
        print(f"   送达:{a['送达']} 打开率:{open_rate:.1f}%")
    
    low_open = [a for a in with_send if a['送达']>1000 and a['read_count']/a['送达']*100 < 1]
    if low_open:
        print("\n⚠️ 低打开率警示（送达>1000，打开率<1%）:")
        for a in low_open[:5]:
            open_rate = a['read_count']/a['送达']*100 if a['送达']>0 else 0
            print(f"   {a['title'][:35]}: {open_rate:.2f}%")
    
    external = [a for a in articles if a['like_count'] > a['read_count'] and a['read_count'] > 0]
    if external:
        print("\n🌟 外部传播文章（点赞>阅读）:")
        for a in external[:5]:
            ext_likes = a['like_count'] - a['read_count']
            print(f"   {a['title'][:35]}: 外部点赞+{ext_likes}")


async def main():
    parser = argparse.ArgumentParser(description='微信公众号数据抓取')
    parser.add_argument('--analyze', action='store_true', help='仅分析已保存数据')
    args = parser.parse_args()
    
    if args.analyze:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE) as f:
                articles = json.load(f)
            analyze_articles(articles)
        else:
            print(f"❌ 数据文件不存在: {STATS_FILE}")
        return
    
    client = HermesWebFetcher()
    await client.connect()
    
    is_logged_in, account_name, token = await check_login_and_account(client)
    
    if not is_logged_in:
        await client.disconnect()
        return
    
    articles = await fetch_all_stats(client, token)
    await client.disconnect()
    
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    titles = [a['title'] for a in articles]
    with open(PUBLISHED_FILE, 'w', encoding='utf-8') as f:
        json.dump({'titles': titles, 'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 保存 {len(articles)} 篇到 {STATS_FILE}")
    print(f"✅ 更新已发布列表: {PUBLISHED_FILE}")
    
    analyze_articles(articles)


if __name__ == '__main__':
    asyncio.run(main())