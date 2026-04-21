#!/usr/bin/env python3
"""
知乎专栏草稿保存脚本（web-fetcher 版）
使用 Hermes Web Fetcher 扩展将文章保存到知乎草稿箱

✅ 支持 Draft.js 编辑器 - 正文填写可靠

⚠️ 安全约束：仅保存草稿，不发布

前置条件:
1. web-fetcher 扩展已安装并启用 (v2.0.0+)
2. WebSocket 服务运行: cd ~/.hermes/skills/web/web-fetcher/server && node server.js
3. Chrome 浏览器已登录知乎账号

更新: 2026-04-16 - 使用 web-fetcher 替代 OpenCLI
"""

import argparse
import asyncio
import json
import re
import sys

# 添加 web-fetcher 路径
sys.path.insert(0, '/Users/timesky/.hermes/skills/web/web-fetcher/server')
from hermes_web_fetcher import HermesWebFetcher


def parse_article(file_path: str):
    """解析文章文件，提取标题和内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return None, None, f"文件不存在: {file_path}"
    
    # 提取标题（第一个 # 标题）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # 移除标题行
        article_content = re.sub(r'^#\s+.+$', '', content, count=1, flags=re.MULTILINE).strip()
    else:
        title = None
        article_content = content.strip()
    
    # 去掉 YAML frontmatter
    article_content = re.sub(r'^---\n.*?\n---\n', '', article_content, flags=re.DOTALL)
    
    # 去掉末尾元信息
    article_content = re.sub(r'\n---\n\*Written by.*$', '', article_content)
    
    return title, article_content.strip(), None


async def publish_zhihu_draft(title: str, content: str):
    """使用 web-fetcher 保存知乎草稿"""
    
    print("=" * 50)
    print("知乎专栏草稿保存 (web-fetcher)")
    print("=" * 50)
    
    # 连接 WebSocket
    client = HermesWebFetcher()
    try:
        await client.connect()
    except Exception as e:
        print(f"❌ 连接 WebSocket 失败: {e}")
        print("\n请确保 WebSocket 服务正在运行:")
        print("  cd ~/.hermes/skills/web/web-fetcher/server && node server.js")
        return None
    
    try:
        # 获取活动标签页
        print("\n🔍 获取当前浏览器标签页...")
        tab = await client.get_active_tab()
        if 'error' in tab:
            print(f"❌ 获取标签页失败: {tab.get('error')}")
            return None
        
        tab_id = tab['id']
        print(f"✅ 当前页面: {tab.get('title', 'N/A')}")
        
        # 导航到知乎写作页
        print("\n📍 导航到知乎写作页...")
        await client.navigate(tab_id, 'https://zhuanlan.zhihu.com/write')
        await asyncio.sleep(2)  # 等待页面加载
        
        # 填写标题
        print(f"\n📝 填写标题: {title}")
        result = await client.fill_input(
            tab_id, 
            'textarea[placeholder*="标题"]', 
            title,
            clear_first=True
        )
        if result.get('success'):
            print(f"✅ 标题已填写 ({result.get('filledLength')} 字符)")
        else:
            print(f"❌ 填写标题失败: {result.get('error')}")
            return None
        
        # 填写正文 (Draft.js 编辑器)
        print(f"\n📄 填写正文 ({len(content)} 字符)...")
        result = await client.fill_input(
            tab_id,
            '.DraftEditor-root [contenteditable="true"]',
            content,
            clear_first=True,
            trigger_react=True  # 强制触发 React/Draft.js 事件
        )
        if result.get('success'):
            print(f"✅ 正文已填写 ({result.get('filledLength')} 字符)")
        else:
            print(f"❌ 填写正文失败: {result.get('error')}")
            return None
        
        # 触发 blur 保存
        print("\n💾 触发自动保存...")
        await client.blur(tab_id, '[contenteditable="true"]')
        await asyncio.sleep(3)  # 等待知乎自动保存
        
        # 获取页面信息（包含草稿 URL）
        info = await client.get_page_info(tab_id)
        draft_url = info.get('url', 'unknown')
        
        # 验证填写结果
        print("\n🔍 验证填写结果...")
        title_info = await client.get_element_info(tab_id, 'textarea[placeholder*="标题"]')
        content_info = await client.get_element_info(tab_id, '.DraftEditor-root [contenteditable="true"]')
        
        print(f"   标题: {title_info.get('value', '')[:30]}...")
        print(f"   正文长度: {content_info.get('valueLength', 0)} 字符")
        
        print("\n" + "=" * 50)
        print("✅ 草稿已保存")
        print("=" * 50)
        print(f"\n📝 标题: {title}")
        print(f"🔗 草稿 URL: {draft_url}")
        print(f"📊 正文字数: {content_info.get('valueLength', 0)}")
        print("\n⚠️ 请手动在浏览器检查后发布")
        
        return draft_url
        
    finally:
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description='保存文章到知乎专栏草稿箱（web-fetcher 版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python publish_draft_webfetcher.py --article /path/to/article.md
  python publish_draft_webfetcher.py --article /path/to/article.md --title "自定义标题"
  
✅ 支持 Draft.js 编辑器，正文填写可靠

⚠️ 注意：本脚本仅保存草稿，不会发布。发布需手动操作。

前置条件:
  1. web-fetcher 扩展已安装 (chrome://extensions)
  2. WebSocket 服务运行 (node ~/.hermes/skills/web/web-fetcher/server/server.js)
  3. Chrome 已登录知乎
        '''
    )
    parser.add_argument('--article', required=True, help='文章文件路径')
    parser.add_argument('--title', help='文章标题（可选，默认从文件提取）')
    args = parser.parse_args()
    
    # 解析文章
    print(f"\n📖 读取文章: {args.article}")
    title, content, error = parse_article(args.article)
    if error:
        print(f"❌ {error}")
        sys.exit(1)
    
    # 使用命令行标题或文件标题
    final_title = args.title or title
    if not final_title:
        print("❌ 未找到标题，请使用 --title 参数指定")
        sys.exit(1)
    
    print(f"   标题: {final_title}")
    print(f"   内容长度: {len(content)} 字符")
    
    # 发布草稿
    asyncio.run(publish_zhihu_draft(final_title, content))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())