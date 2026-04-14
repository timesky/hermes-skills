#!/usr/bin/env python3
"""
MCN 完整工作流执行脚本

用法:
    python scripts/run-full-workflow.py              # 完整流程（需用户确认）
    python scripts/run-full-workflow.py --stage research  # 只调研
    python scripts/run-full-workflow.py --topic "主题名"  # 直接生成指定主题
"""

import sys
import os
import yaml
import json
import datetime
import subprocess

# 配置路径
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
WECHAT_CONFIG = os.path.expanduser("~/.hermes/wechat_mp_config.yaml")
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"

def load_config():
    """加载配置"""
    return yaml.safe_load(open(MCN_CONFIG))

def run_hotspot_research(date: str = None):
    """阶段 1: 热点调研"""
    print("\n=== 阶段 1: 热点调研 ===")
    
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    config = load_config()
    platforms = config['hotspot']['platforms']
    
    for platform_name, platform_cfg in platforms.items():
        if not platform_cfg.get('enabled'):
            continue
        
        print(f"\n抓取 {platform_name} 热搜...")
        cmd = platform_cfg['command'].format(limit=20)
        
        result = subprocess.run(
            f"source ~/.nvm/nvm.sh && nvm use 22 && {cmd}",
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # 保存结果
            output_dir = f"{KB_ROOT}/tmp/hotspot/{date}"
            os.makedirs(output_dir, exist_ok=True)
            
            # 提取 JSON
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                if line.startswith('['):
                    json_str = '\n'.join(lines[i:])
                    break
            
            data = json.loads(json_str)
            
            # 保存为 Markdown
            md_content = f"""---
created: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
platform: {platform_name}
status: pending
type: hotspot
---

# {date} {platform_name} 热搜榜

## Top {len(data)}

| 排名 | 标题 | 热度 | 链接 |
|------|------|------|------|
"""
            for item in data:
                rank = item.get('rank', item.get('position', '?'))
                title = item.get('title', item.get('word', '?'))
                heat = item.get('heat', item.get('hot_value', '?'))
                url = item.get('url', '')
                md_content += f"| {rank} | {title} | {heat} | [查看]({url}) |\n"
            
            filename = f"{output_dir}/{platform_name}-hotspot.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            print(f"✓ 保存：{filename}")
        else:
            print(f"✗ {platform_name} 抓取失败：{result.stderr[:100]}")
    
    print("\n✓ 热点调研完成")
    return True

def run_topic_analysis(date: str = None):
    """阶段 2: 选题分析"""
    print("\n=== 阶段 2: 选题分析 ===")
    
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    config = load_config()
    domains = config['hotspot']['domains']
    
    # 读取热搜数据
    hotspot_dir = f"{KB_ROOT}/tmp/hotspot/{date}"
    if not os.path.exists(hotspot_dir):
        print(f"✗ 热搜数据不存在：{hotspot_dir}")
        print("请先执行阶段 1：热点调研")
        return False
    
    print(f"读取 {hotspot_dir} 数据...")
    # TODO: 实现选题分析逻辑
    
    # 生成推荐报告
    output_dir = f"{KB_ROOT}/tmp/topic/{date}"
    os.makedirs(output_dir, exist_ok=True)
    
    report = f"""---
created: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
type: topic-recommend
status: pending
---

# MCN 选题分析报告

## 推荐主题

请查看热搜数据后手动选择主题，或等待自动分析完成。

## 下一步

确认主题后执行：`python scripts/run-full-workflow.py --topic "主题名"`
"""
    
    filename = f"{output_dir}/recommend.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ 选题报告：{filename}")
    return True

def run_content_generation(topic: str, style: str = 'professional'):
    """阶段 3: 内容生成"""
    print(f"\n=== 阶段 3: 内容生成 - 主题：{topic} ===")
    
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    output_dir = f"{KB_ROOT}/tmp/content/{date}"
    os.makedirs(output_dir, exist_ok=True)
    
    # TODO: 实现内容生成逻辑
    print("内容生成逻辑待实现...")
    return True

def run_publish(article_path: str):
    """阶段 4: 发布草稿"""
    print(f"\n=== 阶段 4: 发布草稿 - {article_path} ===")
    
    # TODO: 实现发布逻辑
    print("发布逻辑待实现...")
    return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='MCN 完整工作流')
    parser.add_argument('--stage', choices=['research', 'topic', 'content', 'publish'],
                       help='执行指定阶段')
    parser.add_argument('--topic', type=str, help='指定主题（跳过调研和选题）')
    parser.add_argument('--date', type=str, help='指定日期（默认今天）')
    parser.add_argument('--style', type=str, default='professional',
                       choices=['professional', 'casual', 'story'],
                       help='文章风格')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MCN Manager - 公众号全自动工作流")
    print("=" * 60)
    
    if args.topic:
        # 直接生成指定主题
        run_content_generation(args.topic, args.style)
        # run_publish(...)
    elif args.stage:
        # 执行指定阶段
        if args.stage == 'research':
            run_hotspot_research(args.date)
        elif args.stage == 'topic':
            run_topic_analysis(args.date)
        elif args.stage == 'content':
            print("请提供主题名：--topic '主题'")
        elif args.stage == 'publish':
            print("请提供文章路径：--article path/to/article.md")
    else:
        # 完整流程
        date = args.date or datetime.datetime.now().strftime("%Y-%m-%d")
        
        run_hotspot_research(date)
        run_topic_analysis(date)
        
        print("\n" + "=" * 60)
        print("✓ 阶段 1-2 完成")
        print("请查看选题报告并确认主题，然后执行:")
        print(f"  python scripts/run-full-workflow.py --topic '主题名'")
        print("=" * 60)

if __name__ == '__main__':
    main()
