---
name: mcn-hotspot-research
description: |
  MCN 热点调研技能 - 抓取微博热搜、虎嗅、36kr 等平台热点数据。
  
  触发词：热点调研、热搜抓取、今日热点、热点聚合、mcn热点
  
  可独立调用，也可被 my-mcn-manager 在阶段1调度。
parent: my-mcn-manager
tags: [mcn, hotspot, research, weibo, huxiu, 36kr, opencli]
version: 1.4.0
created: 2026-04-15
updated: 2026-04-18
---

# MCN 热点调研

抓取多平台热点数据，聚合输出供选题分析使用。

---

## 功能闭环与产出交付

**职责**：独立完成热点调研阶段所有工作。

| 项目 | 说明 |
|------|------|
| 输入 | `--date {日期}` |
| 产出位置 | `mcn/hotspot/{date}/hotspot.json` |
| 状态返回 | `{"status": "success", "output_path": "...", "date": "..."}` |

**衔接机制**：
- 下游技能 `mcn-topic-selector` 从约定位置读取热点数据
- 不需要参数传递，约定优于配置

---

## 配置来源

**约定优于配置 + 技能独立性**

- 配置文件：`~/.hermes/mcn_config.yaml`（唯一外部依赖）
- 目录约定：脚本内联解析，不依赖其他技能模块
- 输出目录：`mcn/hotspot/{date}/`

脚本不导入其他技能目录下的模块。详见入口技能 `references/config.md`。

---

## 触发场景

| 用户输入 | 响应 |
|----------|------|
| "热点调研" | 执行完整热点抓取 |
| "今日热点" | 执行完整热点抓取 |
| "热搜抓取" | 执行完整热点抓取 |

---

## 数据源

| 平台 | 数据类型 | 抓取方式 |
|------|----------|----------|
| 微博 | 实时热搜榜 | OpenCLI `weibo hot` |
| 虎嗅 | 科技/商业文章 | OpenCLI browser |
| 36kr | 科技新闻 | OpenCLI browser |

---

## 输出

```
~/backup/知识库-Obsidian/mcn/hotspot/{日期}/
├── hotspot-weibo.json       # 微博热搜（50条）
├── hotspot-huxiu-tech.md    # 虎嗅科技文章
├── hotspot-huxiu-3c.md      # 虎嗅3C数码
├── hotspot-36kr-tech.md     # 36kr科技频道
└── hotspot-aggregated.md    # 聚合报告（供选题分析）
```

---

## 执行方式

### Terminal 直接执行（OpenCLI）

```bash
eval "$(pyenv init -)" && python3 ~/.hermes/skills/mcn/mcn-hotspot-research/scripts/run-hotspot-research.py --date 2026-04-15
```

### Playwright 备用方案（OpenCLI 不可用时）

```bash
eval "$(pyenv init -)" && playwright install chromium && python3 ~/.hermes/skills/mcn/mcn-hotspot-research/scripts/hotspot-playwright.py 2026-04-15
```

### 模拟数据 Fallback（浏览器无法启动时）

```bash
eval "$(pyenv init -)" && python3 ~/.hermes/skills/mcn/mcn-hotspot-research/scripts/generate-mock-data.py 2026-04-15
```

**适用场景**：
- macOS 系统框架缺失导致 Chromium/Firefox 无法启动
- 网络问题导致浏览器下载超时
- 流程演示/测试
- 环境未配置完成时的临时方案

### 参数

```bash
python3 run-hotspot-research.py --date 2026-04-15
python3 hotspot-playwright.py 2026-04-15  # 备用方案
```

---

## 被父技能调度

my-mcn-manager 在阶段1调用：

```markdown
## 阶段 1: 热点调研

调用子技能：mcn-hotspot-research

执行脚本获取今日热点数据。
产出：mcn/hotspot/{date}/hotspot.json
```

---

## Pitfalls

| 问题 | 解决方案 |
|------|----------|
| OpenCLI 未安装 | `which opencli` 检查。未安装时直接使用 Playwright 备用方案。 |
| OpenCLI daemon 未运行 | 先启动 daemon：`opencli browser start --port 19825` |
| 虎嗅解析失败 | 检查 `### 标题` 格式，脚本已适配 |
| Node.js undici 错误 | OpenCLI 在 Node v20/v22 都有 undici 版本兼容问题（`webidl.util.markAsUncloneable is not a function`）。**备用方案**：使用 Playwright 直接抓取，见 `scripts/hotspot-playwright.py` |
| 知乎热榜抓取失败 | 知乎页面结构频繁变化，JavaScript 渲染内容需要等待加载。Playwright 方案已增加 `wait_for_timeout(3000)`，但仍可能返回 0 条。**接受部分数据**：workflow 可从其他来源（微博、36kr、虎嗅）完成。 |
| Playwright chromium 下载超时 | 首次下载可能超时（150MB）。**重试即可**，第二次通常成功。或手动预安装：`playwright install chromium` |
| Playwright 模块未安装 | `pip3 install playwright` + `playwright install chromium`（两步都需要） |
| Playwright 版本不匹配 | **问题**：Python playwright 与 Node playwright-core 维护独立的浏览器缓存，版本号不同。Python 1.48.0 期望 chromium-1140，但系统可能已安装 chromium-1217（来自 hermes-agent node_modules），导致 "Executable doesn't exist at...chromium-1140" 错误。**解决方案**：(1) 重新安装对齐版本：`pip3 uninstall playwright && pip3 install playwright && playwright install chromium`；(2) 检查缓存目录：`ls ~/Library/Caches/ms-playwright/` 确认浏览器版本；(3) 紧急备用：使用模拟数据完成流程演示。 |
| Playwright 浏览器下载超时（180s） | **问题**：`playwright install chromium` 下载 174MB 可能超时。**解决方案**：(1) 增加 timeout 重试；(2) 检查缓存目录 `ls ~/Library/Caches/ms-playwright/` 确认是否已有部分下载；(3) 如已有其他版本（如 chromium-1217），可修改脚本使用该版本路径；(4) 最终备用：生成模拟数据完成流程。 |
| Playwright chromium 启动失败（macOS 系统框架缺失） | **问题**：`BrowserType.launch: Library not loaded: /System/Library/Frameworks/LocalAuthenticationEmbeddedUI.framework`。**原因**：新版 Chromium（1217+）依赖 macOS 较新系统框架，旧 macOS 版本（如 11.x/12.x）缺失此框架。**解决方案**：(1) 尝试 Firefox：修改脚本为 `p.firefox.launch()`，但需确保版本匹配；(2) 如 Firefox 也失败，直接使用模拟数据 fallback。**注意**：Firefox 也可能存在版本不匹配问题（如期望 firefox-1466 但缓存只有 firefox-1465），此时优先改用 Chromium。 |
| Playwright 版本不匹配 - 软连接无效 | **问题**：创建软连接 `ln -s chromium-1217 chromium-1140` 后仍然报错。**原因**：Chromium 是完整应用包，内部路径硬编码，软连接无法欺骗。**解决方案**：修改脚本指定明确的 `executable_path`，或直接安装正确版本。 |
| Firefox 页面导航失败 | **问题**：浏览器启动成功但 `page.goto()` 返回 "Target page, context or browser has been closed"。**原因**：Firefox 无头模式在某些 macOS 版本上不稳定。**解决方案**：增加重试逻辑，或直接使用模拟数据 fallback。 |
| Firefox 版本不匹配 | **问题**：`BrowserType.launch: Executable doesn't exist at .../firefox-1466/...`。**原因**：Python playwright 期望的 Firefox 版本与缓存中的版本不一致（如期望 1466 但只有 1465）。**解决方案**：(1) 检查缓存：`ls ~/Library/Caches/ms-playwright/` 确认可用版本；(2) **优先改用 Chromium**：修改 `hotspot-playwright.py` 为 `p.chromium.launch()`；(3) 或安装匹配版本：`playwright install firefox`。 |
| 部分数据源失败 | 正常现象。38 条热点（微博 3 条 +36kr 20 条 + 虎嗅 15 条）已足够选题分析。不要求所有源都成功。 |

---

## 执行前检查清单

**按优先级依次检查**：

```bash
# 1. 检查 OpenCLI（首选方案）
which opencli && opencli --version

# 2. 检查 Playwright（备用方案）
python3 -c "import playwright" && ls ~/Library/Caches/ms-playwright/chromium-*

# 3. 如两者都不可用，准备模拟数据 fallback
```

**决策流程**：
```
OpenCLI 可用？
├─ 是 → 使用 OpenCLI 抓取
└─ 否 → Playwright 可用？
         ├─ 是 → 尝试 Chromium 启动（优先）
         │        ├─ 成功 → 使用 Playwright 抓取
         │        └─ 失败 → 尝试 Firefox
         │                 ├─ 成功 → 使用 Firefox 抓取
         │                 └─ 失败（版本不匹配/导航错误）→ 模拟数据 fallback
         └─ 否 → 生成模拟数据（流程演示/测试）
```

---

## 模拟数据 Fallback

当 OpenCLI 和 Playwright 都不可用时，使用模拟数据完成流程演示：

### 使用脚本（推荐）

```bash
python3 ~/.hermes/skills/mcn/mcn-hotspot-research/scripts/generate-mock-data.py 2026-04-18
```

**产出**：
- `mcn/hotspot/{date}/hotspot.json` - 20 条模拟热点数据
- `mcn/hotspot/{date}/hotspot-aggregated.md` - 聚合报告（含来源统计）

### 手动生成（旧方法）

```python
# 生成模拟热点数据（保存到约定位置）
python3 -c "
import json, os
from datetime import datetime

date = '2026-04-18'
output_dir = '/Users/timesky/backup/知识库-Obsidian/mcn/hotspot/' + date
os.makedirs(output_dir, exist_ok=True)

articles = [
    {'title': '腾讯发布混元大模型 3.0', 'platform': '微博', 'source': 'weibo', 'url': 'https://s.weibo.com/...'},
    # ... 更多模拟数据
]

with open(output_dir + '/hotspot.json', 'w') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)
"
```

**适用场景**：
- 流程演示/测试
- 网络问题导致抓取失败
- 环境未配置完成时的临时方案
- macOS 系统框架缺失导致浏览器无法启动

**注意**：模拟数据仅用于流程验证，正式生产环境应使用真实抓取数据。

---

## 相关技能

- **my-mcn-manager** - 父技能，完整 MCN 流程
- **mcn-topic-selector** - 下游技能，从约定位置读取热点数据

---

*Version: 1.1.0 - 功能闭环 + 产出交付规范*