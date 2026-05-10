# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
公众号草稿发布脚本 - 支持代理

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
from datetime import datetime

# Profile隔离：HERMES_HOME在子profile指向子目录，需推导主目录找技能
_hermes_home = os.environ.get('HERMES_HOME', '/Users/hy_timesky/.hermes')
if '/profiles/' in _hermes_home:
    HERMES_MAIN_HOME = _hermes_home.split('/profiles/')[0]
else:
    HERMES_MAIN_HOME = _hermes_home
HERMES_HOME = _hermes_home
SKILLS_DIR = os.path.join(HERMES_MAIN_HOME, 'skills')

# 配置文件（profile隔离）
config_path = os.path.join(HERMES_HOME, 'mcn_config.yaml')
if not os.path.exists(config_path):
    # fallback到主目录
    config_path = os.path.join(HERMES_MAIN_HOME, 'mcn_config.yaml')
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = {}

# 从配置读取 kb_root
KB_ROOT = config.get('paths', {}).get('kb_root', os.path.expanduser("~/Documents/My_Obsidian"))
MCN_ROOT = KB_ROOT + "/mcn"

# ==================== Workflow.json 锚点更新 ====================
WORKFLOW_JSON = os.path.join(KB_ROOT, "mcn/workflow.json")

def update_workflow_json(status: str, topic_slug: str = None, data_updates: dict = None):
    """更新 workflow.json 状态"""
    try:
        if not os.path.exists(WORKFLOW_JSON):
            print(f"  ⚠️ workflow.json 不存在，跳过更新")
            return
        with open(WORKFLOW_JSON, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        workflow['status'] = status
        workflow['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if topic_slug:
            workflow['current_topic'] = topic_slug
        if data_updates:
            workflow.update(data_updates)
        with open(WORKFLOW_JSON, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        print(f"  ✓ workflow.json 已更新: status={status}")
    except Exception as e:
        print(f"  ⚠️ workflow.json 更新失败: {e}")

# 加载环境变量 - 使用HERMES_HOME环境变量
def load_env():
    env_path = os.path.join(HERMES_HOME, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_env()

publish_config = config.get('publish', {}).get('accounts', {}).get('main', {})
PROXY = config.get('publish', {}).get('proxy', '')
APPID = publish_config.get('appid', '')
SECRET = publish_config.get('secret', '')
AUTHOR = publish_config.get('author', 'TimeSky')

# 目录约定（自包含，不依赖其他技能模块）
def slugify(text):
    import re
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【»]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s[:50].strip('-')

def get_images_dir(date, topic_slug):
    return f"{MCN_ROOT}/content/{date}/{topic_slug}/images"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_opener():
    """获取带有代理的 opener"""
    if PROXY:
        proxy_handler = urllib.request.ProxyHandler({
            'http': PROXY,
            'https': PROXY
        })
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
        print(f"  使用代理: {PROXY.split('@')[1] if '@' in PROXY else PROXY}")
        return opener
    else:
        return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def get_access_token():
    """获取公众号 access_token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    
    try:
        opener = get_opener()
        req = urllib.request.Request(url)
        resp = opener.open(req, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'access_token' in result:
            return result['access_token']
        else:
            print(f"获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 token 错误: {e}")
        return None


def upload_temp_image(access_token, filepath, max_retries=3):
    """上传图片到临时素材（正文图片用），返回 URL
    
    Args:
        access_token: 微信 access_token
        filepath: 图片文件路径
        max_retries: 最大重试次数（默认3次）
    """
    import time
    
    with open(filepath, 'rb') as f:
        image_data = f.read()
    
    # 检测实际图片类型（根据文件头）
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        content_type = 'image/png'
        filename = 'image.png'
    elif image_data[:2] == b'\xff\xd8':
        content_type = 'image/jpeg'
        filename = 'image.jpg'
    else:
        content_type = 'image/png'
        filename = 'image.png'
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode())
    body.extend(f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'.encode())
    body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode())
    body.extend(image_data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    
    # 临时素材接口（正文图片用，返回URL）
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
    
    for attempt in range(1, max_retries + 1):
        try:
            opener = get_opener()
            req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
            resp = opener.open(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            
            if 'url' in result:
                if attempt > 1:
                    print(f"  ✓ 重试第{attempt}次成功")
                return result['url']
            else:
                print(f"  ⚠️ 上传失败（第{attempt}次）: {result}")
                if attempt < max_retries:
                    time.sleep(2)
        except Exception as e:
            print(f"  ⚠️ 上传错误（第{attempt}次）: {e}")
            if attempt < max_retries:
                print(f"     → 等待2秒后重试...")
                time.sleep(2)
    
    print(f"  ❌ 上传失败，已重试{max_retries}次")
    return None


def upload_permanent_image(access_token, filepath, max_retries=3):
    """上传图片到永久素材库（封面用），返回 media_id
    
    注意：微信API要求 thumb_media_id 必须是永久素材ID
    
    Args:
        access_token: 微信 access_token
        filepath: 图片文件路径
        max_retries: 最大重试次数（默认3次）
    """
    import time
    
    with open(filepath, 'rb') as f:
        image_data = f.read()
    
    # 检测实际图片类型（根据文件头）
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        content_type = 'image/png'
        filename = 'image.png'
    elif image_data[:2] == b'\xff\xd8':
        content_type = 'image/jpeg'
        filename = 'image.jpg'
    else:
        content_type = 'image/png'
        filename = 'image.png'
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode())
    body.extend(f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'.encode())
    body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode())
    body.extend(image_data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    
    # 永久素材接口（封面用，返回media_id）
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"
    
    for attempt in range(1, max_retries + 1):
        try:
            opener = get_opener()
            req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
            resp = opener.open(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            
            if 'media_id' in result:
                if attempt > 1:
                    print(f"  ✓ 重试第{attempt}次成功")
                return result['media_id']
            else:
                print(f"  ⚠️ 上传失败（第{attempt}次）: {result}")
                if attempt < max_retries:
                    time.sleep(2)
        except Exception as e:
            print(f"  ⚠️ 上传错误（第{attempt}次）: {e}")
            if attempt < max_retries:
                print(f"     → 等待2秒后重试...")
                time.sleep(2)
    
    print(f"  ❌ 上传失败，已重试{max_retries}次")
    return None


def upload_content_image(access_token, filepath, max_retries=3):
    """上传图文消息内图片，返回 URL（支持重试）
    
    Args:
        access_token: 微信 access_token
        filepath: 图片文件路径
        max_retries: 最大重试次数（默认3次）
    """
    import time
    
    with open(filepath, 'rb') as f:
        image_data = f.read()
    
    # 检测实际图片类型（根据文件头）
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        content_type = 'image/png'
        filename = 'image.png'
    elif image_data[:2] == b'\xff\xd8':
        content_type = 'image/jpeg'
        filename = 'image.jpg'
    else:
        # 默认 PNG
        content_type = 'image/png'
        filename = 'image.png'
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode())
    body.extend(f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'.encode())
    body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode())
    body.extend(image_data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
    
    for attempt in range(1, max_retries + 1):
        try:
            opener = get_opener()
            req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
            resp = opener.open(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            
            if 'url' in result:
                if attempt > 1:
                    print(f"  ✓ 重试第{attempt}次成功")
                return result['url']
            else:
                print(f"  ⚠️ 上传失败（第{attempt}次）: {result}")
                if attempt < max_retries:
                    time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            print(f"  ⚠️ 上传错误（第{attempt}次）: {e}")
            if attempt < max_retries:
                print(f"     → 等待2秒后重试...")
                time.sleep(2)
    
    print(f"  ❌ 上传失败，已重试{max_retries}次")
    return None


def get_account_name():
    """获取公众号名称"""
    return publish_config.get('name', '程序员的开发手册')

def get_footer_html():
    """获取固定尾部 HTML"""
    account_name = get_account_name()
    return f'''
<div style="margin-top: 40px; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 10px; text-align: center;">
  <p style="font-size: 14px; color: #666; margin-bottom: 10px;">如果觉得有用，点个「在看」支持一下 👇</p>
  <p style="font-size: 16px; font-weight: bold; color: #333; margin-bottom: 5px;">关注「{account_name}」</p>
  <p style="font-size: 13px; color: #888;">分享技术干货 · 聊聊行业观察 · 记录成长思考</p>
</div>
'''

def md_to_html(md_content, image_urls, cover_url=None):
    """将 Markdown 转换为公众号 HTML
    
    Args:
        md_content: Markdown 内容
        image_urls: 正文配图 URL 列表（img_1, img_2 等）
        cover_url: 封面图 URL（可选，用于作为首图）
    """
    lines = md_content.split('\n')
    html_parts = []
    
    title = ""
    content_started = False
    in_table = False
    table_rows = []
    
    for line in lines:
        if line.startswith('# ') and not title:
            title = line[2:].strip()
            content_started = True
            continue
        
        if not content_started:
            continue
        
        # 处理表格
        if line.startswith('|') and '|' in line[1:]:
            if not in_table:
                in_table = True
                table_rows = []
            # 跳过表头分隔行 |---|---|
            if not re.match(r'^\|[\s\-:]+\|[\s\-:]+\|', line):
                cells = [c.strip() for c in line.split('|') if c.strip()]
                table_rows.append(cells)
            continue
        elif in_table:
            # 表格结束，生成 HTML
            in_table = False
            if table_rows:
                table_html = '<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">'
                for i, row in enumerate(table_rows):
                    bg = '#f5f5f5' if i == 0 else '#fff'
                    table_html += '<tr style="background: ' + bg + ';">'
                    for cell in row:
                        # 处理单元格内的加粗
                        cell = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                        if i == 0:
                            table_html += f'<th style="padding: 10px; border: 1px solid #ddd; text-align: left;">{cell}</th>'
                        else:
                            table_html += f'<td style="padding: 10px; border: 1px solid #ddd;">{cell}</td>'
                    table_html += '</tr>'
                table_html += '</table>'
                html_parts.append(table_html)
            table_rows = []
        
        # 处理分隔线
        if line.strip() == '---':
            html_parts.append('<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;"/>')
            continue
        
        # 处理三级标题
        if line.startswith('### '):
            html_parts.append(f'<p style="font-weight: bold; font-size: 15px;">{line[4:].strip()}</p>')
            continue
        
        # 处理二级标题
        if line.startswith('## '):
            html_parts.append(f'<p style="font-weight: bold; font-size: 16px; margin-top: 20px;">{line[3:].strip()}</p>')
            continue
        
        # 处理空行
        if line.strip() == '':
            html_parts.append('<br/>')
            continue
        
        # 处理列表
        if line.startswith('- ') or line.startswith('* '):
            item = line[2:]
            # 只处理行内加粗，链接保持 Markdown 格式绕过平台屏蔽
            item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
            html_parts.append(f'<p style="padding-left: 10px;">• {item}</p>')
            continue
        
        # 处理普通段落 - 只转换加粗，链接保持 Markdown 格式
        processed = line
        processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
        # 不转换链接，保持 [文字](URL) 格式
        html_parts.append(f'<p>{processed}</p>')
    
    # 添加封面图作为首图（如果有）
    if cover_url:
        cover_html = f'<div style="text-align: center; margin: 20px 0;"><img src="{cover_url}" style="max-width: 100%; border-radius: 8px;"/></div>'
        html_parts.insert(0, cover_html)
        print(f"  ✓ 已添加封面图作为首图")
    
    # 在合适位置插入图片（均匀分布）
    html_content = '\n'.join(html_parts)
    
    parts = html_content.split('</p>')
    total_parts = len(parts)
    
    # 根据图片数量动态计算插入位置（跳过已插入的封面图位置）
    for i, img_url in enumerate(image_urls):
        # 在文章 30%, 60% 位置插入段落图（封面图已在开头）
        insert_ratio = 0.3 + (i * 0.3)
        insert_pos = int(total_parts * insert_ratio)
        
        if insert_pos < len(parts) - 1:
            parts[insert_pos] += f'</p><p><img src="{img_url}"/></p>'
            print(f"  ✓ 插入段落图 {i+1} 在位置 {insert_pos} ({int(insert_ratio*100)}%)")
    
    html_content = ''.join(parts)
    
    # 添加固定尾部
    footer = get_footer_html()
    html_content = html_content + footer
    print(f"  ✓ 已添加固定尾部（公众号: {get_account_name()}）")
    
    return title, html_content


def create_draft(access_token, title, thumb_media_id, author, content, 
                 need_open_comment=True, only_fans_can_comment=True):
    """创建草稿
    
    Args:
        need_open_comment: 是否开启留言（默认 True）
        only_fans_can_comment: 是否仅粉丝可评论（默认 True = 仅关注者可留言）
    """
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    
    # 转换为 API 需要的格式
    comment_flag = 1 if need_open_comment else 0
    fans_flag = 1 if only_fans_can_comment else 0
    
    draft_data = {
        "articles": [{
            "title": title,
            "thumb_media_id": thumb_media_id,
            "author": author,
            "content": content,
            "need_open_comment": comment_flag,  # 留言：0=关闭，1=开启
            "only_fans_can_comment": fans_flag   # 仅粉丝可评论：0=所有人，1=仅粉丝
        }]
    }
    
    try:
        opener = get_opener()
        # 关键：确保 UTF-8 编码正确发送
        req_data = json.dumps(draft_data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json; charset=utf-8'})
        resp = opener.open(req, timeout=30)
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
    parser.add_argument('--topic', type=str, help='文章主题（用于定位配图目录）')
    parser.add_argument('--images', type=str, nargs='+', help='配图路径列表（可选，不指定则自动扫描）')
    parser.add_argument('--no-comment', action='store_true', help='关闭留言（默认开启）')
    parser.add_argument('--all-can-comment', action='store_true', help='所有人可评论（默认仅关注者可留言）')
    
    args = parser.parse_args()
    
    # 从文章路径提取 topic_slug（如果未指定 topic）
    if not args.topic and args.article:
        # 文章路径格式: .../content/{date}/{topic_slug}/article.md
        article_dir = os.path.dirname(args.article)
        topic_slug = os.path.basename(article_dir)
        args.topic = topic_slug
    
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
    
    # 使用内联目录函数（含 topic_slug）
    images_dir = get_images_dir(args.date, args.topic)
    
    print(f"配图目录: {images_dir}")
    
    # 上传封面图
    print("\n[2] 上传封面图...")
    cover_candidates = [
        os.path.join(images_dir, "cover_upload.jpg"),  # 优先 JPG（更小）
        os.path.join(images_dir, "cover.jpg"),
        os.path.join(images_dir, "cover.png"),
    ]
    
    cover_path = None
    for candidate in cover_candidates:
        if os.path.exists(candidate):
            cover_path = candidate
            break
    
    if not cover_path:
        print(f"❌ 封面图不存在，尝试过的路径:")
        for c in cover_candidates:
            print(f"   {c}")
        sys.exit(1)
    
    thumb_media_id = upload_permanent_image(access_token, cover_path)
    if not thumb_media_id:
        print("❌ 上传失败")
        sys.exit(1)
    print(f"✅ thumb_media_id: {thumb_media_id}")
    
    # 上传正文配图
    print("\n[3] 上传正文配图...")
    image_urls = []
    
    # 动态扫描 images_dir 中的所有配图（优先 JPG）
    if os.path.exists(images_dir):
        # 优先 JPG 版本（*_upload.jpg）
        img_files = sorted([f for f in os.listdir(images_dir) if f.endswith("_upload.jpg")])
        if not img_files:
            # 次优先：img_*.jpg
            img_files = sorted([f for f in os.listdir(images_dir) if f.startswith("img_") and f.endswith(".jpg")])
        if not img_files:
            # 回退到 PNG
            img_files = sorted([f for f in os.listdir(images_dir) if f.startswith("img_") and f.endswith(".png")])
        print(f"发现 {len(img_files)} 张配图: {', '.join(img_files)}")
        
        for img_file in img_files:
            img_path = os.path.join(images_dir, img_file)
            url = upload_content_image(access_token, img_path)
            if url:
                image_urls.append(url)
                print(f"✅ {img_file}: {url[:50]}...")
    else:
        print(f"⚠️ 图片目录不存在: {images_dir}")
    
    print(f"共上传 {len(image_urls)} 张配图")
    
    # 读取文章
    print("\n[4] 构建 HTML 内容...")
    
    # 优先使用 layout 文件（如果存在）
    article_dir = os.path.dirname(args.article)
    layout_file = args.article.replace('.md', '-layout.html')
    
    # 如果传入的是 md 文件，检查是否有对应的 layout 文件
    if args.article.endswith('.md') and os.path.exists(layout_file):
        args.article = layout_file
        print(f"  ✓ 使用排版后的 HTML 文件: {layout_file}")
    
    # 检查是否是 HTML 文件
    if args.article.endswith('.html'):
        # 直接读取 HTML 文件
        with open(args.article, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 从 HTML 提取标题（第一个 h1）
        import re
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # 回退到文件名
            title = os.path.basename(args.article).replace('.html', '')
        
        # 提取 body 内容（去掉 <!DOCTYPE>, <html>, <head>, <body> 外层结构）
        # 公众号只需要 body 内的 HTML
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
        if body_match:
            html_content = body_match.group(1).strip()
            print(f"  ✓ 已提取 body 内容（去掉外层 HTML 结构）")
        
        # 替换图片占位符
        # IMG_0 用封面图（第一张上传的）
        # IMG_1, IMG_2 用正文配图
        if len(image_urls) >= 1:
            # 封面图作为首图（IMG_0）
            # 需要单独上传封面图到正文图库（不同于永久素材封面）
            cover_candidates = [
                os.path.join(images_dir, 'cover.jpg'),  # 优先 JPG
                os.path.join(images_dir, 'cover.png'),  # 回退 PNG
            ]
            cover_img_url = None
            for cover_path in cover_candidates:
                if os.path.exists(cover_path):
                    cover_img_url = upload_content_image(access_token, cover_path)
                    if cover_img_url:
                        break
            if cover_img_url:
                html_content = html_content.replace('IMG_0_PLACEHOLDER', cover_img_url)
                print(f"  ✓ 封面图作为首图: {cover_img_url[:50]}...")
        
        # 正文配图
        for i, url in enumerate(image_urls, 1):
            html_content = html_content.replace(f'IMG_{i}_PLACEHOLDER', url)
        
        print(f"标题: {title[:30]}...")
        print(f"HTML 长度: {len(html_content)} 字符")
    else:
        # Markdown 文件（没有 layout 文件时回退）
        with open(args.article, 'r', encoding='utf-8') as f:
            article_md = f.read()
        
        # 上传封面图到正文图库（作为首图）
        cover_url = None
        cover_candidates = [
            os.path.join(images_dir, 'cover.jpg'),  # 优先 JPG
            os.path.join(images_dir, 'cover.png'),  # 回退 PNG
        ]
        for cover_path in cover_candidates:
            if os.path.exists(cover_path):
                cover_url = upload_content_image(access_token, cover_path)
                if cover_url:
                    print(f"  ✓ 封面图上传成功: {cover_url[:50]}...")
                    break
        
        title, html_content = md_to_html(article_md, image_urls, cover_url)
        
        print(f"标题: {title[:30]}...")
        print(f"HTML 长度: {len(html_content)} 字符")
    
    # 创建草稿
    print("\n[5] 创建草稿...")
    need_open_comment = not args.no_comment  # 默认开启留言
    # 默认仅关注者可留言（fans_only_comment 默认 True）
    fans_only = not args.all_can_comment if hasattr(args, 'all_can_comment') else True
    draft_media_id = create_draft(
        access_token, title, thumb_media_id, AUTHOR, html_content,
        need_open_comment=need_open_comment,
        only_fans_can_comment=fans_only
    )
    
    if draft_media_id:
        print(f"\n✅ 草稿创建成功!")
        print(f"   media_id: {draft_media_id}")
        
        # 更新 workflow.json
        update_workflow_json("published", args.topic)
        
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
