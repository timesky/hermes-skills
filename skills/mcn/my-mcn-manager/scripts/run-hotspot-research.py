#!/usr/bin/env python3
"""
热点调研脚本 - 抓取多平台热搜
"""

import subprocess
import json
import os
import yaml
from datetime import datetime

MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
TASKS_DIR = f"{KB_ROOT}/tmp/tasks"

def load_config():
    with open(MCN_CONFIG) as f:
        return yaml.safe_load(f)

def fetch_hotspot(platform: str, limit: int = 20) -> list:
    config = load_config()
    platforms_cfg = config['hotspot']['platforms']
    
    if platform not in platforms_cfg:
        return []
    
    platform_cfg = platforms_cfg[platform]
    if not platform_cfg.get('enabled'):
        return []
    
    if 'command' not in platform_cfg or not platform_cfg['command']:
        return []
    
    cmd = platform_cfg['command'].format(limit=limit)
    cmd = f"source ~/.nvm/nvm.sh && nvm use 22 && {cmd}"
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    
    lines = result.stdout.strip().split('\n')
    for i, line in enumerate(lines):
        if line.startswith('['):
            json_str = '\n'.join(lines[i:])
            break
    
    try:
        return json.loads(json_str)
    except:
        return []

def save_hotspot(platform: str, data: list, date: str) -> str:
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    output_dir = f"{KB_ROOT}/tmp/hotspot/{date}"
    os.makedirs(output_dir, exist_ok=True)
    
    md = f"""---
created: {time_str}
platform: {platform}
---

# {date} {platform} 热搜榜

| 排名 | 标题 | 热度 | 链接 |
|------|------|------|------|
"""
    
    for item in data:
        rank = item.get('rank', '?')
        title = item.get('title', item.get('word', '?'))
        heat = item.get('heat', item.get('hot_value', '?'))
        url = item.get('url', '')
        md += f"| {rank} | {title} | {heat} | [查看]({url}) |\n"
    
    filename = f"{output_dir}/{platform}-hotspot.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return filename

# 执行调研
date = datetime.now().strftime("%Y-%m-%d")
print(f"=== 热点调研 - {date} ===\n")

config = load_config()
platforms_cfg = config['hotspot']['platforms']
platforms = [p for p, cfg in platforms_cfg.items() if cfg.get('enabled') and cfg.get('command')]

print(f"抓取平台：{', '.join(platforms)}\n")

results = []
for platform in platforms:
    data = fetch_hotspot(platform)
    if data:
        filename = save_hotspot(platform, data, date)
        results.append({'platform': platform, 'count': len(data)})
        print(f"✓ {platform}: {len(data)}条")

print(f"\n总计：{sum(r['count'] for r in results)}条")
print(f"输出目录：{KB_ROOT}/tmp/hotspot/{date}/")
