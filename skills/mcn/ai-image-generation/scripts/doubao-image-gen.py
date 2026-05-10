# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
豆包生图脚本 - 支持中文提示词

关键优势：
1. 支持中文提示词（解决 GrsAI 中文乱码问题）
2. 每个模型 200 张免费额度
3. 调用简单，类似 OpenAI 格式

用法:
    python doubao-image-gen.py --topic "编程学习" --count 4 --date 2026-04-19
    python doubao-image-gen.py --prompt "雨后彩虹，一群鸟儿飞过" --output ./test.png
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
    try:
        import yaml
        with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠️ 配置文件不存在: {MCN_CONFIG}")
        return {}
    except Exception as e:
        print(f"⚠️ 配置加载失败: {e}")
        return {}

# 尝试加载配置
_config = load_config()
_image_config = _config.get('image_generation', {})
_doubao_config = _image_config.get('providers', {}).get('doubao', {})

# API 配置（可从配置文件或环境变量获取）
API_URL = _doubao_config.get('api_url', 'https://ark.cn-beijing.volces.com/api/v3/images/generations')
API_KEY = _doubao_config.get('api_key', os.environ.get('DOUBAO_API_KEY', ''))
MODEL_ID = _doubao_config.get('models', {}).get(
    _doubao_config.get('default_model', 'seedream-5.0-lite'),
    'doubao-seedream-5-0-lite'  # 最便宜的模型
)

# 默认超时
TIMEOUT = _doubao_config.get('timeout', 60)

# 目录约定
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


def generate_single_image(prompt, size="2048x2048"):
    """生成单张图片
    
    Args:
        prompt: 图片描述（支持中文）
        size: 图片尺寸 ("2048x2048", "2K") - 豆包要求最小 3686400 像素
    
    Returns:
        图片 URL 或 None
    """
    
    if not API_KEY:
        print("❌ 缺少 API Key，请设置 DOUBAO_API_KEY 或在 mcn_config.yaml 中配置")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # 标准化尺寸 - 豆包要求最小 3686400 像素
    size_normalized = size.replace("*", "x").lower()
    if size_normalized in ("1024x1024", "1k"):
        # 1024x1024 = 1048576 像素，不足 3686400
        size_param = "2048x2048"  # 自动升级到合规尺寸
    elif size_normalized in ("2048x2048", "2k"):
        size_param = "2048x2048"
    else:
        size_param = "2048x2048"  # 默认 2K
    
    payload = {
        "model": MODEL_ID,
        "prompt": prompt,
        "size": size_param,
        "response_format": "url",  # 返回 URL
        "stream": False,  # 同步响应
        "watermark": False  # 无水印
    }
    
    try:
        print(f"  提交任务: {prompt[:50]}...")
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
        
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        
        result = resp.json()
        
        # 解析响应
        if result.get('data') and isinstance(result['data'], list):
            for item in result['data']:
                if 'url' in item:
                    print(f"  ✅ 生成成功")
                    return item['url']
                elif 'b64_json' in item:
                    # Base64 格式
                    print(f"  ✅ 生成成功 (base64)")
                    return {'type': 'base64', 'data': item['b64_json']}
        
        # 错误响应
        if result.get('error'):
            print(f"  ❌ API 错误: {result['error']}")
        
        print(f"  ❌ 响应解析失败: {result}")
        return None
        
    except requests.exceptions.Timeout:
        print(f"  ⏰ 请求超时 ({TIMEOUT}s)")
        return None
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return None


def download_image(url, output_path, is_cover=False):
    """下载图片并保存
    
    Args:
        url: 图片 URL 或 base64 数据
        output_path: 保存路径
        is_cover: 是否封面图（需要调整尺寸）
    
    Returns:
        bool: 是否成功
    """
    
    try:
        if isinstance(url, dict) and url.get('type') == 'base64':
            # Base64 数据
            import base64
            image_data = base64.b64decode(url['data'])
            with open(output_path, 'wb') as f:
                f.write(image_data)
        else:
            # URL下载
            resp = requests.get(url, timeout=60, stream=True)
            if resp.status_code != 200:
                print(f"  ❌ 下载失败: HTTP {resp.status_code}")
                return False
            
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # 封面图调整尺寸
        if is_cover:
            resize_cover(output_path, 900, 500)
        
        size_kb = os.path.getsize(output_path) / 1024
        print(f"  ✅ 保存成功: {output_path} ({size_kb:.1f} KB)")
        return True
        
    except Exception as e:
        print(f"  ❌ 下载异常: {e}")
        return False


def resize_cover(path, target_w=900, target_h=500):
    """调整封面图尺寸"""
    try:
        from PIL import Image
        img = Image.open(path)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(path, 'PNG')
        print(f"  ✅ 尺寸调整: {target_w}x{target_h}")
    except ImportError:
        print("  ⚠️ PIL 未安装，跳过尺寸调整")
    except Exception as e:
        print(f"  ⚠️ 尺寸调整失败: {e}")


def generate_prompts_from_article(topic, article_path, count=4):
    """根据文章段落内容生成差异化提示词
    
    豆包支持中文，所以可以直接用中文描述
    """
    
    prompts = []
    
    # 尝试读取文章
    if article_path and os.path.exists(article_path):
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除 frontmatter
        import re
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        
        # 按段落分割
        paragraphs = content.split('\n## ')
        
        if len(paragraphs) >= count:
            print(f"  ✓ 根据文章段落生成提示词")
            
            # 封面：整体主题
            cover_prompt = f"{topic} 概念艺术，专业数字插画，科技氛围，高质量，现代设计风格"
            prompts.append({'name': 'cover', 'prompt': cover_prompt})
            
            # 内容图：根据段落关键词
            style_templates = [
                "现代简约风格插画，科技感，专业设计",
                "信息图风格，数据可视化，商务场景",
                "场景插画，氛围光效，故事感，高质量",
            ]
            
            for i in range(count - 1):
                para_idx = min(i + 1, len(paragraphs) - 1)
                para = paragraphs[para_idx]
                
                # 提取关键词（前80字）
                snippet = para.replace('#', '').replace('*', '').strip()[:80]
                keywords = snippet.split('，')[0] if '，' in snippet else snippet[:30]
                
                style = style_templates[i % len(style_templates)]
                prompt = f"{keywords} {style}"
                
                prompts.append({'name': f'img_{i+1}', 'prompt': prompt})
        else:
            print(f"  ⚠️ 文章段落不足，使用通用提示词")
            prompts = generate_generic_prompts(topic, count)
    else:
        print(f"  ⚠️ 无文章路径，使用通用提示词")
        prompts = generate_generic_prompts(topic, count)
    
    return prompts


def generate_generic_prompts(topic, count):
    """生成通用差异化提示词"""
    
    prompts = []
    
    # 封面
    cover_prompt = f"{topic} 概念艺术，专业数字插画，科技氛围，高质量构图，现代设计"
    prompts.append({'name': 'cover', 'prompt': cover_prompt})
    
    # 内容图（不同角度）
    angles = [
        f"{topic} 商业合作场景插画",
        f"{topic} 技术竞争概念图",
        f"{topic} 行业变革未来展望",
        f"{topic} 理念之争对比视觉",
    ]
    
    styles = ["现代简约风格，专业设计", "信息图风格，数据可视化", "场景插画，故事感"]
    
    for i in range(count - 1):
        angle = angles[i % len(angles)]
        style = styles[i % len(styles)]
        prompts.append({'name': f'img_{i+1}', 'prompt': f"{angle}, {style}"})
    
    return prompts


def main():
    parser = argparse.ArgumentParser(description='豆包生图（支持中文提示词）')
    parser.add_argument('--prompt', type=str, help='直接指定提示词')
    parser.add_argument('--topic', type=str, help='文章主题（批量生成时使用）')
    parser.add_argument('--count', type=int, default=4, help='图片数量')
    parser.add_argument('--date', type=str, help='日期 (YYYY-MM-DD)')
    parser.add_argument('--article', type=str, help='文章路径（段落差异化）')
    parser.add_argument('--output', type=str, help='单个图片输出路径')
    parser.add_argument('--size', type=str, default='2048x2048', help='图片尺寸（豆包要求≥2K）')
    
    args = parser.parse_args()
    
    # 检查 API Key
    if not API_KEY:
        print("=" * 60)
        print("❌ 缺少豆包 API Key")
        print("=" * 60)
        print("请按以下步骤获取：")
        print("1. 注册火山引擎: https://www.volcengine.com")
        print("2. 开通豆包大模型: https://ark.cn-beijing.volces.com/")
        print("3. 创建 API Key 并复制")
        print("4. 设置环境变量: export DOUBAO_API_KEY=your_key")
        print("   或在 ~/.hermes/mcn_config.yaml 中配置")
        print("=" * 60)
        sys.exit(1)
    
    # 单张图片模式
    if args.prompt:
        output_path = args.output or "./doubao_output.png"
        print(f"单张生成模式")
        print(f"提示词: {args.prompt}")
        print(f"输出: {output_path}")
        print()
        
        url = generate_single_image(args.prompt, args.size)
        if url:
            download_image(url, output_path)
        return
    
    # 批量生成模式
    if not args.topic:
        print("❌ 批量生成需要 --topic 参数")
        sys.exit(1)
    
    if not args.date:
        args.date = datetime.now().strftime('%Y-%m-%d')
    
    output_dir = get_images_dir(args.date, args.topic)
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("豆包生图（批量）")
    print("=" * 60)
    print(f"主题: {args.topic}")
    print(f"数量: {args.count}")
    print(f"模型: {MODEL_ID}")
    print(f"输出: {output_dir}")
    print(f"优势: 支持中文提示词")
    print()
    
    # 生成提示词
    article_path = args.article
    if not article_path:
        # 自动查找
        article_path = os.path.join(output_dir.replace('/images', ''), 'article.md')
        if not os.path.exists(article_path):
            article_path = None
    
    prompts = generate_prompts_from_article(args.topic, article_path, args.count)
    
    # 并发生成
    print("开始生成...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.count, 3)) as executor:
        futures = {}
        for p in prompts:
            future = executor.submit(generate_single_image, p['prompt'], args.size)
            futures[future] = p
        
        for future in concurrent.futures.as_completed(futures):
            p = futures[future]
            url = future.result()
            
            if url:
                is_cover = p['name'] == 'cover'
                output_path = os.path.join(output_dir, f"{p['name']}.png")
                success = download_image(url, output_path, is_cover)
                results.append({'name': p['name'], 'status': 'success' if success else 'download_failed'})
            else:
                results.append({'name': p['name'], 'status': 'failed'})
    
    # 统计
    print()
    print("=" * 60)
    completed = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']
    
    print(f"完成: {len(completed)}/{args.count}")
    if failed:
        print(f"失败: {[f['name'] for f in failed]}")
    
    print("=" * 60)
    
    # 列出文件
    print("\n生成的文件:")
    for r in completed:
        filename = f"{r['name']}.png"
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"  {filename} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()