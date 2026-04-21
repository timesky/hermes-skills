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

# ==================== Workflow.json 锚点更新 ====================

WORKFLOW_JSON = os.path.expanduser("~/backup/知识库-Obsidian/mcn/workflow.json")

def update_workflow_json(status: str, topic_slug: str = None, data_updates: dict = None):
    """更新 workflow.json 状态
    
    Args:
        status: 新状态 (content_done, images_done, published)
        topic_slug: 当前选题 slug（可选，用于更新 current_topic）
        data_updates: 其他数据字段更新（可选）
    """
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
PROXY = config.get('publish', {}).get('proxy', '')
APPID = publish_config.get('appid', '')
SECRET = publish_config.get('secret', '')
AUTHOR = publish_config.get('author', 'TimeSky')

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

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
        opener = get_opener()
        req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        resp = opener.open(req, timeout=30)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'media_id' in result:
            return result['media_id']
        else:
            print(f"上传失败: {result}")
            return None
    except Exception as e:
        print(f"上传错误: {e}")
        return None




def delete_permanent_material(access_token, media_id):
    """删除永久素材（避免累积）"""
    url = f"https://api.weixin.qq.com/cgi-bin/material/del_material?access_token={access_token}"
    
    data = {"media_id": media_id}
    
    try:
        opener = get_opener()
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
        resp = opener.open(req, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        
        if result.get('errcode') == 0:
            print(f"  ✓ 已删除封面永久素材: {media_id}")
            return True
        else:
            print(f"  ⚠️ 删除素材失败: {result}")
            return False
    except Exception as e:
        print(f"  ⚠️ 删除异常: {e}")
        return False
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
        opener = get_opener()
        req = urllib.request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        resp = opener.open(req, timeout=30)
        result = json.loads(resp.read().decode('utf-8'))
        
        if 'url' in result:
            return result['url']
        else:
            print(f"上传失败: {result}")
            return None
    except Exception as e:
        print(f"上传错误: {e}")
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
        opener = get_opener()
        req_data = json.dumps(draft_data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
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
    
    # 动态扫描 images_dir 中的所有 img_*.png 文件
    if os.path.exists(images_dir):
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
            cover_img_url = upload_content_image(access_token, os.path.join(images_dir, 'cover.png'))
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
        cover_path = os.path.join(images_dir, 'cover.png')
        if os.path.exists(cover_path):
            cover_url = upload_content_image(access_token, cover_path)
            if cover_url:
                print(f"  ✓ 封面图上传成功: {cover_url[:50]}...")
        
        title, html_content = md_to_html(article_md, image_urls, cover_url)
        
        print(f"标题: {title[:30]}...")
        print(f"HTML 长度: {len(html_content)} 字符")
    
    # 创建草稿
    print("\n[5] 创建草稿...")
    draft_media_id = create_draft(access_token, title, thumb_media_id, AUTHOR, html_content)
    
    if draft_media_id:
        print(f"\n✅ 草稿创建成功!")
        print(f"   media_id: {draft_media_id}")
        
        # 更新 workflow.json
        update_workflow_json("published", args.topic)
        
        # 删除封面永久素材（避免累积）
        print("\n[清理] 删除封面永久素材...")
        delete_permanent_material(access_token, thumb_media_id)
        
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
