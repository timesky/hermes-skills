#!/usr/bin/env python3
"""
微信公众号：确认主题后生成并发布
用于用户确认主题后自动执行完整流程

用法:
    python scripts/publish_after_confirm.py <主题> [--style professional]
"""

import json
import urllib.request
import ssl
import os
import re
import sys
import yaml
import subprocess
from datetime import datetime

# 配置路径
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
WECHAT_CONFIG = os.path.expanduser("~/.hermes/wechat_mp_config.yaml")
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"

def load_config():
    """加载配置"""
    with open(MCN_CONFIG) as f:
        mcn_config = yaml.safe_load(f)
    with open(WECHAT_CONFIG) as f:
        wechat_config = yaml.safe_load(f)
    return mcn_config, wechat_config

def get_token(appid, secret):
    """获取 access_token"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    resp = urllib.request.urlopen(url, context=ctx)
    return json.loads(resp.read().decode('utf-8'))['access_token']

def upload_image(token, filepath):
    """上传图片到永久素材库"""
    result = subprocess.run([
        'curl', '-s',
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        '-F', f"media=@{filepath}"
    ], capture_output=True, text=True)
    
    data = json.loads(result.stdout)
    return data.get('media_id', ''), data.get('url', '')

def resize_image(input_path, output_path, width=900, height=500):
    """调整图片尺寸"""
    result = subprocess.run([
        'sips', '-z', str(height), str(width),
        input_path, '--out', output_path
    ], capture_output=True, text=True)
    return result.returncode == 0

def create_draft(token, article_data):
    """创建草稿"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # 关键：ensure_ascii=False
    json_body = json.dumps(article_data, ensure_ascii=False)
    
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    req = urllib.request.Request(url,
        data=json_body.encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    
    resp = urllib.request.urlopen(req, context=ctx)
    return json.loads(resp.read().decode('utf-8'))

def generate_article_content(topic, style='professional'):
    """生成文章内容（调用 LLM）"""
    # 这里调用 Ollama 或其他 LLM
    # TODO: 集成实际 LLM 调用
    print(f"生成文章：{topic} (风格：{style})")
    
    # 占位实现
    content = f"""# {topic}

## 引言

{topic}是当前的热门话题...

## 正文

详细内容待生成...

## 总结

...
"""
    return content

def generate_images(topic, count=4):
    """生成配图（调用 AI 图片生成 API）"""
    # TODO: 集成 ai-image-generation 模块
    print(f"生成 {count} 张配图：{topic}")
    return []

def publish_topic(topic, style='professional'):
    """
    发布单个主题的完整流程
    
    Args:
        topic: 文章主题
        style: 文章风格（professional/casual/story）
    
    Returns:
        dict: 发布结果
    """
    print("=" * 60)
    print(f"发布主题：{topic}")
    print("=" * 60)
    
    mcn_config, wechat_config = load_config()
    appid = wechat_config['appid']
    secret = wechat_config['secret']
    author = wechat_config.get('author', 'TimeSky')
    
    # 1. 获取 token
    print("\n[1/6] 获取 access_token...")
    token = get_token(appid, secret)
    print(f"✓ Token 获取成功")
    
    # 2. 生成文章内容
    print("\n[2/6] 生成文章内容...")
    article_content = generate_article_content(topic, style)
    
    # 保存文章到临时文件
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = f"{KB_ROOT}/tmp/content/{date_str}"
    os.makedirs(output_dir, exist_ok=True)
    
    article_filename = f"{output_dir}/{topic.replace(' ', '-')}.md"
    with open(article_filename, 'w', encoding='utf-8') as f:
        f.write(f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
source_topic: {topic}
platform: wechat-mp
status: draft
style: {style}
---

{article_content}
""")
    print(f"✓ 文章已保存：{article_filename}")
    
    # 3. 生成配图
    print("\n[3/6] 生成配图...")
    img_dir = f"{output_dir}/images/{topic.replace(' ', '-')}"
    os.makedirs(img_dir, exist_ok=True)
    
    # TODO: 实际调用 AI 图片生成
    # 这里检查是否已有配图
    if os.path.exists(img_dir):
        existing_imgs = [f for f in os.listdir(img_dir) if f.endswith(('.png', '.jpg'))]
        if existing_imgs:
            print(f"✓ 使用已有配图：{len(existing_imgs)}张")
        else:
            print("⚠️ 暂无配图，需手动添加")
    
    # 4. 上传封面图
    print("\n[4/6] 上传封面图...")
    cover_path = f"{img_dir}/img_1.png"
    cover_resized = f"{img_dir}/cover_900x500.png"
    
    if os.path.exists(cover_path):
        if resize_image(cover_path, cover_resized):
            cover_media_id, cover_url = upload_image(token, cover_resized)
            print(f"✓ 封面图上传成功：{cover_media_id}")
        else:
            print("⚠️ 图片调整失败，使用原图")
            cover_media_id, cover_url = upload_image(token, cover_path)
    else:
        print("⚠️ 封面图不存在，使用占位图")
        cover_media_id = ""
    
    # 5. 上传正文配图
    print("\n[5/6] 上传正文配图...")
    img_urls = []
    if os.path.exists(img_dir):
        for img_file in sorted(os.listdir(img_dir)):
            if img_file.endswith(('.png', '.jpg', '.jpeg')) and img_file != 'cover_900x500.png':
                img_path = f"{img_dir}/{img_file}"
                media_id, img_url = upload_image(token, img_path)
                if img_url:
                    img_urls.append(img_url)
                    print(f"✓ 上传：{img_file} → {img_url[:50]}...")
    
    print(f"共上传 {len(img_urls)} 张配图")
    
    # 6. 创建草稿
    print("\n[6/6] 创建草稿...")
    
    # 构建 HTML 内容
    body_start = article_content.find('\n\n') + 2
    body = article_content[body_start:]
    
    html_paragraphs = []
    for para in body.split('\n\n'):
        if para.strip():
            para = para.strip().replace('\n', '<br/>')
            html_paragraphs.append(f"<p>{para}</p>")
    
    html_content = '\n'.join(html_paragraphs)
    
    # 插入配图
    for img_url in img_urls[:3]:
        img_html = f'<p style="text-align:center;"><img src="{img_url}" style="max-width:100%;border-radius:8px;"/></p>'
        html_content = img_html + html_content
    
    # 提取标题和摘要
    title_match = re.search(r'# (.+)', article_content)
    title = title_match.group(1) if title_match else topic
    digest = body[:200].replace('\n', ' ').strip()
    if len(digest) > 120:
        digest = digest[:117] + "..."
    
    # 创建草稿数据
    draft_data = {
        "articles": [{
            "title": title,
            "author": author,
            "content": html_content,
            "thumb_media_id": cover_media_id,
            "digest": digest,
            "need_open_comment": 0,
        }]
    }
    
    draft_result = create_draft(token, draft_data)
    
    if 'media_id' in draft_result:
        print(f"\n✅ 草稿创建成功!")
        print(f"   media_id: {draft_result['media_id']}")
        print(f"   标题：{title}")
        
        return {
            "status": "success",
            "topic": topic,
            "media_id": draft_result['media_id'],
            "title": title,
            "article_path": article_filename
        }
    else:
        print(f"\n❌ 草稿创建失败: {draft_result}")
        return {
            "status": "failed",
            "topic": topic,
            "error": draft_result
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python publish_after_confirm.py <主题> [--style professional|casual|story]")
        sys.exit(1)
    
    topic = sys.argv[1]
    style = 'professional'
    
    if '--style' in sys.argv:
        idx = sys.argv.index('--style')
        if idx + 1 < len(sys.argv):
            style = sys.argv[idx + 1]
    
    result = publish_topic(topic, style)
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
