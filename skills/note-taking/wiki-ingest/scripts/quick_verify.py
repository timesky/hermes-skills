#!/usr/bin/env python3
"""
Quick Wiki Ingest Verification - 快速验证硬指标

用法：
  python3 quick_verify.py           # 基本验证
  python3 quick_verify.py --verbose # 详细输出

验证内容：
  1. Raw 文件总数 vs Processed.log 记录数
  2. 未处理文件列表
  3. Wiki 页面数量统计
  4. 空 Wiki 页面检测
"""

from pathlib import Path
import re
import argparse

def get_kb_root():
    """自动检测 KB_ROOT"""
    import os
    kb_root = os.environ.get('KB_ROOT')
    if kb_root:
        return Path(kb_root)
    
    # 尝试常见路径
    candidates = [
        Path.home() / "Documents" / "My_Obsidian",
        Path.home() / "backup" / "知识库-Obsidian",
    ]
    for c in candidates:
        if c.exists():
            return c
    
    raise ValueError("无法检测 KB_ROOT，请设置环境变量")

def main(verbose=False):
    KB_ROOT = get_kb_root()
    RAW_DIR = KB_ROOT / "raw"
    PROC_LOG = KB_ROOT / "wiki" / "processed.log"
    WIKI_DIR = KB_ROOT / "wiki"
    ENTITIES_DIR = WIKI_DIR / "entities"
    CONCEPTS_DIR = WIKI_DIR / "concepts"
    
    print("=" * 60)
    print("Wiki Ingest 硬指标验证")
    print("=" * 60)
    print(f"\nKB_ROOT: {KB_ROOT}")
    
    # 1. 统计 raw 文件
    raw_files = list(RAW_DIR.glob("**/*.md"))
    raw_files = [f for f in raw_files if "assets" not in str(f)]
    print(f"\n📊 Raw 目录文件数: {len(raw_files)}")
    
    # 2. 读取 processed.log
    processed_files = set()
    if PROC_LOG.exists():
        content = PROC_LOG.read_text(encoding='utf-8')
        for line in content.split('\n'):
            if '|' in line and '.md' in line:
                match = re.search(r'\| raw/([^\|]+\.md)', line)
                if match:
                    rel_path = match.group(1).strip()
                    processed_files.add(rel_path)
    
    print(f"📊 Processed.log 记录数: {len(processed_files)}")
    
    # 3. 找未处理文件
    unprocessed = []
    for f in raw_files:
        try:
            rel_path = f.relative_to(RAW_DIR)
            rel_str = str(rel_path)
            if rel_str not in processed_files:
                unprocessed.append(rel_str)
        except:
            pass
    
    print(f"📊 未处理文件数: {len(unprocessed)}")
    
    if verbose and unprocessed:
        print("\n未处理文件列表:")
        for f in unprocessed[:20]:
            print(f"  - {f}")
        if len(unprocessed) > 20:
            print(f"  ... 还有 {len(unprocessed) - 20} 个")
    
    # 4. Wiki 页面统计
    entities = list(ENTITIES_DIR.glob("*.md")) if ENTITIES_DIR.exists() else []
    concepts = list(CONCEPTS_DIR.glob("*.md")) if CONCEPTS_DIR.exists() else []
    
    print(f"\n📊 Wiki 页面统计:")
    print(f"  Entities: {len(entities)} 个")
    print(f"  Concepts: {len(concepts)} 个")
    
    # 5. 空 Wiki 页面检测（文件大小 < 500 字节）
    if verbose:
        empty_pages = []
        for page in entities + concepts:
            size = len(page.read_text(encoding='utf-8'))
            if size < 500:
                empty_pages.append((page.name, size))
        
        if empty_pages:
            print(f"\n⚠️ 空 Wiki 页面 ({len(empty_pages)} 个):")
            for name, size in empty_pages[:10]:
                print(f"  - {name}: {size} 字节")
    
    # 6. 结论
    print("\n" + "=" * 60)
    if len(unprocessed) == 0:
        print("✅ 硬指标达标：未处理文件 = 0")
    else:
        print(f"❌ 硬指标未达标：还有 {len(unprocessed)} 个文件待处理")
    
    return len(unprocessed) == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick Wiki Verification")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    success = main(args.verbose)
    exit(0 if success else 1)