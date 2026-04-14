# my-mcn-manager 使用指南

## 快速开始

### 方式 1：自动触发（推荐）

技能描述已配置触发词，提到以下关键词会自动触发：
- 公众号文章
- 自动发布
- MCN 发布
- 热点调研
- 选题分析

### 方式 2：命令行执行

```bash
cd ~/.hermes/skills/mcn/my-mcn-manager

# 完整流程
python scripts/run-full-workflow.py

# 只调研热点
python scripts/run-hotspot-research.py --date 2026-04-14

# 分析选题
python scripts/run-topic-analysis.py --date 2026-04-14 --top 5

# 生成并发布文章
python scripts/publish_after_confirm.py "主题名" --style professional

# 验证文章
python scripts/validate-article.py --article article.md
```

---

## 工作流说明

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  阶段 1      │ → │  阶段 2      │ → │  阶段 3      │ → │  阶段 4      │
│  热点调研   │   │  选题分析   │   │  内容生成   │   │  发布草稿   │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
     ↓                   ↓                   ↓                   ↓
tmp/hotspot/      tmp/topic/          tmp/content/        公众号草稿箱
YYYY-MM-DD/       recommend.md        article.md          media_id: xxx
```

---

## 脚本说明

### run-hotspot-research.py

**功能**：抓取多平台热搜

**参数**：
- `--date`: 指定日期（默认今天）
- `--platforms`: 指定平台（逗号分隔）
- `--limit`: 每个平台抓取条数（默认 20）

**示例**：
```bash
# 抓取今天的热搜
python scripts/run-hotspot-research.py

# 抓取指定日期
python scripts/run-hotspot-research.py --date 2026-04-14

# 只抓取微博和知乎
python scripts/run-hotspot-research.py --platforms weibo,zhihu --limit 30
```

**输出**：
```
tmp/hotspot/2026-04-14/
├── weibo-hotspot.md
├── zhihu-hotspot.md
└── toutiao-hotspot.md
```

---

### run-topic-analysis.py

**功能**：分析热搜数据，生成推荐主题

**参数**：
- `--date`: 指定日期
- `--top`: 推荐主题数量（默认 5）
- `--output`: 输出文件路径

**示例**：
```bash
# 分析今天的热搜
python scripts/run-topic-analysis.py

# 分析指定日期，推荐 3 个主题
python scripts/run-topic-analysis.py --date 2026-04-14 --top 3
```

**输出**：
```markdown
# MCN 选题分析报告

## 推荐主题 (Top 5)

| 排名 | 主题 | 领域 | 热度 | 综合评分 | 来源 |
|------|------|------|------|----------|------|
| 1 | xxx | 科技 | 12345 | 85.5 | [查看](url) |
```

---

### publish_after_confirm.py

**功能**：确认主题后生成文章并发布

**参数**：
- `<主题>`: 文章主题（必需）
- `--style`: 文章风格（professional/casual/story）

**示例**：
```bash
python scripts/publish_after_confirm.py "AI 定价策略分析" --style professional
```

**流程**：
1. 获取 access_token
2. 生成文章内容
3. 生成配图（待实现）
4. 上传封面图（900x500）
5. 上传正文配图
6. 创建草稿

**输出**：
```json
{
  "status": "success",
  "topic": "AI 定价策略分析",
  "media_id": "qDGcf6yeX9zHjtEpm0mrI...",
  "title": "AI 定价策略分析"
}
```

---

### validate-article.py

**功能**：验证文章是否符合发布标准

**参数**：
- `--article`: 文章路径（必需）
- `--json`: 输出 JSON 格式

**示例**：
```bash
python scripts/validate-article.py --article tmp/content/2026-04-14/article.md
```

**验证项**：
- ✓ 字数：1500-2000 字
- ✓ 标题：≤64 字符
- ✓ 摘要：≤120 字符
- ✓ 配图：3-5 张
- ✓ 品牌名：已替换
- ✓ 去 AI 化评分：≥45

---

### update-config.py

**功能**：更新 MCN 配置

**参数**：
- `--set`: 设置配置（格式：key=value）

**示例**：
```bash
# 修改关注领域
python scripts/update-config.py --set "hotspot.domains=[科技，AI,投资]"

# 修改字数要求
python scripts/update-config.py --set "article.min_chars=1800"
```

---

## 配置文件

### 主配置：~/.hermes/mcn_config.yaml

```yaml
# 文章要求
article:
  min_chars: 1500
  max_chars: 2000
  min_images: 3
  max_images: 5

# 热点领域
hotspot:
  domains:
    - name: 科技
      keywords: [科技，数码，手机，AI]
      platforms: [weibo, zhihu, toutiao]
      top_n: 10

# 配图生成
image_generation:
  default_provider: grsai
  providers:
    grsai:
      api_url: https://api.grsai.com/v1/draw/nano-banana
      cost_per_image: 440
```

### 公众号配置：~/.hermes/wechat_mp_config.yaml

```yaml
appid: wx47533ce9c8854fb5
secret: 2b990fc5...eb2f
author: TimeSky
```

---

## 输出目录结构

```
~/backup/知识库-Obsidian/tmp/
├── hotspot/YYYY-MM-DD/      # 热搜原始数据
├── topic/YYYY-MM-DD/        # 选题分析报告
├── content/YYYY-MM-DD/      # 生成的文章 + 配图
│   ├── article.md
│   └── images/topic-name/
│       ├── img_1.png
│       └── img_2.png
└── publish/YYYY-MM-DD/      # 发布记录
```

---

## 常见问题

### Q1: 热搜抓取失败

**原因**：OpenCLI 未启动或配置错误

**解决**：
```bash
source ~/.nvm/nvm.sh && nvm use 22
opencli doctor  # 检查连接状态
```

### Q2: 公众号发布报错 40164

**原因**：IP 白名单未配置

**解决**：
1. 登录公众号后台
2. 设置与开发 → 基本配置
3. IP 白名单 → 添加当前机器 IP

### Q3: 配图数量不足

**原因**：AI 图片生成失败或 API 额度不足

**解决**：
1. 检查 GrsAI 积分余额
2. 手动添加配图到 `images/` 目录
3. 重新运行验证脚本

### Q4: 文章字数不够

**解决**：
```bash
# 验证脚本会自动检测
python scripts/validate-article.py --article article.md

# 如果字数不足，手动补充内容或重新生成
```

---

## 定时任务配置

```bash
# 编辑 crontab
crontab -e

# 添加任务
0 17 * * * cd ~/.hermes/skills/mcn/my-mcn-manager && python scripts/run-hotspot-research.py
30 17 * * * cd ~/.hermes/skills/mcn/my-mcn-manager && python scripts/run-topic-analysis.py
```

---

## 旧技能迁移

| 旧技能 | 新脚本 | 状态 |
|--------|--------|------|
| mcn-hotspot-aggregator | run-hotspot-research.py | ✅ 已实现 |
| mcn-topic-selector | run-topic-analysis.py | ✅ 已实现 |
| wechat-mp-auto-publish | publish_after_confirm.py | ✅ 已实现 |
| mcn-content-rewriter | 待实现 | ⏳ 待完成 |
| mcn-wechat-publisher | publish_after_confirm.py | ✅ 已整合 |

---

*Last updated: 2026-04-14*
