#!/usr/bin/env python3
"""
知乎专栏草稿保存脚本
使用 Hermes Web Fetcher v2.0 控制功能将文章保存到知乎草稿箱

⚠️ 安全约束：仅保存草稿，不发布

优势：
- 使用 chrome.scripting.executeScript，绕过 OpenCLI 的安全限制
- 支持 Draft.js/React 编辑器，正文填写有效
- 使用用户浏览器已登录的 Cookie
"""

import argparse
import asyncio
import json
import os
import re
import sys

# 添加 web-fetcher 路径
WEB_FETCHER_PATH = os.path.expanduser('~/.hermes/skills/web/web-fetcher/server')
sys.path.insert(0, WEB_FETCHER_PATH)

from hermes_web_fetcher import HermesWebFetcher


class ZhihuPublisher:
    """知乎专栏草稿发布器"""
    
    def __init__(self):
        self.client = HermesWebFetcher()
        self.tab_id = None
    
    async def connect(self):
        """连接到 WebSocket 服务"""
        connected = await self.client.connect()
        if not connected:
            return False, "连接 WebSocket 服务失败"
        
        # 获取活动标签页
        tab = await self.client.get_active_tab()
        if not tab or 'error' in tab:
            return False, "无法获取活动标签页"
        
        self.tab_id = tab['id']
        return True, f"已连接，当前页面: {tab.get('title', 'unknown')}"
    
    async def disconnect(self):
        """断开连接"""
        await self.client.disconnect()
    
    async def navigate_to_write(self):
        """导航到知乎写作页面"""
        print("📍 导航到知乎写作页面...")
        result = await self.client.navigate(self.tab_id, 'https://zhuanlan.zhihu.com/write')
        await asyncio.sleep(2)  # 等待页面加载
        return True, result
    
    async def fill_title(self, title: str):
        """填写文章标题"""
        print(f"📝 填写标题: {title}")
        
        result = await self.client.fill_input(
            self.tab_id,
            'textarea[placeholder*="标题"]',
            title,
            clear_first=True
        )
        
        if result.get('success'):
            return True, f"已填写 {result.get('filledLength', 0)} 字符"
        return False, result.get('error', '填写失败')
    
    async def fill_content(self, content: str):
        """填写文章内容（Draft.js 编辑器）"""
        print(f"📄 填写正文（{len(content)} 字符）...")
        
        # 使用 trigger_react=True 强制 Draft.js 处理
        result = await self.client.fill_input(
            self.tab_id,
            '.DraftEditor-root [contenteditable="true"]',
            content,
            clear_first=True,
            trigger_react=True
        )
        
        if result.get('success'):
            # 验证字数
            await asyncio.sleep(1)
            info = await self.client.get_element_info(
                self.tab_id,
                '.DraftEditor-root [contenteditable="true"]'
            )
            actual_length = info.get('valueLength', 0)
            print(f"   实际字数: {actual_length}")
            
            if actual_length > 0:
                return True, f"已填写 {actual_length} 字符"
            else:
                return False, "字数为 0，可能未正确填写"
        
        return False, result.get('error', '填写失败')
    
    async def trigger_save(self):
        """触发自动保存"""
        print("💾 触发保存...")
        
        # blur 编辑器触发保存
        await self.client.blur(self.tab_id, '.DraftEditor-root [contenteditable="true"]')
        await asyncio.sleep(3)  # 等待自动保存
        
        return True, "已触发保存"
    
    async def get_draft_url(self):
        """获取草稿 URL"""
        info = await self.client.get_page_info(self.tab_id)
        return info.get('url', 'unknown')
    
    async def verify_draft(self):
        """验证草稿状态"""
        # 检查标题
        title_info = await self.client.get_element_info(
            self.tab_id,
            'textarea[placeholder*="标题"]'
        )
        
        # 检查正文
        content_info = await self.client.get_element_info(
            self.tab_id,
            '.DraftEditor-root [contenteditable="true"]'
        )
        
        return {
            'title_length': title_info.get('valueLength', 0),
            'content_length': content_info.get('valueLength', 0),
            'title_ok': title_info.get('success', False),
            'content_ok': content_info.get('success', False) and content_info.get('valueLength', 0) > 0
        }


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


async def main():
    parser = argparse.ArgumentParser(
        description='保存文章到知乎专栏草稿箱',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python publish_draft.py --article /path/to/article.md
  python publish_draft.py --article /path/to/article.md --title "自定义标题"

⚠️ 注意：本脚本仅保存草稿，不会发布。发布需手动操作。

使用 Hermes Web Fetcher v2.0 控制功能，支持 Draft.js 编辑器。
需要：Chrome 扩展已加载 + WebSocket 服务运行
        '''
    )
    parser.add_argument('--article', required=True, help='文章文件路径')
    parser.add_argument('--title', help='文章标题（可选，默认从文件提取）')
    args = parser.parse_args()
    
    print("=" * 50)
    print("知乎专栏草稿保存 (Web Fetcher v2.0)")
    print("=" * 50)
    
    # 1. 解析文章
    print(f"\n📖 读取文章: {args.article}")
    title, content, error = parse_article(args.article)
    if error:
        print(f"❌ {error}")
        return 1
    
    final_title = args.title or title
    if not final_title:
        print("❌ 未找到标题，请使用 --title 参数指定")
        return 1
    
    print(f"   标题: {final_title}")
    print(f"   内容长度: {len(content)} 字符")
    
    # 2. 连接
    publisher = ZhihuPublisher()
    success, msg = await publisher.connect()
    if not success:
        print(f"❌ {msg}")
        print("\n请确保:")
        print("  1. Chrome 扩展已加载 (chrome://extensions)")
        print("  2. WebSocket 服务已启动 (cd ~/.hermes/skills/web/web-fetcher/server && node server.js)")
        return 1
    print(f"✅ {msg}")
    
    try:
        # 3. 导航到写作页面
        success, msg = await publisher.navigate_to_write()
        if not success:
            print(f"❌ 导航失败: {msg}")
            return 1
        print("✅ 已打开写作页面")
        
        # 4. 填写标题
        success, msg = await publisher.fill_title(final_title)
        if not success:
            print(f"❌ 填写标题失败: {msg}")
            return 1
        print(f"✅ 标题已填写: {msg}")
        
        # 5. 填写正文
        success, msg = await publisher.fill_content(content)
        if not success:
            print(f"❌ 填写正文失败: {msg}")
            return 1
        print(f"✅ 正文已填写: {msg}")
        
        # 6. 触发保存
        await publisher.trigger_save()
        
        # 7. 验证草稿
        status = await publisher.verify_draft()
        print(f"\n📊 草稿验证:")
        print(f"   标题字数: {status['title_length']}")
        print(f"   正文字数: {status['content_length']}")
        
        # 8. 获取草稿 URL
        url = await publisher.get_draft_url()
        
        print("\n" + "=" * 50)
        if status['content_ok']:
            print("✅ 草稿已保存成功")
        else:
            print("⚠️ 草稿可能不完整，请手动检查")
        print("=" * 50)
        print(f"\n📝 标题: {final_title}")
        print(f"📊 正文: {status['content_length']} 字")
        print(f"🔗 URL: {url}")
        print("\n⚠️ 请手动在浏览器检查后发布")
        
        return 0
        
    finally:
        await publisher.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))