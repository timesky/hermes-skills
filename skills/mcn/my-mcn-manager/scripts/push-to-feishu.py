# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
飞书推送脚本 - 支持多种推送模式
"""

import sys
import os
import json
import re
import argparse
import urllib.request
import ssl
import time

# 加载环境变量
def load_env():
    """从 .env 文件加载环境变量"""
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

# 配置
FEISHU_WEBHOOK = os.environ.get('FEISHU_WEBHOOK', '')
FEISHU_CHAT_ID = os.environ.get('FEISHU_CHAT_ID', '')
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', '')
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"
TASKS_DIR = KB_ROOT + "/tmp/tasks"

# Token 缓存
_cached_token = None
_token_expire_time = 0

def get_app_access_token():
    """获取飞书应用访问令牌"""
    global _cached_token, _token_expire_time
    
    # 检查缓存（提前 5 分钟刷新）
    if _cached_token and time.time() < _token_expire_time - 300:
        return _cached_token
    
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return None
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    data = json.dumps({
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        result = json.loads(resp.read().decode('utf-8'))
        
        if result.get('code') == 0:
            _cached_token = result['app_access_token']
            _token_expire_time = time.time() + result.get('expire', 7200)
            print("✓ 获取 app_access_token 成功")
            return _cached_token
        else:
            print("✗ 获取 token 失败：" + str(result))
            return None
    except Exception as e:
        print("✗ 错误：" + str(e))
        return None

def load_topic_report(date):
    """加载选题报告"""
    report_path = MCN_ROOT + "/topic/" + date + "/recommend.md"
    
    if not os.path.exists(report_path):
        print("✗ 选题报告不存在：" + report_path)
        return []
    
    content = open(report_path, encoding='utf-8').read()
    
    topics = []
    # 匹配表格内容
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('|') and '---' not in line and '排名' not in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 6:
                try:
                    rank = parts[1]
                    if rank.isdigit():
                        score = float(parts[5])
                        topics.append({
                            'rank': rank,
                            'title': parts[2],
                            'domain': parts[3],
                            'heat': parts[4],
                            'score': score,
                            'url': parts[6].replace('[查看](', '').replace(')', '')
                        })
                except:
                    pass
    
    return topics

def build_message(date, topics):
    """构建飞书消息"""
    
    message = "📊 MCN 选题分析报告\n日期：" + date + "\n\n🎯 推荐主题 (Top " + str(len(topics)) + ")\n\n"
    
    for topic in topics[:5]:
        emoji = "🔥" if topic['score'] > 70 else "📌"
        message += emoji + " " + topic['rank'] + ". " + topic['title'] + "\n"
        message += "   领域：" + topic['domain'] + " | 热度：" + topic['heat'] + " | 评分：" + str(topic['score']) + "\n\n"
    
    message += "\n💡 选题建议：优先选择评分 > 70 的话题\n"
    message += "\n👉 下一步：回复主题序号确认选题"
    
    return message

def send_via_api(message, chat_id):
    """通过飞书 API 发送"""
    
    token = get_app_access_token()
    if not token:
        print("✗ 无法获取 app_access_token")
        return False
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    
    data = json.dumps({
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": message}, ensure_ascii=False)
    }, ensure_ascii=False).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }
    )
    
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        
        if result.get('code') == 0:
            print("✓ 推送成功（API → " + chat_id + ")")
            return True
        else:
            print("✗ 推送失败：" + str(result))
            return False
    except Exception as e:
        print("✗ 错误：" + str(e))
        return False

def main():
    parser = argparse.ArgumentParser(description='飞书推送')
    parser.add_argument('--topic-report', type=str, help='推送选题报告（指定日期）')
    parser.add_argument('--message', type=str, help='消息内容')
    parser.add_argument('--target', type=str, choices=['current', 'default', 'task'],
                       default='current', help='推送目标')
    parser.add_argument('--chat-id', type=str, help='指定会话 ID')
    
    args = parser.parse_args()
    
    # 加载选题
    if args.topic_report:
        topics = load_topic_report(args.topic_report)
        if not topics:
            sys.exit(1)
        message = build_message(args.topic_report, topics)
    elif args.message:
        message = args.message
    else:
        print("用法：python push-to-feishu.py --topic-report 2026-04-14 [选项]")
        sys.exit(1)
    
    # 确定推送方式
    print("=" * 60)
    print("飞书推送")
    print("=" * 60)
    if FEISHU_APP_ID:
        print("APP_ID: " + FEISHU_APP_ID[:10] + "...")
    else:
        print("APP_ID: 未配置")
    if FEISHU_CHAT_ID:
        print("CHAT_ID: " + FEISHU_CHAT_ID)
    else:
        print("CHAT_ID: 未配置")
    print()
    
    success = False
    
    if args.chat_id:
        print("推送到指定会话：" + args.chat_id)
        success = send_via_api(message, args.chat_id)
    elif FEISHU_CHAT_ID:
        print("推送到当前会话：" + FEISHU_CHAT_ID)
        success = send_via_api(message, FEISHU_CHAT_ID)
    else:
        print("⚠️ FEISHU_CHAT_ID 未配置，无法推送")
        sys.exit(1)
    
    # 输出消息预览
    print("\n消息预览:")
    print("-" * 60)
    if len(message) > 500:
        print(message[:500] + "...")
    else:
        print(message)
    print("-" * 60)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()