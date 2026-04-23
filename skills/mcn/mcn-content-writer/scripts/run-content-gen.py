#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import requests
from datetime import datetime

# 配置
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
# 目录约定（自包含，不依赖其他技能模块）
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

# ==================== LLM API 调用 ====================

def call_llm_api(prompt: str) -> str:
    """调用 GLM-5 API（阿里云 DashScope 编码专用）
    
    Args:
        prompt: 提示词
        
    Returns:
        str: LLM 生成的文本，失败返回 None
    """
    
    config_path = os.path.expanduser("~/.hermes/mcn_config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    llm_config = config.get('llm', {})
    api_key = llm_config.get('api_key', '')
    base_url = llm_config.get('base_url', 'https://coding.dashscope.aliyuncs.com/v1')
    model = llm_config.get('model', 'glm-5')
    
    if not api_key or '...' in api_key:
        print("⚠️ LLM API Key 未配置或已截断，使用占位内容")
        return None
    
    # OpenAI 格式调用
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": llm_config.get('parameters', {}).get('temperature', 0.7),
        "max_tokens": llm_config.get('parameters', {}).get('max_tokens', 3000)
    }
    
    try:
        print(f"  → 调用 {model} API...")
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=120  # 增加超时
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"  ✓ LLM API 成功（返回 {len(content)} 字符）")
            return content
        else:
            print(f"  ⚠️ LLM API 错误: {response.status_code}")
            print(f"     {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  ⚠️ LLM API 异常: {e}")
        return None

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

# 模板路径（本技能内部）
TEMPLATE_FILE = os.path.expanduser("~/.hermes/skills/mcn/mcn-content-writer/templates/content-templates.md")

def slugify(text: str) -> str:
    """将文本转换为目录名安全的 slug"""
    import re
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【】\n\r\t]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s[:50].strip('-')

def get_article_dir(date: str, topic: str) -> str:
    return f"{MCN_ROOT}/content/{date}/{slugify(topic)}"

def get_images_dir(date: str, topic: str) -> str:
    return f"{MCN_ROOT}/content/{date}/{slugify(topic)}/images"

def get_article_file(date: str, topic: str) -> str:
    return f"{MCN_ROOT}/content/{date}/{slugify(topic)}/article.md"

def detect_article_type(topic: str) -> str:
    """根据话题自动识别文章类型"""
    
    # 关键词特征
    if any(kw in topic for kw in ['教程', '方法', '如何', '步骤', '指南']):
        return '干货教程'
    
    if any(kw in topic for kw in ['分析', '市场', '趋势', '估值', '融资', '财报']):
        return '行业分析'
    
    if any(kw in topic for kw in ['争议', '质疑', '问题', '危机', '之争', '撕']):
        return '观点争议'
    
    if any(kw in topic for kw in ['经历', '故事', '创业', '历程', '背后']):
        return '故事叙述'
    
    # 默认热点评论
    return '热点评论'

def load_template_prompt(article_type: str) -> str:
    """加载模板提示词"""
    
    # 模板编号映射
    template_ids = {
        '热点评论': 'T-01',
        '干货教程': 'T-02',
        '行业分析': 'T-03',
        '故事叙述': 'T-04',
        '观点争议': 'T-05'
    }
    
    template_id = template_ids.get(article_type, 'T-01')
    
    # 读取模板文件，提取对应模板
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取模板部分（三个反引号）
        pattern = f'### {template_id}：{article_type}模板.*?(```markdown\\n.*?)\\n```'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            template = match.group(1).replace('```markdown', '').strip()
            print(f"✓ 加载模板：{template_id}（{article_type}）")
            return template
        else:
            print(f"⚠️ 模板匹配失败，使用增强默认模板")
    
    # 增强默认模板（更完整的提示词）
    return """# 任务：热点评论文章生成

## 输入参数
- 话题：{topic}
- 标题：{title}

## 改写要求

### 结构框架（5段式）
1. **开篇引入**（150字）：用场景或反差切入，引发好奇
2. **事件还原**（300字）：简述事件核心，不啰嗦
3. **观点分析**（500字）：2-3个分析角度，有数据支撑
4. **延伸思考**（400字）：关联行业/社会，升华价值
5. **结尾互动**（150字）：提问引导，不喊口号

### 去 AI 化要求
- ❌ 禁止："作为...的证明"、"综上所述"、"值得注意的是"
- ✅ 使用："说实话"、"我觉得"、"你想想"、"有意思的是"
- ✅ 添加个人视角：程序员/从业者/观察者的真实感受
- ✅ 句子节奏变化：长短句交替，避免全是陈述句

### 字数要求
- 总字数：1500-2000字
- 开篇不超过150字，结尾不超过150字

## 输出格式
直接输出文章正文，无需标题"""

def load_config():
    """加载配置"""
    with open(MCN_CONFIG) as f:
        return yaml.safe_load(f)

def read_topic_report(date: str):
    """读取选题报告"""
    filename = f"{MCN_ROOT}/topic/{date}/recommend.md"
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
1. 具体数据 + 结果（如：华为芯片：数据揭示了什么）
2. 争议观点 + 反转（如：华为芯片火了，但争议背后是什么）
3. 问题 + 深度分析（如：华为芯片：事实和想象差距有多大）
4. 对比 + 引发思考（如：同样是讨论华为芯片，为何观点天差地别）
5. 热点 + 个人看法（如：关于华为芯片，我想说几句）

要求：
- 标题长度：15-25 字
- 吸引点击但不夸张
- 避免模板词：揭秘、关键点、让你看懂、真相、核心、方法、步骤
- 使用个性化词：数据、争议、差距、反转、看法

输出格式（JSON数组，不要包含其他内容）：
[
  {{\"formula\": \"公式类型\", \"title\": \"标题内容\"}},
  ...
]
"""

    # 调用 GLM-5 API
    print(f"生成标题：{topic}")
    
    result = call_llm_api(prompt)
    
    if result:
        # 解析 JSON 结果
        try:
            # 尝试提取 JSON 部分
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                titles = json.loads(json_match.group())
                print(f"✓ LLM 生成了 {len(titles)} 个标题")
                return titles
        except json.JSONDecodeError:
            print("⚠️ LLM 返回格式错误，使用备用标题")
    
    # 备用标题（如果 LLM 失败）
    titles = [
        {"formula": "具体数据 + 结果", "title": f"{topic}：数据揭示了什么"},
        {"formula": "争议观点 + 反转", "title": f"{topic}：事实和想象差距有多大"},
        {"formula": "问题 + 深度分析", "title": f"{topic}火了，但争议背后是什么"},
        {"formula": "对比 + 引发思考", "title": f"同样是讨论{topic}，为何观点天差地别"},
        {"formula": "热点 + 个人看法", "title": f"关于{topic}，我想说几句"},
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
    """生成文章内容（使用 LLM API + 模板系统）"""
    
    # 1. 自动识别文章类型
    article_type = detect_article_type(topic)
    print(f"识别文章类型: {article_type}")
    
    # 2. 加载模板提示词
    template_prompt = load_template_prompt(article_type)
    
    # 3. 构建完整 prompt
    prompt = f"""{template_prompt}

## 当前任务参数
- 原标题/话题：{topic}
- 生成的标题：{title}
- 写作风格：{style}

请按照模板要求生成文章正文（1500-2000字）。
"""
    
    # 调用 GLM-5 API
    print(f"生成文章：{title}")
    print(f"使用模板类型：{article_type}")
    
    result = call_llm_api(prompt)
    
    if result:
        print(f"✓ LLM 生成了文章内容（约 {len(result)} 字符）")
        return result
    
    # 备用内容（如果 LLM 失败）
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
    
    # 使用内联目录函数
    output_dir = get_article_dir(date_str, topic)
    filename = get_article_file(date_str, topic)
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)  # 创建配图目录
    
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
    
    # 6. 去 AI 化处理（调用 humanize-article.py）
    print("\n[6/6] 去 AI 化处理...")
    humanize_script = os.path.join(os.path.dirname(__file__), 'humanize-article.py')
    
    try:
        result = subprocess.run(
            ['python3', humanize_script, '--input', filename],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # 解析评分
            score_match = re.search(r'最终评分：(\d+)/50', result.stdout)
            if score_match:
                humanize_score = int(score_match.group(1))
                print(f"  ✓ 去 AI 化完成，评分：{humanize_score}/50")
                
                if humanize_score < 45:
                    print("  ⚠️ 评分不足45，建议人工审核")
            else:
                print("  ✓ 去 AI 化处理完成")
        else:
            print(f"  ⚠️ 去 AI 化处理失败：{result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print("  ⚠️ 去 AI 化处理超时")
    except Exception as e:
        print(f"  ⚠️ 去 AI 化处理异常：{e}")
    
    # 更新 workflow.json 状态
    update_workflow_json("content_done", slugify(topic))
    
    return {
        'status': 'success',
        'topic': topic,
        'title': best['best_title'],
        'word_count': verify_result['word_count'],
        'file': filename,
        'humanized': True
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
    
    # 更新 workflow.json
    update_workflow_json("content_done", slugify(topic))
    
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
