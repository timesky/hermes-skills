#!/usr/bin/env python3
"""
文章验证脚本

验证文章是否符合发布标准：
- 字数：1500-2000 字
- 配图：3-5 张
- 去 AI 化评分：≥ 45
- 标题：≤ 64 字符
- 摘要：≤ 120 字符
- 品牌名：已替换

用法:
    python scripts/validate-article.py --article article.md
"""

import sys
import os
import re
import json
import argparse

def count_words(content: str) -> int:
    """计算字数（排除标点空格）"""
    text_only = re.sub(r'[^\w]', '', content)
    return len(text_only)

def extract_title(content: str) -> str:
    """提取标题"""
    match = re.search(r'# (.+)', content)
    return match.group(1) if match else ""

def extract_digest(content: str, max_length: int = 120) -> str:
    """提取摘要"""
    body_start = content.find('\n\n') + 2
    body = content[body_start:body_start + 500]
    digest = body.replace('\n', ' ').strip()
    if len(digest) > max_length:
        digest = digest[:max_length - 3] + "..."
    return digest

def check_brand_names(content: str) -> list:
    """检查品牌名是否已替换"""
    brand_keywords = ['豆包', '字节跳动', '莫氏鸡煲']
    found = []
    for brand in brand_keywords:
        if brand in content:
            found.append(brand)
    return found

def count_images(img_dir: str) -> int:
    """统计配图数量"""
    if not os.path.exists(img_dir):
        return 0
    images = [f for f in os.listdir(img_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    return len(images)

def evaluate_humanization(content: str) -> int:
    """评估去 AI 化评分（简化版）"""
    score = 50
    
    # 扣分项：AI 模板词
    ai_patterns = ['综上所述', '值得注意的是', '首先', '其次', '最后', '作为', '的证明', '此外']
    for pattern in ai_patterns:
        if pattern in content:
            score -= 5
    
    # 加分项：口语化
    human_patterns = ['我觉得', '在我看来', '其实', '说白了', '你说', '这事儿']
    for pattern in human_patterns:
        if pattern in content:
            score += 3
    
    return min(50, max(0, score))

def validate_article(article_path: str) -> dict:
    """验证文章"""
    
    content = open(article_path, encoding='utf-8').read()
    dir_path = os.path.dirname(article_path)
    
    # 查找配图目录
    img_dir = None
    for d in os.listdir(dir_path):
        if d == 'images':
            img_dir = f"{dir_path}/images"
            break
    
    # 如果有 images 目录，查找文章对应的子目录
    if img_dir:
        article_name = os.path.basename(article_path).replace('.md', '')
        for sub in os.listdir(img_dir):
            if article_name in sub or sub in article_name:
                img_dir = f"{img_dir}/{sub}"
                break
    
    results = {
        'article': article_path,
        'checks': {},
        'passed': True,
        'message': ''
    }
    
    # 1. 字数检查
    word_count = count_words(content)
    results['checks']['word_count'] = {
        'value': word_count,
        'min': 1500,
        'max': 2000,
        'status': 'pass' if 1500 <= word_count <= 2000 else 'fail'
    }
    
    # 2. 标题检查
    title = extract_title(content)
    title_length = len(title)
    results['checks']['title_length'] = {
        'value': title_length,
        'max': 64,
        'status': 'pass' if title_length <= 64 else 'fail',
        'title': title
    }
    
    # 3. 摘要检查
    digest = extract_digest(content)
    digest_length = len(digest)
    results['checks']['digest_length'] = {
        'value': digest_length,
        'max': 120,
        'status': 'pass' if digest_length <= 120 else 'fail'
    }
    
    # 4. 配图检查
    img_count = count_images(img_dir) if img_dir else 0
    results['checks']['image_count'] = {
        'value': img_count,
        'min': 3,
        'max': 5,
        'status': 'pass' if 3 <= img_count <= 5 else 'fail',
        'dir': img_dir or 'N/A'
    }
    
    # 5. 品牌名检查
    found_brands = check_brand_names(content)
    results['checks']['brand_names'] = {
        'found': found_brands,
        'status': 'pass' if len(found_brands) == 0 else 'fail'
    }
    
    # 6. 去 AI 化评分
    human_score = evaluate_humanization(content)
    results['checks']['humanization_score'] = {
        'value': human_score,
        'min': 45,
        'status': 'pass' if human_score >= 45 else 'warn'
    }
    
    # 总体判断
    failed_checks = [k for k, v in results['checks'].items() if v['status'] == 'fail']
    if failed_checks:
        results['passed'] = False
        results['message'] = f"验证失败：{', '.join(failed_checks)}"
    else:
        results['message'] = "验证通过，符合发布标准"
    
    return results

def print_report(results: dict):
    """打印验证报告"""
    print("\n" + "=" * 60)
    print("文章验证报告")
    print("=" * 60)
    print(f"文章：{results['article']}\n")
    
    for check_name, check_data in results['checks'].items():
        status_icon = "✓" if check_data['status'] == 'pass' else "✗" if check_data['status'] == 'fail' else "○"
        print(f"{status_icon} {check_name}:")
        
        if check_name == 'word_count':
            print(f"   字数：{check_data['value']} ({check_data['min']}-{check_data['max']})")
        elif check_name == 'title_length':
            print(f"   标题：{check_data['title'][:50]}...")
            print(f"   长度：{check_data['value']} 字符 (≤{check_data['max']})")
        elif check_name == 'digest_length':
            print(f"   摘要长度：{check_data['value']} 字符 (≤{check_data['max']})")
        elif check_name == 'image_count':
            print(f"   配图：{check_data['value']} 张 ({check_data['min']}-{check_data['max']})")
            print(f"   目录：{check_data['dir']}")
        elif check_name == 'brand_names':
            if check_data['found']:
                print(f"   未替换品牌：{', '.join(check_data['found'])}")
            else:
                print(f"   品牌名已替换")
        elif check_name == 'humanization_score':
            print(f"   评分：{check_data['value']}/50 (≥{check_data['min']})")
        print()
    
    print("=" * 60)
    if results['passed']:
        print("✅ 结论：符合发布标准")
    else:
        print(f"❌ 结论：{results['message']}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='文章验证')
    parser.add_argument('--article', type=str, required=True, help='文章路径')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.article):
        print(f"✗ 文件不存在：{args.article}")
        sys.exit(1)
    
    results = validate_article(args.article)
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results)
    
    sys.exit(0 if results['passed'] else 1)

if __name__ == '__main__':
    main()
