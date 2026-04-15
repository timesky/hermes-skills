# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
配图任务轮询脚本 - 异步处理长时间任务

功能：
1. 扫描 pending 状态的配图任务
2. 斐波那契间隔轮询（从3秒开始，最多5次）
3. 完成后下载图片，更新状态
4. 检查排版条件：≥3张成功（封面+中间+尾图）
5. 不满足则自动补图继续循环

用法：
    python poll-image-tasks.py [--date YYYY-MM-DD]
    
Cron 配置：
    */5 * * * * cd ~/.hermes/skills/mcn/my-mcn-manager && \
        eval "$(pyenv init -)" && python scripts/poll-image-tasks.py
"""

import sys
import os
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

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

# 配置
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")

def load_config():
    """加载配置文件"""
    try:
        import yaml
        with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return {}

_config = load_config()
_image_config = _config.get('image_generation', {})
_grsai_config = _image_config.get('providers', {}).get('grsai', {})

API_BASE = _grsai_config.get('api_url', 'https://grsai.dakka.com.cn/v1/draw/nano-banana')
API_BASE = API_BASE.replace('/v1/draw/nano-banana', '')
API_KEY = _grsai_config.get('api_key', '')

# 知识库路径
KB_ROOT = _config.get('kb_paths', {}).get('root', '/Users/timesky/backup/知识库-Obsidian')
MCN_ROOT = _config.get('kb_paths', {}).get('mcn_root', KB_ROOT + '/mcn')


def fibonacci_intervals(max_wait: int = 2000) -> list:
    """斐波那契等待间隔（秒）
    
    从3秒开始，最多5次：
    - 第1次：3秒
    - 第2次：5秒
    - 第3次：8秒
    - 第4次：13秒
    - 第5次：21秒
    
    之后固定每120秒检查一次，直到2000秒超时
    """
    fib_intervals = [3, 5, 8, 13, 21]  # 累计50秒
    
    # 填充固定120秒间隔
    total = sum(fib_intervals)
    while total + 120 <= max_wait:
        fib_intervals.append(120)
        total += 120
    
    return fib_intervals


def check_task_status(task_id: str) -> dict:
    """检查任务状态"""
    import requests
    
    url = API_BASE + "/v1/draw/result"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }
    
    try:
        resp = requests.post(url, headers=headers, json={"id": task_id}, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0 and result.get('data'):
            data = result['data']
            status = data.get('status', 'unknown')
            
            if status == 'succeeded':
                results = data.get('results', [])
                if results:
                    return {
                        'status': 'succeeded',
                        'url': results[0].get('url'),
                        'progress': 100
                    }
            
            elif status == 'failed':
                return {
                    'status': 'failed',
                    'reason': data.get('failure_reason', 'unknown')
                }
            
            elif status == 'running':
                return {
                    'status': 'running',
                    'progress': data.get('progress', 0)
                }
        
        return {'status': 'unknown', 'reason': str(result)}
        
    except Exception as e:
        return {'status': 'error', 'reason': str(e)}


def download_image(url: str, output_path: str) -> bool:
    """下载图片"""
    import requests
    
    try:
        resp = requests.get(url, timeout=60)
        with open(output_path, 'wb') as f:
            f.write(resp.content)
        
        size = os.path.getsize(output_path)
        print(f"  ✅ 下载完成: {output_path} ({size} bytes)")
        return True
        
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return False


def check_layout_ready(tasks: dict) -> tuple:
    """检查是否满足排版条件
    
    条件：
    1. 所有任务状态是 succeeded 或 failed（无 pending）
    2. 成功图片数 >= 3
    3. 必须包含：封面图(cover)、至少1张中间图(img_x)、尾图(end)
    
    返回：(是否满足, 缺少原因)
    """
    succeeded = {k: v for k, v in tasks.items() 
                 if v.get('status') == 'succeeded'}
    
    # 检查是否还有 pending 任务
    pending = [k for k, v in tasks.items() if v.get('status') == 'pending']
    if pending:
        return False, f"仍有 {len(pending)} 张待完成"
    
    # 检查数量
    if len(succeeded) < 3:
        return False, f"图片不足：{len(succeeded)}/3"
    
    # 检查类型
    has_cover = any('cover' in k for k in succeeded.keys())
    has_middle = any(k.startswith('img_') for k in succeeded.keys())
    has_end = any('end' in k for k in succeeded.keys())
    
    missing = []
    if not has_cover:
        missing.append("封面图")
    if not has_middle:
        missing.append("中间图")
    if not has_end:
        missing.append("尾图")
    
    if missing:
        return False, f"缺少：{', '.join(missing)}"
    
    return True, "满足条件"


def supplement_images(tasks: dict, images_dir: str, article_info: dict) -> int:
    """补足缺失图片
    
    流程：
    1. 分析缺失类型
    2. 重新生成缺失类型的图片
    3. 提交新任务 → 继续等待循环
    
    返回：补图数量
    """
    succeeded = [k for k, v in tasks.items() if v.get('status') == 'succeeded']
    
    # 检查缺失类型
    need_cover = not any('cover' in k for k in succeeded)
    need_end = not any('end' in k for k in succeeded)
    middle_count = sum(1 for k in succeeded if k.startswith('img_'))
    
    # 计算需要补充的中间图数量（最少1张）
    need_middle = max(0, 1 - middle_count)
    
    topic = article_info.get('topic', '默认主题')
    date = article_info.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    print(f"\n[补图] 分析缺失：封面={need_cover}, 中间={need_middle}, 尾图={need_end}")
    
    # 生成脚本调用
    gen_script = os.path.join(os.path.dirname(__file__), 'generate-images.py')
    
    supplement_count = 0
    
    if need_cover:
        print(f"  补充封面图...")
        # 调用生成脚本提交封面任务
        try:
            subprocess.run([
                'python', gen_script,
                '--topic', topic,
                '--type', 'cover',
                '--date', date,
                '--supplement'
            ], check=True)
            supplement_count += 1
        except Exception as e:
            print(f"    ❌ 补图失败: {e}")
    
    for i in range(need_middle):
        print(f"  补充中间图 {i+1}...")
        try:
            subprocess.run([
                'python', gen_script,
                '--topic', topic,
                '--type', 'middle',
                '--index', str(middle_count + i + 1),
                '--date', date,
                '--supplement'
            ], check=True)
            supplement_count += 1
        except Exception as e:
            print(f"    ❌ 补图失败: {e}")
    
    if need_end:
        print(f"  补充尾图...")
        try:
            subprocess.run([
                'python', gen_script,
                '--topic', topic,
                '--type', 'end',
                '--date', date,
                '--supplement'
            ], check=True)
            supplement_count += 1
        except Exception as e:
            print(f"    ❌ 补图失败: {e}")
    
    return supplement_count


def trigger_layout(article_info: dict):
    """触发排版流程"""
    
    date = article_info.get('date')
    topic = article_info.get('topic')
    
    print(f"\n[自动排版] 开始处理...")
    
    layout_script = os.path.join(os.path.dirname(__file__), 'layout-article.py')
    
    if os.path.exists(layout_script):
        try:
            subprocess.run([
                'python', layout_script,
                '--date', date,
                '--topic', topic
            ], check=True)
            print(f"✅ 排版完成")
        except Exception as e:
            print(f"❌ 排版失败: {e}")
    else:
        print(f"⚠️ 排版脚本不存在: {layout_script}")


def send_feishu_notification(message: str):
    """发送飞书通知"""
    
    push_script = os.path.join(os.path.dirname(__file__), 'push-to-feishu.py')
    
    if os.path.exists(push_script):
        try:
            subprocess.run([
                'python', push_script,
                '--message', message
            ], check=True)
        except Exception as e:
            print(f"飞书通知失败: {e}")


def poll_pending_tasks(date: str = None):
    """轮询 pending 状态的任务"""
    
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    images_dir = os.path.join(MCN_ROOT, 'content', date, 'images')
    tasks_file = os.path.join(images_dir, 'tasks.json')
    
    if not os.path.exists(tasks_file):
        print(f"没有任务文件: {tasks_file}")
        return
    
    with open(tasks_file, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)
    
    tasks = tasks_data.get('tasks', {})
    pending_tasks = {k: v for k, v in tasks.items() if v.get('status') == 'pending'}
    
    print(f"\n=== 配图任务轮询 ({date}) ===")
    print(f"总任务: {len(tasks)}, 待处理: {len(pending_tasks)}")
    
    # 如果没有 pending，检查是否满足排版条件
    if not pending_tasks:
        ready, reason = check_layout_ready(tasks)
        
        if ready:
            if not tasks_data.get('layout_completed'):
                print(f"✅ {reason}，触发排版...")
                trigger_layout(tasks_data.get('article_info', {}))
                tasks_data['layout_completed'] = True
                save_tasks(tasks_file, tasks_data)
                
                # 飞书通知
                succeeded_count = len([t for t in tasks.values() 
                                       if t.get('status') == 'succeeded'])
                message = f"✅ 配图完成！{succeeded_count}张图片，排版已完成\n下一步：回复「发布」"
                send_feishu_notification(message)
            else:
                print("排版已完成")
        else:
            print(f"⚠️ {reason}")
            
            # 检查是否需要补图
            if "缺少" in reason or "不足" in reason:
                supplement_count = supplement_images(tasks, images_dir, 
                                                     tasks_data.get('article_info', {}))
                if supplement_count > 0:
                    print(f"已补充 {supplement_count} 张图片，继续等待...")
                    # 重新加载任务（新提交的）
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        tasks_data = json.load(f)
                    save_tasks(tasks_file, tasks_data)
        return
    
    # 有 pending 任务，继续轮询
    intervals = fibonacci_intervals()
    now = time.time()
    
    completed_count = 0
    failed_count = 0
    
    for name, task in pending_tasks.items():
        task_id = task.get('task_id')
        submit_time = task.get('submit_time', now)
        
        if isinstance(submit_time, str):
            submit_ts = datetime.fromisoformat(submit_time).timestamp()
        else:
            submit_ts = submit_time
        
        elapsed = now - submit_ts
        poll_count = task.get('poll_count', 0)
        
        # 超时检查（2000秒）
        if elapsed > 2000:
            print(f"  ⏱️ {name}: 超时 ({int(elapsed)}s)")
            task['status'] = 'timeout'
            failed_count += 1
            continue
        
        # 斐波那契间隔（最多5次，之后固定120秒）
        if poll_count < len(intervals):
            next_interval = intervals[poll_count]
        else:
            next_interval = 120
        
        last_poll = task.get('last_poll_time', submit_ts)
        if isinstance(last_poll, str):
            last_poll = datetime.fromisoformat(last_poll).timestamp()
        
        if now - last_poll < next_interval:
            wait_time = int(next_interval - (now - last_poll))
            print(f"  ⏳ {name}: 等待中（下次检查 {wait_time}s 后）")
            continue
        
        # 执行检查
        print(f"\n  检查 {name}...")
        print(f"    Task ID: {task_id[:20]}...")
        print(f"    已等待: {int(elapsed)}s, 轮询: {poll_count + 1}次")
        
        result = check_task_status(task_id)
        
        if result['status'] == 'succeeded':
            url = result.get('url')
            if url:
                output_path = os.path.join(images_dir, f"{name}.png")
                if download_image(url, output_path):
                    task['status'] = 'succeeded'
                    task['image_url'] = url
                    task['local_path'] = output_path
                    completed_count += 1
        
        elif result['status'] == 'failed':
            print(f"    ❌ 失败: {result.get('reason')}")
            task['status'] = 'failed'
            task['failure_reason'] = result.get('reason')
            failed_count += 1
        
        elif result['status'] == 'running':
            print(f"    🔄 运行中 ({result.get('progress', 0)}%)")
            task['poll_count'] = poll_count + 1
            task['last_poll_time'] = datetime.now().isoformat()
        
        else:
            print(f"    ⚠️ 状态: {result.get('status')}")
    
    # 保存更新
    tasks_data['tasks'] = tasks
    save_tasks(tasks_file, tasks_data)
    
    print(f"\n=== 轮询结果 ===")
    print(f"完成: {completed_count}, 失败/超时: {failed_count}")
    
    # 检查是否全部完成
    pending_remaining = len([t for t in tasks.values() 
                             if t.get('status') == 'pending'])
    
    if pending_remaining == 0:
        ready, reason = check_layout_ready(tasks)
        
        if ready:
            print(f"✅ 满足排版条件，触发排版...")
            trigger_layout(tasks_data.get('article_info', {}))
            tasks_data['layout_completed'] = True
            save_tasks(tasks_file, tasks_data)
            
            succeeded_count = len([t for t in tasks.values() 
                                   if t.get('status') == 'succeeded'])
            message = f"✅ 配图完成！{succeeded_count}张图片，排版已完成"
            send_feishu_notification(message)
        else:
            print(f"⚠️ {reason}，尝试补图...")
            supplement_images(tasks, images_dir, tasks_data.get('article_info', {}))


def save_tasks(tasks_file: str, tasks_data: dict):
    """保存任务状态"""
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(tasks_data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='配图任务轮询')
    parser.add_argument('--date', type=str, help='日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if not API_KEY:
        print("❌ API Key 未配置")
        sys.exit(1)
    
    poll_pending_tasks(args.date)


if __name__ == '__main__':
    main()