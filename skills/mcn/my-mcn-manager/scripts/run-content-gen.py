#!/usr/bin/env python3
"""
内容生成脚本 - 根据选题生成公众号文章

整合自：mcn-content-rewriter 技能

用法:
    python scripts/run-content-gen.py --topic "主题名" --style professional
    python scripts/run-content-gen.py --date 2026-04-14 --auto  # 从选题报告自动读取
"""

import sys
import os
import re
import json
import yaml
import argparse
import subprocess
from datetime import datetime

# 配置
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"

def load_config():
    """加载配置"""
    with open(MCN_CONFIG) as f:
        return yaml.safe_load(f)

def read_topic_report(date: str):
    """读取选题报告"""
    filename = f"{KB_ROOT}/tmp/topic/{date}/recommend.md"
    if not os.path.exists(filename):
        print(f"✗ 选题报告不存在：{filename}")
        return None
    
    content = open(filename, encoding='utf-8').read()
    
    # 解析推荐主题表格
    topics = []
    table_match = re.search(r'\| 排名 \| 主题 \| 领域 \| 热度 \| 综合评分 \| 来源 \|(.*?)\n##', content, re.DOTALL)
    if table_match:
        table_content = table_match.group(1)
        for line in table_content.strip().split('\n'):
            if line.strip().startswith('|'):
                parts = line.split('|')
                if len(parts) >= 6:
                    topics.append({
                        'rank': parts[1].strip(),
                        'title': parts[2].strip(),
                        'domain': parts[3].strip(),
                        'heat': parts[4].strip(),
                        'score': parts[5].strip(),
                        'source_url': parts[6].strip().replace('[查看]', '').replace('(', '').replace(')', '')
                    })
    
    return topics

def generate_titles(topic: str, style: str = 'professional') -> list:
    """生成 5 个候选标题"""
    
    prompt = f"""根据以下话题，生成 5 个公众号文章标题：

话题：{topic}
风格：{style}

使用不同的标题公式：
1. 数字 + 结果 + 方法（如：3 个方法让存款翻倍）
2. 人群 + 痛点 + 方案（如：30 岁没存款？这个计划适合你）
3. 对比 + 反差 + 原因（如：同样工作 5 年，为什么他存款是你的 10 倍）
4. 悬念 + 揭秘 + 价值（如：揭秘：配音演员的声音被谁偷走了）
5. 热点 + 观点 + 引发思考（如：AI 风波：行业饭碗还稳吗）

要求：
- 标题长度：15-25 字
- 吸引点击但不夸张
- 符合公众号风格
- 避免：标题党、负面词汇、敏感词

输出格式（JSON）：
[
  {{"formula": "数字 + 结果 + 方法", "title": "..."}},
  {{"formula": "人群 + 痛点 + 方案", "title": "..."}},
  ...
]
"""
    
    # 调用 LLM（这里用占位，实际应集成 Ollama 或其他 LLM）
    print(f"生成标题：{topic}")
    
    # 占位实现
    titles = [
        {"formula": "数字 + 结果 + 方法", "title": f"3 个方法，让你理解{topic}"},
        {"formula": "人群 + 痛点 + 方案", "title": f"关注{topic}的人都在看什么？"},
        {"formula": "对比 + 反差 + 原因", "title": f"同样关注{topic}，为什么他更专业？"},
        {"formula": "悬念 + 揭秘 + 价值", "title": f"揭秘：{topic}背后的真相"},
        {"formula": "热点 + 观点 + 引发思考", "title": f"{topic}：我们该如何看待？"}
    ]
    
    return titles

def evaluate_title(title: str, topic: str) -> dict:
    """评估单个标题"""
    
    score = 0
    reasons = []
    
    # 1. 长度检查（15-25 字）
    length = len(title)
    if 15 <= length <= 25:
        score += 20
        reasons.append(f"长度合适 ({length}字)")
    elif length < 15:
        score -= 10
        reasons.append(f"太短 ({length}字)")
    else:
        score -= 5
        reasons.append(f"略长 ({length}字)")
    
    # 2. 吸引力关键词
    attract_words = ['揭秘', '背后', '如何', '为什么', '方法', '真相', '关键', '核心']
    for word in attract_words:
        if word in title:
            score += 10
            reasons.append(f"含吸引力词'{word}'")
    
    # 3. 数字元素（具体化）
    if re.search(r'\d+', title):
        score += 15
        reasons.append("含数字元素")
    
    # 4. 避免负面词
    negative_words = ['失败', '惨', '悲剧', '死', '亡']
    for word in negative_words:
        if word in title:
            score -= 20
            reasons.append(f"含负面词'{word}'")
    
    # 5. 与主题相关性
    topic_keywords = topic.split()
    relevance = sum(1 for kw in topic_keywords if kw in title)
    score += relevance * 5
    reasons.append(f"主题相关度{relevance}")
    
    return {
        'title': title,
        'score': score,
        'reasons': reasons,
        'grade': 'A' if score >= 50 else 'B' if score >= 30 else 'C'
    }

def select_best_title(titles: list, topic: str) -> dict:
    """选择最佳标题"""
    
    evaluations = []
    
    for title_info in titles:
        eval_result = evaluate_title(title_info['title'], topic)
        eval_result['formula'] = title_info['formula']
        evaluations.append(eval_result)
    
    # 按分数排序
    sorted_evals = sorted(evaluations, key=lambda x: x['score'], reverse=True)
    best = sorted_evals[0]
    
    return {
        'best_title': best['title'],
        'best_formula': best['formula'],
        'best_score': best['score'],
        'all_evaluations': sorted_evals,
        'reason': best['reasons']
    }

def generate_article_content(topic: str, title: str, style: str = 'professional') -> str:
    """生成文章内容"""
    
    prompt = f"""请根据以下热点话题，生成一篇适合微信公众号的文章。

话题：{topic}
标题：{title}
风格：{style}

要求：
1. 开头使用「场景引入式」，300 字内抓住读者
2. 正文 1500-2000 字，分 3-5 个要点阐述
3. 结尾使用「总结升华式 + 互动引导」
4. 避免敏感内容，保持客观中立
5. 去 AI 化：用口语化表达，添加个人观点

输出格式：
# {title}

[正文内容]
"""
    
    # 调用 LLM（占位实现）
    print(f"生成文章：{title}")
    
    content = f"""# {title}

## 引言

{topic}是当前的热门话题。作为一名科技从业者，我最近也关注到了这个现象...

## 正文

详细内容待生成...

## 总结

总的来说，这个话题值得我们深入思考。你怎么看？欢迎在评论区分享你的观点。

## 标签建议
#AI #技术 #干货 #思考
"""
    
    return content

def verify_word_count(content: str, min_words: int = 1500, max_words: int = 2000) -> dict:
    """验证字数"""
    
    text_only = re.sub(r'[^\w]', '', content)
    word_count = len(text_only)
    
    result = {
        'word_count': word_count,
        'min_words': min_words,
        'max_words': max_words,
        'status': 'unknown',
        'message': ''
    }
    
    if word_count < min_words:
        result['status'] = 'insufficient'
        result['message'] = f"字数不足：{word_count}字，需要补充{min_words - word_count}字"
        result['action'] = 'supplement'
    elif word_count > max_words:
        result['status'] = 'excessive'
        result['message'] = f"字数过多：{word_count}字，需要删减{word_count - max_words}字"
        result['action'] = 'condense'
    else:
        result['status'] = 'valid'
        result['message'] = f"字数合格：{word_count}字"
        result['action'] = 'pass'
    
    return result

def supplement_article(content: str, need_words: int, topic: str) -> str:
    """补充文章内容"""
    
    print(f"补充文章内容：需要{need_words}字")
    
    supplement = f"""
## 补充内容

关于{topic}，我们还需要注意以下几点：

1. 行业背景分析
2. 技术细节说明
3. 实操建议
4. 常见问题解答

这些内容可以帮助读者更好地理解这个话题。
"""
    
    return content + supplement

def replace_brand_names(content: str) -> str:
    """替换品牌名称"""
    
    replacements = {
        '豆包': '某 AI',
        '字节跳动': '平台',
        '莫氏鸡煲': '网红店',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    return content

def generate_article(topic: str, style: str = 'professional') -> dict:
    """生成文章的完整流程"""
    
    print("=" * 60)
    print(f"生成文章：{topic}")
    print("=" * 60)
    
    # 1. 生成标题
    print("\n[1/5] 生成标题...")
    titles = generate_titles(topic, style)
    
    # 2. 选择最佳标题
    print("\n[2/5] 评估标题...")
    best = select_best_title(titles, topic)
    print(f"✓ 最佳标题：{best['best_title']}")
    print(f"  公式：{best['best_formula']}")
    print(f"  评分：{best['best_score']}")
    
    # 3. 生成文章
    print("\n[3/5] 生成文章内容...")
    content = generate_article_content(topic, best['best_title'], style)
    
    # 4. 验证字数
    print("\n[4/5] 验证字数...")
    verify_result = verify_word_count(content)
    print(f"  {verify_result['message']}")
    
    if verify_result['status'] == 'insufficient':
        print("  自动补充内容...")
        content = supplement_article(content, verify_result['min_words'] - verify_result['word_count'], topic)
        verify_result = verify_word_count(content)
        print(f"  补充后：{verify_result['message']}")
    
    # 5. 替换品牌名
    print("\n[5/5] 替换品牌名...")
    content = replace_brand_names(content)
    print("✓ 品牌名已替换")
    
    # 保存文章
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = f"{KB_ROOT}/tmp/content/{date_str}"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{output_dir}/{topic.replace(' ', '-')}.md"
    
    # 添加 frontmatter
    frontmatter = f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
source_topic: {topic}
platform: wechat-mp
status: draft
style: {style}
word_count: {verify_result['word_count']}
---

"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)
    
    print(f"\n✓ 文章已保存：{filename}")
    print(f"  字数：{verify_result['word_count']}")
    print(f"  标题：{best['best_title']}")
    
    return {
        'status': 'success',
        'topic': topic,
        'title': best['best_title'],
        'word_count': verify_result['word_count'],
        'file': filename
    }

def main():
    parser = argparse.ArgumentParser(description='内容生成')
    parser.add_argument('--topic', type=str, help='文章主题')
    parser.add_argument('--date', type=str, help='从选题报告读取（指定日期）')
    parser.add_argument('--rank', type=int, default=1, help='选题排名（默认第 1 个）')
    parser.add_argument('--style', type=str, default='professional',
                       choices=['professional', 'casual', 'story'],
                       help='文章风格')
    parser.add_argument('--auto', action='store_true', help='自动模式（从选题报告读取）')
    
    args = parser.parse_args()
    
    if args.auto:
        date = args.date or datetime.now().strftime("%Y-%m-%d")
        topics = read_topic_report(date)
        
        if not topics:
            print("✗ 无法读取选题报告")
            sys.exit(1)
        
        if args.rank > len(topics):
            print(f"✗ 排名超出范围：{args.rank} > {len(topics)}")
            sys.exit(1)
        
        topic = topics[args.rank - 1]['title']
        print(f"自动选择主题：{topic}")
    elif args.topic:
        topic = args.topic
    else:
        print("用法：python scripts/run-content-gen.py --topic '主题名'")
        print("   或：python scripts/run-content-gen.py --date 2026-04-14 --auto")
        sys.exit(1)
    
    result = generate_article(topic, args.style)
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
