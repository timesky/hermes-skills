# 微信公众号后台关键页面路径

> 更新时间: 2026-04-24
> 账号: 程序员的开发手册 (gh_00dc0365fa21)

## 基础 URL 格式

```
https://mp.weixin.qq.com/cgi-bin/{path}?{params}&token={token}&lang=zh_CN
```

**⚠️ Token 会过期**，需要检测登录状态并可能重新登录。

## 关键页面路径

### 1. 首页（数据概览）

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/home` |
| params | `t=home/index` |
| 完整 URL | `https://mp.weixin.qq.com/cgi-bin/home?t=home/index&token={token}&lang=zh_CN` |

**用途**: 
- 查看昨日数据概览（阅读/分享/新增关注）
- 确认账号名称
- 提取 token

### 2. 已发布文章列表（主要数据来源）

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/appmsgpublish` |
| params | `sub=list&begin=0&count=10` |
| 完整 URL | `https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=10&token={token}&lang=zh_CN` |

**用途**: 
- 获取文章列表（标题、链接）
- 文章统计数据嵌入在页面 JavaScript 中

**分页**: 
- `begin=0` 起始位置
- `count=10` 每页数量（最大 20）

### 3. 草稿管理

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/appmsg` |
| params | `begin=0&count=10&type=77&action=list_card` |

**用途**: 新建/编辑文章草稿

### 4. 素材管理

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/filepage` |
| params | `type=2&begin=0&count=12` |

**用途**: 图片/视频等素材管理

### 5. 用户管理

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/contactmanage` |
| params | `t=user/index` |

**用途**: 粉丝列表、用户标签

### 6. 消息管理

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/message` |
| params | `t=message/list&count=20&day=7` |

**用途**: 私信、自动回复

### 7. 设置页

| 参数 | 值 |
|------|-----|
| path | `/cgi-bin/settingpage` |
| params | `t=setting/index` |

**用途**: 公众号设置、开发者配置

## 数据字段结构

### 文章信息 (appmsg_info)

```json
{
  "appmsgid": "2247484740",
  "title": "文章标题",
  "content_url": "https://mp.weixin.qq.com/s/xxx",
  "cover": "封面图 URL",
  "digest": "摘要",
  "read_num": 0,
  "like_num": 0,
  "share_num": 0,
  "comment_num": 0,
  "copyright_status": 11,
  "is_deleted": false,
  "create_time": 1776899526,
  "update_time": 1776899531
}
```

### 发布信息 (publish_info)

```json
{
  "bizuin": 3948712872,
  "msgid": "2247484740",
  "draft_msgid": "100001085",
  "publish_type": 1,
  "publish_status": 200,
  "create_time": 1776853726,
  "update_time": 1776853747,
  "index_count": 1
}
```

## 导航菜单结构

| 菜单项 | 说明 |
|--------|------|
| 首页 | 数据概览、通知 |
| 内容管理 | 草稿、已发布、素材 |
| 创作 | 图文、视频、专辑 |
| 互动管理 | 评论、私信、点赞 |
| 用户管理 | 粉丝、标签 |
| 用户分析 | 粉丝增长、画像 |
| 数据分析 | 文章数据详情 |
| 消息分析 | 私信统计 |
| 设置与开发 | API、菜单配置 |

## 数据获取方法

**重要**: 微信公众号后台没有独立的 REST API，数据嵌入在页面 JavaScript 中。

### 方法一：解析 HTML 中的 JSON

```python
# 在 HTML 中搜索 JSON 数据块
import re

# 文章数据格式
pattern = r'"appmsg_info":\s*\[{[^}]+}\]'
matches = re.findall(pattern, html_content)

# 解析 JSON
for match in matches:
    data = json.loads(match)
    read_num = data['read_num']
    like_num = data['like_num']
```

### 方法二：使用 web-fetcher 抓取

```python
from hermes_web_fetcher import HermesWebFetcher

client = HermesWebFetcher()
await client.connect()

tab = await client.create_agent_tab(url)
result = await client.fetch_article(tab['id'])
html = result.get('content', '')

# 解析 HTML 提取数据
```

## Token 过期处理

1. 检测页面是否包含账号名称（如 "程序员的开发手册")
2. 如果未检测到，截屏保存二维码
3. 通知用户扫码登录
4. 用户登录后重新运行脚本

---

*注意: 此配置基于 2026-04-24 页面分析，微信后台可能随时更新结构*