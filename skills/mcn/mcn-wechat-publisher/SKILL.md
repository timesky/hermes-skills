---
name: mcn-wechat-publisher
description: |
  MCN 微信公众号发布技能 - 将文章和配图发布到微信公众号草稿箱。
  
  触发词：微信发布、公众号发布、发布草稿、mcn发布
  
  可独立调用，也可被 my-mcn-manager 在阶段5调度。
parent: my-mcn-manager
tags: [mcn, wechat, publisher, draft, 微信公众号]
version: 1.2.0
created: 2026-04-15
updated: 2026-04-25
---

# MCN 微信公众号发布

将文章和配图发布到微信公众号草稿箱，负责渠道特定的排版和格式转换。

---

## 功能闭环与产出交付

**职责**：独立完成微信发布阶段所有工作。

| 项目 | 说明 |
|------|------|
| 输入 | `--article {文章路径}` `--date {日期}` |
| 输入位置 | `mcn/content/{date}/{slug}/article.md` + `images/` |
| 产出 | 公众号草稿 `media_id` |
| 状态返回 | `{"status": "success", "media_id": "...", "topic_slug": "..."}` |

**衔接机制**：
- 上游技能 `mcn-content-writer` 产出文章和配图到约定位置
- 本技能从文章路径自动提取 `topic_slug`，定位配图目录
- 排版逻辑：微信特定（HTML格式 + 图片按百分比插入）

---

## 渠道特定排版

**微信排版规则**：

| 项目 | 说明 |
|------|------|
| 格式 | HTML（微信公众号要求） |
| 图片插入 | 按百分比（20%, 40%, 60%, 80%） |
| 封面尺寸 | 900×500px |
| 正文图片 | 自动上传到素材库 |

**排版代码位置**：`scripts/publish-draft.py` 第200-208行

```python
# 图片插入位置：20%, 40%, 60%, 80%
insert_ratio = 0.2 + (i * 0.2)
parts[insert_pos] += f'</p><p><img src="{img_url}"/></p>'
```

---

## 配置来源

**约定优于配置 + 技能独立性**

- 配置文件：`~/.hermes/mcn_config.yaml`（公众号凭证、代理）
- 目录约定：脚本内联解析，不依赖其他技能模块
- 输入目录：从文章路径自动提取

脚本不导入其他技能目录下的模块。详见入口技能 `references/config.md`。

---

## 执行方式

```bash
# Terminal 直接执行
eval "$(pyenv init -)" && python3 ~/.hermes/skills/mcn/mcn-wechat-publisher/scripts/publish-draft.py \
  --article "mcn/content/2026-04-15/{slug}/article.md" \
  --date 2026-04-15
```

**脚本目录**：`mcn-wechat-publisher/scripts/`
- `publish-draft.py` - 主脚本（含排版、上传、发布）

---

## 配置要求

```yaml
# ~/.hermes/mcn_config.yaml
publish:
  proxy: http://user:pass@host:port  # 可选代理
  accounts:
    main:
      appid: wx...
      secret: ...
      author: 作者名
```

---

## 工作流程

```
读取文章 → 提取topic_slug → 定位配图目录 → 上传封面 → 上传正文图片 → 
排版（HTML转换+图片插入） → 创建草稿 → 返回media_id
```

---

## Pitfalls

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **标题45003报错** | `requests.post(json=...)` 对中文编码处理不当，微信API收到的标题字节超限 | **关键修复**：改用 `data=json_bytes` + `Content-Type: application/json; charset=utf-8`。已在脚本中修复（第341行） |
| **图片上传代理失败** | 豆包生成图片命名 `.png` 但实际是 JPEG 格式，格式混乱导致代理上传断开 | 用 `sips -s format jpeg cover.png --out cover.jpg` 转换为正确格式后上传 |
| **批量发布排版缺失** | 发布前未运行 `layout-article.py`，导致缺少尾部和首图 | **必须先排版**：`python layout-article.py --article ARTICLE --date DATE` |
| **Markdown图片占位符残留** | 文章中 `![xxx](images/xxx.png)` 未被处理，当作普通文本输出到 HTML | **删除占位符**：脚本按固定位置（30%, 60%）插入图片，不处理 Markdown 占位符。发布前需删除文章中的所有图片占位符 |
|| **Markdown格式未转换** | 表格、链接、分隔线等 Markdown 格式当作普通文本 | **脚本已修复**：v1.2.1+ 支持表格→HTML table、链接→`<a>`、分隔线→`<hr>`、行内加粗 |
|| **PNG图片过大导致代理超时** | 豆包生成的 PNG 常常 >1MB，代理连接易超时 | **脚本已修复**：优先上传 JPG 版本 (`*_upload.jpg`)，回退 PNG |
|| **Profile环境 `~` 路径展开错误** | Profile 模式下 `os.path.expanduser('~')` 指向错误 home 目录 | **脚本已修复**：使用绝对路径 `/Users/hy_timesky/.hermes/mcn_config.yaml` |
|| **`config` 变量使用前未定义** | 多个脚本开头直接使用 `config.get()`，但 `config` 在后面才赋值 | **脚本已修复**：先设置默认值，再按条件加载配置 |
|| 封面永久素材累积 | thumb_media_id 必须是永久素材（API限制） | 发布成功后调用 delete_permanent_material 删除封面素材 |
| IP白名单未添加 | 在公众号后台添加服务器IP |
| 代理配置错误 | 检查 `mcn_config.yaml` 中 `publish.proxy` |
| 封面尺寸不符 | 封面图需 900×500px |

**最小修改原则（重要）**：
用户要求只做必要修改时（如"去掉相关阅读"），不要：
- 重新上传已上传的图片
- 改动标题或其他内容
- 引入不必要的新问题

正确做法：只执行用户指定的最小必要修改。

**排版流程一致性（重要）**：

批量发布时，必须确保每篇文章都完成了排版流程：
```
layout-article.py → 生成 article-layout.html → publish-draft.py
```

若跳过排版直接发布 Markdown，`md_to_html()` 回退逻辑已支持尾部和首图，但样式不如 layout 文件精美。

---

## 相关技能

- **mcn-content-writer** - 上游技能，产出文章和配图
- **my-mcn-manager** - 父技能，调度和引导

---

## 未来扩展

本技能是微信渠道特定实现，未来可扩展其他渠道：

| 渠道 | 技能 | 排版特点 |
|------|------|----------|
| 微信公众号 | mcn-wechat-publisher | HTML + 图片百分比插入 |
| 小红书 | mcn-xiaohongshu-publisher | 卡片式排版 |
| 抖音 | mcn-douyin-publisher | 视频脚本 + 封面 |
| B站 | mcn-bilibili-publisher | 视频稿件格式 |

---

*Version: 1.2.1 - 添加 PNG 上传超时、Profile 路径、config 变量陷阱 pitfalls*