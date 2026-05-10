---
name: mcn-workflow-fallback
description: MCN工作流降级执行方案 - 当主技能不可用时的完整执行方法
tags: [mcn, fallback, cron, analytics]
version: 1.0.0
created: 2026-04-30
---

# MCN Workflow Fallback 执行方案

当 MCN 主技能（wechat-analytics, mcn-content-writer 等）不可用时，使用本技能执行降级分析。

## 触发条件

- 定时任务启动但 `wechat-analytics` 技能缺失
- `mcn-topic/` 目录不存在（无原文/竞品预抓取数据）
- 公众号登录已过期，无法获取最新数据

## 降级执行流程

### Step 1: 检查可用数据源

```bash
# 检查缓存数据
cat mcn/published_stats.json | jq 'length'

# 检查历史报告
ls -la mcn/closed_loop_report*.md

# 检查今日内容
find mcn/content/$(date +%Y-%m-%d) -name "*.md" 2>/dev/null
```

### Step 2: 分析缓存数据

**数据文件**: `mcn/published_stats.json`
**字段结构**:
```json
{
  "title": "文章标题",
  "url": "微信公众号链接",
  "read_count": 阅读数,
  "like_count": 点赞数,
  "share_count": 转发数,
  "fav_count": 收藏数,
  "送达": 送达数
}
```

**分析方法**:
1. 统计总量（总阅读、总点赞、总转发）
2. 筛选高表现文章（点赞排序 Top 10）
3. 识别失败模式（如"数据揭示了什么"全部零阅读）
4. 计算互动率（有互动文章数 / 总文章数）

### Step 3: 对比分析（数据可用时）

如果存在 `mcn/topic/{date}/sources/topic-{idx}/`:
- 读取 `source.json` 获取原文数据
- 读取 `competitors.json` 获取竞品数据
- 对比我们的文章 vs 原文/竞品的阅读、点赞

### Step 4: 生成报告

**报告模板**:
```markdown
## MCN 闭环分析报告 - {日期}

### ⚠️ 技能状态
[列出缺失的技能]

### 📊 数据概览（缓存数据）
[统计数据表格]

### 🏆 高表现文章
[Top 5 点赞]

### 📉 低表现分析
[失败模式识别]

### 📅 今日内容生产状态
[检查 mcn/content/{date}/ 目录]

### 🔄 下一步行动
[P0/P1/P2 优先级列表]
```

### Step 5: 推送通知

**飞书推送**（使用 curl）:
```bash
# 获取 token
TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
    -H "Content-Type: application/json" \
    -d '{"app_id":"'$FEISHU_APP_ID'","app_secret":"'$FEISHU_APP_SECRET'"}' | jq -r '.tenant_access_token')

# 发送消息
curl -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"receive_id":"'$FEISHU_HOME_CHANNEL'","msg_type":"text","content":"{\"text\":\"报告内容\"}"}'
```

**注意**: 如果认证失败，保存报告到本地 `mcn/closed_loop_report_{date}.md`

## 关键发现记录

### 失败模式库

| 模式 | 证据 | 建议 |
|------|------|------|
| "数据揭示了什么"副标题 | 11篇100%零阅读 | **立即禁用** |
| AI痕迹词（揭秘、背后的真相） | 表现差 | 减少使用 |
| 热点搬运无原创观点 | 零互动 | 增加深度分析 |

### 成功模式库

| 模式 | 证据 | 建议 |
|------|------|------|
| 垂直领域教程 | NAS/Jellyfin avg_likes=36.2 | ⭐⭐⭐⭐⭐ |
| 情感共鸣/避坑 | "玩不起的七牛" 69赞 | ⭐⭐⭐⭐ |
| 问题解决导向 | 精准受众匹配 | ⭐⭐⭐⭐ |

## P0 行动清单

当降级执行时，必须报告以下 P0 问题：

1. **重新登录公众号** - 数据已过时
2. **发布今日文章** - 内容已生成未发布
3. **移除失败模板** - "数据揭示了什么"模式
4. **安装缺失技能** - wechat-analytics, mcn-content-writer

## 注意事项

1. 缓存数据会过时，必须标注"数据未更新"
2. 无原文/竞品数据时跳过对比分析
3. 飞书推送失败时保存本地报告
4. 报告必须包含"下一步行动"表格

---

*Created: 2026-04-30*
*Author: Luna*