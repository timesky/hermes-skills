#!/usr/bin/env python3
"""
Batch Wiki Ingest Script - 批量处理第一批文件

处理规则：
1. 完整文章：创建 Wiki 页面到 entities/ 或 concepts/
2. 无frontmatter文章：生成 frontmatter 后创建 Wiki 页面
3. 碎片笔记/短笔记：追加到 fragments.md
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
import hashlib

# 配置
KB_ROOT = Path(os.environ.get('KB_ROOT', "/Users/timesky/backup/知识库-Obsidian"))
WIKI_DIR = KB_ROOT / "wiki"
RAW_DIR = KB_ROOT / "raw"
PROCESSED_LOG = WIKI_DIR / "processed.log"
UNPROCESSED_LOG = WIKI_DIR / "unprocessed.log"
FRAGMENTS_MD = WIKI_DIR / "fragments.md"

def load_unprocessed_files(limit=50):
    """从 unprocessed.log 加载未处理文件列表，优先完整文章"""
    if not UNPROCESSED_LOG.exists():
        return []
    
    content = UNPROCESSED_LOG.read_text(encoding='utf-8')
    files = []
    
    # 解析表格格式
    for line in content.split('\n'):
        if 'raw/' in line and '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                path = parts[1].strip()
                file_type = parts[2].strip()
                body_length = int(parts[3].strip()) if parts[3].strip().isdigit() else 0
                title = parts[4].strip()
                if path.startswith('raw/'):
                    files.append({
                        'path': path,
                        'type': file_type,
                        'body_length': body_length,
                        'title': title
                    })
    
    # 优先排序：完整文章 > 碎片笔记 > 短笔记 > 无frontmatter文章
    type_priority = {
        '完整文章': 0,
        '碎片笔记': 1,
        '短笔记': 2,
        '无frontmatter文章': 3
    }
    
    files.sort(key=lambda x: (type_priority.get(x['type'], 99), -x['body_length']))
    
    return files[:limit]

def read_source_file(rel_path):
    """读取源文件内容"""
    full_path = KB_ROOT / rel_path
    if not full_path.exists():
        return None, "文件不存在"
    
    try:
        content = full_path.read_text(encoding='utf-8')
        return content, None
    except Exception as e:
        return None, str(e)

def extract_frontmatter(content):
    """提取 frontmatter"""
    if content.strip().startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return None, content

def generate_frontmatter(title, file_type, source_path):
    """为无 frontmatter 文件生成 frontmatter"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 根据 file_type 决定 type
    wiki_type = 'entity' if file_type in ['完整文章', '无frontmatter文章'] else 'concept'
    
    frontmatter = f"""---
title: {title}
created: {today}
updated: {today}
type: {wiki_type}
tags: []
sources: [{source_path}]
---

"""
    return frontmatter

def slugify(text):
    """转换为 slug 格式"""
    # 移除特殊字符，保留中文和英文
    slug = re.sub(r'[^\w\u4e00-\u9fff-]', '-', text)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug.lower()[:50] or 'untitled'

def determine_target_path(title, file_type, content):
    """确定目标 wiki 页面路径"""
    slug = slugify(title)
    
    # 根据内容判断是实体还是概念
    has_entity_keywords = any(kw in content.lower() for kw in [
        '工具', '平台', '软件', '框架', '系统', 'app', '工具', '平台',
        'openclaw', 'claude', 'cursor', 'openai', 'gemini', 'gpt'
    ])
    
    if file_type in ['完整文章', '无frontmatter文章']:
        if has_entity_keywords:
            return WIKI_DIR / "entities" / f"{slug}.md"
        else:
            return WIKI_DIR / "concepts" / f"{slug}.md"
    else:
        return None  # 碎片笔记不创建单独页面

def create_wiki_page(target_path, frontmatter, body, title):
    """创建 Wiki 页面"""
    if target_path.exists():
        # 合并到现有页面
        existing = target_path.read_text(encoding='utf-8')
        # 在现有内容后追加新内容
        new_content = existing + "\n\n---\n\n## 补充内容\n\n" + body.strip()
        target_path.write_text(new_content, encoding='utf-8')
        return 'merged'
    else:
        # 创建新页面
        full_content = frontmatter + body.strip()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(full_content, encoding='utf-8')
        return 'created'

def append_to_fragments(file_info, content):
    """追加碎片笔记到 fragments.md"""
    if not FRAGMENTS_MD.exists():
        return
    
    fragments_content = FRAGMENTS_MD.read_text(encoding='utf-8')
    
    # 提取正文（去掉可能的 frontmatter）
    fm, body = extract_frontmatter(content)
    body = body.strip()
    
    # 更新统计
    # 找到统计表并更新
    stats_match = re.search(r'\| 碎片笔记总数 \| (\d+) \|', fragments_content)
    short_match = re.search(r'\| 短笔记总数 \| (\d+) \|', fragments_content)
    
    if stats_match:
        new_count = int(stats_match.group(1)) + (1 if file_info['type'] == '碎片笔记' else 0)
        fragments_content = re.sub(
            r'\| 碎片笔记总数 \| \d+ \|',
            f'| 碎片笔记总数 | {new_count} |',
            fragments_content
        )
    
    if short_match:
        new_count = int(short_match.group(1)) + (1 if file_info['type'] == '短笔记' else 0)
        fragments_content = re.sub(
            r'\| 短笔记总数 \| \d+ \|',
            f'| 短笔记总数 | {new_count} |',
            fragments_content
        )
    
    # 添加新条目到对应表格
    if file_info['type'] == '碎片笔记':
        # 找到碎片笔记列表表格
        table_match = re.search(
            r'(## 碎片笔记列表.*?\n\n\|.*?\n\|.*?\n)((?:\|.*?\n)+)',
            fragments_content,
            re.DOTALL
        )
        if table_match:
            new_row = f"| {file_info['path']} | {body[:50]}... | {file_info['body_length']} | 待定 |\n"
            fragments_content = fragments_content.replace(
                table_match.group(0),
                table_match.group(1) + table_match.group(2) + new_row
            )
    else:
        # 短笔记
        table_match = re.search(
            r'(## 短笔记列表.*?\n\n\|.*?\n\|.*?\n)((?:\|.*?\n)+)',
            fragments_content,
            re.DOTALL
        )
        if table_match:
            new_row = f"| {file_info['path']} | {body[:50]}... | {file_info['body_length']} | 待定 |\n"
            fragments_content = fragments_content.replace(
                table_match.group(0),
                table_match.group(1) + table_match.group(2) + new_row
            )
    
    # 更新日期
    fragments_content = re.sub(
        r'updated: \d{4}-\d{2}-\d{2}',
        f"updated: {datetime.now().strftime('%Y-%m-%d')}",
        fragments_content
    )
    
    FRAGMENTS_MD.write_text(fragments_content, encoding='utf-8')

def append_to_processed_log(file_info, wiki_path, status='✅'):
    """追加到 processed.log"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    wiki_rel_path = str(wiki_path.relative_to(WIKI_DIR)) if wiki_path else 'fragments.md'
    
    entry = f"| {file_info['path']} | {today} | {wiki_rel_path} | {status} |\n"
    
    with open(PROCESSED_LOG, 'a', encoding='utf-8') as f:
        f.write(entry)

def process_file(file_info):
    """处理单个文件"""
    rel_path = file_info['path']
    file_type = file_info['type']
    title = file_info['title']
    
    # 读取内容
    content, error = read_source_file(rel_path)
    if error:
        return {'status': 'error', 'message': error}
    
    # 处理不同类型
    if file_type in ['碎片笔记', '短笔记']:
        # 追加到 fragments.md
        append_to_fragments(file_info, content)
        append_to_processed_log(file_info, FRAGMENTS_MD)
        return {'status': 'fragment', 'path': rel_path}
    
    # 完整文章或无frontmatter文章
    frontmatter, body = extract_frontmatter(content)
    
    if frontmatter is None:
        # 无 frontmatter，生成一个
        frontmatter = generate_frontmatter(title, file_type, rel_path)
    
    # 确定目标路径
    target_path = determine_target_path(title, file_type, body)
    
    if target_path:
        # 创建/更新 Wiki 页面
        result = create_wiki_page(target_path, frontmatter, body, title)
        append_to_processed_log(file_info, target_path)
        return {
            'status': result,
            'path': rel_path,
            'wiki_page': str(target_path.relative_to(WIKI_DIR))
        }
    
    return {'status': 'skipped', 'message': '无法确定目标路径'}

def batch_process(limit=50):
    """批量处理"""
    print("=" * 60)
    print(f"Wiki Ingest 批量处理 - 第一批 ({limit}个文件)")
    print("=" * 60)
    
    files = load_unprocessed_files(limit)
    
    if not files:
        print("❌ 没有找到未处理文件")
        return
    
    print(f"\n📋 待处理文件: {len(files)} 个")
    
    # 分类统计
    by_type = {}
    for f in files:
        by_type[f['type']] = by_type.get(f['type'], 0) + 1
    
    print("\n分类:")
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c} 个")
    
    # 处理每个文件
    results = {
        'created': [],
        'merged': [],
        'fragment': [],
        'error': [],
        'skipped': []
    }
    
    for i, file_info in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 处理: {file_info['path'][:60]}...")
        
        try:
            result = process_file(file_info)
            results[result['status']].append(result)
            
            if result['status'] in ['created', 'merged']:
                print(f"  ✅ Wiki 页面: {result.get('wiki_page', 'N/A')}")
            elif result['status'] == 'fragment':
                print(f"  📝 追加到 fragments.md")
            else:
                print(f"  ⚠️ {result.get('message', 'skipped')}")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            results['error'].append({'path': file_info['path'], 'message': str(e)})
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("处理完成汇总")
    print("=" * 60)
    
    print(f"\n📊 处理结果:")
    print(f"  ✅ 新建 Wiki 页面: {len(results['created'])} 个")
    print(f"  🔄 合并到现有页面: {len(results['merged'])} 个")
    print(f"  📝 追加到碎片笔记: {len(results['fragment'])} 个")
    print(f"  ⚠️ 跳过: {len(results['skipped'])} 个")
    print(f"  ❌ 错误: {len(results['error'])} 个")
    
    print(f"\n📁 创建的 Wiki 页面:")
    for r in results['created']:
        print(f"  - {r.get('wiki_page', 'N/A')}")
    
    # 重新生成 unprocessed.log
    regenerate_unprocessed_log(files)
    
    print(f"\n⏳ 剩余待处理文件: 查看更新后的 unprocessed.log")
    
    return results

def regenerate_unprocessed_log(processed_files):
    """重新生成 unprocessed.log，排除已处理文件"""
    if not UNPROCESSED_LOG.exists():
        return
    
    content = UNPROCESSED_LOG.read_text(encoding='utf-8')
    
    # 提取所有未处理文件
    all_files = []
    for line in content.split('\n'):
        if 'raw/' in line and '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                path = parts[1].strip()
                if path.startswith('raw/'):
                    all_files.append(line)
    
    # 排除已处理
    processed_paths = {f['path'] for f in processed_files}
    remaining = [l for l in all_files if l.split('|')[1].strip() not in processed_paths]
    
    # 更新统计
    type_counts = {}
    for line in remaining:
        parts = line.split('|')
        if len(parts) >= 3:
            t = parts[2].strip()
            type_counts[t] = type_counts.get(t, 0) + 1
    
    # 重写文件
    new_content = f"""# Unprocessed Files Log

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 分类统计

- 无frontmatter文章: {type_counts.get('无frontmatter文章', 0)} 个
- 完整文章: {type_counts.get('完整文章', 0)} 个
- 碎片笔记: {type_counts.get('碎片笔记', 0)} 个
- 短笔记: {type_counts.get('短笔记', 0)} 个

总数: {len(remaining)} 个

## 文件列表

| 相对路径 | 类型 | 正文长度 | 标题 |
|----------|------|----------|------|
"""
    new_content += '\n'.join(remaining)
    
    UNPROCESSED_LOG.write_text(new_content, encoding='utf-8')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch Wiki Ingest")
    parser.add_argument("--limit", type=int, default=50, help="处理文件数量限制")
    
    args = parser.parse_args()
    batch_process(args.limit)