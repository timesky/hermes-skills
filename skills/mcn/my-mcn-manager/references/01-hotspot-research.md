---
module: 01-hotspot-research
type: reference
source: mcn-hotspot-aggregator (整合)
---

# 模块 1: 热点调研

自动抓取多平台热搜/热榜，保存到知识库 tmp 目录。

---

## 支持平台

| 平台 | OpenCLI 命令 | 输出格式 |
|------|-------------|----------|
| 知乎 | `opencli zhihu hot` | JSON (rank, title, heat, answers, url) |
| 微博 | `opencli weibo hot` | JSON (rank, word, hot_value, category, url) |
| 抖音 | `opencli douyin hot` | JSON |
| 虎嗅 | web 搜索 | 需用 web_search |
| 掘金 | web 搜索 | 需用 web_search |

---

## 配置

路径：`~/.hermes/mcn_config.yaml`

```yaml
hotspot:
  domains:
    - name: 科技
      keywords: [科技，数码，手机，AI, 互联网]
      platforms: [weibo, zhihu, toutiao, huxiu]
      top_n: 10
    - name: 编程
      keywords: [编程，代码，开发，程序员]
      platforms: [zhihu, juejin]
      top_n: 10
  
  platforms:
    weibo:
      enabled: true
      command: "opencli weibo hot --limit {limit} --format json"
    zhihu:
      enabled: true
      command: "opencli zhihu hot --limit {limit} --format json"
```

---

## 执行流程

### 1. 检查 OpenCLI 状态

```bash
source ~/.nvm/nvm.sh && nvm use 22
opencli doctor  # 期望：[OK] Extension: connected
```

### 2. 抓取热搜

```python
import subprocess
import json

def fetch_hotspot(platform: str, limit: int = 20) -> list:
    """抓取指定平台热搜"""
    cmd = f"source ~/.nvm/nvm.sh && nvm use 22 && opencli {platform} hot --limit {limit} --format json"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # 提取 JSON（跳过 nvm 提示）
    lines = result.stdout.strip().split('\n')
    for i, line in enumerate(lines):
        if line.startswith('['):
            json_str = '\n'.join(lines[i:])
            break
    
    return json.loads(json_str)
```

### 3. 保存到知识库

```python
import datetime
import os

KB_ROOT = "/Users/timesky/backup/知识库-Obsidian"
HOTSPOT_DIR = f"{KB_ROOT}/tmp/hotspot"

def save_hotspot(platform: str, data: list) -> str:
    """保存热搜到知识库"""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    os.makedirs(f"{HOTSPOT_DIR}/{date_str}", exist_ok=True)
    
    # 生成 Markdown
    md = f"""---
created: {time_str}
platform: {platform}
status: pending
type: hotspot
---

# {date_str} {platform} 热搜榜

## Top {len(data)}

| 排名 | 标题 | 热度 | 链接 |
|------|------|------|------|
"""
    
    for item in data:
        rank = item.get('rank', item.get('position', '?'))
        title = item.get('title', item.get('word', '?'))
        heat = item.get('heat', item.get('hot_value', '?'))
        url = item.get('url', '')
        md += f"| {rank} | {title} | {heat} | [查看]({url}) |\n"
    
    # 写入文件
    filename = f"{HOTSPOT_DIR}/{date_str}/{platform}-hotspot.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return filename
```

---

## 输出目录

```
tmp/hotspot/YYYY-MM-DD/
├── weibo-hotspot.md
├── zhihu-hotspot.md
├── toutiao-hotspot.md
└── ...
```

---

## Pitfalls

1. **OpenCLI 必须激活**：`source ~/.nvm/nvm.sh && nvm use 22`
2. **JSON 解析**：跳过 nvm 提示行
3. **平台限制**：头条热榜可能返回空数据（用 web_search 替代）
4. **微博内容**：需要登录才能获取详情（用 web_search + web_extract）

---

*整合自：mcn-hotspot-aggregator*
