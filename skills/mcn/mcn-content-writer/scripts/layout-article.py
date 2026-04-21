#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章排版脚本 - 标题竞选 + 美化样式 + 图片锚点 + 固定尾部

完整排版流程：
1. 标题竞选：生成5个候选标题，自动评估选择最佳
2. 美化样式：转换为公众号 HTML 格式（标题、正文、引用）
3. 图片锚点：在段落位置插入图片标记
4. 固定尾部：添加关注公众号模板

用法:
    python layout-article.py --article path/to/article.md --date 2026-04-19
"""

import sys
import os
import re
import json
import argparse
import yaml
from datetime import datetime

# 配置
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
MCN_ROOT = KB_ROOT + "/mcn"

def load_config():
    """加载配置"""
    with open(MCN_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def slugify(text: str) -> str:
    """将文本转换为目录名安全的 slug"""
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【】\n\r\t]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s[:50].strip('-')

# ==================== 1. 标题竞选 ====================

def generate_titles(topic: str) -> list:
    """生成 5 个候选标题"""
    
    # 标题公式
    formulas = [
        ("数字 + 结果 + 方法", f"3 个关键点，让你看懂{topic}"),
        ("人群 + 痛点 + 方案", f"关注{topic}的人，都在思考什么？"),
        ("对比 + 反差 + 原因", f"同样是{topic}，为什么观点差距这么大"),
        ("悬念 + 揭秘 + 价值", f"揭秘：{topic}背后的真相"),
        ("热点 + 观点 + 引发思考", f"{topic}：这个趋势你怎么看？"),
    ]
    
    titles = []
    for formula, title in formulas:
        titles.append({
            "formula": formula,
            "title": title,
            "length": len(title)
        })
    
    return titles

def evaluate_title(title_info: dict, topic: str) -> dict:
    """评估单个标题"""
    
    score = 0
    reasons = []
    title = title_info['title']
    
    # 1. 长度检查（15-25 字）
    length = title_info['length']
    if 15 <= length <= 25:
        score += 20
        reasons.append(f"长度合适({length}字)")
    elif length < 15:
        score -= 10
        reasons.append(f"太短({length}字)")
    else:
        score -= 5
        reasons.append(f"略长({length}字)")
    
    # 2. 吸引力关键词
    attract_words = ['揭秘', '背后', '如何', '为什么', '方法', '真相', '关键', '核心', '看懂']
    for word in attract_words:
        if word in title:
            score += 10
            reasons.append(f"含吸引力词'{word}'")
    
    # 3. 数字元素
    if re.search(r'\d+', title):
        score += 15
        reasons.append("含数字元素")
    
    # 4. 避免负面词
    negative_words = ['失败', '惨', '悲剧', '死', '亡', '问题']
    for word in negative_words:
        if word in title:
            score -= 20
            reasons.append(f"含负面词'{word}'")
    
    # 5. 主题相关性
    topic_keywords = re.findall(r'\w+', topic)
    relevance = sum(1 for kw in topic_keywords if kw in title)
    score += relevance * 5
    reasons.append(f"主题相关度{relevance}")
    
    return {
        "title": title,
        "formula": title_info['formula'],
        "score": score,
        "grade": 'A' if score >= 50 else 'B' if score >= 30 else 'C',
        "reasons": reasons
    }

def select_best_title(topic: str) -> dict:
    """标题竞选：生成并评估，选择最佳"""
    
    print("\n[1/4] 标题竞选...")
    print(f"  主题: {topic}")
    
    # 生成候选
    titles = generate_titles(topic)
    
    # 评估每个标题
    evaluations = []
    for t in titles:
        eval_result = evaluate_title(t, topic)
        evaluations.append(eval_result)
        print(f"  [{eval_result['grade']}] {eval_result['title']} (分数: {eval_result['score']})")
    
    # 按分数排序
    sorted_evals = sorted(evaluations, key=lambda x: x['score'], reverse=True)
    best = sorted_evals[0]
    
    print(f"\n  ✓ 最佳标题: {best['title']}")
    print(f"    公式: {best['formula']}")
    print(f"    评分: {best['score']} ({best['grade']})")
    
    return best

# ==================== 2. 图片锚点 ====================

def insert_image_anchors(content: str) -> str:
    """在文章段落位置插入图片锚点
    
    规则（3张图均匀分布）：
    - img_1: 在文章前 1/3 位置
    - img_2: 在文章后 1/3 位置（总结段落之前）
    
    注意：封面图（IMG_0）已在标题后单独插入
    """
    
    # 去掉标签建议部分
    if '## 标签建议' in content:
        content = content.split('## 标签建议')[0]
        print("  ✓ 已去掉标签建议部分")
    
    # 按段落分割（双换行符）
    paragraphs = re.split(r'\n\n+', content)
    
    # 过滤掉空段落和分隔线
    paragraphs = [p for p in paragraphs if p.strip() and p.strip() != '---']
    
    total = len(paragraphs)
    
    if total < 6:
        print("  ⚠️ 段落较少，使用默认位置")
        img1_pos = 2
        img2_pos = max(3, total - 2)
    else:
        # 三张图均匀分布：
        # 封面图：标题后（已单独处理）
        # img_1：前 1/3 位置
        # img_2：后 1/3 位置（总结前）
        img1_pos = total // 3  # 前 1/3
        img2_pos = total * 2 // 3  # 后 1/3
    
    # 插入锚点
    paragraphs.insert(img1_pos, '<!-- IMG: img_1 -->')
    paragraphs.insert(img2_pos + 1, '<!-- IMG: img_2 -->')  # +1 因为已插入一个
    
    result = '\n\n'.join(paragraphs)
    print(f"  ✓ 已插入 2 个图片锚点（段落总数: {total}，位置: {img1_pos}, {img2_pos}）")
    
    return result

# ==================== 3. 美化样式 ====================

def beautify_html(content: str, title: str) -> str:
    """转换为公众号 HTML 格式
    
    图片布局：
    - IMG_0: 封面图，放在标题后作为第一张图
    - IMG_1: 段落图1（前半部分）
    - IMG_2: 段落图2（后半部分）
    
    输出两种用途：
    1. 本地预览：完整 HTML（含 charset、body）
    2. 公众号发布：提取 body 内容（去掉外层结构）
    """
    
    # HTML 头部（本地预览用，公众号发布时会去掉）
    html_head = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
  </style>
</head>
<body>
'''
    
    html_end = '''</body>
</html>'''
    
    # 标题样式
    title_html = f'''<h1 style="font-size: 24px; font-weight: bold; color: #333; margin-bottom: 20px; text-align: center;">{title}</h1>'''
    
    # 封面图（放在标题后）
    cover_html = '''
<div style="text-align: center; margin: 20px 0;">
  <img src="IMG_0_PLACEHOLDER" style="max-width: 100%; border-radius: 8px;" />
</div>
'''
    
    # 处理图片锚点为 img 标签占位
    content = content.replace('<!-- IMG: img_1 -->', '''
<div style="text-align: center; margin: 20px 0;">
  <img src="IMG_1_PLACEHOLDER" style="max-width: 100%; border-radius: 8px;" />
</div>
''')
    content = content.replace('<!-- IMG: img_2 -->', '''
<div style="text-align: center; margin: 20px 0;">
  <img src="IMG_2_PLACEHOLDER" style="max-width: 100%; border-radius: 8px;" />
</div>
''')
    
    # 处理 Markdown 标题为 HTML
    content = re.sub(r'^## (.+)$', r'<h2 style="font-size: 18px; font-weight: bold; color: #333; margin-top: 30px; margin-bottom: 15px;">\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^### (.+)$', r'<h3 style="font-size: 16px; font-weight: bold; color: #555; margin-top: 20px; margin-bottom: 10px;">\1</h3>', content, flags=re.MULTILINE)
    
    # 处理段落为 HTML
    lines = content.split('\n')
    html_lines = []
    
    for line in lines:
        if line.strip() and not line.startswith('<'):
            # 普通段落
            html_lines.append(f'<p style="font-size: 15px; line-height: 1.8; color: #333; margin-bottom: 15px; text-align: justify;">{line}</p>')
        else:
            html_lines.append(line)
    
    content = '\n'.join(html_lines)
    
    print("  ✓ 已转换为公众号 HTML 格式")
    print("  ✓ 已添加封面图作为首图")
    
    # 返回完整 HTML（本地预览），尾部在 add_footer 函数添加
    return html_head + '\n' + title_html + '\n' + cover_html + '\n' + content + '\n' + html_end

# ==================== 4. 固定尾部 ====================

def get_account_name():
    """获取公众号名称"""
    config = load_config()
    publish_config = config.get('publish', {}).get('accounts', {}).get('main', {})
    return publish_config.get('name', '程序员的开发手册')

def add_footer(content: str) -> str:
    """添加固定尾部 - 关注公众号模板
    
    处理：将 footer 插入到 </body></html> 之前
    """
    
    account_name = get_account_name()
    
    footer = f'''
<div style="margin-top: 40px; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 10px; text-align: center;">
  <p style="font-size: 14px; color: #666; margin-bottom: 10px;">如果觉得有用，点个「在看」支持一下 👇</p>
  <p style="font-size: 16px; font-weight: bold; color: #333; margin-bottom: 5px;">关注「{account_name}」</p>
  <p style="font-size: 13px; color: #888;">分享技术干货 · 聊聊行业观察 · 记录成长思考</p>
</div>
'''
    
    print(f"  ✓ 已添加固定尾部（公众号: {account_name})")
    
    # 如果有 html_end，将 footer 插入到 </body> 之前
    if '</body>' in content:
        content = content.replace('</body>', footer + '\n</body>')
        return content
    else:
        # 没有 html 结构，直接追加
        return content + footer

# ==================== 主流程 ====================

def layout_article(article_path: str, date: str) -> dict:
    """完整排版流程"""
    
    print("=" * 60)
    print("文章排版")
    print("=" * 60)
    print(f"输入: {article_path}")
    print(f"日期: {date}")
    
    # 读取文章
    if not os.path.exists(article_path):
        print(f"✗ 文章不存在: {article_path}")
        return {"status": "error", "message": "文章不存在"}
    
    with open(article_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # 解析 frontmatter
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', original_content, re.DOTALL)
    frontmatter = ""
    content = original_content
    
    if frontmatter_match:
        frontmatter = frontmatter_match.group(0)
        content = original_content[len(frontmatter):]
    
    # 提取主题（从 frontmatter 或目录名）
    topic_match = re.search(r'source_topic:\s*(.+)', frontmatter)
    if topic_match:
        topic = topic_match.group(1).strip()
    else:
        # 从目录名提取
        article_dir = os.path.dirname(article_path)
        topic = os.path.basename(article_dir)
    
    # 1. 标题竞选
    best_title = select_best_title(topic)
    
    # 2. 插入图片锚点
    content_with_anchors = insert_image_anchors(content)
    
    # 3. 美化 HTML
    html_content = beautify_html(content_with_anchors, best_title['title'])
    
    # 4. 添加固定尾部
    final_content = add_footer(html_content)
    
    # 保存排版结果
    layout_file = article_path.replace('.md', '-layout.html')
    with open(layout_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"\n✓ 排版完成")
    print(f"  最佳标题: {best_title['title']}")
    print(f"  输出文件: {layout_file}")
    
    # 更新原文章的标题
    new_frontmatter = frontmatter.replace(
        re.search(r'^title:\s*.+$', frontmatter).group(0) if re.search(r'^title:\s*.+$', frontmatter) else '',
        f"title: {best_title['title']}"
    ) if re.search(r'^title:\s*.+$', frontmatter) else frontmatter + f"title: {best_title['title']}\n"
    
    # 保存更新后的文章（Markdown 版）
    with open(article_path, 'w', encoding='utf-8') as f:
        # 如果 frontmatter 没有 title，添加一个
        if 'title:' not in frontmatter:
            # 在 frontmatter 中添加 title
            fm_dict = {}
            if frontmatter_match:
                fm_content = frontmatter_match.group(1)
                for line in fm_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        fm_dict[key.strip()] = value.strip()
            fm_dict['title'] = best_title['title']
            
            new_fm = "---\n"
            for k, v in fm_dict.items():
                new_fm += f"{k}: {v}\n"
            new_fm += "---\n"
            
            f.write(new_fm + content)
        else:
            # 替换现有 title
            updated_fm = re.sub(r'^title:\s*.+$', f"title: {best_title['title']}", frontmatter, flags=re.MULTILINE)
            f.write(updated_fm + content)
    
    print(f"  文章标题已更新: {article_path}")
    
    return {
        "status": "success",
        "title": best_title['title'],
        "layout_file": layout_file,
        "article_file": article_path
    }

def main():
    parser = argparse.ArgumentParser(description='文章排版（标题竞选 + 美化 + 锚点 + 尾部）')
    parser.add_argument('--article', type=str, required=True, help='文章路径')
    parser.add_argument('--date', type=str, required=True, help='日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    result = layout_article(args.article, args.date)
    
    if result['status'] == 'success':
        print("\n" + "=" * 60)
        print("排版流程完成")
        print("=" * 60)
        print(f"标题: {result['title']}")
        print(f"排版文件: {result['layout_file']}")
        print(f"文章文件: {result['article_file']}")
        print("\n下一步: 配图生成 → 发布草稿")
    else:
        print(f"\n✗ 排版失败: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    main()