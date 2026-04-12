---
name: web-fetcher
description: Chrome 扩展 + WebSocket 服务抓取网页内容（文章、列表、收藏夹）。使用用户已登录的 Cookie，避免 CDP 封禁风险。
tags: [web, scraping, chrome-extension, websocket]
version: 1.0.0
created: 2026-04-11
---

# Hermes Web Fetcher 扩展

通过 Chrome 扩展 + WebSocket 服务抓取任意网站内容。使用用户已登录的 Cookie，绕过登录验证和反爬机制。

## 架构

```
Hermes → Python 客户端 → WebSocket 服务(9234) → Chrome 扩展 → 目标网站
```

---

## 🔧 第一部分：浏览器扩展（用户手动安装）

### 安装步骤

1. **打开 Chrome 扩展管理页**
   ```
   chrome://extensions
   ```

2. **开启开发者模式**
   - 右上角开关切换为「开启」

3. **加载已解压的扩展程序**
   - 点击「加载已解压的扩展程序」
   - 选择目录：`~/.hermes/skills/web/web-fetcher/extension`

4. **验证安装**
   - 扩展列表应显示「Hermes Web Fetcher」
   - 扩展图标出现在工具栏

### 使用扩展

点击扩展图标打开 Popup：

| 按钮 | 功能 |
|------|------|
| 📄 获取页面信息 | 显示当前页面标题、URL、加载状态 |
| 📋 抓取列表/收藏夹 | 抓取列表类页面（知乎收藏夹、GitHub Trending 等） |
| 📖 抓取当前文章 | 抓取单篇文章内容 |
| WebSocket 开关 | 启用/禁用与服务器的连接 |

### 状态说明

| 状态徽章 | 含义 |
|----------|------|
| 🟢 已连接 | WebSocket 正常连接，可以抓取 |
| 🟡 断开 | 已启用但未连接（正在重试） |
| 🔴 禁用 | 用户关闭，不连接服务器 |

---

## 🖥️ 第二部分：本地服务（自动管理）

Hermes 会自动启动/关闭 WebSocket 服务器，无需用户手动操作。

### 服务启动流程

```bash
# Hermes 自动执行：
cd ~/.hermes/skills/web/web-fetcher/server
node server.js  # 后台运行
```

### 服务端口

- WebSocket: `ws://localhost:9234`
- 健康检查: `http://localhost:9234/health`

### 验证连接

```bash
curl http://localhost:9234/health
# 期望输出: {"status":"ok","clients":1,"pending":0}
```

- `clients: 1` = 扩展已连接 ✅
- `clients: 0` = 扩展未连接，请检查扩展 Popup 开关

---

## 📖 使用指南

### 完整流程（每次使用）

```
步骤 1: Hermes 启动 WebSocket 服务（自动）
步骤 2: Hermes 提示用户在 Chrome 中打开目标页面
步骤 3: 用户确认扩展已连接（Popup 显示「已连接」）
步骤 4: Hermes 通过 WebSocket 发送抓取命令
步骤 5: 扩展执行抓取，返回结果
步骤 6: Hermes 关闭 WebSocket 服务（自动）
```

### 用户操作要点

1. **打开目标页面** - 在 Chrome 中打开要抓取的页面
2. **确认扩展连接** - 点击扩展图标，确保状态为「已连接」
3. **等待抓取完成** - Hermes 会自动执行抓取并返回结果

---

## 🔌 Python 客户端 API

### 连接管理

```python
from hermes_web_fetcher import HermesWebFetcher
import asyncio

async def main():
    client = HermesWebFetcher()
    await client.connect()  # 连接 WebSocket
    
    # ... 抓取操作 ...
    
    await client.disconnect()  # 关闭连接
```

### 可用方法

| 方法 | 参数 | 返回 |
|------|------|------|
| `get_active_tab()` | 无 | `{id, title, url}` |
| `get_page_info(tab_id)` | tab_id | `{title, url, isReady}` |
| `navigate(tab_id, url)` | tab_id, url | `{success, title, url}` |
| `fetch_article(tab_id)` | tab_id | `{title, content, author, date, url}` |
| `fetch_list(tab_id, options)` | tab_id, options | `{items, pageInfo, totalItems}` |

### 抓取收藏夹示例

```python
async def fetch_zhihu_collection(url):
    client = HermesWebFetcher()
    await client.connect()
    
    # 获取活动标签页
    tab = await client.get_active_tab()
    
    # 导航到收藏夹
    await client.navigate(tab['id'], url)
    
    # 等待页面加载
    await asyncio.sleep(3)
    
    # 抓取列表
    result = await client.fetch_list(tab['id'])
    
    await client.disconnect()
    return result
```

---

## ⚠️ 注意事项

### chrome:// 页面限制

Chrome 扩展**无法访问** `chrome://` 协议页面：
- `chrome://newtab/` - 新标签页
- `chrome://extensions/` - 扩展管理页
- `chrome://settings/` - 设置页

遇到这些页面时，直接导航到目标 URL 即可。

### Service Worker 休眠

Manifest V3 的 Service Worker 会在约 30 秒后休眠。扩展使用 Alarm API 每 30 秒发送心跳保持连接。

### 分页抓取

列表类页面（如知乎收藏夹）需要分页抓取时：

```python
for page in range(1, total_pages + 1):
    url = f"https://www.zhihu.com/collection/{id}?page={page}"
    await client.navigate(tab_id, url)
    await asyncio.sleep(2)  # 等待加载
    items = await client.fetch_list(tab_id)
    all_items.extend(items['items'])
```

---

## 🔍 故障排查

| 问题 | 检查步骤 |
|------|----------|
| 服务未启动 | `curl http://localhost:9234/health` 是否返回 |
| 扩展未连接 | 检查 Popup 状态徽章，确认开关已启用 |
| 抓取失败 | 检查 Chrome DevTools → Extensions → Service Worker 日志 |
| 页面空白 | 等待页面完全加载后再抓取 |

### 查看扩展日志

1. Chrome → `chrome://extensions`
2. 找到 Hermes Web Fetcher
3. 点击「Service Worker」链接
4. 查看控制台输出

---

## 📂 文件结构

```
~/.hermes/skills/web/web-fetcher/
├── SKILL.md                    # 使用指南
├── extension/                  # Chrome 扩展（用户手动安装）
│   ├── manifest.json           # 扩展配置
│   ├── background.js           # Service Worker（WebSocket 连接）
│   ├── content.js              # 内容脚本（页面抓取）
│   ├── popup.html              # Popup UI
│   ├── popup.js                # Popup 逻辑
│   └── icons/                  # 扩展图标
└── server/                     # WebSocket 服务（自动管理）
    ├── server.js               # WebSocket 服务器
    ├── hermes_web_fetcher.py   # Python 客户端
    ├── package.json            # npm 配置
    ├── start_server.sh         # 启动脚本
    └── scripts/
        └── fetch_example.py    # 抓取示例
```

---

## 🎯 快速检查清单

使用前确认：

- [ ] Chrome 扩展已安装（从 `extension/` 目录加载）
- [ ] 扩展 Popup 显示「已连接」状态
- [ ] 目标页面已在 Chrome 中打开
- [ ] WebSocket 服务已启动（Hermes 自动处理）

---

*Last updated: 2026-04-11 by Luna*