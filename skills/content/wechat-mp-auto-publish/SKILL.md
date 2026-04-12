---
name: wechat-mp-auto-publish
description: 微信公众号全自动发布流程 - 调研、成文、配图、发草稿，只需输入主题
trigger:
  - 公众号文章
  - 微信发布
  - 自动发布公众号
tools:
  - ollama
  - wechatpy
  - stable-diffusion
dependencies:
  - pip install wechatpy cryptography
config_file: ~/.hermes/wechat_mp_config.yaml
---

# 微信公众号全自动发布流程

## 前置要求

- 已配置 AppID + AppSecret（保存在 config_file）
- Ollama 已安装并拉取模型（可选）
- Stable Diffusion WebUI 运行中（可选，用于主题配图）

## 流程

## 流程概览

```
17:00定时触发 → 调研热点 → 推荐主题 → 【人工确认】 → 生成文章 → 配图 → 发布草稿
    自动           自动        自动        唯一交互       自动      自动     自动
```

### 详细流程文档

见：[references/flow-tools-summary.md](./references/flow-tools-summary.md)

### 阶段划分

| 阶段 | 步骤 | 自动化程度 |
|------|------|------------|
| **A: 调研推荐** | 定时触发 → 热点调研 → 推荐主题 | 全自动 |
| **B: 人工确认** | 用户选择主题 | 唯一交互点 |
| **C: 内容生成** | 深度调研 → 写文章 → 配图 | 全自动 |
| **D: 发布草稿** | 上传素材 → 创建草稿 → 通知 | 全自动 |

### Step 1: 询问主题（唯一人工交互）

```
请确认：
1. 文章主题：________
2. 文章风格：[科技/商业/生活/热点]
3. 是否配图：[是/否]
```

### 文章要求

| 项目 | 要求 |
|------|------|
| **字数** | 1500~2000字（按字数计算） |
| **配图** | 不少于3张，5张更佳，符合主题，无商标 |
| **结构** | 5-6章节 + 开头 + 总结 |
| **排版** | 合理分段，h2小标题，blockquote引用 |

### 人设模板（按主题类型）

| 主题类型 | 人设 | 语言风格 |
|----------|------|----------|
| **科技** | 技术从业者/行业观察者 | 专业、客观、数据支撑、技术术语适度 |
| **商业** | 商业分析师/投资人 | 深度分析、行业视角、趋势判断 |
| **生活** | 生活达人/体验者 | 轻松、实用、贴近日常、有温度 |
| **热点** | 资深评论员 | 快速、观点鲜明、引发讨论、有争议性 |

### 去AI化要点

1. **避免AI痕迹词**：
   - 不用：综上所述、值得注意的是、首先其次最后、让我们来看看
   - 用：其实、换句话说、说白了、关键在于

2. **增加个人色彩**：
   - 加入个人观点：「我觉得」「在我看来」
   - 加入口语化表达：用比喻、用反问、用调侃
   - 加入行业黑话：圈内术语、流行梗

3. **打破模板感**：
   - 章节标题不要太整齐（不要全是「一、二、三」）
   - 段落长短交替，不要每段都一样长
   - 适当用短句、感叹句

### 配图要求

| 要求 | 说明 |
|------|------|
| **数量** | 不少于3张，推荐5张 |
| **内容** | 符合文章主题，不使用商标/品牌元素 |
| **来源** | Stable Diffusion生成 或 免版权图库 |
| **分布** | 开篇1张 + 各章节均匀分布 |

**配图提示词模板**（Stable Diffusion）：
```
科技主题: "tech concept, abstract digital visualization, futuristic, blue tones, minimalist, no text, no logo"
商业主题: "business concept, professional office setting, corporate environment, clean design, no branding"
生活主题: "lifestyle scene, warm atmosphere, natural lighting, everyday moment, authentic feel"
热点主题: "news concept, dynamic composition, attention-grabbing, modern design, bold colors"
```

### 草稿字段（公众号接口）

```python
draft_data = {
    "articles": [{
        "title": "标题（64字符内）",
        "author": "作者名",
        "content": "HTML内容",
        "thumb_media_id": "封面素材ID",
        "digest": "摘要（120字符内，用于文章概述）",
        "content_source_url": "原文链接（可选）",
        "show_cover_pic": 1,  # 显示封面
        "need_open_comment": 0,  # 开放评论
        "only_fans_can_comment": 0,  # 仅粉丝评论
    }]
}
```

### Step 2-6: 全自动执行

调研 → 成文 → 配图 → 格式化 → 发布

#### 配图流程

1. **封面图**：上传永久素材，获取 media_id
2. **内容配图**：
   - Stable Diffusion生成（推荐）或下载免版权图
   - 上传素材库，获取 URL
   - 嵌入 HTML：`<img src="{url}" style="max-width:100%;"/>`

### Pitfalls

1. **关键：JSON 编码必须用 ensure_ascii=False**
   ```python
   json.dumps(draft_data, ensure_ascii=False)
   ```
2. 标题 64 字符以内
3. 摘要 120 字符以内
4. 封面用永久素材接口（material.add）
5. 每次发布前清理旧测试草稿
6. **Memory 记录已发布内容**（避免重复推荐）
   - 发布成功后用 memory 工具记录标题和主题
   - 推荐前检查 Memory，过滤已发布主题

---

## 定时任务配置

| 时间 | 任务 | Job ID | 推送方式 |
|------|------|--------|----------|
| **11:00** | 文章数据分析 | `92e49e93dcd4` | feishu:chat_id |
| **17:00** | 热点调研 | `0131aab79846` | local（只保存） |
| **17:30** | 推荐推送 | `106eecae54c8` | feishu:chat_id |

### 定时任务拆分原则（重要）

**调研和推送必须分离**，避免：
- 推送失败 → 触发重新调研 → 浪费资源
- 调研失败 → 无法推送 → 用户收不到任何信息

**正确模式**：
```
调研任务（17:00）→ 保存文件到 tmp/topic/{日期}/recommend.md → deliver=local
推送任务（17:30）→ 读取文件 → 推送到飞书 → deliver=feishu:chat_id
```

**Cron 推送配置**：
- ❌ `deliver=origin` - 在 cron 执行时无法确定目标
- ✅ `deliver=feishu:oc_xxx` - 具体聊天ID
- ✅ `deliver=local` - 只保存文件，不推送

### 数据分析流程（11:00）

```
获取15天数据 → 分析热门文章 → 对比改写效果 → 输出创作建议 → 推送飞书
```

重点关注：
- 阅读量 > 500 的文章 → 分析主题特点
- 原素材热门但改写后阅读低 → 总结改进点
- 完读率分析 → 内容质量指标

### 任务：每日主题推荐（17:00）

- **时间**：每天 17:00（北京时间）
- **Job ID**：`0131aab79846`
- **内容**：搜索热点 → 筛选主题 → 推送到飞书
- **输出**：3-5个推荐主题，等待人工确认

### 确认后执行

用户回复主题序号（如"1"或"1,2,3"）后，自动执行：
```
加载 wechat-mp-auto-publish skill
→ 深度调研确认主题
→ 生成文章（1500+字）
→ 生成配图（3-5张）
→ 发布草稿
→ 推送结果通知
```