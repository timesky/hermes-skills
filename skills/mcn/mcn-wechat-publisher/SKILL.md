---
name: mcn-wechat-publisher
description: 公众号发布技能 - 通过浏览器自动化登录公众号后台，将改写后的文章发布为草稿
tags: [mcn, wechat, publisher, browser-automation]
version: 1.1.0
created: 2026-04-12
author: Luna
---

# 公众号发布技能

通过 OpenCLI browser 将文章发布到公众号草稿箱。

> ⚠️ **兼容性说明**
> - Hermes 内置 Playwright browser 不兼容 macOS 11.7（需要 macOS 12+）
> - OpenCLI browser 使用用户 Chrome，完全兼容 macOS 11.7
> - 推荐使用 OpenCLI browser 命令

---

## 知识库路径

```
KB_ROOT = /Users/timesky/backup/知识库-Obsidian
CONTENT_DIR = KB_ROOT/tmp/content/
PUBLISH_DIR = KB_ROOT/tmp/publish/
```

---

## ⚠️ 重要技术限制（2026-04-12 发现）

公众号编辑器使用**微信特定的 JSAPI**，标准自动化方法**全部失效**：

| 方法 | 结果 | 说明 |
|------|------|------|
| JS innerHTML/innerText | ❌ 不保存 | DOM 操作不触发服务器保存 |
| OpenCLI browser type | ❌ 不保存 | 输入到元素但服务器不保存 |
| UEditor.setContent | ❌ API 报错 | 语言文件未加载 |
| __MP_Editor_JSAPI__.invoke | ❌ 调用成功但内容不显示 | JSAPI 存在但未生效 |
| ClipboardEvent paste | ❌ 不生效 | 粘贴事件无法触发保存 |

**根本原因**：公众号编辑器内容保存依赖微信特定的 JSAPI 和事件监听，标准 DOM 操作无法触发。

---

## 可行方案

**方案 A：手动粘贴（推荐）**

1. 打开编辑器 URL
2. 用户点击正文区域
3. Ctrl+V 粚贴内容
4. 点击「保存为草稿」

**方案 B：使用公众号官方 API（推荐，如果有开发者权限）**

需要 AppID + AppSecret。用户 TimeSky 已确认有 key，可以使用此方案。

> 📋 详细工具评估报告：`/Users/timesky/backup/知识库-Obsidian/tmp/content/2026-04-12/微信公众号工具评估.md`

---

## ⚠️ 用户登录说明

公众号发布需要用户扫码登录，自动化部分有限：

工作流程：
1. 技能打开公众号后台，等待用户扫码
2. 用户扫码登录后
3. **标题/摘要可自动填写**（textarea/input 正常工作）
4. **正文需要用户手动粘贴**
5. **封面图需要从素材库选择**
6. 技能保存为草稿，等待用户确认发布

---

## ⭐ 新增流程：去AI化验证

发布前必须确认文章已经过 humanizer-zh 处理：

```python
def verify_humanization(article_path: str) -> bool:
    """验证文章是否已去AI化"""
    
    content = open(article_path).read()
    
    # 检查 humanizer-zh 的评分
    # 文件中应有评分记录：## Humanization Score: XX/50
    
    score_match = re.search(r'Humanization Score: (\d+)/50', content)
    
    if score_match:
        score = int(score_match.group(1))
        if score >= 45:
            return True
        else:
            print(f"⚠️ 去AI化评分不足：{score}/50，建议重新处理")
            return False
    else:
        print("⚠️ 文章未进行去AI化处理，请先使用 humanizer-zh")
        return False
```

---

## 配置文件位置

```yaml
# ~/.hermes/wechat_mp_config.yaml
appid: wx47533ce9c8854fb5
secret: 2b990fc5247bfb98b71dfe8ab038eb2f
author: TimeSky

# 封面提示词模板
cover_prompts:
  科技: "tech cover, blue gradient, minimalist, abstract shapes, clean design"
  商业: "business cover, dark blue, professional, corporate style, modern"
  生活: "lifestyle cover, warm colors, nature elements, soft, peaceful"
  热点: "news cover, bold colors, dynamic, modern, attention-grabbing"

# 文章风格模板
article_styles:
  科技: "专业、客观、数据驱动"
  商业: "深度分析、行业视角"
  生活: "轻松、实用、贴近日常"
  热点: "快速、观点鲜明、引发讨论"
```

---

## 推荐方案：使用 wechatpy SDK

配置已存在，推荐使用 wechatpy 进行 API 发布：

```python
#!/usr/bin/env python3
"""微信公众号文章发布脚本"""

import yaml
from pathlib import Path
from wechatpy import WeChatClient

# 读取配置
CONFIG_PATH = Path.home() / ".hermes" / "wechat_mp_config.yaml"
config = yaml.safe_load(CONFIG_PATH.read_text())

APPID = config['appid']
SECRET = config['secret']
AUTHOR = config['author']

client = WeChatClient(APPID, SECRET)

def publish_article(title, content_html, cover_path, digest=''):
    """发布文章到公众号草稿箱"""
    
    # 1. 上传封面图（永久素材）
    with open(cover_path, 'rb') as f:
        media = client.material.add('image', f)
        thumb_id = media['media_id']
    
    # 2. 创建草稿
    articles = [{
        'title': title,
        'author': AUTHOR,
        'content': content_html,
        'thumb_media_id': thumb_id,
        'digest': digest,
    }]
    draft_id = client.draft.add(articles)
    
    return {
        'draft_id': draft_id,
        'status': 'success'
    }

def get_article_stats(begin_date, end_date):
    """获取文章统计数据"""
    
    # 获取文章阅读数据
    datacube = client.datacube
    
    # 用户分析
    user_summary = datacube.get_user_summary(begin_date, end_date)
    
    # 文章分析
    article_summary = datacube.get_article_summary(begin_date, end_date)
    
    return {
        'users': user_summary,
        'articles': article_summary
    }
```

---

## 使用流程

### 1. 准备工作

```bash
# 检查 OpenCLI 状态
source ~/.nvm/nvm.sh && nvm use 22
opencli doctor
# 期望输出: [OK] Extension: connected
```

### 2. 实际执行命令（已验证可行）

```bash
# 打开编辑器（直接新建）
opencli browser open "https://mp.weixin.qq.com/cgi-bin/appmsg?t=appmsg/edit_v2&action=edit&isNew=1&type=77&token=TOKEN&lang=zh_CN"

# 等待加载（5-8秒）
sleep 5

# 查找元素索引
opencli browser state | grep -E "textarea|input|placeholder"

# 填写标题（索引 474）
opencli browser type 474 "文章标题"

# 填写作者（索引 475）
opencli browser type 475 "作者名"

# 填写摘要（索引 535）
opencli browser type 535 "摘要内容"

# 填写正文（使用 JS 操作编辑器）
# 编辑器索引: [498] contenteditable=true
```
    
    # 读取文章内容
    article = parse_article(article_path)
    
    # 打开公众号后台
    await browser_navigate("https://mp.weixin.qq.com")
    
    # 等待用户扫码登录
    print("请在浏览器中扫码登录公众号...")
    await wait_for_login()
    
    # 进入素材管理
    await browser_click("素材管理")
    
    # 新建图文消息
    await browser_click("新建图文")
    
    # 填写标题
    await browser_type("#title", article['title'])
    
    # 填写正文（使用编辑器）
    await fill_editor(article['content'])
    
    # 设置封面（可选）
    await set_cover(article['cover_url'])
    
    # 保存为草稿
    await browser_click("保存")
    
    print(f"文章已保存到草稿箱: {article['title']}")
    return {'status': 'draft', 'title': article['title']}
```

---

## 登录检测

```python
async def wait_for_login(timeout: int = 120):
    """等待用户扫码登录"""
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # 检查是否已登录
        snapshot = await browser_snapshot()
        
        # 登录成功标志：页面显示账号信息
        if "账号详情" in snapshot or "素材管理" in snapshot:
            return True
        
        # 等待 2 秒
        await asyncio.sleep(2)
    
    raise TimeoutError("登录超时，请重新执行")
```

---

## 编辑器填充

公众号使用富文本编辑器，**必须用 JS 操作**：

```javascript
// 保存到文件避免 shell 转义问题
var content = "<p>正文内容...</p>";
var editors = document.querySelectorAll('[contenteditable=true]');
if(editors.length > 0){
    editors[0].innerHTML = content;
    'success';
} else {
    'no editor';
}
```

```bash
# 执行方式：保存 JS 到文件，然后 eval
cat > /tmp/fill-editor.js << 'EOF'
var content = "<p>正文...</p>";
var editors = document.querySelectorAll('[contenteditable=true]');
if(editors.length > 0){editors[0].innerHTML=content;'success'}else{'no editor'}
EOF

opencli browser eval "$(cat /tmp/fill-editor.js)"
```

### 插入图片（使用免费图库）

```javascript
var imgHtml = "<p style='text-align:center;'>";
imgHtml += "<img src='https://images.unsplash.com/photo-xxx?w=800' style='max-width:100%;border-radius:8px;'/>";
imgHtml += "<p style='text-align:center;font-size:14px;color:#888;'>▲ 图片说明</p></p>";

var editors = document.querySelectorAll('[contenteditable=true]');
if(editors.length > 0){
    editors[0].innerHTML = imgHtml + editors[0].innerHTML;
    'success';
}
```

### 保存草稿

```bash
# 找保存按钮索引
opencli browser state | grep "保存"

# 点击保存（索引 777）
opencli browser click 777

# 等待保存完成
sleep 3

# 验证 URL（检查 appmsgid）
opencli browser state | grep "URL"
# 期望: appmsgid=100000xxx
```

---

## 关键元素索引（测试验证）

| 元素 | 索引 | 说明 |
|------|------|------|
| 标题 textarea | [474] | id=title |
| 作者 input | [475] | id=author |
| 摘要 textarea | [535] | id=js_description |
| 正文编辑器 | [498] | contenteditable=true |
| 保存按钮 | [777] | "保存为草稿" |
| 图片上传 | [804] | "上传文件" |

---

## 完整工作流示例

```bash
# 1. 打开编辑器
opencli browser open "https://mp.weixin.qq.com/cgi-bin/appmsg?t=appmsg/edit_v2&action=edit&isNew=1&type=77&token=TOKEN"
sleep 5

# 2. 填写标题/作者/摘要
opencli browser type 474 "标题"
opencli browser type 475 "作者"
opencli browser type 535 "摘要"

# 3. 填写正文（JS 文件）
opencli browser eval "$(cat /tmp/article-content.js)"

# 4. 截图验证
opencli browser screenshot /tmp/check.png

# 5. 保存草稿
opencli browser click 777
sleep 3

# 6. 验证草稿箱
opencli browser open "https://mp.weixin.qq.com/cgi-bin/appmsg?type=77&action=list_card&token=TOKEN"
opencli browser state | grep "标题关键词"
```

---

## 文章格式解析

```python
def parse_article(path: str) -> dict:
    """解析改写后的文章"""
    
    content = open(path).read()
    
    # 解析 Markdown
    title_match = re.search(r'# (.+)', content)
    body_match = re.search(r'## 正文\n(.+?)\n##', content, re.DOTALL)
    tags_match = re.search(r'## 标签建议\n(.+)', content)
    
    return {
        'title': title_match.group(1) if title_match else '无标题',
        'content': body_match.group(1) if body_match else '',
        'tags': tags_match.group(1) if tags_match else '',
        'path': path
    }
```

---

## 批量发布

```python
async def batch_publish(date: str):
    """批量发布当日文章"""
    
    pattern = f"{CONTENT_DIR}/{date}/*-professional.md"
    articles = glob.glob(pattern)
    
    results = []
    
    for article_path in articles:
        try:
            result = await publish_to_wechat(article_path)
            results.append(result)
        except Exception as e:
            results.append({'error': str(e), 'path': article_path})
    
    # 保存发布记录
    save_publish_log(date, results)
    
    return results
```

---

## 输出目录结构

```
tmp/publish/
└── YYYY-MM-DD/
    └── publish-log.md
```

---

## 发布记录格式

```markdown
---
created: YYYY-MM-DD HH:MM
type: publish-log
---

# YYYY-MM-DD 发布记录

## 发布成功

| 文章 | 标题 | 状态 | 时间 |
|------|------|------|------|
| 选题1-professional.md | xxx | draft | HH:MM |

## 发布失败

| 文章 | 错误 |
|------|------|
| xxx | xxx |

## Meta
- 总数: N
- 成功: M
- 失败: K
```

---

## Pitfalls

1. **⚠️ IP白名单必须配置**: 公众号后台 → 基本配置 → IP白名单 → 添加当前机器 IP（错误码 40164）
2. **⚠️ JSON编码必须用 ensure_ascii=False**: 否则中文会变成 unicode 编码显示
   ```python
   # 正确写法
   json.dumps(draft_data, ensure_ascii=False).encode('utf-8')
   
   # 错误写法（中文变乱码）
   json.dumps(draft_data).encode('utf-8')
   ```
3. **⚠️ 标题长度限制**: 64字节（约21中文字），超限报错 45003
2. **⚠️ 部分API需授权**: 错误码 48001 表示权限不足，需要在后台开通「用户管理」「数据分析」等权限
3. **草稿创建正常**: 配置白名单后，`/cgi-bin/draft/add` API 可正常使用
2. **Shell 转义问题**: JS 代码要保存到文件，不要直接在命令行写
3. **编辑器是 contenteditable**: 不是 iframe，用 `[contenteditable=true]` 查找
4. **⚠️ 外部图片 URL 不支持**: Unsplash 等外部图片链接会被公众号拒绝，草稿显示"图文内容不完整"。必须先上传图片到公众号素材库，再从素材库选择
5. **封面图尺寸**: 必须是 900×500px，不符合尺寸无法作为封面
6. **Token 会过期**: URL 中的 token 参数每次登录都会变化
7. **元素索引会变**: 重新加载页面后索引可能不同，用 `state` 重新查找
8. **不要重复创建草稿**: 编辑已有草稿用 `appmsgid=xxx` 参数，不要每次新建
9. **页面加载时间**: 编辑器加载需要 8-10 秒，太快操作会导致找不到元素
10. **⚠️ API 标题特殊字符限制**: 标题中不能包含「」【】等特殊符号，否则报错 45003 "title size out of limit"。标题长度限制 64 字符（中文按 1 字符计）
11. **⚠️ API 素材类型**: 创建草稿的封面图必须用**永久素材 API** (`/cgi-bin/material/add_material`)，不能用临时素材 API (`/cgi-bin/media/upload`)。临时素材 media_id 会报错 40007 "invalid media_id"
12. **Access Token 时效**: access_token 有效期 7200 秒（2小时），需要及时使用，跨 shell 会话可能失效

## 图片上传流程（必须执行）

公众号不接受外部图片 URL，必须上传到素材库：

```bash
# 封面图尺寸要求
sips -z 500 900 /tmp/cover.png

# 上传方式：
# 1. 手动上传：mp.weixin.qq.com → 素材库 → 上传图片
# 2. 从正文选择：编辑器中插入图片后，点击"从正文选择"作为封面
```

**图片获取来源**：
- Unsplash (免费): `https://images.unsplash.com/photo-xxx?w=800&h=400&fit=crop`
- AI 生成: Midjourney/DALL-E
- 自制图表: Excel 导出 PNG

---

## 兼容性记录

| 系统 | Hermes browser | OpenCLI browser |
|------|---------------|-----------------|
| macOS 12+ | ✅ 可用 | ✅ 可用 |
| macOS 11.7 | ❌ Chromium 崩溃 | ✅ 使用用户 Chrome |

---

## 长期解决方案：官方 API + SDK

如果需要完全自动化，推荐使用官方 API：

### 成熟的 SDK 选项

| SDK | Stars | 语言 | 说明 |
|-----|-------|------|------|
| **wechatpy** | 4279 | Python | 最成熟的 Python SDK，推荐使用 |
| WxJava | 32702 | Java | 微信全平台 SDK |
| WeiXinMPSDK | 8842 | .NET | C# SDK |
| openwechat | 5481 | Go | Go SDK |

### wechatpy 核心功能模块

```
wechatpy/client/api/
├── draft.py        → 草稿管理 (新增/修改/删除)
├── freepublish.py  → 发布管理 (发布/查询状态)
├── material.py     → 永久素材管理
├── media.py        → 临时素材上传
├── user.py         → 用户管理
├── message.py      → 消息群发
├── datacube.py     → 数据统计
└── ... (共 25+ 模块)
```

### wechatpy 使用示例

```python
from wechatpy import WeChatClient
import os

# 从环境变量获取配置
APPID = os.environ.get('WECHAT_APPID')
SECRET = os.environ.get('WECHAT_SECRET')

client = WeChatClient(APPID, SECRET)

# 1. 上传封面图（临时素材）
with open('cover.jpg', 'rb') as f:
    media = client.media.upload('image', f)
    thumb_media_id = media['media_id']

# 2. 新增草稿
articles = [{
    'title': '文章标题',
    'author': '作者名',
    'content': '<p>正文HTML内容...</p>',
    'thumb_media_id': thumb_media_id,
    'digest': '文章摘要',
    'content_source_url': '',  # 原文链接（可选）
    'need_open_comment': 0,    # 是否打开评论
}]
draft_media_id = client.draft.add(articles)

# 3. 发布草稿（群发）
# 注意：订阅号每天1次，服务号每月4次
result = client.freepublish.publish(draft_media_id)
publish_id = result['publish_id']

# 4. 查询发布状态
status = client.freepublish.get(publish_id)
```

### 安装 wechatpy

```bash
pip install wechatpy cryptography

# 或用 uv
uv pip install wechatpy cryptography
```

### 申请开发者权限

1. 登录公众号后台 → 设置与开发 → 基本配置
2. 获取 AppID + AppSecret
3. 配置 IP 白名单（服务器 IP）
4. 使用 wechatpy 完全自动化

**限制**：订阅号每天只能群发 1 次，服务号每月 4 次

---

## 有 AppID/AppSecret 时的推荐流程

当用户有开发者权限时，推荐使用 wechatpy API 方案。

**⚠️ 已验证成功的工作流程（2026-04-12）**：

```python
# 完整的 API 发布流程（已验证）
import json
import urllib.request
import ssl

APPID = "your_appid"
SECRET = "your_secret"

# Step 1: 获取 access_token
url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
resp = urllib.request.urlopen(url, context=ctx)
ACCESS_TOKEN = json.loads(resp.read())['access_token']

# Step 2: 上传永久素材（封面图）- 必须用此 API！
# 使用 curl 处理 multipart 上传
import subprocess
upload_cmd = f'''curl -s "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={ACCESS_TOKEN}&type=image" -F "media=@cover.jpg"'''
result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
MEDIA_ID = json.loads(result.stdout)['media_id']

# Step 3: 创建草稿（注意标题不能有特殊字符）
draft_data = {
    "articles": [{
        "title": "MiMo定价策略分析",  # 不能有「」等特殊符号！
        "author": "TimeSky",
        "content": html_content,  # 完整 HTML
        "thumb_media_id": MEDIA_ID,
        "digest": "摘要内容",
    }]
}

draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={ACCESS_TOKEN}"
req = urllib.request.Request(draft_url, data=json.dumps(draft_data).encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req, context=ctx)
draft_result = json.loads(resp.read())

if 'media_id' in draft_result:
    DRAFT_ID = draft_result['media_id']
    print(f"草稿创建成功: {DRAFT_ID}")
    
    # Step 4: 发布草稿（可选）
    publish_url = f"https://api.weixin.qq.com/cgi-bin/freepublish/publish?access_token={ACCESS_TOKEN}"
    publish_data = {"media_id": DRAFT_ID}
    req = urllib.request.Request(publish_url, data=json.dumps(publish_data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, context=ctx)
    print(f"发布结果: {json.loads(resp.read())}")
```

---

### 使用 wechatpy SDK（推荐）

```python
#!/usr/bin/env python3
"""微信公众号文章发布脚本 - wechatpy 版"""

from wechatpy import WeChatClient
import os

APPID = os.environ.get('WECHAT_APPID')
SECRET = os.environ.get('WECHAT_SECRET')

def publish_article(title, content_html, cover_path, author='', digest=''):
    """发布文章到公众号"""
    
    client = WeChatClient(APPID, SECRET)
    
    # 1. 上传封面图
    with open(cover_path, 'rb') as f:
        media = client.media.upload('image', f)
        thumb_id = media['media_id']
    
    # 2. 创建草稿
    articles = [{
        'title': title,
        'author': author,
        'content': content_html,
        'thumb_media_id': thumb_id,
        'digest': digest,
    }]
    draft_id = client.draft.add(articles)
    
    # 3. 发布
    result = client.freepublish.publish(draft_id)
    return result

if __name__ == '__main__':
    # 使用示例
    result = publish_article(
        title='测试文章',
        content_html='<p>正文内容</p>',
        cover_path='cover.jpg',
        author='作者',
        digest='摘要'
    )
    print(f"发布成功: {result}")
```

**环境变量设置**：
```bash
export WECHAT_APPID="your_appid"
export WECHAT_SECRET="your_secret"
```

**与 MCN 工作流集成**：
- `mcn-content-rewriter` → 生成文章内容
- 转换为 HTML 格式
- `wechatpy` → 发布到公众号

---

## 调研报告参考

完整调研报告保存位置：
```
/Users/timesky/backup/知识库-Obsidian/tmp/content/2026-04-12/微信公众号自动化方案调研.md
```

---

## 与入口技能的关系

**入口技能**：`wechat-mp-auto-publish`（MCN 唯一入口，定时任务 + 人工确认 + 一键执行）

**子技能**（可单独调用）：
- `mcn-hotspot-aggregator`: 热搜抓取
- `mcn-topic-selector`: 选题分析
- `mcn-content-rewriter`: 内容改写
- `mcn-wechat-publisher`: 公众号发布

---

## 相关技能

- `mcn-content-rewriter`: 内容改写（前置）
- `web-fetcher`: 浏览器控制

---

*Last updated: 2026-04-12 by Luna*