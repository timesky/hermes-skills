# 知乎收藏夹抓取流程总结

## 当前状态

| 项目 | 状态 |
|------|------|
| 收藏夹 ID | 797328373 |
| 已处理文章 | 104 篇 |
| 定时任务 | 已创建（Job ID: 187fd140e8ad）|
| 下次执行 | 20:00 |

## 工具选择

| 工具 | 状态 | 说明 |
|------|------|------|
| **OpenCLI** | ❌ 不支持收藏夹 | 仅支持热榜抓取 |
| **Hermes Browser** | ❌ macOS 11.7 不兼容 | Chromium 需要 macOS 12+ |
| **web-fetcher** | ✅ 推荐 | Chrome 扩展 + WebSocket 服务 |
| **CDP 直连** | ✅ 备选 | 18800 端口 |

## web-fetcher 启动步骤

```bash
# 1. 安装依赖
cd ~/.hermes/skills/web/web-fetcher/server
npm install ws

# 2. 启动 WebSocket 服务
nohup node server.js > /tmp/webfetcher.log 2>&1 &

# 3. 检查状态
curl http://localhost:9234/status

# 4. 在 Chrome 中加载扩展
# chrome://extensions → 加载 ~/.hermes/skills/web/web-fetcher/extension
```

## 增量抓取逻辑

```
每2小时执行（8:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00）:

1. 读取进度文件 /tmp/zhihu_collection_progress.json
2. 访问收藏夹第一页
3. 对比 latest_article_time，找出48小时内新增
4. 如果有新增 → 抓取并保存
5. 如果无新增 → [SILENT]
6. 更新进度文件
```

## 文件保存位置

```
~/backup/知识库-Obsidian/tmp/zhihu/YYYY-MM-DD/
├── article-{id}.md  # 文章内容
└── metadata.json    # 元数据
```

## 进度文件格式

```json
{
  "last_check_time": "2026-04-12 19:48:00",
  "latest_article_time": "2026-04-10",
  "processed_ids": ["2023650574...", "2025269851..."],
  "collection_id": "797328373",
  "total_saved": 104
}
```

## 注意事项

1. **请求间隔**: 2-3秒，避免封禁
2. **Chrome 扩展必须加载**: 需手动在 chrome://extensions 加载
3. **WebSocket 服务必须启动**: 9234 端口
4. **用户必须已登录知乎**: 扩展使用用户 Cookie

---
*Created by Luna 2026-04-12*