#!/usr/bin/env python3
"""
Wiki Ingest Script - 增量式 ingest 流程

用法：
python3 wiki_ingest.py --file <源文件路径>    # 单个文件 ingest
python3 wiki_ingest.py --batch              # 批量 ingest
python3 wiki_ingest.py --dry-run            # 预览模式
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re

# 配置
KB_ROOT = Path(os.environ.get('KB_ROOT', "/Users/timesky/backup/知识库-Obsidian"))
RAW_SOURCES = KB_ROOT / "raw" / "sources"
WIKI_DIR = KB_ROOT / "wiki"
PROCESSED_LOG = WIKI_DIR / "processed.log"
INDEX_MD = WIKI_DIR / "index.md"
LOG_MD = WIKI_DIR / "log.md"

# 缓存消息特征
CACHE_MESSAGES = [
    "File unchanged since last read",
    "The content from the earlier read_file result",
]


def validate_file_content(filepath: Path) -> Tuple[bool, str]:
    """验证文件内容是否有效"""
    if not filepath.exists():
        return False, "文件不存在"
    
    size = filepath.stat().st_size
    if size == 0:
        return False, "文件大小为 0"
    
    if size < 1000:
        return False, f"文件过小 ({size} bytes)，可能是 placeholder"
    
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"读取失败：{e}"
    
    # 检查缓存消息
    if any(msg in content for msg in CACHE_MESSAGES):
        return False, "文件内容是缓存消息"
    
    # 检查 frontmatter
    if not content.strip().startswith('---'):
        return False, "文件格式不正确（无 frontmatter）"
    
    # 检查正文字数
    parts = content.split('---', 2)
    if len(parts) < 3 or len(parts[2].strip()) < 50:
        return False, "正文内容过短"
    
    return True, "验证通过"


def load_processed_log() -> set:
    """加载已处理文件列表"""
    processed = set()
    if not PROCESSED_LOG.exists():
        return processed
    
    content = PROCESSED_LOG.read_text(encoding='utf-8')
    for line in content.split('\n'):
        if 'raw/sources/' in line and '|' in line:
            parts = line.split('|')
            if len(parts) >= 1:
                path_str = parts[0].strip()
                if path_str.startswith('raw/sources/'):
                    processed.add(path_str)
    
    return processed


def update_index_md(new_pages: List[dict]):
    """
    增量更新 index.md
    
    使用 patch 添加新页面到索引表格，更新 Statistics
    """
    if not INDEX_MD.exists():
        print(f"⚠️  {INDEX_MD} 不存在，跳过更新")
        return
    
    content = INDEX_MD.read_text(encoding='utf-8')
    
    # 1. 更新 Statistics
    import re
    
    # 更新 page_count
    old_count_pattern = r'page_count: (\d+)'
    match = re.search(old_count_pattern, content)
    if match:
        old_count = int(match.group(1))
        new_count = old_count + len(new_pages)
        content = re.sub(old_count_pattern, f'page_count: {new_count}', content)
        print(f"  📊 更新 page_count: {old_count} → {new_count}")
    
    # 更新 Wiki 页面数
    old_stat_pattern = r'\*\*Wiki 页面数\*\*: (\d+)'
    match = re.search(old_stat_pattern, content)
    if match:
        old_count = int(match.group(1))
        new_count = old_count + len(new_pages)
        content = re.sub(old_stat_pattern, f'**Wiki 页面数**: {new_count}', content)
        print(f"  📊 更新 Wiki 页面数：{old_count} → {new_count}")
    
    # 2. 添加新页面到表格（简化处理，实际应该更智能）
    # 这里只是更新统计数字，具体页面添加需要手动或使用更复杂的逻辑
    
    INDEX_MD.write_text(content, encoding='utf-8')
    print(f"  ✅ 更新 index.md")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wiki Ingest Script")
    parser.add_argument("--file", type=str, help="单个文件路径")
    parser.add_argument("--batch", action="store_true", help="批量 ingest")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    
    args = parser.parse_args()
    
    print("="*60)
    print("Wiki Ingest Script")
    print("="*60)
    
    if args.file:
        # 单个文件 ingest
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"❌ 文件不存在：{filepath}")
            return
        
        is_valid, msg = validate_file_content(filepath)
        if not is_valid:
            print(f"❌ 文件验证失败：{msg}")
            return
        
        print(f"✅ 文件验证通过：{filepath}")
        print("   （后续处理逻辑待实现）")
        
    elif args.batch:
        # 批量 ingest（调用 batch_ingest.py）
        batch_script = Path(__file__).parent / "batch_ingest.py"
        if not batch_script.exists():
            print(f"❌ 批量脚本不存在：{batch_script}")
            return
        
        cmd = f"python3 {batch_script} {'--dry-run' if args.dry_run else '--execute'}"
        print(f"执行：{cmd}")
        os.system(cmd)
    
    else:
        print("请指定 --file <路径> 或 --batch")


if __name__ == "__main__":
    main()