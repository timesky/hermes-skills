---
name: mcn-multi-platform
description: MCN 多平台分发技能 - 一键发布到公众号、知乎、掘金、CSDN
category: mcn
created: 2026-05-07
---

# MCN 多平台分发技能

## 触发词

- 多平台发布、一键分发、同步发布

## 支持平台

| 平台 | 状态 | 发布方式 |
|------|------|---------|
| 公众号 | ✓ 已集成 | API发布 |
| 知乎 | ✓ 已集成 | web-fetcher控制浏览器 |
| 掘金 | ⏳ 待实现 | API（需掘金账号） |
| CSDN | ⏳ 待实现 | API（需CSDN账号） |
| 头条号 | ⏳ 待实现 | API（需头条账号） |

## 发布顺序（workflow.json配置）

1. 公众号（即时）- 主平台
2. 知乎（即时）- 深度分析受众
3. 掘金（1小时后）- 技术人群
4. CSDN（2小时后）- SEO流量
5. 头条号（即时）- 大众流量

## 使用方法

```bash
# 一键发布到所有平台
python3 ~/.hermes/profiles/mcn/skills/mcn/mcn-multi-platform/scripts/publish-all.py --article ARTICLE_PATH --date DATE

# 只发布到指定平台
python3 publish-all.py --article ARTICLE_PATH --platforms 公众号,知乎
```

## 内容适配

每个平台自动适配：
- **公众号**: 标准HTML排版，图片嵌入
- **知乎**: 长文格式，疑问式标题
- **掘金**: 技术标签，代码高亮
- **CSDN**: SEO关键词，教程格式

## 相关技能

- mcn-wechat-publisher: 公众号发布
- mcn-zhihu-publisher: 知乎发布
- mcn-content-writer: 内容生成