#!/usr/bin/env python3
"""
去 AI 化脚本

整合自：humanizer-zh 技能

用法:
    python scripts/humanize-article.py --input article.md --output humanized.md
"""

import sys
import os
import re
import json
import argparse

# AI 模板词（扣分项）
AI_PATTERNS = [
    '综上所述', '值得注意的是', '首先', '其次', '最后',
    '作为', '的证明', '此外', '让我们来看看',
    '总而言之', '概括来说', '总的来看'
]

# 口语化词（加分项）
HUMAN_PATTERNS = [
    '我觉得', '在我看来', '其实', '说白了', '你想想',
    '你说', '这事儿', '嘛', '呢', '啊', '吧',
    '说实话', '说真的', '讲真'
]

def evaluate_humanization(content: str) -> int:
    """评估去 AI 化评分（满分 50）"""
    
    score = 50  # 基础分
    
    # 扣分项：AI 模板词
    for pattern in AI_PATTERNS:
        count = content.count(pattern)
        score -= count * 5
    
    # 加分项：口语化
    for pattern in HUMAN_PATTERNS:
        count = content.count(pattern)
        score += count * 3
    
    # 句子长度变化
    sentences = re.split(r'[。！？]', content)
    if sentences:
        lengths = [len(s) for s in sentences if s.strip()]
        if lengths:
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            if variance > 100:
                score += 10
    
    return min(50, max(0, score))

def humanize_content(content: str) -> str:
    """去 AI 化处理"""
    
    # 替换 AI 模板词
    replacements = {
        '综上所述': '总的来说',
        '值得注意的是': '有个细节很有意思',
        '此外': '另外',
        '首先': '第一点',
        '其次': '第二点',
        '最后': '最后一点',
        '总而言之': '说白了',
        '概括来说': '简单说',
        '作为...的证明': '这说明',
        '让我们来看看': '我们来看看'
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # 添加口语化表达（在段落开头）
    paragraphs = content.split('\n\n')
    humanized = []
    
    starters = ['说实话，', '讲真，', '我个人觉得，', '你想想，']
    
    for i, para in enumerate(paragraphs):
        if para.strip().startswith('#') or para.strip().startswith('-'):
            humanized.append(para)
        elif i > 0 and len(para.strip()) > 50:  # 非标题段落
            import random
            if random.random() > 0.7:  # 30%概率添加
                starter = random.choice(starters)
                humanized.append(starter + para)
            else:
                humanized.append(para)
        else:
            humanized.append(para)
    
    return '\n\n'.join(humanized)

def humanize_article(input_path: str, output_path: str = None, max_iterations: int = 2) -> dict:
    """去 AI 化处理文章"""
    
    content = open(input_path, encoding='utf-8').read()
    
    results = {
        'input': input_path,
        'output': output_path,
        'iterations': 0,
        'scores': [],
        'final_score': 0
    }
    
    for i in range(max_iterations):
        print(f"\n=== 第{i+1}次处理 ===")
        
        # 去 AI 化
        humanized = humanize_content(content)
        
        # 评分
        score = evaluate_humanization(humanized)
        results['scores'].append(score)
        results['iterations'] = i + 1
        
        print(f"评分：{score}/50")
        
        if score >= 45:
            print("✓ 评分达标")
            content = humanized
            break
        else:
            print("⚠️ 评分不足，继续优化")
            content = humanized
    
    results['final_score'] = results['scores'][-1]
    
    # 保存结果
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✓ 已保存：{output_path}")
        results['output'] = output_path
    
    return results

def main():
    parser = argparse.ArgumentParser(description='去 AI 化')
    parser.add_argument('--input', type=str, required=True, help='输入文件')
    parser.add_argument('--output', type=str, help='输出文件（默认覆盖原文件）')
    parser.add_argument('--max-iterations', type=int, default=2, help='最大迭代次数')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"✗ 文件不存在：{args.input}")
        sys.exit(1)
    
    output_path = args.output or args.input
    
    print("=" * 60)
    print("去 AI 化处理")
    print("=" * 60)
    print(f"输入：{args.input}")
    print(f"输出：{output_path}")
    
    results = humanize_article(args.input, output_path, args.max_iterations)
    
    print("\n" + "=" * 60)
    print("处理完成")
    print("=" * 60)
    print(f"迭代次数：{results['iterations']}")
    print(f"最终评分：{results['final_score']}/50")
    
    if results['final_score'] >= 45:
        print("✅ 评分达标，符合发布标准")
    else:
        print("⚠️ 评分不足，建议人工审核")
    
    if args.json:
        print("\n" + json.dumps(results, ensure_ascii=False, indent=2))
    
    return results

if __name__ == '__main__':
    main()
