#!/usr/bin/env python3
"""
微信公众号：确认主题后生成并发布
用于用户确认主题后自动执行完整流程
"""

import json
import urllib.request
import ssl
import os
import re

# 配置
CONFIG_PATH = os.path.expanduser("~/.hermes/wechat_mp_config.yaml")
OUTPUT_DIR = os.path.expanduser("~/backup/知识库-Obsidian/tmp/content")

def load_config():
    """加载配置"""
    import yaml
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def get_token(appid, secret):
    """获取 access_token"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    resp = urllib.request.urlopen(url, context=ctx)
    return json.loads(resp.read().decode('utf-8'))['access_token']

def upload_image(token, filepath):
    """上传图片到素材库"""
    import subprocess
    
    result = subprocess.run([
        'curl', '-s',
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        '-F', f"media=@{filepath}"
    ], capture_output=True, text=True)
    
    data = json.loads(result.stdout)
    return data.get('media_id', ''), data.get('url', '')

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

def publish_topic(topic: str, style: str = "科技"):
    """
    发布单个主题的完整流程
    
    Args:
        topic: 文章主题
        style: 文章风格（科技/商业/生活/热点）
    
    Returns:
        dict: 发布结果
    """
    config = load_config()
    appid = config['appid']
    secret = config['secret']
    author = config.get('author', 'TimeSky')
    
    # 1. 获取 token
    token = get_token(appid, secret)
    
    # 2. 生成配图（这里用占位图，实际应调用 SD）
    # TODO: 集成 Stable Diffusion API
    
    # 3. 上传配图
    # ...
    
    # 4. 生成文章内容（这里用占位，实际应调用 Ollama）
    # TODO: 集成 Ollama
    
    # 5. 创建草稿
    # ...
    
    return {"status": "success", "topic": topic}

if __name__ == "__main__":
    # 示例用法
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python publish_after_confirm.py <主题>")
        sys.exit(1)
    
    topic = sys.argv[1]
    result = publish_topic(topic)
    print(json.dumps(result, ensure_ascii=False))