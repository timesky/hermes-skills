# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
配图生成脚本 - 并发版本

关键设计：
1. 创建接口拿到 task_id 就不重试（绝对禁止）
2. result 接口可以轮询
3. 并发提交所有任务 → 并发等待结果 → 并发下载
4. 超时记录 task_id 供找回，不消耗积分重试

用法:
    python generate-images.py --topic "编程学习" --count 4 --date 2026-04-14
"""

import sys
import os
import json
import time
import argparse
import concurrent.futures
from datetime import datetime

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests")
    sys.exit(1)

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

# 配置常量
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")

def load_config():
    import yaml
    with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

_config = load_config()
_image_config = _config.get('image_generation', {})
_grsai_config = _image_config.get('providers', {}).get('grsai', {})

API_BASE = _grsai_config.get('api_url', 'https://grsai.dakka.com.cn/v1/draw/nano-banana').replace('/v1/draw/nano-banana', '')
API_KEY = _grsai_config.get('api_key', '')
MODEL_NAME = _grsai_config.get('models', {}).get(_grsai_config.get('default_model', 'fast'), 'nano-banana-fast')

# 轮询参数
POLL_INTERVAL = 5  # 5秒间隔
MAX_POLL_COUNT = 60  # 60次 = 5分钟

FAKE_WEBHOOK = "http://192.168.1.1"

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"


def submit_single_image(name, prompt):
    """提交单个图片任务，返回 task_id 或 None"""
    
    url = API_BASE + "/v1/draw/nano-banana"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "webHook": FAKE_WEBHOOK,
        "shutProgress": False
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0 and result.get('data'):
            task_id = result['data']['id']
            print(f"  ✅ [{name}] 提交成功: {task_id}")
            return {'name': name, 'task_id': task_id, 'prompt': prompt, 'status': 'submitted'}
        else:
            print(f"  ❌ [{name}] 提交失败: {result.get('msg', result)}")
            # 创建失败不重试！记录失败
            return {'name': name, 'task_id': None, 'prompt': prompt, 'status': 'submit_failed', 'error': result.get('msg')}
    except Exception as e:
        print(f"  ❌ [{name}] 提交异常: {e}")
        return {'name': name, 'task_id': None, 'prompt': prompt, 'status': 'submit_error', 'error': str(e)}


def poll_single_result(task_info, output_dir):
    """轮询单个任务结果，返回成功则下载"""
    
    name = task_info['name']
    task_id = task_info['task_id']
    
    if not task_id:
        return task_info  # 没有task_id，直接返回
    
    url = API_BASE + "/v1/draw/result"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }
    
    poll_count = 0
    
    while poll_count < MAX_POLL_COUNT:
        poll_count += 1
        
        try:
            resp = requests.post(url, headers=headers, json={"id": task_id}, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0 and result.get('data'):
                data = result['data']
                status = data.get('status')
                
                if poll_count % 10 == 0:  # 每50秒报告一次
                    print(f"  [{name}] 状态: {status} ({poll_count * POLL_INTERVAL}s)")
                
                if status == 'succeeded':
                    results = data.get('results', [])
                    if results:
                        image_url = results[0].get('url')
                        # 下载图片
                        download_result = download_image(name, image_url, output_dir, name == 'cover')
                        if download_result:
                            task_info['status'] = 'completed'
                            task_info['image_url'] = image_url
                        else:
                            task_info['status'] = 'download_failed'
                        return task_info
                
                elif status == 'failed':
                    task_info['status'] = 'failed'
                    task_info['error'] = data.get('failure_reason', 'unknown')
                    return task_info
                
                elif status == 'running':
                    time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            print(f"  [{name}] 轮询异常: {e}")
            time.sleep(POLL_INTERVAL)
    
    # 超时 - 记录 task_id 供找回，不重试
    task_info['status'] = 'timeout'
    task_info['error'] = f'超时 {MAX_POLL_COUNT * POLL_INTERVAL}s'
    print(f"  ⏰ [{name}] 超时，task_id={task_id} 已记录")
    return task_info


def download_image(name, url, output_dir, is_cover=False):
    """下载图片"""
    
    try:
        resp = requests.get(url, timeout=60, stream=True)
        if resp.status_code != 200:
            print(f"  ❌ [{name}] 下载失败: HTTP {resp.status_code}")
            return False
        
        filename = f"{name}.png"
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 封面图调整尺寸
        if is_cover:
            resize_cover(output_path, 900, 500)
        
        size_kb = os.path.getsize(output_path) / 1024
        print(f"  ✅ [{name}] 下载完成: {filename} ({size_kb:.1f} KB)")
        return True
    
    except Exception as e:
        print(f"  ❌ [{name}] 下载异常: {e}")
        return False


def resize_cover(path, target_w=900, target_h=500):
    """调整封面图尺寸"""
    try:
        from PIL import Image
        img = Image.open(path)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(path, 'PNG')
    except ImportError:
        print("  ⚠️ PIL 未安装，跳过尺寸调整")
    except Exception as e:
        print(f"  ⚠️ 尺寸调整失败: {e}")


def generate_prompts(topic, count):
    """生成所有图片的 prompts"""
    
    prompts = []
    
    # 封面图
    cover_prompts = [
        f"{topic} concept art, professional digital illustration, modern tech style, blue gradient, high quality",
        f"{topic} visual design, futuristic concept, clean composition, professional artwork",
    ]
    prompts.append({'name': 'cover', 'prompt': cover_prompts[0]})
    
    # 内容图
    content_prompts = [
        f"{topic} illustration, modern minimalist design, tech atmosphere, clean style",
        f"{topic} diagram, professional infographic style, digital art, modern design",
        f"{topic} scene, technology theme, warm lighting, professional quality",
    ]
    
    for i in range(count - 1):
        idx = i % len(content_prompts)
        prompts.append({'name': f'img_{i+1}', 'prompt': content_prompts[idx]})
    
    return prompts


def main():
    parser = argparse.ArgumentParser(description='配图生成（并发版）')
    parser.add_argument('--topic', type=str, required=True, help='文章主题')
    parser.add_argument('--count', type=int, default=4, help='图片数量')
    parser.add_argument('--date', type=str, required=True, help='日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = os.path.join(MCN_ROOT, "images", args.date)
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("配图生成（并发版）")
    print("=" * 60)
    print(f"主题: {args.topic}")
    print(f"数量: {args.count}")
    print(f"模型: {MODEL_NAME}")
    print(f"输出: {output_dir}")
    print(f"模式: 并发提交 → 并发等待")
    print()
    
    # Step 1: 生成所有 prompts
    all_prompts = generate_prompts(args.topic, args.count)
    
    # Step 2: 并发提交所有任务
    print("Step 1: 并发提交任务...")
    submitted_tasks = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as executor:
        futures = [executor.submit(submit_single_image, p['name'], p['prompt']) for p in all_prompts]
        for future in concurrent.futures.as_completed(futures):
            submitted_tasks.append(future.result())
    
    # 保存任务状态
    tasks_file = os.path.join(output_dir, "tasks.json")
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(submitted_tasks, f, indent=2, ensure_ascii=False)
    print(f"  任务状态已保存: {tasks_file}")
    print()
    
    # Step 3: 并发轮询结果
    print("Step 2: 并发等待结果...")
    final_tasks = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as executor:
        futures = [executor.submit(poll_single_result, task, output_dir) for task in submitted_tasks]
        for future in concurrent.futures.as_completed(futures):
            final_tasks.append(future.result())
    
    # 更新任务状态
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(final_tasks, f, indent=2, ensure_ascii=False)
    
    # 统计结果
    print()
    print("=" * 60)
    completed = [t for t in final_tasks if t['status'] == 'completed']
    failed = [t for t in final_tasks if t['status'] != 'completed']
    
    print(f"完成: {len(completed)}/{args.count}")
    if failed:
        print(f"失败/超时: {[f['name'] for f in failed]}")
        print(f"  可用 task_id 找回: {[f['task_id'] for f in failed if f['task_id']]}")
    
    print("=" * 60)
    
    # 列出生成的文件
    print("\n生成的文件:")
    for t in completed:
        filename = f"{t['name']}.png"
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"  {filename} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()