#!/usr/bin/env python3
"""
任务管理器 - 统一管理 MCN 工作流
每个完整流程创建一个 task.md，记录所有步骤和文件位置
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
TASKS_DIR = KB_ROOT + "/tmp/tasks"
PUBLISHED_FILE = KB_ROOT + "/tmp/published_topics.json"

def get_task_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def init_task(topic="今日热点", platform=None, chat_id=None):
    """初始化任务，记录推送目标"""
    os.makedirs(TASKS_DIR, exist_ok=True)
    
    task_id = get_task_id()
    
    if platform is None:
        platform = 'feishu' if os.environ.get('FEISHU_WEBHOOK') else 'local'
    if chat_id is None:
        chat_id = os.environ.get('FEISHU_CHAT_ID', '')
    
    task_data = {
        'task_id': task_id,
        'created': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'topic': topic,
        'status': 'initiated',
        'notify': {
            'platform': platform,
            'chat_id': chat_id,
            'thread_id': os.environ.get('HERMES_THREAD_ID', '')
        },
        'steps': {
            'research': {'status': 'pending'},
            'topic_selection': {'status': 'pending'},
            'content_gen': {'status': 'pending'},
            'humanize': {'status': 'pending'},
            'images': {'status': 'pending'},
            'layout': {'status': 'pending'},
            'publish': {'status': 'pending'}
        }
    }
    
    # 保存 JSON
    json_file = TASKS_DIR + "/" + task_id + "_task.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)
    
    # 生成 Markdown
    md_content = "# MCN 工作流任务\n\n"
    md_content += "- **任务 ID**: " + task_id + "\n"
    md_content += "- **创建时间**: " + task_data['created'] + "\n"
    md_content += "- **主题**: " + topic + "\n"
    md_content += "- **推送平台**: " + platform + "\n"
    md_content += "- **会话 ID**: " + chat_id + "\n\n"
    md_content += "## 流程步骤\n\n"
    
    for i, (step, info) in enumerate(task_data['steps'].items(), 1):
        md_content += str(i) + ". " + step + ": ⏳ 待执行\n"
    
    md_file = TASKS_DIR + "/" + task_id + "_task.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print("✓ 任务已创建：" + md_file)
    print("  任务 ID: " + task_id)
    print("  推送目标：" + platform + " (" + (chat_id if chat_id else '默认') + ")")
    
    return task_id

def update_step(task_id, step, data=None, status='completed'):
    """更新步骤状态"""
    json_file = TASKS_DIR + "/" + task_id + "_task.json"
    
    if not os.path.exists(json_file):
        print("✗ 任务不存在：" + task_id)
        return False
    
    task_data = json.load(open(json_file))
    task_data['steps'][step] = {
        'status': status,
        'data': data or {},
        'updated': datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    # 更新总体状态
    completed = sum(1 for s in task_data['steps'].values() if s['status'] == 'completed')
    if completed == len(task_data['steps']):
        task_data['status'] = 'completed'
    elif completed > 0:
        task_data['status'] = 'in_progress'
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)
    
    print("✓ 步骤 " + step + " 已更新：" + status)
    return True

def get_task_status(task_id):
    """获取任务状态"""
    json_file = TASKS_DIR + "/" + task_id + "_task.json"
    
    if not os.path.exists(json_file):
        print("✗ 任务不存在：" + task_id)
        return None
    
    task_data = json.load(open(json_file))
    
    print("=" * 60)
    print("任务状态：" + task_id)
    print("=" * 60)
    print("主题：" + task_data['topic'])
    print("创建时间：" + task_data['created'])
    print("总体状态：" + task_data['status'])
    print()
    
    for step, info in task_data['steps'].items():
        icon = '✅' if info['status'] == 'completed' else '🔄' if info['status'] == 'in_progress' else '⏳'
        print(icon + " " + step + ": " + info['status'])
    
    return task_data

def list_tasks(days=7):
    """列出最近的任务"""
    if not os.path.exists(TASKS_DIR):
        print("暂无任务")
        return []
    
    tasks = []
    cutoff = datetime.now() - timedelta(days=days)
    
    for f in os.listdir(TASKS_DIR):
        if f.endswith('_task.json'):
            task_data = json.load(open(TASKS_DIR + "/" + f))
            created = datetime.strptime(task_data['created'], "%Y-%m-%d %H:%M")
            if created >= cutoff:
                tasks.append(task_data)
    
    tasks.sort(key=lambda x: x['created'], reverse=True)
    
    print("=" * 60)
    print("最近 " + str(days) + " 天的任务")
    print("=" * 60)
    
    for task in tasks:
        icon = '✅' if task['status'] == 'completed' else '🔄'
        print(icon + " " + task['task_id'] + " | " + task['topic'] + " | " + task['created'])
    
    return tasks

def record_published_topic(topic, media_id, date=None):
    """记录已发布主题（30 天内去重）"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(PUBLISHED_FILE):
        published = json.load(open(PUBLISHED_FILE))
    else:
        published = {'topics': []}
    
    published['topics'].append({
        'topic': topic,
        'media_id': media_id,
        'date': date,
        'published_at': datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    # 保留最近 30 天
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    published['topics'] = [t for t in published['topics'] if t['date'] >= cutoff]
    
    os.makedirs(os.path.dirname(PUBLISHED_FILE), exist_ok=True)
    with open(PUBLISHED_FILE, 'w', encoding='utf-8') as f:
        json.dump(published, f, ensure_ascii=False, indent=2)
    
    print("✓ 已记录发布主题：" + topic)

def check_duplicate_topic(topic):
    """检查主题是否已发布（30 天内）"""
    if not os.path.exists(PUBLISHED_FILE):
        return False
    
    published = json.load(open(PUBLISHED_FILE))
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    for item in published['topics']:
        if item['date'] >= cutoff:
            if topic.lower() in item['topic'].lower() or item['topic'].lower() in topic.lower():
                return True
    
    return False

def get_notify_info(task_id):
    """获取任务的推送信息"""
    json_file = TASKS_DIR + "/" + task_id + "_task.json"
    
    if not os.path.exists(json_file):
        return None
    
    task_data = json.load(open(json_file))
    return task_data.get('notify', {})

def main():
    parser = argparse.ArgumentParser(description='任务管理器')
    parser.add_argument('action', choices=['init', 'update', 'status', 'list', 'record', 'check', 'notify'])
    parser.add_argument('--topic', type=str)
    parser.add_argument('--task-id', type=str)
    parser.add_argument('--step', type=str)
    parser.add_argument('--data', type=str)
    parser.add_argument('--status', type=str, default='completed')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--media-id', type=str)
    parser.add_argument('--platform', type=str)
    parser.add_argument('--chat-id', type=str)
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_task(args.topic or "今日热点", args.platform, args.chat_id)
    
    elif args.action == 'update':
        if not args.task_id or not args.step:
            print("✗ 需要 --task-id 和 --step")
            sys.exit(1)
        data = json.loads(args.data) if args.data else {}
        update_step(args.task_id, args.step, data, args.status)
    
    elif args.action == 'status':
        if not args.task_id:
            print("✗ 需要 --task-id")
            sys.exit(1)
        get_task_status(args.task_id)
    
    elif args.action == 'list':
        list_tasks(args.days)
    
    elif args.action == 'record':
        if not args.topic or not args.media_id:
            print("✗ 需要 --topic 和 --media-id")
            sys.exit(1)
        record_published_topic(args.topic, args.media_id)
    
    elif args.action == 'check':
        if not args.topic:
            print("✗ 需要 --topic")
            sys.exit(1)
        is_dup = check_duplicate_topic(args.topic)
        if is_dup:
            print("⚠️ 主题已发布（30 天内）：" + args.topic)
            sys.exit(1)
        else:
            print("✓ 主题未发布：" + args.topic)
    
    elif args.action == 'notify':
        if not args.task_id:
            print("✗ 需要 --task-id")
            sys.exit(1)
        notify = get_notify_info(args.task_id)
        if notify:
            print("推送信息:")
            print("  平台：" + notify.get('platform', 'unknown'))
            print("  会话 ID: " + notify.get('chat_id', 'N/A'))
            print("  线程 ID: " + notify.get('thread_id', 'N/A'))
        else:
            print("✗ 未找到推送信息")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
