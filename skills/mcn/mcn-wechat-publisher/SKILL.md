---
name: mcn-wechat-publisher
description: |
  MCN 微信公众号发布技能 - 将文章和配图发布到微信公众号草稿箱。
  
  触发词：微信发布、公众号发布、发布草稿、mcn发布
  
  可独立调用，也可被 my-mcn-manager 在阶段5调度。
parent: my-mcn-manager
tags: [mcn, wechat, publisher, draft, 微信公众号]
version: 1.4.0
created: 2026-04-15
updated: 2026-05-03
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

## 草稿配置功能

| 功能 | API 支持 | 脚本参数 | 说明 |
|------|---------|---------|------|
| ✅ 留言 | ✅ | `--no-comment` 关闭（默认开启） | `need_open_comment=1` |
| ✅ 仅关注者评论 | ✅ | 默认行为 | `only_fans_can_comment=1`（默认） |
| ❌ 赞赏 | ❌ | 需公众号后台手动 | 腾讯限制，需原创权限 |
| ❌ 合集 | ❌ | 需公众号后台手动 | 后台添加到合集 |

**命令示例**：
```bash
# 默认：开启留言 + 仅关注者可评论
python publish-draft.py --article ARTICLE --date DATE

# 关闭留言
python publish-draft.py --article ARTICLE --date DATE --no-comment

# 所有人可评论（改为非默认）
python publish-draft.py --article ARTICLE --date DATE --all-can-comment
```

**赞赏和合集配置**：
1. 登录公众号后台 → 草稿箱
2. 点击编辑目标草稿
3. 开启赞赏 / 添加到合集
4. 保存

---

## 图片处理完整流程

```
1. 生成配图 → cover.png, img_1.png, img_2.png
2. 转换JPG → cover_upload.jpg, img_1_upload.jpg, img_2_upload.jpg (减小文件大小)
3. 构建HTML → 使用占位符 IMG_0_PLACEHOLDER, IMG_1_PLACEHOLDER, IMG_2_PLACEHOLDER
4. 上传图片 → 脚本自动上传并替换占位符为微信URL
5. 创建草稿 → 完成
```

**关键命令**：
```bash
# PNG转JPG 60%质量（解决代理超时，PNG>1MB会失败）
sips -s format jpeg -s formatOptions 60 cover.png --out cover_upload.jpg
sips -s format jpeg -s formatOptions 60 img_1.png --out img_1_upload.jpg
sips -s format jpeg -s formatOptions 60 img_2.png --out img_2_upload.jpg
```

**压缩效果**：
- 原PNG（~1.1MB）→ JPG 60%（~400KB）
- 85%质量仍可能超时，60%质量稳定可用

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
|| **配图命名格式错误** | 图片命名为 `img1.png`, `img2.png` 而非 `img_1.png`, `img_2.png`，导致正文配图未上传 | **必须使用下划线格式**：`cover.png`, `img_1.png`, `img_2.png`（脚本用正则 `img_\\d+\\.png` 匹配） |
|| **HTML图片路径格式错误** | HTML使用相对路径 `<img src="images/cover.png">`，发布后图片不显示 | **HTML必须使用占位符格式**：`<img src="IMG_0_PLACEHOLDER"/>` (封面)、`<img src="IMG_1_PLACEHOLDER"/>` (段落图1)、`<img src="IMG_2_PLACEHOLDER"/>` (段落图2)。脚本上传图片后自动替换为微信URL |
|| **HTML包含行号格式** | 使用 `read_file` 读取后用 `write_file` 写入，保留了 `LINE_NUM|` 格式（如 `53|    53|<h1>...`） | **清理行号**：修改HTML后用 `sed 's/^[[:space:]]*[0-9]*|//' filename.html` 清理。⚠️ **切勿**将 `read_file` 返回的内容直接传给 `write_file` |
|| **目录结构不一致** | 配图生成到 `{date}/images/` 而非 `{date}/{slug}/images/`，脚本找不到图片 | **必须遵循格式**：`mcn/content/{date}/{topic_slug}/article.md` + `images/cover.png, img_1.png, img_2.png`。用 `shutil.move()` 调整目录结构 |
|| **Profile环境 `~` 路径展开错误** | Profile 模式下 `os.path.expanduser('~')` 指向错误 home 目录 | **脚本已修复**：使用绝对路径 `/Users/hy_timesky/.hermes/mcn_config.yaml` |
|| **`config` 变量使用前未定义** | 多个脚本开头直接使用 `config.get()`，但 `config` 在后面才赋值 | **脚本已修复**：先设置默认值，再按条件加载配置 |
|| 封面永久素材累积 | thumb_media_id 必须是永久素材（API限制） | 发布成功后调用 delete_permanent_material 删除封面素材 |
|| **图片上传网络不稳定** | 代理连接导致 `Remote end closed connection without response` | **v1.2.2+**：添加重试机制（最多3次，每次等待2秒） |
|| **thumb_media_id API限制** | 微信API硬性要求：封面 `thumb_media_id` 必须是**永久素材ID**，不能用临时素材 | **正确方案**：封面用 `/material/add_material`（永久），正文用 `/media/uploadimg`（临时返回URL）。临时素材无法用于封面 |
|| IP白名单未添加 | 在公众号后台添加服务器IP |
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