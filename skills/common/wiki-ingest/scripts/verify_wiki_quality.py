#!/usr/bin/env python3
"""
Wiki Ingest 硬指标验证脚本

验证标准:
1. 所有 raw 文件都已处理（processed.log 记录）
2. 所有 wiki 页面都有实质内容（文件大小 > 500 字节）

用法:
    python scripts/verify_wiki_quality.py
    python scripts/verify_wiki_quality.py --verbose
"""

from pathlib import Path
import re
import argparse

KB_ROOT = Path("/Users/hy_timesky/Documents/My_Obsidian")
RAW_DIR = KB_ROOT / "raw"
WIKI_DIR = KB_ROOT / "wiki"
PROC_LOG = WIKI_DIR / "processed.log"


def get_raw_files():
    """获取所有 raw 文件路径"""
    raw_files = list(RAW_DIR.glob("**/*.md"))
    raw_files = [f for f in raw_files if "assets" not in str(f)]
    raw_paths = set()
    for f in raw_files:
        try:
            rel_path = f.relative_to(KB_ROOT / "raw")
            raw_paths.add(str(rel_path))
        except:
            pass
    return raw_paths


def get_processed_files():
    """从 processed.log 提取已处理文件"""
    processed = set()
    if PROC_LOG.exists():
        content = PROC_LOG.read_text()
        for line in content.split('\n'):
            if '|' in line and '.md' in line:
                # 使用 [^|] 匹配直到管道符（处理含空格/中文路径）
                match = re.search(r'\| raw/([^\|]+\.md)', line)
                if match:
                    processed.add(match.group(1).strip())
    return processed


def get_wiki_pages():
    """获取所有 wiki 页面"""
    pages = []
    entities_dir = WIKI_DIR / "entities"
    concepts_dir = WIKI_DIR / "concepts"
    
    if entities_dir.exists():
        pages.extend(list(entities_dir.glob("**/*.md")))
    if concepts_dir.exists():
        pages.extend(list(concepts_dir.glob("**/*.md")))
    
    return pages


def validate():
    """执行完整验证"""
    print("=" * 60)
    print("Wiki Ingest 硬指标验证")
    print("=" * 60)
    
    # 1. Raw 文件处理检查
    raw_paths = get_raw_files()
    processed = get_processed_files()
    unprocessed = raw_paths - processed
    
    print(f"\n📊 Raw 文件统计:")
    print(f"   总文件数: {len(raw_paths)}")
    print(f"   已处理: {len(processed & raw_paths)}")
    print(f"   未处理: {len(unprocessed)}")
    
    # 2. Wiki 页面质量检查（使用文件大小）
    wiki_pages = get_wiki_pages()
    valid_pages = 0
    incomplete_pages = []
    
    for page in wiki_pages:
        file_size = page.stat().st_size
        if file_size > 500:
            valid_pages += 1
        else:
            incomplete_pages.append({
                'name': page.name,
                'size': file_size
            })
    
    print(f"\n📊 Wiki 页面质量:")
    print(f"   总页面数: {len(wiki_pages)}")
    print(f"   有效页面 (>500字节): {valid_pages}")
    print(f"   不足页面: {len(incomplete_pages)}")
    
    # 3. 详细输出
    if incomplete_pages and args.verbose:
        print(f"\n⚠️ 不足页面详情:")
        for p in incomplete_pages[:10]:
            print(f"   - {p['name']}: {p['size']} 字节")
        if len(incomplete_pages) > 10:
            print(f"   ... 还有 {len(incomplete_pages) - 10} 个")
    
    # 4. 结论
    print("\n" + "=" * 60)
    all_passed = len(unprocessed) == 0 and len(incomplete_pages) == 0
    if all_passed:
        print("✅ 硬指标验证通过")
        return 0
    else:
        print(f"⚠️ 验证完成")
        print(f"   Raw 处理率: {len(processed & raw_paths)}/{len(raw_paths)}")
        print(f"   Wiki 有效率: {valid_pages}/{len(wiki_pages)} ({valid_pages*100//len(wiki_pages)}%)")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wiki Ingest 硬指标验证")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    args = parser.parse_args()
    
    exit(validate())
