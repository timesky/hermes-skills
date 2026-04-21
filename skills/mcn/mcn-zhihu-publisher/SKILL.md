---
name: mcn-zhihu-publisher
description: 'MCN 知乎专栏文章发布技能 - 将文章保存到知乎专栏草稿箱（仅草稿，不发布）。使用 web-fetcher 控制功能，支持 Draft.js 编辑器。触发词：知乎发布、zhihu发布、知乎草稿。'
version: 2.1.0
updated: 2026-04-16
---

# MCN 知乎发布技能

将 MCN 生成的文章保存到知乎专栏草稿箱。

## ✅ 主方案：web-fetcher 扩展

**web-fetcher v2.0 已集成控制功能，可正确处理 Draft.js 编辑器**：

| 特性 | web-fetcher | OpenCLI |
|------|-------------|---------|
| Draft.js 支持 | ✅ fill_input 自动处理 | ❌ type 无效 |
| Cookie 访问 | ✅ callApi 无限制 | ❌ eval 受安全限制 |
| 事件触发 | ✅ 模拟 Playwright fill() | ❌ 只做 DOM 操作 |
| 正文字数 | ✅ 正常显示 | ❌ 显示 0 |

### 前置条件

1. **web-fetcher 扩展已安装并启用**
   - 扩展目录：`~/.hermes/skills/web/web-fetcher/extension`
   - 版本：v2.0.0+
   - 在 `chrome://extensions` 刷新扩展

2. **WebSocket 服务运行**
   ```bash
   cd ~/.hermes/skills/web/web-fetcher/server && node server.js
   ```

3. **已登录知乎账号**
   - Chrome 浏览器已登录知乎

### 使用方法

```bash
# 保存草稿
python ~/.hermes/skills/mcn/mcn-zhihu-publisher/scripts/publish_draft.py \
  --article "/path/to/article.md"

# 自定义标题
python ~/.hermes/skills/mcn/mcn-zhihu-publisher/scripts/publish_draft.py \
  --article "/path/to/article.md" \
  --title "自定义标题"
```

### 知乎编辑器选择器

```javascript
// 标题（普通 textarea）
'textarea[placeholder*="标题"]'

// 正文（Draft.js 编辑器）
'.DraftEditor-root [contenteditable="true"]'
```

### 工作流程

```python
from hermes_web_fetcher import HermesWebFetcher
import asyncio

async def publish_zhihu_draft(title: str, content: str):
    client = HermesWebFetcher()
    await client.connect()
    
    # 获取活动标签页
    tab = await client.get_active_tab()
    tab_id = tab['id']
    
    # 导航到知乎写作页
    await client.navigate(tab_id, 'https://zhuanlan.zhihu.com/write')
    await asyncio.sleep(2)
    
    # 填写标题
    await client.fill_input(tab_id, 'textarea[placeholder*="标题"]', title)
    
    # 填写正文（自动检测 Draft.js）
    await client.fill_input(tab_id, '.DraftEditor-root [contenteditable="true"]', content)
    
    # 触发 blur 保存
    await client.blur(tab_id, '[contenteditable="true"]')
    await asyncio.sleep(3)  # 等待自动保存
    
    # 获取页面信息（包含草稿 URL）
    info = await client.get_page_info(tab_id)
    print(f"草稿 URL: {info['url']}")
    
    await client.disconnect()
    return info['url']
```

---

## ⚠️ 旧方案：OpenCLI（已弃用）

OpenCLI 方案正文填写**不可靠**（字数显示 0），已不再推荐。

详见下方"已知限制"部分。

---

## 已验证结果（2026-04-16）

测试输出：
```
✅ 标题已填写 (19 字符)
✅ 正文已填写 (63 字符)
✅ 草稿已保存
🔗 草稿 URL: https://zhuanlan.zhihu.com/p/xxx/edit
📊 正文字数: 63  ← 知乎正确识别！
```

对比 OpenCLI（字数显示 0），web-fetcher 通过 `chrome.scripting.executeScript` 直接在页面上下文执行，成功触发 Draft.js 内部状态。

---

## 输入文件格式

文章文件应为 Markdown 格式：

```markdown
# 文章标题

正文内容...

## 二级标题

更多内容...
```

- 标题：第一个 `#` 标题或 `--title` 参数
- 内容：标题后的所有内容
- YAML frontmatter 自动移除
- 末尾元信息自动移除

---

## 安全机制

| 检查项 | 实现 |
|--------|------|
| 发布按钮 | 脚本中不包含点击发布按钮的代码 |
| 自动保存 | 知乎会自动保存草稿，触发 blur 即可 |
| 用户确认 | 返回草稿 URL 供用户检查 |
| 正文验证 | 获取正文字数，确保 > 0 |

---

## 故障排查

### 问题：WebSocket 服务未运行

```bash
# 启动服务
cd ~/.hermes/skills/web/web-fetcher/server && node server.js

# 检查扩展是否连接
# 打开 chrome://extensions，点击 Hermes Web Fetcher 的 popup
# 应显示 "已连接"
```

### 问题：扩展未启用

1. 打开 `chrome://extensions`
2. 找到 **Hermes Web Fetcher**
3. 点击刷新按钮 🔄
4. 打开 popup 检查连接状态

### 问题：未登录知乎

手动在浏览器登录知乎，然后重试。

---

## Pitfalls

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| WebSocket 连接失败 | 服务未启动 | `node server.js` |
| 扩展显示断开 | 需手动启用 | popup 中开启开关 |
| 正文字数 = 0 | 使用旧版 OpenCLI | 使用 web-fetcher |
| 标题选择器过时 | 知乎更新编辑器 | 检查 DevTools 更新选择器 |

---

## ⚠️ OpenCLI 已知限制（已弃用）

以下方法**都报告成功但知乎不识别内容**：

| 方法 | 结果 | 说明 |
|------|------|------|
| `opencli browser type` | innerHTML 有内容，字数=0 | 框架不响应 DOM 操作 |
| `document.execCommand('insertText')` | innerHTML 有内容，字数=0 | 同上 |
| Clipboard API + paste | 同上 | 安全限制 |

**根本原因**：知乎使用 Draft.js 编辑器，`opencli browser type` 只做 DOM 操作，无法触发框架内部状态。

---

## 与其他技能的关系

```
mcn-hotspot-research  → 热点调研
         ↓
mcn-topic-selector    → 选题分析
         ↓
mcn-content-writer    → 内容生成
         ↓
mcn-zhihu-publisher   → 知乎草稿（本技能）
         ↓
[用户手动发布]
```

---

## 相关技能

- `mcn-wechat-publisher`: 微信公众号发布（有官方 API）
- `mcn-content-writer`: 内容生成
- `web-fetcher`: 页面抓取和控制（本技能依赖）
- `opencli-browser-api`: OpenCLI browser API（旧方案，已弃用）