#!/usr/bin/env python3
"""
Wiki Curator - 定时整理知识库 tmp 目录的脚本

完整流程：
1. 扫描 tmp 目录中的 pending 文件
2. 分析内容价值（基于原文指标 + 引用次数 + 用户标记 + LLM评估）
3. 有价值 → 移入 raw/sources/ → 输出待 ingest 列表
4. 无价值 → 删除 → 记录到 wiki/delete.log
5. 超过7天 → 自动删除 → 记录到 wiki/delete.log

评估权重：
- 原文指标（阅读/点赞/收藏）：30%
- 对话引用次数：20%
- 用户明确表示有价值：30%
- LLM 内容质量评估：20%

输出会注入到 cronjob 的 prompt 中，由 LLM 决定具体操作并执行 ingest。
"""

import os
import sys
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

KB_ROOT = Path("/Users/timesky/backup/知识库-Obsidian")
TMP_DIR = KB_ROOT / "tmp"
RAW_SOURCES = KB_ROOT / "raw" / "sources"
WIKI_DIR = KB_ROOT / "wiki"
DELETE_LOG = WIKI_DIR / "delete.log"
RAW_LOG = KB_ROOT / "logs" / "raw.log"

def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    RAW_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    with open(RAW_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    
    print(log_entry)


def append_delete_log(file_info: dict, reason: str):
    """追加删除记录到 delete.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    entry = f"""
## [{timestamp}] 删除记录

**文件**: `{file_info.get('path', 'unknown')}`
**来源**: {file_info.get('source', 'unknown')}
**标题**: {file_info.get('title', 'unknown')}
**删除原因**: {reason}
**评估分数**: {file_info.get('total_score', 'N/A')}
**删除时间**: {timestamp}

---
"""
    
    DELETE_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    if not DELETE_LOG.exists():
        DELETE_LOG.write_text("# Delete Log\n\n知识库删除记录，append-only。\n\n---\n", encoding="utf-8")
    
    with open(DELETE_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def parse_indicators(content):
    """解析原文指标"""
    indicators = {
        'views': 0,
        'likes': 0,
        'favorites': 0
    }
    
    views_match = re.search(r'阅读量[:\s]+(\d+)(万)?', content)
    if views_match:
        num = int(views_match.group(1))
        if views_match.group(2):
            num *= 10000
        indicators['views'] = num
    
    likes_match = re.search(r'点赞(?:数)?[:\s]+(\d+)', content)
    if likes_match:
        indicators['likes'] = int(likes_match.group(1))
    
    fav_match = re.search(r'收藏(?:数)?[:\s]+(\d+)', content)
    if fav_match:
        indicators['favorites'] = int(fav_match.group(1))
    
    return indicators


def calculate_indicator_score(indicators):
    """计算指标分数（权重30%，满分3分）"""
    score = 0
    
    if indicators['views'] >= 10000:
        score += 1.5
    elif indicators['views'] >= 1000:
        score += 0.75
    
    if indicators['likes'] >= 100:
        score += 0.75
    
    if indicators['favorites'] >= 50:
        score += 0.75
    
    return min(score, 3.0)


def scan_tmp_files():
    """扫描 tmp 目录中的所有文件"""
    files = []
    
    if not TMP_DIR.exists():
        return files
    
    for date_dir in TMP_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        if date_dir.name.startswith('_'):  # 跳过 _to_delete 等特殊目录
            continue
        
        for md_file in date_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        fm = parts[1]
                        body = parts[2]
                        
                        metadata = {}
                        for line in fm.strip().split('\n'):
                            if ':' in line:
                                key, val = line.split(':', 1)
                                metadata[key.strip()] = val.strip()
                        
                        indicators = parse_indicators(body)
                        indicator_score = calculate_indicator_score(indicators)
                        
                        created = metadata.get('created', '')
                        age_hours = 0
                        if created:
                            try:
                                created_dt = datetime.strptime(created.split()[0], "%Y-%m-%d")
                                age_hours = (datetime.now() - created_dt).total_seconds() / 3600
                            except:
                                pass
                        
                        title_match = re.search(r'^#\s+(.+)$', body)
                        title = title_match.group(1) if title_match else md_file.stem
                        
                        files.append({
                            'path': str(md_file),
                            'relative_path': str(md_file.relative_to(KB_ROOT)),
                            'filename': md_file.name,
                            'date_dir': date_dir.name,
                            'status': metadata.get('status', 'pending'),
                            'created': created,
                            'age_hours': round(age_hours, 1),
                            'age_days': round(age_hours / 24, 1),
                            'source': metadata.get('source', 'unknown'),
                            'session_id': metadata.get('session_id', ''),
                            'tags': metadata.get('tags', ''),
                            'title': title,
                            'indicators': indicators,
                            'indicator_score': round(indicator_score, 2),
                            'content_preview': body.strip()[:500] if body else '',
                            'content': body
                        })
            except Exception as e:
                files.append({
                    'path': str(md_file),
                    'relative_path': str(md_file.relative_to(KB_ROOT)),
                    'error': str(e),
                    'status': 'error'
                })
    
    return files


def analyze_value(file_info):
    """分析内容价值，计算总分"""
    scores = {
        'indicator': 0,
        'reference': 0,
        'user_mark': 0,
        'content': 0
    }
    
    age = file_info.get('age_hours', 0)
    source = file_info.get('source', '')
    content = file_info.get('content', '')
    title = file_info.get('title', '')
    
    # 过期检查（超过7天）
    if age > 168:
        return 'delete_expired', f'超过{round(age/24)}天未处理', scores
    
    # 新文件（等待观察）
    if age < 2:
        return 'wait', '新文件，等待下次整理', scores
    
    # 指标分数（30%）
    scores['indicator'] = file_info.get('indicator_score', 0)
    
    # 用户标记检查（30%）
    user_mark_patterns = [
        '用户明确表示有价值',
        '保存原因: 用户要求',
        '标记保留',
        '重要内容',
        '必须保留'
    ]
    if any(p in content for p in user_mark_patterns):
        scores['user_mark'] = 3.0
    
    # 内容质量关键词（20%）
    important_keywords = ['AI', 'LLM', 'GPT', 'Claude', 'model', 'API', 
                          '投资', '理财', '研究', '论文', 'arxiv', 
                          '最佳实践', '教程', '指南', '深度分析',
                          'Karpathy', '方法论', '架构', '设计']
    combined = f"{title} {content}".lower()
    keywords_found = [k for k in important_keywords if k.lower() in combined]
    if len(keywords_found) >= 3:
        scores['content'] = 2.0
    elif len(keywords_found) >= 1:
        scores['content'] = 1.0
    
    # 引用分数（20%）- 需要 LLM 后续查询 session_search
    scores['reference'] = 0
    
    # 计算总分
    total = sum(scores.values())
    file_info['total_score'] = round(total, 2)
    file_info['scores'] = scores
    
    # 判断
    if total >= 5:
        return 'keep', f'总分{total}（指标{scores["indicator"]}+用户{scores["user_mark"]}+内容{scores["content"]}）', scores
    elif total < 2:
        return 'delete_low', f'分数过低 ({total})', scores
    else:
        return 'evaluate', f'需要LLM评估，当前分数 {total}', scores


def validate_file_content(filepath: Path) -> tuple:
    """
    验证文件内容是否有效
    
    返回：(is_valid, error_message)
    """
    if not filepath.exists():
        return False, "文件不存在"
    
    if filepath.stat().st_size == 0:
        return False, "文件大小为 0"
    
    if filepath.stat().st_size < 100:
        return False, f"文件过小 ({filepath.stat().st_size} bytes)，可能是 placeholder"
    
    content = filepath.read_text(encoding='utf-8')
    
    # 检查是否是缓存消息
    cache_messages = [
        "File unchanged since last read",
        "The content from the earlier read_file result",
    ]
    
    if any(msg in content for msg in cache_messages):
        return False, "文件内容是缓存消息（错误写入）"
    
    # 检查是否有实际内容（至少有一个#标题）
    if not content.strip().startswith('---'):
        return False, "文件格式不正确（无 frontmatter）"
    
    # 检查正文字数
    parts = content.split('---', 2)
    if len(parts) < 3 or len(parts[2].strip()) < 50:
        return False, "正文内容过短"
    
    return True, "验证通过"


def move_to_raw_with_validation(file_info: dict) -> tuple:
    """
    移动文件到 raw，带内容验证
    
    如果验证失败，尝试从 tmp 恢复原始内容
    """
    src_path = Path(file_info['path'])
    dst_path = RAW_SOURCES / file_info['date_dir'] / file_info['filename']
    
    # Step 1: 验证源文件
    is_valid, error_msg = validate_file_content(src_path)
    
    if not is_valid:
        print(f"⚠️ 源文件验证失败：{file_info['relative_path']} - {error_msg}")
        # 尝试从 tmp 的其他位置恢复
        # （这里可以添加恢复逻辑）
        return False, error_msg
    
    # Step 2: 确保目标目录存在
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Step 3: 复制文件（使用 shutil.copy2 保留元数据）
    shutil.copy2(src_path, dst_path)
    
    # Step 4: 验证目标文件
    is_valid, error_msg = validate_file_content(dst_path)
    if not is_valid:
        print(f"❌ 目标文件验证失败：{dst_path} - {error_msg}")
        return False, error_msg
    
    print(f"✅ 移动成功：{file_info['relative_path']} → {dst_path.relative_to(KB_ROOT)}")
    return True, "移动成功"


def main():
    """主函数"""
    files = scan_tmp_files()
    
    by_action = {
        'keep': [],
        'delete_expired': [],
        'delete_low': [],
        'evaluate': [],
        'wait': [],
        'error': []
    }
    
    for f in files:
        if f.get('status') == 'error':
            by_action['error'].append(f)
        else:
            action, reason, scores = analyze_value(f)
            f['recommendation'] = action
            f['reason'] = reason
            f['scores'] = scores
            by_action[action].append(f)
    
    # 输出报告
    print("## Wiki Curator Report\n")
    print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    print(f"总计文件: {len(files)} 个\n")
    
    print("### 评估权重\n")
    print("| 维度 | 权重 | 说明 |")
    print("|------|------|------|")
    print("| 原文指标 | 30% | 阅读/点赞/收藏 |")
    print("| 对话引用 | 20% | session_search 查询 |")
    print("| 用户标记 | 30% | 明确表示有价值 |")
    print("| 内容质量 | 20% | 关键词检测 |")
    print()
    
    print("---\n")
    
    # 建议保留（移入 raw）
    if by_action['keep']:
        print("### 建议保留 → 移入 raw/sources/\n")
        print("以下文件建议移入 `raw/sources/YYYY-MM-DD/`，移入后请执行 ingest：\n")
        
        moved_count = 0
        for f in by_action['keep']:
            # 验证并移动
            success, msg = move_to_raw_with_validation(f)
            if success:
                moved_count += 1
                print(f"- `{f['relative_path']}`")
                print(f"  - 标题：{f['title']}")
                print(f"  - 总分：{f['total_score']}")
                print(f"  - 原文指标：阅读 {f['indicators']['views']}, 点赞 {f['indicators']['likes']}, 收藏 {f['indicators']['favorites']}")
                print(f"  - 移入目标：`raw/sources/{f['date_dir']}/{f['filename']}`")
                print()
            else:
                print(f"❌ `{f['relative_path']}` 移动失败：{msg}")
                print()
        
        print(f"\n**成功移动：{moved_count}/{len(by_action['keep'])}**\n")
        
        if moved_count > 0:
            print("**Ingest 指令**：\n")
            print("移入 raw 后，对每个新文件执行 ingest：")
            print("- 读取源文件 → 提取实体/概念 → 创建 wiki 页面 → 更新 index.md → 追加 log.md → 追加 processed.log")
            print()
    
    # 过期删除
    if by_action['delete_expired']:
        print("### 过期删除（超过7天）\n")
        print("以下文件超过7天未处理，自动删除并记录到 delete.log：\n")
        
        for f in by_action['delete_expired']:
            print(f"- `{f['relative_path']}` ({round(f['age_hours']/24)}天)")
            # 记录到 delete.log
            append_delete_log(f, f['reason'])
            # 实际删除
            try:
                Path(f['path']).unlink()
                print(f"  ✅ 已删除并记录")
            except Exception as e:
                print(f"  ❌ 删除失败: {e}")
        print()
    
    # 低分删除
    if by_action['delete_low']:
        print("### 低分删除\n")
        print("以下文件评估分数过低，建议删除：\n")
        
        for f in by_action['delete_low']:
            print(f"- `{f['relative_path']}`")
            print(f"  - 总分: {f['total_score']}")
            print(f"  - 原因: {f['reason']}")
            print(f"  - 请确认是否删除，删除后记录到 delete.log")
        print()
    
    # 需要评估
    if by_action['evaluate']:
        print("### 需要LLM评估\n")
        print("以下文件需要你进一步评估（执行 session_search 查询引用次数）：\n")
        
        for f in by_action['evaluate']:
            print(f"**文件**: `{f['relative_path']}`")
            print(f"- Session ID: `{f['session_id']}`")
            print(f"- 当前分数: {f['total_score']}")
            print(f"- 标题: {f['title']}")
            print(f"- 原文指标: 阅读 {f['indicators']['views']}, 点赞 {f['indicators']['likes']}, 收藏 {f['indicators']['favorites']}")
            print(f"- 内容预览:")
            print(f"  ```")
            print(f"  {f['content_preview'][:200]}...")
            print(f"  ```")
            print(f"- **操作**: 执行 `session_search(query='{f['session_id']}')` 查询引用次数")
            print(f"  - 每引用一次 +1分，上限 2分")
            print(f"  - 新总分 >= 5 → 保留")
            print(f"  - 新总分 < 3 → 删除")
            print()
    
    # 新文件等待
    if by_action['wait']:
        print("### 新文件（等待下次整理）\n")
        for f in by_action['wait']:
            print(f"- `{f['relative_path']}` ({f['age_hours']}小时)")
        print()
    
    # 错误文件
    if by_action['error']:
        print("### 读取错误\n")
        for f in by_action['error']:
            print(f"- `{f['relative_path']}`: {f['error']}")
        print()
    
    # 输出 JSON
    print("---\n")
    print("### 详细数据 (JSON)\n")
    print("```json")
    print(json.dumps(by_action, ensure_ascii=False, indent=2))
    print("```")
    
    # 输出操作指令
    print("\n---\n")
    print("## 操作指令\n")
    
    if by_action['keep']:
        print("\n### 1. 移入 raw 并 ingest\n")
        print("```python")
        print("# 移入 raw")
        for f in by_action['keep']:
            print(f"# shutil.move('{f['path']}', '{RAW_SOURCES}/{f['date_dir']}/{f['filename']}')")
        print("\n# 执行 ingest")
        print("# 对每个新文件：读取 → 提取实体/概念 → 创建 wiki 页面 → 更新 index.md → 追加 log.md")
        print("```")
    
    if by_action['delete_low']:
        print("\n### 2. 确认删除低分文件\n")
        print("请确认以下文件是否删除，删除后记录到 delete.log：")
        for f in by_action['delete_low']:
            print(f"- `{f['relative_path']}`")
    
    if by_action['evaluate']:
        print("\n### 3. 评估需要查询的文件\n")
        print("执行 session_search 补充引用分数后决定保留或删除")


if __name__ == "__main__":
    main()