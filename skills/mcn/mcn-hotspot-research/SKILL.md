---
name: mcn-hotspot-research
description: MCN热点调研技能 - 抓取百度热搜数据，分析筛选科技/AI话题，生成Top 5推荐并保存本地
version: 1.0
created: 2026-05-04
---

# MCN 热点调研技能

## 任务流程

1. 访问百度热搜页面
2. 提取热搜数据（标题+热度）
3. 筛选科技话题关键词
4. 按热度排序取 Top 5
5. 保存到本地目录
6. 推送到飞书（如配置可用）

---

## 核心步骤

### 1. 访问百度热搜

```
browser_navigate("https://top.baidu.com/board?tab=realtime")
```

### 2. 提取数据 - XPath 方式

```javascript
// 在 browser_console 中执行
const items = [];
const categoryItems = document.querySelectorAll('.category-wrap_iQLoo.horizontal_1eKyQ');
categoryItems.forEach((item, index) => {
  const titleEl = item.querySelector('.content_1YWBm');
  const hotEl = item.querySelector('.hot-index_1Bl1a');
  if (titleEl && hotEl) {
    items.push({
      rank: index + 1,
      title: titleEl.textContent.trim(),
      hot: hotEl.textContent.trim()
    });
  }
});
JSON.stringify(items, null, 2);
```

### 3. 筛选科技话题关键词

```python
tech_keywords = [
    'AI', 'ai', '科技', '互联网', '芯片', '大模型', 
    '智能', '数据', '算法', '新能源', '量化', 
    '豆包', '字节', '腾讯', '阿里', '百度', 
    '华为', '小米', 'openai', 'gpt', 'claude', 
    'app', 'App', 'APP', '数字化', '云计算', 
    '自动驾驶', '机器人', '风电'
]
```

### 4. 保存路径

```
/Users/hy_timesky/Documents/My_Obsidian/mcn/hotspot/{YYYY-MM-DD}/hotspots.json
/Users/hy_timesky/Documents/My_Obsidian/mcn/topic/{YYYY-MM-DD}/recommend.md
```

**日期格式统一使用 YYYY-MM-DD（带分隔符，如 2026-05-05）**

**⚠️ 版本管理重要说明**

定时任务每日三次执行（6:30, 10:30, 16:30），每次执行会**覆盖**上述两个文件。用户在飞书收到推送时，文件可能已被后续执行覆盖为新版本。

**下游技能衔接规则**：必须读取**最新文件**，不要根据推送时间去找旧版本。
```python
# 正确：始终读取最新
topic_file = f"{kb_root}/mcn/topic/{date}/recommend.md"
hotspot_file = f"{kb_root}/mcn/hotspot/{date}/hotspots.json"
```

---

## Pitfalls

### 1. Cron 环境变量不可用

**问题**: 定时任务(cron)执行时，shell 子进程无法获取父进程的环境变量

```
# 在父进程中可用
echo $FEISHU_APP_ID  # 输出: cli_xxx

# 但在 terminal() 子进程中为空
terminal('echo $FEISHU_APP_ID')  # 输出: (空)
```

**解决方案**:
- 方案A: 在 skill 中硬编码凭证（不推荐）
- 方案B: 使用 `execute_code` 读取环境变量（推荐）
- 方案C: 将凭证写入配置文件，脚本读取配置
- 方案D: 使用 process 工具启动带环境变量的进程

**验证方法**:
```python
import os
# execute_code 中可以获取
app_id = os.environ.get('FEISHU_APP_ID', '')
```

### 2. Emoji 变体选择符触发安全扫描

**问题**: 带 emoji 的消息文本会触发 Security Scan 阻止执行

```
# 触发 Security Scan
1️⃣ 豆包将上线付费服务  # 包含 VS1-256 变体选择符
```

**解决方案**: 使用纯文本格式替代 emoji

```
# 推荐格式
[1] 豆包将上线付费服务
```

### 3. Shell 转义问题

**问题**: 消息内容含特殊字符时，shell heredoc 可能出错

**解决方案**: 使用 `--rawfile` 而非 `--arg`

```bash
# ✅ 推荐方式
jq -n --rawfile msg /tmp/content.txt '{content: $msg}'

# ❌ 避免方式
jq -n --arg msg "$CONTENT" '{content: $msg}'
```

---

## 输出格式

### Markdown 报告模板

```markdown
# 百度热搜科技话题 Top 5

**日期**: {YYYY-MM-DD}

---

## 1. {标题}

- 热搜指数: **{热度}**
- 排名: 第 {n} 位

{话题简介}

---

> 数据来源: 百度热搜 | 抓取时间: {HH:MM:SS}
```

---

## 相关技能

- `mcn-topic-selector` - 选题分析
- `mcn-content-writer` - 内容生成
- `feishu-message-push` - 飞书推送