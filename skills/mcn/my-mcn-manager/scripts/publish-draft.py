# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
公众号草稿发布脚本

用法:
    python publish-draft.py --article article.md --date 2026-04-14

流程:
    1. 获取 access_token
    2. 上传封面图（永久素材）
    3. 上传正文配图（获取 URL）
    4. 构建 HTML 内容
    5. 创建草稿
"""

import sys
import os
import json
import ssl
import urllib.request
import argparse
import yaml
import re

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
AUTHOR = publish_config.get('author', 'TimeSky')

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

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


def upload_permanent_image(access_token, filepath):
    """上传图片到永久素材库，返回 media_id"""
    with open(filepath, 'rb') as f:
        image_data = f.read()
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode())
    body.extend(f'Content-Disposition: form-data; name="media"; filename="image.png"\r\n'.encode())
    body.extend(f'Content-Type: image/png\r\n\r\n'.encode())
    body.extend(image_data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"
    
    try:
        req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'media_id' in result:
            return result['media_id']
        else:
            print(f"上传失败: {result}")
            return None
    except Exception as e:
        print(f"上传错误: {e}")
        return None


def upload_content_image(access_token, filepath):
    """上传图文消息内图片，返回 URL"""
    with open(filepath, 'rb') as f:
        image_data = f.read()
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode())
    body.extend(f'Content-Disposition: form-data; name="media"; filename="image.png"\r\n'.encode())
    body.extend(f'Content-Type: image/png\r\n\r\n'.encode())
    body.extend(image_data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
    
    try:
        req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'url' in result:
            return result['url']
        else:
            print(f"上传失败: {result}")
            return None
    except Exception as e:
        print(f"上传错误: {e}")
        return None


def md_to_html(md_content, image_urls):
    """将 Markdown 转换为公众号 HTML"""
    lines = md_content.split('\n')
    html_parts = []
    
    title = ""
    content_started = False
    
    for line in lines:
        if line.startswith('# ') and not title:
            title = line[2:].strip()
            content_started = True
            continue
        
        if not content_started:
            continue
        
        if line.startswith('## '):
            html_parts.append(f'<p><strong>{line[3:].strip()}</strong></p>')
        elif line.startswith('**') and line.endswith('**'):
            html_parts.append(f'<p><strong>{line[2:-2]}</strong></p>')
        elif line.strip() == '':
            html_parts.append('<br/>')
        elif line.startswith('- ') or line.startswith('* '):
            html_parts.append(f'<p>• {line[2:]}</p>')
        else:
            html_parts.append(f'<p>{line}</p>')
    
    # 在合适位置插入图片
    html_content = '\n'.join(html_parts)
    
    # 简化：在第 3 和第 5 个段落后插入图片
    parts = html_content.split('</p>')
    if len(image_urls) > 0 and len(parts) > 5:
        parts[2] += f'</p><p><img src="{image_urls[0]}"/></p>'
    if len(image_urls) > 1 and len(parts) > 10:
        parts[5] += f'</p><p><img src="{image_urls[1]}"/></p>'
    if len(image_urls) > 2 and len(parts) > 15:
        parts[8] += f'</p><p><img src="{image_urls[2]}"/></p>'
    
    html_content = ''.join(parts)
    
    return title, html_content


def create_draft(access_token, title, thumb_media_id, author, content):
    """创建草稿"""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    
    draft_data = {
        "articles": [{
            "title": title,
            "thumb_media_id": thumb_media_id,
            "author": author,
            "content": content,
            "need_open_comment": 0,
            "only_fans_can_comment": 0
        }]
    }
    
    try:
        req_data = json.dumps(draft_data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'media_id' in result:
            return result['media_id']
        else:
            print(f"创建草稿失败: {result}")
            return None
    except Exception as e:
        print(f"创建草稿错误: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='公众号草稿发布')
    parser.add_argument('--article', type=str, required=True, help='文章路径')
    parser.add_argument('--date', type=str, required=True, help='日期')
    parser.add_argument('--images', type=str, nargs='+', help='配图路径列表')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("公众号草稿发布")
    print("=" * 60)
    print()
    
    # 获取 access_token
    print("[1] 获取 access_token...")
    access_token = get_access_token()
    if not access_token:
        print("❌ 获取失败")
        sys.exit(1)
    print(f"✅ Token: {access_token[:20]}...")
    
    # 确定图片目录
    images_dir = os.path.join(KB_ROOT, "tmp/images", args.date)
    
    # 上传封面图
    print("\n[2] 上传封面图...")
    cover_path = os.path.join(images_dir, "cover.png")
    if not os.path.exists(cover_path):
        print(f"❌ 封面图不存在: {cover_path}")
        sys.exit(1)
    
    thumb_media_id = upload_permanent_image(access_token, cover_path)
    if not thumb_media_id:
        print("❌ 上传失败")
        sys.exit(1)
    print(f"✅ thumb_media_id: {thumb_media_id}")
    
    # 上传正文配图
    print("\n[3] 上传正文配图...")
    image_urls = []
    image_files = ["img_1.png", "img_2.png", "img_3.png"]
    
    for img_file in image_files:
        img_path = os.path.join(images_dir, img_file)
        if os.path.exists(img_path):
            url = upload_content_image(access_token, img_path)
            if url:
                image_urls.append(url)
                print(f"✅ {img_file}: {url[:50]}...")
    
    print(f"共上传 {len(image_urls)} 张配图")
    
    # 读取文章
    print("\n[4] 构建 HTML 内容...")
    with open(args.article, 'r', encoding='utf-8') as f:
        article_md = f.read()
    
    title, html_content = md_to_html(article_md, image_urls)
    
    print(f"标题: {title[:30]}...")
    print(f"HTML 长度: {len(html_content)} 字符")
    
    # 创建草稿
    print("\n[5] 创建草稿...")
    draft_media_id = create_draft(access_token, title, thumb_media_id, AUTHOR, html_content)
    
    if draft_media_id:
        print(f"\n✅ 草稿创建成功!")
        print(f"   media_id: {draft_media_id}")
        print()
        print("下一步: 登录公众号后台查看并发布")
    else:
        print("\n❌ 创建失败")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == '__main__':
    main()