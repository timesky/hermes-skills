# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
配图生成脚本 - 多提供商支持（豆包优先 + GrsAI备选）

关键设计：
1. 默认使用豆包（支持中文提示词，解决乱码问题）
2. GrsAI 作为备选（英文场景）
3. 默认生成 3 张图：首图 + 中间2张按段落均匀插入
4. 豆包直接返回 URL，无需轮询

用法:
    # 使用豆包（默认，支持中文）
    python generate-images.py --topic "编程学习" --date 2026-04-19
    
    # 指定 GrsAI（英文场景）
    python generate-images.py --topic "AI trends" --date 2026-04-19 --provider grsai
    
    # 自定义数量
    python generate-images.py --topic "选题" --date 2026-04-19 --count 3
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

def load_config():
    import yaml
    with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

_config = load_config()
_image_config = _config.get('image_generation', {})

# 默认配置
DEFAULT_PROVIDER = _image_config.get('default_provider', 'doubao')
DEFAULT_COUNT = _image_config.get('image_count', 3)

# 豆包配置
_doubao_config = _image_config.get('providers', {}).get('doubao', {})
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DOUBAO_API_KEY = _doubao_config.get("api_key", "")
DOUBAO_MODEL = _doubao_config.get("model", "doubao-seedream-4-5-251128")

# GrsAI 配置
_grsai_config = _image_config.get('providers', {}).get('grsai', {})
GRSAI_API_BASE = _grsai_config.get('api_url', '').replace('/v1/draw/nano-banana', '')
GRSAI_API_KEY = _grsai_config.get("api_key", "")
GRSAI_MODEL = _grsai_config.get('models', {}).get(_grsai_config.get('default_model', 'fast'), 'nano-banana-fast')

# 轮询参数（仅 GrsAI）
POLL_INTERVAL = 5
MAX_POLL_COUNT = 60

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

def slugify(text):
    import re
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【»]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s[:50].strip('-')

def get_images_dir(date, topic):
    return f"{MCN_ROOT}/content/{date}/{slugify(topic)}/images"


# ==================== 豆包 API ====================

def doubao_generate_image(name, prompt):
    """豆包生图 - 直接返回 URL，无需轮询"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DOUBAO_API_KEY}"
    }
    
    payload = {
        "model": DOUBAO_MODEL,
        "prompt": prompt,
        "size": "2048x2048",  # 豆包要求最小 3686400 像素
        "response_format": "url",
        "stream": False,
        "watermark": False
    }
    
    try:
        print(f"  🎨 [{name}] 豆包生成: {prompt[:40]}...")
        resp = requests.post(DOUBAO_API_URL, headers=headers, json=payload, timeout=120)
        
        if resp.status_code != 200:
            print(f"  ❌ [{name}] HTTP {resp.status_code}: {resp.text[:100]}")
            return {'name': name, 'status': 'failed', 'error': resp.text[:100]}
        
        result = resp.json()
        
        if result.get('data') and isinstance(result['data'], list):
            url = result['data'][0].get('url')
            if url:
                print(f"  ✅ [{name}] 豆包成功")
                return {'name': name, 'status': 'completed', 'image_url': url}
        
        if result.get('error'):
            print(f"  ❌ [{name}] 豆包错误: {result['error']}")
            return {'name': name, 'status': 'failed', 'error': result['error']}
        
        return {'name': name, 'status': 'failed', 'error': '响应解析失败'}
        
    except Exception as e:
        print(f"  ❌ [{name}] 豆包异常: {e}")
        return {'name': name, 'status': 'failed', 'error': str(e)}


# ==================== GrsAI API ====================

def grsai_submit_task(name, prompt):
    """GrsAI 提交任务"""
    
    url = GRSAI_API_BASE + "/v1/draw/nano-banana"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRSAI_API_KEY}"
    }
    payload = {
        "model": GRSAI_MODEL,
        "prompt": prompt,
        "webHook": "http://192.168.1.1",
        "shutProgress": False
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0 and result.get('data'):
            task_id = result['data']['id']
            print(f"  ✅ [{name}] GrsAI 提交成功: {task_id}")
            return {'name': name, 'task_id': task_id, 'prompt': prompt, 'status': 'submitted'}
        else:
            print(f"  ❌ [{name}] GrsAI 提交失败: {result.get('msg', result)}")
            return {'name': name, 'status': 'failed', 'error': result.get('msg')}
    except Exception as e:
        print(f"  ❌ [{name}] GrsAI 提交异常: {e}")
        return {'name': name, 'status': 'failed', 'error': str(e)}


def grsai_poll_result(task_info, output_dir):
    """GrsAI 轮询结果"""
    
    name = task_info['name']
    task_id = task_info.get('task_id')
    
    if not task_id:
        return task_info
    
    url = GRSAI_API_BASE + "/v1/draw/result"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRSAI_API_KEY}"
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
                
                if poll_count % 10 == 0:
                    print(f"  [{name}] GrsAI 状态: {status} ({poll_count * POLL_INTERVAL}s)")
                
                if status == 'succeeded':
                    results = data.get('results', [])
                    if results:
                        image_url = results[0].get('url')
                        download_result = download_image(name, image_url, output_dir, name == 'cover')
                        task_info['status'] = 'completed' if download_result else 'download_failed'
                        task_info['image_url'] = image_url
                        return task_info
                
                elif status == 'failed':
                    task_info['status'] = 'failed'
                    task_info['error'] = data.get('failure_reason', 'unknown')
                    return task_info
                
                elif status == 'running':
                    time.sleep(POLL_INTERVAL)
        
        except Exception as e:
            print(f"  [{name}] GrsAI 轮询异常: {e}")
            time.sleep(POLL_INTERVAL)
    
    task_info['status'] = 'timeout'
    task_info['error'] = f'超时 {MAX_POLL_COUNT * POLL_INTERVAL}s'
    print(f"  ⏰ [{name}] GrsAI 超时，task_id={task_id} 已记录")
    return task_info


# ==================== 通用函数 ====================

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
        print(f"  ✅ 封面尺寸调整: {target_w}x{target_h}")
    except ImportError:
        print("  ⚠️ PIL 未安装，跳过尺寸调整")
    except Exception as e:
        print(f"  ⚠️ 尺寸调整失败: {e}")


def extract_keywords_from_paragraph(text, max_words=8):
    """从段落文本提取关键词"""
    
    text = text.replace('**', '').replace('*', '').replace('#', '')
    snippet = text[:80].strip()
    
    stop_words = ['最近', '说实话', '要知道', '不过', '这种', '其实', '我觉得', 
                  '这个', '那个', '但是', '而且', '因为', '所以', '如果', '什么',
                  '怎么', '怎样', '多少', '一些', '这些', '那些', '每个', '所有',
                  '可以', '可能', '应该', '需要', '想要', '希望能够', '来说']
    
    words = []
    for part in snippet.replace('，', ' ').replace('。', ' ').replace('、', ' ').replace('：', ' ').split():
        if len(part) >= 2 and part not in stop_words:
            words.append(part)
    
    keywords = words[:max_words]
    return keywords if keywords else ['科技', '概念']


def read_article_paragraphs(article_path):
    """读取文章并按段落分割"""
    
    if not article_path or not os.path.exists(article_path):
        return None
    
    with open(article_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
    
    paragraphs = []
    sections = content.split('\n## ')
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        
        if i == 0 and not section.startswith('#'):
            title = '引言'
            body = section.strip()
        else:
            lines = section.strip().split('\n')
            title = lines[0].replace('#', '').strip() if lines else f'段落{i}'
            body = '\n'.join(lines[1:]) if len(lines) > 1 else lines[0]
        
        keywords = extract_keywords_from_paragraph(title + ' ' + body)
        
        paragraphs.append({
            'title': title,
            'content': body[:200],
            'keywords': keywords
        })
    
    return paragraphs


def generate_prompts_from_article(topic, article_path, count=3, provider='doubao'):
    """根据文章段落生成差异化提示词
    
    3张图分配：
    - cover: 主题封面
    - img_1: 前半部分段落
    - img_2: 后半部分段落
    
    豆包用中文，GrsAI用英文
    """
    
    prompts = []
    paragraphs = read_article_paragraphs(article_path)
    
    use_chinese = provider == 'doubao'
    
    if paragraphs and len(paragraphs) >= 2:
        print(f"  ✓ 根据文章 {len(paragraphs)} 个段落生成差异化提示词")
        
        # 封面图：主题概念
        all_keywords = []
        for p in paragraphs[:3]:
            all_keywords.extend(p.get('keywords', []))
        
        if use_chinese:
            cover_prompt = f"{topic} 概念插画，科技氛围，专业设计，现代风格，高质量"
        else:
            cover_keywords = ' '.join(all_keywords[:6]) if all_keywords else topic
            cover_prompt = f"{cover_keywords} concept art, professional digital illustration, tech atmosphere, high quality"
        
        prompts.append({'name': 'cover', 'prompt': cover_prompt, 'paragraph': '封面'})
        
        # 内容图：按段落均匀分配
        # img_1: 前半部分段落（索引1到中间）
        mid_idx = len(paragraphs) // 2
        front_para = paragraphs[mid_idx] if mid_idx > 0 else paragraphs[1]
        front_keywords = ' '.join(front_para.get('keywords', [])[:5])
        
        if use_chinese:
            img1_prompt = f"{front_keywords} 现代插画，科技感，故事氛围，高质量"
        else:
            img1_prompt = f"{front_keywords} illustration, modern tech style, storytelling visual"
        
        prompts.append({'name': 'img_1', 'prompt': img1_prompt, 'paragraph': front_para.get('title', '前半段')})
        
        # img_2: 后半部分段落
        back_para = paragraphs[-1] if len(paragraphs) > 2 else paragraphs[1]
        back_keywords = ' '.join(back_para.get('keywords', [])[:5])
        
        if use_chinese:
            img2_prompt = f"{back_keywords} 场景插画，商务风格，信息图，高质量"
        else:
            img2_prompt = f"{back_keywords} scene illustration, business style, infographic"
        
        prompts.append({'name': 'img_2', 'prompt': img2_prompt, 'paragraph': back_para.get('title', '后半段')})
        
        for p in prompts:
            print(f"     [{p['name']}] 段落: {p.get('paragraph', 'N/A')}")
    
    else:
        print(f"  ⚠️ 文章段落不足，使用通用提示词")
        
        if use_chinese:
            prompts = [
                {'name': 'cover', 'prompt': f"{topic} 概念插画，科技氛围，专业设计，高质量"},
                {'name': 'img_1', 'prompt': f"{topic} 现代场景，故事感，高质量插画"},
                {'name': 'img_2', 'prompt': f"{topic} 信息图风格，数据可视化，高质量"},
            ]
        else:
            prompts = [
                {'name': 'cover', 'prompt': f"{topic} concept art, professional illustration, tech atmosphere, high quality"},
                {'name': 'img_1', 'prompt': f"{topic} scene illustration, storytelling visual, modern style"},
                {'name': 'img_2', 'prompt': f"{topic} infographic, data visualization, professional quality"},
            ]
    
    return prompts


def check_existing_images(output_dir, expected_count=3):
    """检查已存在的配图
    
    Returns:
        dict: {'exists': bool, 'files': list, 'missing': list}
    """
    expected_files = ['cover.png', 'img_1.png', 'img_2.png']
    existing = []
    missing = []
    
    for fname in expected_files[:expected_count]:
        path = os.path.join(output_dir, fname)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            existing.append(fname)
        else:
            missing.append(fname)
    
    return {
        'exists': len(existing) >= expected_count,
        'files': existing,
        'missing': missing,
        'count': len(existing)
    }


def main():
    parser = argparse.ArgumentParser(description='配图生成（豆包优先）')
    parser.add_argument('--topic', type=str, required=True, help='文章主题')
    parser.add_argument('--count', type=int, default=DEFAULT_COUNT, help='图片数量（默认3）')
    parser.add_argument('--date', type=str, required=True, help='日期 (YYYY-MM-DD)')
    parser.add_argument('--article', type=str, help='文章路径（段落差异化）')
    parser.add_argument('--provider', type=str, default=DEFAULT_PROVIDER, help='提供商 (doubao/grsai)')
    parser.add_argument('--force', action='store_true', help='强制重新生成（覆盖已有配图）')
    
    args = parser.parse_args()
    
    output_dir = get_images_dir(args.date, args.topic)
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print(f"配图生成 - {args.provider.upper()}")
    print("=" * 60)
    print(f"主题: {args.topic}")
    print(f"数量: {args.count}")
    print(f"日期: {args.date}")
    print(f"提供商: {args.provider}")
    print(f"输出: {output_dir}")
    print()
    
    # ==================== 配图保护检查 ====================
    existing_check = check_existing_images(output_dir, args.count)
    
    if existing_check['exists'] and not args.force:
        print("🔴 配图保护：已存在配图，跳过生成")
        print(f"   已有文件: {existing_check['files']}")
        print(f"   文件大小: {[f'{f}: {os.path.getsize(os.path.join(output_dir, f))/1024:.1f}KB' for f in existing_check['files']]}")
        print()
        print("   如需重新生成，请使用 --force 参数")
        print("=" * 60)
        
        # 更新 workflow.json 状态为 images_done（已有配图视为完成）
        update_workflow_json("images_done", slugify(args.topic))
        
        return True  # 返回成功（已有配图）
    
    # 查找文章
    article_path = args.article
    if not article_path:
        article_path = os.path.join(output_dir.replace('/images', ''), 'article.md')
        if not os.path.exists(article_path):
            article_path = None
    
    if article_path and os.path.exists(article_path):
        print(f"  ✓ 使用文章段落差异化: {article_path}")
    else:
        print(f"  ⚠️ 无文章路径，使用通用提示词")
    
    # 生成提示词
    all_prompts = generate_prompts_from_article(args.topic, article_path, args.count, args.provider)
    
    print()
    print("开始生成...")
    
    # 根据提供商选择生成方式
    if args.provider == 'doubao':
        # 豆包：并发生成，直接返回
        final_tasks = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as executor:
            futures = {executor.submit(doubao_generate_image, p['name'], p['prompt']): p for p in all_prompts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result['status'] == 'completed' and result.get('image_url'):
                    download_image(result['name'], result['image_url'], output_dir, result['name'] == 'cover')
                final_tasks.append(result)
    
    else:
        # GrsAI：提交 → 轮询
        submitted_tasks = []
        
        print("Step 1: 提交任务...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as executor:
            futures = [executor.submit(grsai_submit_task, p['name'], p['prompt']) for p in all_prompts]
            for future in concurrent.futures.as_completed(futures):
                submitted_tasks.append(future.result())
        
        print("Step 2: 等待结果...")
        final_tasks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as executor:
            futures = [executor.submit(grsai_poll_result, task, output_dir) for task in submitted_tasks]
            for future in concurrent.futures.as_completed(futures):
                final_tasks.append(future.result())
    
    # 保存任务状态
    tasks_file = os.path.join(output_dir, "tasks.json")
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(final_tasks, f, indent=2, ensure_ascii=False)
    
    # 统计
    print()
    print("=" * 60)
    completed = [t for t in final_tasks if t['status'] == 'completed']
    failed = [t for t in final_tasks if t['status'] != 'completed']
    
    print(f"完成: {len(completed)}/{args.count}")
    if failed:
        print(f"失败: {[f['name'] for f in failed]}")
    
    # 更新 workflow.json
    update_workflow_json("images_done", slugify(args.topic))
    
    print("=" * 60)
    
    # 列出文件
    print("\n生成的文件:")
    for t in completed:
        filename = f"{t['name']}.png"
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"  {filename} ({size_kb:.1f} KB)")
    
    return len(completed) > 0


if __name__ == "__main__":
    main()