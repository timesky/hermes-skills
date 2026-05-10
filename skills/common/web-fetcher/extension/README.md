# Hermes Web Fetcher - 通用网页抓取扩展

受 Accio Browser Relay 启发的通用 Chrome 扩展，用于抓取任何网站的内容。

## 核心特性

- ✅ **通用性**: 支持任何网站，不只是知乎
- ✅ **复用 Cookies**: 使用用户已登录的会话
- ✅ **避免封禁**: 通过 chrome.scripting API，不是直接 CDP
- ✅ **双路径提取**: Simple walker + Scoring-based（参考 Accio）
- ✅ **Manifest V3**: 最新 Chrome 扩展标准

## 安装

### 1. 加载扩展

1. 打开 Chrome 浏览器
2. 访问 `chrome://extensions/`
3. 启用 **开发者模式**
4. 点击 **加载已解压的扩展程序**
5. 选择目录：`~/.hermes/browser-extension/web-fetcher/`

### 2. 验证

加载成功后看到：
- 名称：Hermes Web Fetcher
- 版本：0.1.0

## 使用

### 方法一：扩展 Popup

1. 打开任何网页
2. 点击扩展图标
3. 选择：
   - 📄 获取页面信息
   - 📋 抓取列表/收藏夹
   - 📖 抓取当前文章

### 方法二：预设网站

Popup 提供快捷按钮：
- 知乎收藏夹
- GitHub Trending

### 方法三：Hermes Agent 集成

```python
# 通过 Hermes Agent 调用
from hermes_tools import browser

# 抓取列表
list_data = browser.execute_script("""
  fetchList(tabId, {
    itemSelector: '.post',
    titleSelector: 'h2',
    linkSelector: 'a'
  })
""")

# 抓取文章
article = browser.execute_script("""
  fetchArticle(tabId)
""")
```

## 文件结构

```
web-fetcher/
├── manifest.json       # Manifest V3 配置
├── background.js       # Service Worker（消息路由）
├── content.js          # 核心内容提取
│   ├── fetchList()     # 抓取列表
│   ├── fetchArticle()  # 抓取文章（双路径）
│   ├── navigateToUrl() # 导航
│   └── getPageInfo()   # 页面信息
├── popup.html/js       # 用户界面
├── fetcher.py          # Python 集成
└── README.md           # 文档
```

## API 参考

### fetchList(tabId, options)

抓取页面列表（收藏夹、搜索结果等）

```javascript
{
  itemSelector: '[data-zop], article, .post',  // 列表项选择器
  titleSelector: 'h2, .title',                  // 标题选择器
  linkSelector: 'a[href]',                      // 链接选择器
  authorSelector: '.author',                    // 作者选择器
  dateSelector: 'time',                         // 日期选择器
  idPattern: '/p/(\\d+)',                       // ID 提取正则
  maxItems: 100                                 // 最大数量
}
```

返回：
```javascript
{
  items: [...],           // 文章列表
  pageInfo: { currentPage, totalPages },
  totalItems: 20,
  url: '...'
}
```

### fetchArticle(tabId)

抓取完整文章内容（双路径提取）

返回：
```javascript
{
  title: '...',
  content: '...',      // Markdown 格式
  author: '...',
  date: '...',
  url: '...',
  method: 'walker' | 'scoring' | 'body-fallback'
}
```

## 内容提取策略

参考 Accio 的 `extract-readability.js`：

### Path 1: Simple Walker
- 遍历 DOM 树
- 提取文本、标题、列表、链接
- 保留基本 Markdown 格式

### Path 2: Scoring-based
- 计算每个元素的内容得分
- 考虑段落数、链接密度、逗号数
- 识别主要内容区域

### 智能选择
- 选择较长的结果
- 如果都太短，回退到 body.innerText

## 支持的场景

| 场景 | 支持 | 配置 |
|------|------|------|
| 知乎收藏夹 | ✅ | 预设 |
| 知乎文章 | ✅ | 自动 |
| GitHub Trending | ✅ | 预设 |
| 博客文章 | ✅ | 自动 |
| 新闻网站 | ✅ | 自动 |
| 论坛帖子 | ✅ | 自动 |
| 文档页面 | ✅ | 自动 |

## 与 Accio 对比

| 功能 | Accio | Hermes Web Fetcher |
|------|-------|-------------------|
| 目标 | 通用 Agent 工具 | 通用内容抓取 |
| 复杂度 | 高（完整框架） | 中（专注抓取） |
| 内容提取 | 双路径 + 评分 | 双路径 + 评分 |
| CDP 使用 | 通过 relay | 可选 |
| 预设网站 | 少 | 可扩展 |

## 故障排除

### 扩展无法加载
- 检查 Chrome 版本（需要 88+ 支持 MV3）
- 检查 manifest.json 格式
- 查看 chrome://extensions/ 错误信息

### 无法获取内容
- 确保页面已完全加载
- 检查浏览器控制台（F12）
- 确认网站没有反爬机制

### 提取内容为空
- 尝试不同的选择器
- 检查是否是 SPA（需要等待渲染）
- 使用 scoring 方法回退

## 扩展开发

### 添加新网站支持

在 `SITE_CONFIGS` 中添加：

```python
'new_site': {
    'name': 'Site Name',
    'url_pattern': r'site\.com',
    'id_pattern': r'/id/(\d+)',
    'category_map': {...}
}
```

### 自定义选择器

通过 `fetchList()` 的 options 参数：

```javascript
fetchList(tabId, {
    itemSelector: '.custom-item',
    titleSelector: '.custom-title h2'
})
```

## 许可证

MIT License

## 致谢

灵感来自：
- [Accio Browser Relay](https://accio.com) - 架构参考
- Mozilla Readability - 内容提取算法
- Hermes Agent - 集成平台
