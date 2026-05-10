# Accio Browser Relay 交互方式调研报告

**调研时间**: 2026-04-11  
**来源**: `/Applications/Accio.app/Contents/Resources/chrome-extension/accio-browser-relay/`

---

## 📋 核心架构

Accio 使用 **混合架构** 与扩展交互：

```
┌─────────────────────────────────────────────────────────┐
│  Accio Desktop App                                      │
│  (本地 Node.js 服务)                                     │
├─────────────────────────────────────────────────────────┤
│  控制端口 (Control Port): 默认 9222                      │
│  中继端口 (Relay Port): 默认 9223                        │
└─────────────────────────────────────────────────────────┘
                          ↕ WebSocket
┌─────────────────────────────────────────────────────────┐
│  Chrome Extension (MV3 Service Worker)                  │
├─────────────────────────────────────────────────────────┤
│  background.js (Relay Connection)                       │
│    ↓ chrome.debugger API                                │
│  content_script/ (DOM Interaction)                      │
│    ↓ chrome.scripting.executeScript                     │
│  Web Page (User's Logged Session)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🔌 交互方式

### 方式一：WebSocket Relay（主要方式）

**流程**:
1. Accio 本地服务启动 WebSocket 服务器（端口 9223）
2. 扩展的 `background.js` 连接到 WebSocket
3. 通过 `forwardCDPCommand` 消息传递 CDP 命令
4. 扩展使用 `chrome.debugger.sendCommand()` 执行

**代码示例**:

```javascript
// Accio 本地服务 → 扩展
ws.send(JSON.stringify({
  id: 1,
  method: 'forwardCDPCommand',
  params: {
    method: 'Extension.extractContent',
    sessionId: 'tab-123'
  }
}));

// 扩展 → Accio 本地服务
ws.send(JSON.stringify({
  id: 1,
  result: { title: '...', content: '...' }
}));
```

**关键文件**:
- `lib/cdp/relay/connection.js` - WebSocket 连接管理
- `lib/cdp/commands/dispatch.js` - 命令路由

### 方式二：Chrome Debugger API（底层方式）

**流程**:
1. 扩展通过 `chrome.debugger.attach()` 附加到标签页
2. 直接发送 CDP 命令
3. 接收 CDP 事件

**代码示例**:

```javascript
// 附加调试器
await chrome.debugger.attach({ tabId }, '1.3');

// 发送 CDP 命令
const result = await chrome.debugger.sendCommand(
  { tabId },
  'Runtime.evaluate',
  { expression: 'document.title', returnByValue: true }
);

// 接收事件
chrome.debugger.onEvent.addListener((source, method, params) => {
  console.log('CDP Event:', method, params);
});
```

**关键文件**:
- `lib/cdp/tabs/manager.js` - 标签页管理
- `lib/cdp/events/interceptor.js` - CDP 事件拦截

### 方式三：chrome.scripting API（内容提取）

**流程**:
1. 扩展通过 `chrome.scripting.executeScript()` 注入代码
2. 在页面上下文中执行
3. 返回结果

**代码示例**:

```javascript
// 内容提取（双路径算法）
const results = await chrome.scripting.executeScript({
  target: { tabId },
  func: () => {
    // 在页面上下文中执行
    const title = document.querySelector('h1')?.textContent || '';
    const content = document.body.innerText;
    return { title, content };
  }
});

console.log(results[0].result); // { title: '...', content: '...' }
```

**关键文件**:
- `lib/content_script/extension-ops.js` - 核心操作
- `lib/content_script/extract-readability.js` - 双路径提取

---

## 📊 三种方式对比

| 方式 | 优点 | 缺点 | 使用场景 |
|------|------|------|----------|
| **WebSocket Relay** | - 解耦<br>- 支持远程<br>- 可扩展 | - 需要本地服务<br>- 复杂度高 | - 主要交互方式<br>- 多标签页管理 |
| **Chrome Debugger** | - 直接<br>- 功能完整<br>- 低延迟 | - 需要权限<br>- 可能触发警告 | - 底层 CDP 命令<br>- 页面导航 |
| **chrome.scripting** | - 简单<br>- 复用 cookies<br>- 避免封禁 | - 功能有限<br>- 仅限 DOM 操作 | - 内容提取<br>- 元素交互 |

---

## 🔑 关键技术点

### 1. 虚拟命令系统

Accio 定义了 `Extension.*` 虚拟命令：

```javascript
// 虚拟命令路由
if (method === 'Extension.extractContent') {
  return extExtractContent(tabId);
}
if (method === 'Extension.click') {
  return extClick(tabId, params);
}
if (method === 'Extension.getViewportInfo') {
  return extGetViewportInfo(tabId);
}
```

**优势**:
- 统一接口
- 隐藏实现细节
- 便于扩展

### 2. 标签页队列管理

```javascript
const _tabQueues = new Map();

function enqueueForTab(tabId, task) {
  const q = getTabQueue(tabId);
  q.queue.push({ task, resolve, reject });
  processQueue(q);
}
```

**优势**:
- 避免并发冲突
- 保证执行顺序
- 防止队列溢出

### 3. 双路径内容提取

参考 Mozilla Readability：

```javascript
// Path 1: Simple walker
function simpleExtract() {
  const lines = [];
  walk(root);
  return lines.join('\n');
}

// Path 2: Scoring-based
function scoringExtract() {
  const candidates = [];
  for (const el of document.querySelectorAll('div, section, article')) {
    const s = score(el);
    if (s > 0) candidates.push({ el, score: s });
  }
  candidates.sort((a, b) => b.score - a.score);
  return best.el.innerText;
}

// 智能选择
const content = simple.length >= scored.length ? simple : scored;
```

### 4. 连接状态管理

```javascript
// 3 状态模型
enum RelayState {
  DISABLED = 'disabled',       // 扩展关闭
  DISCONNECTED = 'disconnected', // 启用但未连接
  CONNECTED = 'connected'      // 已连接
}

// 自动重连
function scheduleReconnect() {
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), 30000);
  chrome.alarms.create('relayReconnect', { delayInMinutes: delay / 60000 });
}
```

---

## 📁 核心文件结构

```
accio-browser-relay/
├── manifest.json              # MV3 配置
├── background.js              # Service Worker 入口
├── lib/
│   ├── cdp/
│   │   ├── relay/
│   │   │   └── connection.js  # WebSocket 连接管理 ⭐
│   │   ├── tabs/
│   │   │   └── manager.js     # 标签页管理 ⭐
│   │   ├── commands/
│   │   │   └── dispatch.js    # 命令路由 ⭐
│   │   └── events/
│   │       └── interceptor.js # CDP 事件拦截
│   ├── content_script/
│   │   ├── extension-ops.js   # DOM 操作 ⭐
│   │   ├── extract-readability.js  # 双路径提取 ⭐
│   │   ├── press-key.js       # 键盘模拟
│   │   ├── scroll.js          # 滚动
│   │   └── click.js           # 点击
│   ├── constants.js           # 常量配置
│   ├── icon-badge.js          # 图标状态
│   └── logger.js              # 日志系统
├── pages/
│   ├── popup.html             # Popup UI
│   └── options.html           # 设置页面
└── test/                      # 测试
```

---

## 🎯 与 Hermes Web Fetcher 的对比

| 功能 | Accio | Hermes Web Fetcher |
|------|-------|-------------------|
| **架构** | WebSocket Relay + Debugger | chrome.scripting only |
| **复杂度** | 高（完整框架） | 低（专注抓取） |
| **交互方式** | 3 种（Relay/Debugger/Scripting） | 1 种（Scripting） |
| **内容提取** | 双路径 + 评分 | 双路径 + 评分 |
| **标签页管理** | ✅ 完整 | ❌ 无 |
| **命令队列** | ✅ 有 | ❌ 无 |
| **自动重连** | ✅ 有 | ❌ 无 |
| **虚拟命令** | ✅ Extension.* | ❌ 无 |
| **适用场景** | 通用 Agent 工具 | 专注内容抓取 |

---

## 💡 改进建议

### 为 Hermes Web Fetcher 添加

1. **虚拟命令系统**
   ```javascript
   // 定义 Hermes.* 虚拟命令
   if (method === 'Hermes.fetchList') {
     return fetchList(tabId, options);
   }
   if (method === 'Hermes.fetchArticle') {
     return fetchArticle(tabId);
   }
   ```

2. **标签页队列管理**
   ```javascript
   const tabQueues = new Map();
   
   function enqueue(tabId, task) {
     const q = tabQueues.get(tabId) || { queue: [], running: false };
     q.queue.push(task);
     processQueue(q);
   }
   ```

3. **连接状态指示器**
   ```javascript
   // 在 popup 中显示状态
   const status = {
     connected: isRelayConnected(),
     attachedTabs: mgr.size
   };
   ```

---

## 📚 参考资料

- [Chrome Extension Manifest V3](https://developer.chrome.com/docs/extensions/mv3/intro/)
- [chrome.debugger API](https://developer.chrome.com/docs/extensions/reference/debugger/)
- [chrome.scripting API](https://developer.chrome.com/docs/extensions/reference/scripting/)
- [Mozilla Readability](https://github.com/mozilla/readability)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)

---

*调研完成于 2026-04-11*
