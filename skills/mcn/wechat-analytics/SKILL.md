---
name: wechat-analytics
description: 微信公众号内容分析技能 - 抓取发布历史、获取文章数据指标（阅读/点赞/转发/收藏）、检测登录状态、生成分析报告。使用 web-fetcher 实现。
category: mcn
created: 2026-04-18
updated: 2026-05-04
---

# 微信公众号数据分析技能

## 触发场景

- 用户要求分析公众号文章数据（阅读、点赞、转发、收藏）
- 每日/每周数据分析流程
- 需要优化内容创作策略
- 分析爆款文章的成功因素
- 更新已发布文章列表（用于选题过滤）

## 前置条件

1. **web-fetcher 扩展已安装并连接**（v2.2.0+）
2. **用户已登录公众号后台**（mp.weixin.qq.com）
3. 登录过期时可截屏二维码让用户扫码

## 关键页面路径配置

详见 `references/mp_api_paths.md`，包含：
- 首页、已发布文章列表、草稿管理等关键页面 URL
- 文章数据字段结构（read_num, like_num, share_num 等）
- Token 过期处理方法

**⚠️ Token 会过期**，每次使用前检测登录状态

## 执行流程

### 1. 启动 WebSocket 服务

```python
# Hermes 自动启动 web-fetcher 服务
# 端口: ws://localhost:9234
```

### 2. 检测登录状态和账号

```bash
python ~/.hermes/skills/mcn/wechat-analytics/scripts/fetch-published-stats.py
```

脚本会：
1. 打开公众号主页
2. 检测是否登录过期
3. 确认当前公众号账号名称
4. 提取 token 用于后续抓取

### 3. 登录过期处理

如果检测到 token 过期：
1. 截屏当前页面（可能显示二维码）
2. 保存到 `~/.hermes/mcn_qrcode.png`
3. 通知用户扫码登录
4. 用户登录后重新运行脚本

### 4. 抓取发布历史

```bash
# 抓取最近 N 页（每页 20 篇）
python fetch-published-stats.py --pages 10

# 手动指定 token
python fetch-published-stats.py --token 123456789
```

抓取内容：
- 文章标题
- 发布日期
- 阅读数
- 点赞数
- 转发数
- 收藏数
- 文章链接

### 5. 生成分析报告

报告自动保存到：
- `~/mcn/published_stats.json` - 原始数据
- `~/mcn/published_report.md` - 分析报告
- `~/.hermes/mcn_published.json` - 已发布列表（用于选题过滤）

## 报告内容

```
📊 公众号内容分析报告

【数据概览】
- 总阅读量: XXX
- 总点赞量: XXX
- 平均阅读量: XX
- 平均点赞量: XX

【TOP 10 热门文章】
| 排名 | 标题 | 阅读 | 点赞 | 转发 | 收藏 |
...

【低阅读量文章】
- 分析低阅读原因（标题、内容、话题等）

【互动率分析】
- 阅转率: 转发/阅读
- 阅藏率: 收藏/阅读
- 阅赞率: 点赞/阅读

【爆款分析】
- 高阅读文章的共同特征
- 话题选择、标题风格、内容类型
```

## 爆款文章分析方法

当用户询问某篇文章为什么阅读量高时：

1. **提取文章特征**
   - 标题关键词分析
   - 内容类型（热点解读、技术干货、情感共鸣）
   - 发布时间

2. **对比同类文章**
   - 同话题文章的阅读差异
   - 标题风格对比

3. **分析互动数据**
   - 高转发 → 话题有传播性
   - 高收藏 → 内容有实用价值
   - 高点赞 → 内容有共鸣

4. **可能原因**
   - **话题劲爆**：热点事件、争议话题
   - **内容共情**：引发读者情感共鸣
   - **实用干货**：有收藏价值的技术内容
   - **标题吸引**：好奇心、悬念、数字
   - **槽点共鸣**：说出公众想说的话

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| Token 过期 | 脚本自动截屏二维码，用户扫码后重试 |
| 多账号错乱 | 脚本检测当前账号名称，确认无误后继续 |
| 统计数据不全 | 部分文章可能无统计数据，脚本会跳过 |
| 抓取中断 | 络问题可重试，已抓取数据会保存 |
| ModuleNotFoundError: websockets | 运行 `pip3 install websockets` 安装依赖 |
| ModuleNotFoundError: hermes_web_fetcher | web-fetcher 扩展未安装，使用**���览器备选方案**（见下方） |
| 飞书推送失败 | 检查 FEISHU 环境变量是否配置（见下方） |

## ⚠️ 浏览器备选方案（web-fetcher 不可用时）

当 `hermes_web_fetcher` 模块不存在时，使用 browser 工具直接操作：

### 完整登录检测流程

```
# 1. 检测登录状态
browser_navigate("https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN")

# 2. 如果显示"登录超时"，跳转到主页获取二维码
browser_navigate("https://mp.weixin.qq.com")

# 3. 点击登录按钮显示二维码
browser_click("登录")  # ref=e13 或类似

# 4. 截取二维码（vision可能超时，但截图仍会保存）
browser_vision(question="获取登录二维码")

# 5. 复制截图到标准位置
# 原始: ~/.hermes/profiles/mcn/cache/screenshots/browser_screenshot_*.png
# 复制到: ~/.hermes/mcn_qrcode.png
```

### 已知问题

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| browser_vision 超时 | Request timed out | 截图仍会保存，直接使用 screenshot_path |
| 首页无二维码 | 登录页需要点击"登录" | 先访问主页，点击登录按钮 |
| 飞书通知失败 | Gateway 未运行 | 需确保 localhost:18789 可达 |

### 飞书通知前置条件

通知依赖 **Hermes Gateway** 运行：
```bash
# 检查 Gateway 状态
curl http://localhost:18789/health

# 如果未运行，飞书推送会失败
```

**限制**: 浏览器方案无法自动抓取统计数据，只能检测登录状态和截屏。完整数据抓取需 web-fetcher 扩展。

## 飞书通知配置

需要配置以下环境变量（在 mcn_config.yaml 或系统环境变量）：

```bash
FEISHU_APP_ID=cli_xxx          # 飞书应用ID
FEISHU_APP_SECRET=xxx          # 飞书应用密钥
FEISHU_HOME_CHANNEL=oc_xxx     # 默认推送群聊ID
```

**当前状态**: mcn profile 未配置飞书环境变量，通知功能不可用

## 依赖要求

1. **Python 模块**: `websockets`（必须）
   ```bash
   pip3 install websockets
   ```

2. **环境变量检查**:
   - `FEISHU_APP_SECRET` 不能是遮盖值（`***`）
   - `FEISHU_HOME_CHANNEL` 需要配置正确的飞书群 ID

## 输出物

- `~/mcn/published_stats.json` - 文章统计数据
- `~/mcn/published_report.md` - 分析报告
- `~/.hermes/mcn_published.json` - 已发布列表（选题过滤用）
- `~/.hermes/mcn_qrcode.png` - 登录二维码（过期时）

## 相关技能

- mcn-wechat-publisher：发布文章到公众号
- mcn-content-writer：生成公众号文章内容
- mcn-topic-selector：选题分析（使用已发布列表过滤）
- web-fetcher：网页抓取和控制

---

*Last updated: 2026-04-24 by Luna (added mp_api_paths.md reference)*