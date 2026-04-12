# Hermes Web Fetcher - 完整架构

## 📋 问题：为什么光有扩展不够？

您说得对！**Accio 能与扩展通讯是因为它有本地服务作为中介**。

### Accio 的完整架构

```
┌─────────────────────────────────────────────────────────┐
│  Accio Desktop App (本地 Node.js 服务)                    │
│  - WebSocket 服务器 (端口 9223)                           │
│  - Python/Node.js 可调用                                  │
└─────────────────────────────────────────────────────────┘
                          ↕ WebSocket
┌─────────────────────────────────────────────────────────┐
│  Chrome Extension (MV3)                                 │
│  - 连接到本地 WebSocket                                 │
│  - chrome.debugger / chrome.scripting                   │
└─────────────────────────────────────────────────────────┘
```

### Hermes 之前的问题

```
┌─────────────────────────────────────────────────────────┐
│  Hermes Agent (Python)                                  │
│  ❌ 无法直接调用扩展 API                                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Chrome Extension                                       │
│  ❌ 没有本地服务可以连接                                  │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ 解决方案：创建 Hermes 本地服务

现在 Hermes 也有了完整的架构：

```
┌─────────────────────────────────────────────────────────┐
│  Hermes Agent (Python)                                  │
│  - 使用 hermes_web_fetcher.py 客户端                     │
└─────────────────────────────────────────────────────────┘
                          ↕ WebSocket (端口 9234)
┌─────────────────────────────────────────────────────────┐
│  Hermes Local Server (Node.js)                          │
│  - server.js (WebSocket 服务器)                          │
│  - 转发消息到扩展                                         │
└─────────────────────────────────────────────────────────┘
                          ↕ Chrome Extension API
┌─────────────────────────────────────────────────────────┐
│  Hermes Web Fetcher Extension                           │
│  - extension-bridge.js (WebSocket 客户端)                │
│  - chrome.scripting.executeScript                       │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 安装步骤

### 1. 安装 Node.js 依赖

```bash
cd ~/.hermes/browser-extension/web-fetcher/server
npm install
```

### 2. 安装 Python 依赖

```bash
pip install websockets
```

### 3. 更新扩展 manifest

需要在扩展的 `manifest.json` 中添加 WebSocket 权限：

```json
{
  "permissions": [
    "scripting",
    "tabs",
    "activeTab",
    "storage",
    "alarms"
  ],
  "background": {
    "service_worker": "server/extension-bridge.js"
  }
}
```

**注意**: 需要重新加载扩展。

---

## 🚀 使用方法

### 1. 启动本地服务器

```bash
cd ~/.hermes/browser-extension/web-fetcher/server
node server.js
```

输出：
```
🚀 Hermes Web Fetcher Server starting on port 9234...
✅ Server running on ws://localhost:9234
   Health check: http://localhost:9234/health
   Waiting for extension connection...
```

### 2. 加载扩展

1. 打开 `chrome://extensions/`
2. 启用开发者模式
3. 重新加载扩展（确保 `extension-bridge.js` 已连接）

扩展控制台会显示：
```
[Hermes] Connecting to server: ws://localhost:9234
[Hermes] ✅ Connected to server
```

### 3. Python 调用

```python
import asyncio
from hermes_web_fetcher import HermesWebFetcher

async def main():
    client = HermesWebFetcher()
    
    # 连接
    if not await client.connect():
        print("连接失败")
        return
    
    # 获取页面信息
    info = await client.get_page_info(tab_id=123)
    print(f"标题：{info['title']}")
    
    # 抓取文章
    article = await client.fetch_article(tab_id=123)
    print(f"内容长度：{len(article['content'])}")
    
    # 抓取列表
    items = await client.fetch_list(tab_id=123, options={
        'itemSelector': '.CollectionItem',
        'titleSelector': 'h2'
    })
    print(f"文章数：{items['totalItems']}")
    
    await client.disconnect()

asyncio.run(main())
```

---

## 📊 完整架构对比

| 组件 | Accio | Hermes (新) |
|------|-------|-------------|
| **本地服务** | ✅ Node.js WebSocket | ✅ Node.js WebSocket |
| **扩展连接** | ✅ WebSocket 客户端 | ✅ WebSocket 客户端 |
| **Python 客户端** | ✅ 有 | ✅ 有 (hermes_web_fetcher.py) |
| **CDP 命令** | ✅ forwardCDPCommand | ✅ forwardCDPCommand |
| **虚拟命令** | ✅ Extension.* | ✅ Hermes.* |
| **内容提取** | ✅ 双路径 | ✅ 双路径 |
| **标签页管理** | ✅ TabManager | ⏳ 待实现 |
| **命令队列** | ✅ 有 | ⏳ 待实现 |
| **自动重连** | ✅ 有 | ✅ 有 |

---

## 🔧 文件结构

```
web-fetcher/
├── manifest.json               # 扩展清单
├── content.js                  # 内容提取（独立使用）
├── popup.html/js               # Popup UI
├── README.md                   # 扩展文档
├── research/
│   └── accio-interaction-analysis.md  # Accio 调研报告
└── server/                     # 本地服务 ⭐ 新增
    ├── package.json            # Node.js 配置
    ├── server.js               # WebSocket 服务器
    ├── extension-bridge.js     # 扩展桥接代码
    ├── hermes_web_fetcher.py   # Python 客户端
    └── README.md               # 服务文档
```

---

## 🎯 下一步

### 立即可用

1. ✅ 启动本地服务器
2. ✅ 重新加载扩展
3. ✅ Python 调用扩展 API

### 待实现（参考 Accio）

1. ⏳ 标签页队列管理
2. ⏳ 虚拟命令系统完善
3. ⏳ 连接状态指示器
4. ⏳ 命令超时处理
5. ⏳ 多标签页支持

---

## 💡 关键代码对比

### Accio 的扩展连接

```javascript
// accio-browser-relay/lib/cdp/relay/connection.js
const ws = new WebSocket(`ws://localhost:${relayPort}`);
ws.onopen = () => setState(RelayState.CONNECTED);
ws.onmessage = (event) => handleRelayMessage(JSON.parse(event.data));
```

### Hermes 的扩展连接

```javascript
// web-fetcher/server/extension-bridge.js
const ws = new WebSocket(`ws://localhost:${9234}`);
ws.onopen = () => console.log('✅ Connected to server');
ws.onmessage = async (event) => handleCommand(JSON.parse(event.data));
```

**几乎一样！** 🎉

---

*创建时间：2026-04-11*
