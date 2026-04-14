# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
配图生成脚本 - 优化版本

关键改进：
1. webHook 使用假地址（而非 -1）
2. task_id 持久化到文件，避免重试丢失
3. 轮询频率 5秒，最大等待 5分钟
4. 超时放弃不重试，积分不浪费
5. failed 时换 prompt，不重复相同 prompt

用法:
    python generate-images.py --topic "编程学习" --count 4 --date 2026-04-14

输出:
    mcn/images/{date}/cover.png, img_1.png, img_2.png, ...
"""

import sys
import os
import json
import time
import argparse
import subprocess

# 使用 requests 库（更稳定）
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
API_BASE = "https://grsai.dakka.com.cn"
API_KEY = os.environ.get('GRSAI_API_KEY', 'sk-0c6f0263a0d24861bf954f5a7154e369')
MODEL = "nano-banana-fast"

# 轮询参数（关键改进）
POLL_INTERVAL = 5  # 5秒间隔
MAX_POLL_COUNT = 60  # 60次 = 5分钟
MAX_TIMEOUT = 300  # 5分钟最大等待

# 假地址（关键：不能是 -1 或空）
FAKE_WEBHOOK = "http://192.168.1.1"

# 知识库路径
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"


class ImageGenerator:
    """图片生成器，支持任务持久化"""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.tasks_file = os.path.join(output_dir, "tasks.json")
        self.tasks = self._load_tasks()
        
    def _load_tasks(self):
        """加载未完成的任务"""
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_tasks(self):
        """保存任务状态"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)
    
    def _get_task_key(self, name, prompt):
        """生成任务唯一键"""
        return f"{name}:{prompt[:30]}"
    
    def submit_task(self, name, prompt):
        """提交任务，返回 task_id"""
        
        # 检查是否已有相同任务
        task_key = self._get_task_key(name, prompt)
        if task_key in self.tasks:
            existing = self.tasks[task_key]
            if existing.get('status') == 'running':
                print(f"  发现已有任务: {existing['task_id']}")
                return existing['task_id']
            elif existing.get('status') == 'succeeded':
                print(f"  任务已完成，跳过提交")
                return existing['task_id']
        
        url = API_BASE + "/v1/draw/nano-banana"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY
        }
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "webHook": FAKE_WEBHOOK,  # 关键：假地址
            "shutProgress": False
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0 and result.get('data'):
                task_id = result['data']['id']
                # 保存任务
                self.tasks[task_key] = {
                    'task_id': task_id,
                    'name': name,
                    'prompt': prompt,
                    'status': 'running',
                    'submit_time': time.time()
                }
                self._save_tasks()
                return task_id
            else:
                print(f"  提交失败: {result}")
                return None
        except Exception as e:
            print(f"  提交错误: {e}")
            return None
    
    def poll_result(self, task_id, name, prompt):
        """轮询结果，最多5分钟"""
        
        url = API_BASE + "/v1/draw/result"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY
        }
        
        start_time = time.time()
        poll_count = 0
        
        while poll_count < MAX_POLL_COUNT:
            poll_count += 1
            
            try:
                resp = requests.post(url, headers=headers, json={"id": task_id}, timeout=30)
                result = resp.json()
                
                if result.get('code') == 0 and result.get('data'):
                    data = result['data']
                    status = data.get('status')
                    progress = data.get('progress', 0)
                    
                    # 每5次显示进度
                    if poll_count % 5 == 0:
                        elapsed = int(time.time() - start_time)
                        print(f"  [{poll_count}/{MAX_POLL_COUNT}] {status} {progress}% ({elapsed}s)")
                    
                    if status == 'succeeded':
                        results = data.get('results', [])
                        if results:
                            # 更新任务状态
                            task_key = self._get_task_key(name, prompt)
                            self.tasks[task_key]['status'] = 'succeeded'
                            self.tasks[task_key]['image_url'] = results[0].get('url')
                            self._save_tasks()
                            return results[0].get('url')
                    
                    elif status == 'failed':
                        failure_reason = data.get('failure_reason', 'unknown')
                        print(f"  ❌ 失败: {failure_reason}")
                        # 更新任务状态
                        task_key = self._get_task_key(name, prompt)
                        self.tasks[task_key]['status'] = 'failed'
                        self.tasks[task_key]['failure_reason'] = failure_reason
                        self._save_tasks()
                        return None
                    
                    elif status == 'running':
                        # 继续等待
                        time.sleep(POLL_INTERVAL)
                    
                    else:
                        print(f"  未知状态: {status}")
                        time.sleep(POLL_INTERVAL)
                        
            except Exception as e:
                print(f"  轮询错误: {e}")
                time.sleep(POLL_INTERVAL)
        
        # 超时处理：放弃不重试
        elapsed = int(time.time() - start_time)
        print(f"  ⏱️ 超时 ({elapsed}s)，放弃此任务")
        task_key = self._get_task_key(name, prompt)
        self.tasks[task_key]['status'] = 'timeout'
        self._save_tasks()
        return None
    
    def download_image(self, url, output_path):
        """下载图片"""
        try:
            resp = requests.get(url, timeout=60)
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            return os.path.getsize(output_path)
        except Exception as e:
            print(f"  下载错误: {e}")
            return 0
    
    def resize_cover(self, input_path, output_path, width=900, height=500):
        """调整封面图尺寸"""
        try:
            subprocess.run([
                'sips', '-z', str(height), str(width),
                input_path, '--out', output_path
            ], capture_output=True)
            return True
        except Exception as e:
            print(f"  调整尺寸错误: {e}")
            return False
    
    def generate_image(self, name, prompt, is_cover=False):
        """生成单张图片的完整流程"""
        
        output_path = os.path.join(self.output_dir, f"{name}.png")
        
        # 检查是否已存在
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"[{name}] 已存在，跳过")
            return True
        
        print(f"[{name}] 提交任务...")
        print(f"  Prompt: {prompt[:50]}...")
        
        task_id = self.submit_task(name, prompt)
        if not task_id:
            print(f"  ❌ 提交失败")
            return False
        
        print(f"  Task ID: {task_id}")
        
        # 轮询结果
        image_url = self.poll_result(task_id, name, prompt)
        if not image_url:
            return False
        
        print(f"  URL: {image_url[:50]}...")
        
        # 下载
        temp_path = os.path.join(self.output_dir, f"{name}_temp.png")
        size = self.download_image(image_url, temp_path)
        
        if size == 0:
            print(f"  ❌ 下载失败")
            return False
        
        # 封面图调整尺寸
        if is_cover:
            self.resize_cover(temp_path, output_path, 900, 500)
            os.remove(temp_path)
        else:
            os.rename(temp_path, output_path)
        
        final_size = os.path.getsize(output_path)
        print(f"  ✅ 完成 ({final_size/1024:.1f} KB)")
        return True


def generate_prompt(topic, image_type, variant=0):
    """生成 prompt，支持变体"""
    
    base_prompts = {
        "cover": [
            f"{topic} concept art, professional digital illustration, modern tech style, blue gradient, high quality",
            f"{topic} visual design, futuristic concept, clean composition, professional artwork",
        ],
        "content": [
            f"{topic} illustration, modern minimalist design, tech atmosphere, clean style",
            f"{topic} diagram, professional infographic style, digital art, modern design",
            f"{topic} scene, technology theme, warm lighting, professional quality",
        ]
    }
    
    prompts = base_prompts.get(image_type, base_prompts["content"])
    
    # 如果之前的 prompt 失败，使用变体
    if variant < len(prompts):
        return prompts[variant]
    else:
        # 添加随机元素避免完全相同
        return prompts[0] + f", variant {variant}"


def main():
    parser = argparse.ArgumentParser(description='配图生成（优化版）')
    parser.add_argument('--topic', type=str, required=True, help='文章主题')
    parser.add_argument('--count', type=int, default=4, help='图片数量')
    parser.add_argument('--date', type=str, required=True, help='日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = os.path.join(MCN_ROOT, "images", args.date)
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("配图生成（优化版）")
    print("=" * 60)
    print(f"主题: {args.topic}")
    print(f"数量: {args.count}")
    print(f"API: {API_BASE}")
    print(f"输出: {output_dir}")
    print(f"webHook: {FAKE_WEBHOOK}")
    print(f"轮询: {POLL_INTERVAL}s × {MAX_POLL_COUNT} = {MAX_TIMEOUT}s")
    print()
    
    generator = ImageGenerator(output_dir)
    
    # 图片列表
    images = [
        {"name": "cover", "type": "cover", "variant": 0},
    ]
    for i in range(args.count - 1):
        images.append({"name": f"img_{i+1}", "type": "content", "variant": i % 3})
    
    success_count = 0
    failed_images = []
    
    for img in images:
        prompt = generate_prompt(args.topic, img["type"], img["variant"])
        is_cover = img["type"] == "cover"
        
        # 最多尝试2个变体
        for attempt in range(2):
            if attempt > 0:
                # 失败后换 prompt
                prompt = generate_prompt(args.topic, img["type"], img["variant"] + attempt)
                print(f"[{img['name']}] 换 prompt 重试 (变体 {attempt})...")
            
            success = generator.generate_image(img["name"], prompt, is_cover)
            if success:
                success_count += 1
                break
            elif attempt == 0:
                continue  # 尝试下一个变体
            else:
                failed_images.append(img["name"])
    
    # 清理任务文件（全部成功后）
    if success_count >= args.count - 1:
        tasks_file = os.path.join(output_dir, "tasks.json")
        if os.path.exists(tasks_file):
            os.remove(tasks_file)
    
    print()
    print("=" * 60)
    print(f"完成: {success_count}/{args.count}")
    if failed_images:
        print(f"失败: {failed_images}")
    print("=" * 60)
    
    # 列出生成的文件
    print("\n生成的文件:")
    for f in os.listdir(output_dir):
        if f.endswith('.png') and not f.endswith('_temp.png'):
            path = os.path.join(output_dir, f)
            print(f"  {f} ({os.path.getsize(path)/1024:.1f} KB)")
    
    sys.exit(0 if success_count >= 3 else 1)


if __name__ == '__main__':
    main()