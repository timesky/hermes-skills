#!/usr/bin/env python3
"""
MCN 完整工作流执行脚本

基于 task.md 统一管理，避免步骤脱钩

用法:
    python scripts/run-workflow.py init                    # 初始化任务
    python scripts/run-workflow.py research                # 执行调研
    python scripts/run-workflow.py topic-select            # 选题分析
    python scripts/run-workflow.py content --topic "主题"  # 生成内容
    python scripts/run-workflow.py publish                 # 发布草稿
"""

import sys
import os
import json
import subprocess
from datetime import datetime

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
TASKS_DIR = f"{KB_ROOT}/tmp/tasks"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

def run_command(cmd: str) -> bool:
    """执行命令"""
    print(f"\n执行：{cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ 错误：{result.stderr[:200]}")
        return False
    print(result.stdout[:500])
    return True

def get_latest_task():
    """获取最新的任务"""
    if not os.path.exists(TASKS_DIR):
        return None
    
    tasks = []
    for f in os.listdir(TASKS_DIR):
        if f.endswith('_task.json'):
            filepath = os.path.join(TASKS_DIR, f)
            task_data = json.load(open(filepath))
            tasks.append((task_data['created'], task_data['task_id']))
    
    if tasks:
        tasks.sort(reverse=True)
        return tasks[0][1]
    return None

def init_workflow():
    """初始化工作流"""
    cmd = f"python {SCRIPTS_DIR}/task_manager.py init --topic 'MCN 工作流 {datetime.now().strftime('%Y-%m-%d')}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # 提取 task_id
    for line in result.stdout.split('\n'):
        if '任务 ID:' in line:
            task_id = line.split(':')[1].strip()
            return task_id
    return None

def run_research(task_id: str):
    """执行调研"""
    date = datetime.now().strftime("%Y-%m-%d")
    cmd = f"python {SCRIPTS_DIR}/run-hotspot-research.py --date {date} --task-id {task_id}"
    return run_command(cmd)

def run_topic_selection(task_id: str):
    """执行选题分析"""
    date = datetime.now().strftime("%Y-%m-%d")
    cmd = f"python {SCRIPTS_DIR}/run-topic-analysis.py --date {date}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # 更新 task.md
    task_json = f"{TASKS_DIR}/{task_id}_task.json"
    if os.path.exists(task_json):
        task_data = json.load(open(task_json))
        task_data['steps']['topic_selection'] = {
            'status': 'completed',
            'data': {'date': date, 'report': f"{KB_ROOT}/tmp/topic/{date}/recommend.md"},
            'updated': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        with open(task_json, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)
    
    return True

def run_feishu_notify(task_id: str):
    """发送飞书通知"""
    date = datetime.now().strftime("%Y-%m-%d")
    cmd = f"python {SCRIPTS_DIR}/push-to-feishu.py --topic-report {date}"
    return run_command(cmd)

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python scripts/run-workflow.py init          # 初始化任务")
        print("  python scripts/run-workflow.py research      # 执行调研")
        print("  python scripts/run-workflow.py topic-select  # 选题分析")
        print("  python scripts/run-workflow.py content       # 生成内容")
        print("  python scripts/run-workflow.py publish       # 发布草稿")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'init':
        task_id = init_workflow()
        print(f"\n✓ 任务已初始化：{task_id}")
        print(f"下一步：python scripts/run-workflow.py research")
    
    elif action == 'research':
        task_id = get_latest_task()
        if not task_id:
            print("✗ 未找到任务，请先初始化：python scripts/run-workflow.py init")
            sys.exit(1)
        
        print(f"使用任务：{task_id}")
        if run_research(task_id):
            print(f"\n✓ 调研完成")
            print(f"下一步：python scripts/run-workflow.py topic-select")
    
    elif action == 'topic-select':
        task_id = get_latest_task()
        if not task_id:
            print("✗ 未找到任务")
            sys.exit(1)
        
        if run_topic_selection(task_id):
            print(f"\n✓ 选题分析完成")
            if run_feishu_notify(task_id):
                print(f"\n✓ 飞书通知已发送")
                print(f"\n等待用户确认主题...")
                print(f"确认后执行：python scripts/run-workflow.py content --topic '主题名'")
    
    elif action == 'content':
        # TODO: 实现内容生成
        print("内容生成待实现")
    
    elif action == 'publish':
        # TODO: 实现发布
        print("发布待实现")
    
    else:
        print(f"✗ 未知操作：{action}")
        sys.exit(1)

if __name__ == '__main__':
    main()
