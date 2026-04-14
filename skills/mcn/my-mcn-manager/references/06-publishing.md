---
module: 06-publishing
type: reference
source: mcn-wechat-publisher (整合)
---

# 模块 6: 公众号发布

通过官方 API 发布文章到草稿箱。

---

## 配置

路径：`~/.hermes/wechat_mp_config.yaml`

```yaml
appid: wx47533ce9c8854fb5
secret: 2b990fc5...eb2f
author: TimeSky
```

---

## 发布流程

### 1. 获取 access_token

```python
import json
import urllib.request
import ssl

def get_access_token(appid: str, secret: str) -> str:
    """获取 access_token（有效期 2 小时）"""
    
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    resp = urllib.request.urlopen(url, context=ctx)
    data = json.loads(resp.read())
    
    return data['access_token']
```

### 2. 上传封面图

```python
import subprocess

def upload_cover(cover_path: str, access_token: str) -> dict:
    """上传封面图（永久素材）"""
    
    # 调整尺寸为 900x500
    resized_path = "/tmp/cover_900x500.png"
    subprocess.run(f"sips -z 500 900 '{cover_path}' --out '{resized_path}'", shell=True)
    
    # 上传
    upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"
    result = subprocess.run(f'curl -s "{upload_url}" -F "media=@{resized_path}"', 
                            shell=True, capture_output=True, text=True)
    
    return json.loads(result.stdout)
    # 返回：{'media_id': 'xxx', 'url': 'http://mmbiz.qpic.cn/...'}
```

### 3. 上传正文配图

```python
def upload_article_images(img_paths: list, access_token: str) -> list:
    """批量上传正文配图"""
    
    upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"
    uploaded_urls = []
    
    for img_path in img_paths:
        result = subprocess.run(f'curl -s "{upload_url}" -F "media=@{img_path}"', 
                                shell=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        if 'url' in data:
            uploaded_urls.append(data['url'])
    
    return uploaded_urls
```

### 4. 构建 HTML 内容

```python
def build_html_content(article_path: str, img_urls: list) -> str:
    """构建带配图的 HTML"""
    
    content = open(article_path, encoding='utf-8').read()
    
    # 提取正文
    body_start = content.find('\n\n') + 2
    body = content[body_start:]
    
    # 转换为 HTML 段落
    html_paragraphs = []
    for para in body.split('\n\n'):
        if para.strip():
            html_paragraphs.append(f"<p>{para.strip().replace(chr(10), '<br/>')}</p>")
    
    html_content = '\n'.join(html_paragraphs)
    
    # 在开头插入配图
    for img_url in img_urls[:3]:
        img_html = f'<p style="text-align:center;"><img src="{img_url}" style="max-width:100%;border-radius:8px;"/></p>'
        html_content = img_html + html_content
    
    return html_content
```

### 5. 创建草稿

```python
def create_draft(title: str, content_html: str, cover_media_id: str, 
                 digest: str, author: str, access_token: str) -> dict:
    """创建草稿"""
    
    draft_data = {
        "articles": [{
            "title": title,
            "author": author,
            "content": content_html,
            "thumb_media_id": cover_media_id,
            "digest": digest,
            "need_open_comment": 0,
        }]
    }
    
    draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    req_data = json.dumps(draft_data, ensure_ascii=False).encode('utf-8')  # ⚠️ 必须用 ensure_ascii=False
    req = urllib.request.Request(draft_url, data=req_data, headers={'Content-Type': 'application/json'})
    
    resp = urllib.request.urlopen(req, context=ctx)
    return json.loads(resp.read())
    # 返回：{'media_id': 'xxx'}
```

---

## 完整发布脚本

```python
def publish_article(article_path: str, img_dir: str):
    """完整发布流程"""
    
    # 1. 获取 token
    config = yaml.safe_load(open("~/.hermes/wechat_mp_config.yaml"))
    token = get_access_token(config['appid'], config['secret'])
    
    # 2. 上传封面
    cover_path = f"{img_dir}/img_1.png"
    cover_result = upload_cover(cover_path, token)
    cover_media_id = cover_result['media_id']
    
    # 3. 上传正文配图
    img_paths = [f"{img_dir}/{f}" for f in os.listdir(img_dir) if f.endswith('.png')]
    img_urls = upload_article_images(img_paths, token)
    
    # 4. 构建 HTML
    html_content = build_html_content(article_path, img_urls)
    
    # 5. 提取标题和摘要
    article = open(article_path, encoding='utf-8').read()
    title = re.search(r'# (.+)', article).group(1)
    digest = extract_digest(article)[:120]
    
    # 6. 创建草稿
    result = create_draft(title, html_content, cover_media_id, digest, config['author'], token)
    
    print(f"✅ 草稿创建成功：{result['media_id']}")
    return result['media_id']
```

---

## Pitfalls

| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | 外部图片 URL | 必须上传素材库获取 mmbiz URL |
| 2 | JSON 中文乱码 | `ensure_ascii=False` |
| 3 | 标题超限 | ≤64 字符 |
| 4 | 摘要超限 | ≤120 字符 |
| 5 | 封面报错 40007 | 用永久素材 API（material.add） |
| 6 | IP 白名单 | 公众号后台 → 基本配置 → 添加 IP |

---

*整合自：mcn-wechat-publisher*
