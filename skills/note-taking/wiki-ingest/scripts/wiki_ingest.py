#!/usr/bin/env python3
"""
Wiki Ingest Script - 增量式处理

扫描 raw 目录所有子目录，将源文件转换为 wiki 结构化内容。
处理所有文件，包括无 frontmatter 和内容过短的文件。

用法：
python3 wiki_ingest.py --status     # 查看处理状态
python3 wiki_ingest.py --file <路径>  # 单个文件处理
python3 wiki_ingest.py --batch      # 批量处理
python3 wiki_ingest.py --dry-run    # 预览模式
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import re

# 配置
KB_ROOT = Path(os.environ.get('KB_ROOT', "/Users/timesky/backup/知识库-Obsidian"))
RAW_DIR = KB_ROOT / "raw"  # 扫描整个 raw 目录
WIKI_DIR = KB_ROOT / "wiki"
PROCESSED_LOG = WIKI_DIR / "processed.log"
UNPROCESSED_LOG = WIKI_DIR / "unprocessed.log"
INDEX_MD = WIKI_DIR / "index.md"
LOG_MD = WIKI_DIR / "log.md"
DUPLICATE_MD = WIKI_DIR / "duplicates.md"

# 缓存消息特征（无效内容）
CACHE_MESSAGES = [
    "File hasn't been modified since last read",
    "The content from the earlier read_file result",
    "result_stale",
]

# 排除目录
EXCLUDE_DIRS = ["assets", ".backup"]


def validate_file_content(filepath):
    """验证文件内容，返回 (is_valid, reason, content_info)"""
    if not filepath.exists():
        return False, "文件不存在", None
    
    size = filepath.stat().st_size
    if size == 0:
        return False, "文件大小为 0", None
    
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"读取失败: {e}", None
    
    # 检查是否是缓存消息（无效）
    for msg in CACHE_MESSAGES:
        if msg in content:
            return False, "文件内容是缓存消息", None
    
    # 检查 frontmatter
    has_frontmatter = content.strip().startswith('---')
    
    # 提取正文（去掉 frontmatter）
    if has_frontmatter:
        parts = content.split('---', 2)
        body = parts[2] if len(parts) >= 3 else ""
    else:
        body = content
    
    body_length = len(body.strip())
    
    # 所有文件都需要处理，只是分类不同
    content_info = {
        'size': size,
        'has_frontmatter': has_frontmatter,
        'body_length': body_length,
        'title': extract_title(filepath, content),
        'type': classify_file(has_frontmatter, body_length, size)
    }
    
    return True, "需要处理", content_info


def extract_title(filepath, content):
    """从文件名或内容提取标题"""
    # 尝试从 frontmatter 提取
    if content.strip().startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 2:
            frontmatter = parts[1]
            for line in frontmatter.split('\n'):
                if line.startswith('title:'):
                    return line.split(':', 1)[1].strip()
    
    # 使用文件名作为标题
    return filepath.stem


def classify_file(has_frontmatter, body_length, size):
    """分类文件类型"""
    if has_frontmatter and body_length >= 200:
        return "完整文章"
    elif has_frontmatter and body_length < 200:
        return "短笔记"
    elif not has_frontmatter and body_length >= 200:
        return "无frontmatter文章"
    else:
        return "碎片笔记"


def scan_raw_directory():
    """扫描 raw 目录所有子目录"""
    all_files = []
    
    for subdir in RAW_DIR.iterdir():
        if subdir.is_dir() and subdir.name not in EXCLUDE_DIRS:
            for md_file in subdir.rglob("*.md"):
                all_files.append(md_file)
    
    return all_files


def load_processed_log():
    """加载已处理文件列表"""
    processed = set()
    if not PROCESSED_LOG.exists():
        return processed
    
    content = PROCESSED_LOG.read_text(encoding='utf-8')
    for line in content.split('\n'):
        # 匹配表格格式：| raw/xxx/... | 日期 | ... |
        if 'raw/' in line and '|' in line:
            parts = line.split('|')
            for part in parts:
                if 'raw/' in part:
                    path_str = part.strip()
                    if path_str.startswith('raw/'):
                        processed.add(path_str)
                    break
    
    return processed


def get_relative_path(filepath):
    """获取相对于 KB_ROOT 的路径"""
    return str(filepath.relative_to(KB_ROOT))


def check_status():
    """检查处理状态"""
    print("=" * 60)
    print("Wiki Ingest 状态检查")
    print("=" * 60)
    
    # 1. 扫描 raw 目录
    all_files = scan_raw_directory()
    print(f"\n📚 raw 目录文件总数: {len(all_files)}")
    
    # 2. 按子目录统计
    subdir_stats = {}
    for f in all_files:
        rel_path = get_relative_path(f)
        subdir = rel_path.split('/')[1]  # raw/xxx/...
        subdir_stats[subdir] = subdir_stats.get(subdir, 0) + 1
    
    print("\n📊 各子目录统计:")
    for subdir, count in sorted(subdir_stats.items(), key=lambda x: -x[1]):
        print(f"  {subdir}: {count} 个文件")
    
    # 3. 加载已处理列表
    processed = load_processed_log()
    print(f"\n✅ 已处理文件: {len(processed)} 个")
    
    # 4. 分析所有文件
    unprocessed = []
    processed_files = []
    by_type = {}
    
    for f in all_files:
        rel_path = get_relative_path(f)
        is_valid, reason, content_info = validate_file_content(f)
        
        if rel_path in processed:
            processed_files.append((f, rel_path, content_info))
        elif is_valid and content_info:
            file_type = content_info['type']
            by_type[file_type] = by_type.get(file_type, 0) + 1
            unprocessed.append((f, rel_path, content_info))
    
    # 5. 显示分类统计
    print("\n📋 未处理文件分类:")
    for file_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {file_type}: {count} 个")
    
    print(f"\n⏳ 未处理文件总数: {len(unprocessed)} 个")
    
    # 6. 显示未处理列表（按类型分组）
    if unprocessed:
        print("\n未处理文件列表（前30个）:")
        
        # 按类型分组显示
        grouped = {}
        for f, rel_path, info in unprocessed:
            t = info['type']
            if t not in grouped:
                grouped[t] = []
            grouped[t].append((rel_path, info))
        
        for file_type in ["完整文章", "无frontmatter文章", "短笔记", "碎片笔记"]:
            if file_type in grouped:
                print(f"\n【{file_type}】")
                for rel_path, info in grouped[file_type][:10]:
                    print(f"  {rel_path} ({info['body_length']}字)")
    
    # 7. 保存未处理列表
    save_unprocessed_log(unprocessed, by_type)
    
    return {
        'total': len(all_files),
        'processed': len(processed),
        'unprocessed': len(unprocessed),
        'by_type': by_type,
        'subdir_stats': subdir_stats
    }


def save_unprocessed_log(unprocessed, by_type):
    """保存未处理列表"""
    with open(UNPROCESSED_LOG, 'w', encoding='utf-8') as f:
        f.write("# Unprocessed Files Log\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        f.write("## 分类统计\n\n")
        for file_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            f.write(f"- {file_type}: {count} 个\n")
        
        f.write(f"\n总数: {len(unprocessed)} 个\n\n")
        
        f.write("## 文件列表\n\n")
        f.write("| 相对路径 | 类型 | 正文长度 | 标题 |\n")
        f.write("|----------|------|----------|------|\n")
        
        for filepath, rel_path, info in unprocessed:
            f.write(f"| {rel_path} | {info['type']} | {info['body_length']} | {info['title']} |\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wiki Ingest Script")
    parser.add_argument("--file", type=str, help="单个文件路径")
    parser.add_argument("--batch", action="store_true", help="批量处理")
    parser.add_argument("--status", action="store_true", help="查看处理状态")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    
    args = parser.parse_args()
    
    if args.status:
        check_status()
    
    elif args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"❌ 文件不存在: {filepath}")
            return
        
        is_valid, reason, info = validate_file_content(filepath)
        print(f"文件: {filepath}")
        print(f"状态: {reason}")
        if info:
            print(f"类型: {info['type']}")
            print(f"正文长度: {info['body_length']}字")
            print(f"标题: {info['title']}")
    
    elif args.batch:
        print("批量处理模式（待实现）")
        print("建议：使用 Luna agent 执行 ingest 任务")
    
    else:
        # 默认显示状态
        check_status()


if __name__ == "__main__":
    main()