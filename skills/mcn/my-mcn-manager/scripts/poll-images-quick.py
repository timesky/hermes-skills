# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
轮询待处理配图任务

检查 tasks.json 中的 submitted 任务，轮询结果，下载图片
"""

import os
import json
import time
import requests

API_BASE = "https://grsai.dakka.com.cn"
API_KEY = "sk-0c6f0263a0d24861bf954f5a7154e369"

OUTPUT_DIR = "/Users/timesky/backup/知识库-Obsidian/mcn/images/2026-04-15"
TASKS_FILE = os.path.join(OUTPUT_DIR, "tasks.json")

def poll_tasks():
    """轮询所有 submitted 任务"""
    
    if not os.path.exists(TASKS_FILE):
        print("无待处理任务")
        return
    
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    headers = {"Authorization": "Bearer " + API_KEY}
    
    completed = 0
    
    for task in tasks:
        if task['status'] != 'submitted':
            continue
        
        name = task['name']
        task_id = task['task_id']
        
        if not task_id:
            continue
        
        try:
            resp = requests.post(f"{API_BASE}/v1/draw/result", headers=headers, json={"id": task_id}, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                status = data.get('status')
                progress = data.get('progress', 0)
                
                print(f"[{name}] {status} ({progress}%)")
                
                if status == 'succeeded':
                    results = data.get('results', [])
                    if results:
                        url = results[0].get('url')
                        if download_image(name, url):
                            task['status'] = 'completed'
                            completed += 1
                
                elif status == 'failed':
                    task['status'] = 'failed'
                    task['error'] = data.get('failure_reason', 'unknown')
        
        except Exception as e:
            print(f"[{name}] 查询异常: {e}")
    
    # 更新任务文件
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    
    print(f"完成: {completed}")

def download_image(name, url):
    """下载图片"""
    
    try:
        resp = requests.get(url, timeout=60, stream=True)
        if resp.status_code != 200:
            print(f"  [{name}] 下载失败")
            return False
        
        filename = f"{name}.png"
        path = os.path.join(OUTPUT_DIR, filename)
        
        with open(path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 封面图调整尺寸
        if name == 'cover':
            try:
                from PIL import Image
                img = Image.open(path)
                img = img.resize((900, 500), Image.LANCZOS)
                img.save(path, 'PNG')
            except:
                pass
        
        size_kb = os.path.getsize(path) / 1024
        print(f"  [{name}] 下载完成 ({size_kb:.1f} KB)")
        return True
    
    except Exception as e:
        print(f"  [{name}] 下载异常: {e}")
        return False

if __name__ == "__main__":
    poll_tasks()