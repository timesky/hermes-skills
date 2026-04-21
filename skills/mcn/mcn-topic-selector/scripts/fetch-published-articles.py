#!/usr/bin/env python3
"""
获取公众号已发布文章列表

用法:
    python fetch-published-articles.py

输出:
    ~/.hermes/mcn_published.json - 已发布文章列表
"""

import os
import json
import ssl
import urllib.request
import time
import yaml

# 加载环境变量
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

# 加载配置
config_path = os.path.expanduser('~/.hermes/mcn_config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

publish_config = config.get('publish', {}).get('accounts', {}).get('main', {})
APPID = publish_config.get('appid', '')
SECRET = publish_config.get('secret', '')

OUTPUT_FILE = os.path.expanduser('~/.hermes/mcn_published.json')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_access_token():
    """获取公众号 access_token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'access_token' in result:
            return result['access_token']
        else:
            print(f"获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 token 错误: {e}")
        return None


def get_materials_list(access_token, offset=0, count=20):
    """获取素材列表"""
    url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={access_token}"
    
    payload = {
        "type": "news",
        "offset": offset,
        "count": count
    }
    
    try:
        req_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'item' in result:
            return result
        else:
            print(f"获取素材失败: {result}")
            return None
    except Exception as e:
        print(f"获取素材错误: {e}")
        return None


def extract_articles(materials_result):
    """从素材列表提取文章信息"""
    articles = []
    
    for item in materials_result.get('item', []):
        update_time = item.get('update_time', 0)
        
        for news_item in item.get('content', {}).get('news_item', []):
            title = news_item.get('title', '')
            
            if title:
                articles.append({
                    'title': title,
                    'publish_time': update_time,
                    'publish_date': time.strftime('%Y-%m-%d', time.localtime(update_time)) if update_time else None,
                    'media_id': item.get('media_id', '')
                })
    
    return articles


def fetch_all_published_articles():
    """获取所有已发布文章（分页）"""
    access_token = get_access_token()
    if not access_token:
        return []
    
    print(f"✅ Token: {access_token[:20]}...")
    
    all_articles = []
    offset = 0
    count = 20
    
    while True:
        print(f"获取素材列表 (offset={offset})...")
        result = get_materials_list(access_token, offset, count)
        
        if not result or not result.get('item'):
            break
        
        articles = extract_articles(result)
        all_articles.extend(articles)
        print(f"  获取 {len(articles)} 篇文章")
        
        # 检查是否还有更多
        total_count = result.get('total_count', 0)
        if offset + count >= total_count:
            break
        
        offset += count
    
    return all_articles


def extract_keywords(title):
    """从标题提取关键词"""
    # 简单分词：去掉标点，按2-4字分组
    import re
    
    # 去掉标点和特殊字符
    clean_title = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
    
    # 提取2-4字的词组
    keywords = []
    for length in range(4, 1, -1):  # 4字、3字、2字
        for i in range(len(clean_title) - length + 1):
            word = clean_title[i:i+length]
            if word and word not in keywords:
                keywords.append(word)
    
    return keywords[:10]  # 最多10个关键词


def main():
    print("=" * 60)
    print("获取公众号已发布文章列表")
    print("=" * 60)
    
    articles = fetch_all_published_articles()
    
    # 提取关键词
    for article in articles:
        article['keywords'] = extract_keywords(article['title'])
    
    # 保存
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 已保存 {len(articles)} 篇文章到 {OUTPUT_FILE}")
    
    # 显示最近文章
    if articles:
        print("\n最近发布的文章:")
        recent = sorted(articles, key=lambda x: x['publish_time'], reverse=True)[:5]
        for a in recent:
            print(f"  - {a['title']} ({a['publish_date']})")


if __name__ == '__main__':
    main()