---
name: web-fetcher
description: Chrome 扩展 + WebSocket 服务抓取网页内容并控制页面（填写表单、点击、API调用）。支持 Draft.js/React 编辑器，使用用户已登录的 Cookie。v2.1 新增 Agent Tab Group，独立页签分组不抢占用户活动页签。
tags: [web, scraping, chrome-extension, websocket, control, automation]
version: 2.1.0
created: 2026-04-11
updated: 2026-04-20
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

### 🆕 控制方法 (v2.0)

**支持 Draft.js/React 编辑器的填写操作：**

|| 方法 | 参数 | 返回 |
||------|------|------|
|| `fill_input(tab_id, selector, value, options)` | tab_id, selector, value, {clearFirst, triggerReact} | `{success, filledLength}` |
|| `click_element(tab_id, selector, options)` | tab_id, selector, {doubleClick} | `{success}` |
|| `send_keys(tab_id, selector, text)` | tab_id, selector, text | `{success, typed}` |
|| `wait_for(tab_id, selector, timeout)` | tab_id, selector, timeout_ms | `{success}` 或 `{error: timeout}` |
|| `blur(tab_id, selector)` | tab_id, selector | `{success}` |
|| `get_element_info(tab_id, selector)` | tab_id, selector | `{value, contentEditable, ...}` |
|| `call_api(tab_id, url, method, data)` | tab_id, url, method, data | `{success, status, data}` |

**关键特性：**
- `fill_input` 自动检测 Draft.js/React 编辑器，触发正确的事件序列
- `call_api` 使用页面已有的 Cookie/认证，绕过 CORS 限制
- `blur` 触发自动保存（知乎等自动保存编辑器）

### 🆕 截屏方法 (v2.2)

|| 方法 | 参数 | 返回 |
|------|------|------|
|| `screenshot(tab_id, options)` | tab_id, {format, quality} | `{success, dataUrl, format}` - 截取可见区域 |
|| `screenshot_to_file(tab_id, filepath, format)` | tab_id, filepath, format | `filepath` - 截屏并保存到文件 |

**使用场景：**
- 登录过期时截屏二维码让用户扫码
- 记录页面状态用于调试
- 验证页面布局和渲染效果

**示例：**

```python
# 截屏并保存到文件
filepath = await client.screenshot_to_file(tab_id, "~/.hermes/login_qrcode.png")

# 或获取 base64 数据
result = await client.screenshot(tab_id, {"format": "png"})
if result.get('success'):
    data_url = result['dataUrl']  # data:image/png;base64,...
```

### 🆕 Agent Tab Group (v2.1)

**独立页签分组，不抢占用户当前活动页签：**

|| 方法 | 参数 | 返回 |
||------|------|------|
|| `create_agent_tab(url)` | url | `{id, title, url}` - 创建新页签并加入分组 |
|| `add_to_agent_group(tab_id)` | tab_id | `{groupId, tabId}` - 将已有页签加入分组 |
|| `close_agent_tab(tab_id)` | tab_id | `{success}` - 关闭指定页签 |
|| `dissolve_agent_group()` | 无 | `{closed, ungrouped}` - 关闭分组中所有页签 |
|| `list_agent_tabs()` | 无 | `{groupId, tabs, count}` - 列出分组中的页签 |

**使用场景：**
- 后台抓取多个页面，不影响用户当前浏览
- 自动化任务完成后关闭页签，保持浏览器整洁
- 分组标题 "Hermes Agent"，紫色标识

**示例：**

```python
async def batch_fetch(urls):
    client = HermesWebFetcher()
    await client.connect()
    
    results = []
    for url in urls:
        # 在 Agent Group 中创建新页签
        tab = await client.create_agent_tab(url)
        
        # 抓取内容
        article = await client.fetch_article(tab['id'])
        results.append(article)
        
        # 关闭页签
        await client.close_agent_tab(tab['id'])
    
    await client.disconnect()
    return results
```

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

## 💡 实用选择器模式

### Cookie 弹窗处理

```python
# 常见 cookie 接受按钮选择器
await client.click_element(tab_id, "button[class*='cookie']")
await client.click_element(tab_id, "button[class*='accept']")
await client.click_element(tab_id, "#accept-cookies")
```

### 表单字段定位

```python
# 按占位符文本查找（推荐）
await client.fill_input(tab_id, "input[placeholder*='Last']", "wang")
await client.fill_input(tab_id, "input[placeholder*='email']", "user@example.com")

# 按类型查找
await client.fill_input(tab_id, "input[type='email']", "...")
await client.fill_input(tab_id, "input[type='tel']", "...")
await client.fill_input(tab_id, "input[type='text']", "...")
```

### Select 下拉框注意事项

**`send_keys` 对 select 元素效果有限**，可能无法正确选择选项。替代方案：

```python
# 方案 1：等待页面加载后，select 可能已有正确默认值
# 方案 2：点击 select 展开选项，再用其他方式选择
await client.click_element(tab_id, "select")
await asyncio.sleep(1)
# 部分网站支持直接输入选项文本
await client.send_keys(tab_id, "select", "China")
```

### 检查元素状态

```python
# 获取元素信息（判断是否可见、可操作）
info = await client.get_element_info(tab_id, "input[type='email']")
if 'error' not in info and info.get('visible'):
    # 元素存在且可见，可以操作
    await client.fill_input(tab_id, "input[type='email']", value)
```

---

## ⚠️ 注意事项

### Service Worker API 陷阱

**Chrome Extension Service Worker 中必须使用 Promise 版本的 API：**

```javascript
// ❌ 错误：callback 版本在 Service Worker 中无响应
chrome.tabs.get(tabId, (tab) => { ... });

// ✅ 正确：Promise 版本
const tab = await chrome.tabs.get(tabId);
```

**原因**：Service Worker 的执行环境不同，callback 版本的 Chrome API 可能无法正常触发回调，导致请求超时。

**受影响的 API**：
- `chrome.tabs.get()` → 用 `await chrome.tabs.get(id)`
- `chrome.tabs.group()` → 用 `await chrome.tabs.group({...})`
- `chrome.tabGroups.get()` → 用 `await chrome.tabGroups.get(id)`
- `chrome.tabGroups.query()` → 用 `await chrome.tabGroups.query({...})`

**Promise 队列问题**：

```javascript
// ❌ 在 Service Worker 中可能导致死锁
const done = groupQueue.then(() => doWork());
groupQueue = done.catch(() => {});

// ✅ 直接执行更可靠
return await doWork();
```

### 复杂 JavaScript 交互 UI 局限性

**部分网站的选择机制依赖复杂 JS 动态交互，web-fetcher 无法自动化：**

| 特征 | 示例 | 原因 |
|------|------|------|
| 无标准表单元素（radio/checkbox） | VietJet 代金券选择 | 选择状态不在 DOM 中体现 |
| hidden input 存储非产品值 | hidden input 值为 "event" | 无法通过修改 DOM 改变选择 |
| 选择状态依赖 JavaScript 状态管理 | React/Vue 状态驱动 UI | DOM 操作不触发状态更新 |

**解决方案**：此类 UI 需完整浏览器自动化工具（Playwright/Selenium/Puppeteer），而非 DOM 操作。

**VietJet 案例**（2026-04-20）：
- 页面显示 4 个代金券选项（500/1000/2000/5000 THB）
- 尝试方法：点击 nth-of-type divs、JS 注入修改 hidden input、URL 参数、text input 填值
- 结果：所有方法无效，checkout 始终默认 500 THB
- 结论：VietJet 代金券选择无法用 web-fetcher 自动化

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

*Last updated: 2026-04-20 by Luna (added JS interaction UI limitation)*