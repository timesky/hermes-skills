---
name: wechat-analytics-browser
description: 微信公众号数据分析 - 使用 browser 工具替代失效的 web-fetcher
version: 1.0.0
created: 2026-05-02
---

# 微信公众号数据分析（Browser 方案）

## 背景

原 `wechat-analytics` 技能的 Python 脚本因模块缺失无法使用：
```
ModuleNotFoundError: No module named 'hermes_web_fetcher'
```

本技能使用 browser 工具实现相同功能。

## 执行流程

### 1. 检测登录状态

```
browser_navigate(url="https://mp.weixin.qq.com")
browser_snapshot() 或 browser_vision()
```

**判断标准**：
- 已登录：页面包含 "程序员的开发手册" 或 "设置与开发"
- 未登录：页面显示 QR code 和 "微信扫一扫"

### 2. 登录过期处理

```
# 截图 QR code
browser_vision(question="是否有二维码登录？")

# 复制截图到固定位置
cp ~/.hermes/cache/BROWSER_SCREENSHOT.png ~/mcn/screenshots/wechat_qrcode.png

# 通知用户扫码（如果有 gateway）
send_message(target="feishu", message="公众号登录已过期，请扫码")
```

### 3. 抓取发布历史

**前提**：必须先登录

```
browser_navigate(url="https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token=TOKEN")

# 使用 browser_console 提取数据
browser_console(expression="document.body.innerText")
```

### 4. 解析数据字段

公众号后台数据顺序：
| 列号 | 字段 |
|------|------|
| 1 | 送达人数 |
| 2 | 阅读数 |
| 3 | 点赞数 |
| 4 | 分享数 |
| 5 | 收藏数 |

### 5. 输出文件

- `~/mcn/published_stats.json` - 文章统计数据
- `~/mcn/screenshots/wechat_qrcode.png` - 登录二维码

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| Gateway 连接失败 (18789) | 检查 hermes-gateway 是否运行 |
| QR code 截图空白 | 等待 3-4 秒后重试 |
| Token 提取失败 | 从页面源码提取：`token=(\d+)` |

---

*Created: 2026-05-02 - 解决原技能模块缺失问题*