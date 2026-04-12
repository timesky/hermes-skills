#!/usr/bin/env python3
"""
Hermes Web Fetcher - 使用示例
演示完整的抓取流程：启动服务 → 抓取 → 关闭服务
"""

import asyncio
import json
import subprocess
import sys
import websockets
from pathlib import Path

SERVER_URL = "ws://localhost:9234"
SERVER_DIR = Path.home() / ".hermes" / "skills" / "web" / "web-fetcher" / "server"


class WebFetcher:
    """WebSocket 客户端，管理连接和抓取操作"""
    
    def __init__(self):
        self.ws = None
        self.server_process = None
    
    async def connect(self):
        """连接 WebSocket 服务器"""
        self.ws = await websockets.connect(SERVER_URL)
        # 等待 welcome 消息
        welcome = await asyncio.wait_for(self.ws.recv(), timeout=5)
        data = json.loads(welcome)
        if data.get('type') == 'welcome':
            print(f"✅ 已连接: {data.get('server', 'unknown')}")
    
    async def disconnect(self):
        """断开连接"""
        if self.ws:
            await self.ws.close()
            self.ws = None
    
    async def _send_and_wait(self, method: str, params: dict, timeout: int = 30) -> dict:
        """发送命令并等待响应"""
        msg_id = f"cmd-{method}-{int(asyncio.get_event_loop().time() * 1000)}"
        msg = {
            "id": msg_id,
            "method": "forwardCDPCommand",
            "params": {
                "method": method,
                "params": params,
                "ts": int(asyncio.get_event_loop().time() * 1000)
            }
        }
        await self.ws.send(json.dumps(msg))
        
        # 过滤 ping/welcome，等待匹配响应
        while True:
            response = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(response)
            
            if data.get('type') == 'ping':
                await self.ws.send(json.dumps({"type": "pong"}))
                continue
            if data.get('type') == 'welcome':
                continue
            
            if data.get('id') == msg_id:
                return data
    
    async def get_active_tab(self) -> dict:
        """获取当前活动标签页"""
        data = await self._send_and_wait("Hermes.getActiveTab", {})
        return data.get('result', {})
    
    async def navigate(self, tab_id: int, url: str) -> dict:
        """导航到指定 URL"""
        data = await self._send_and_wait("Hermes.navigate", 
                                         {"tabId": tab_id, "url": url},
                                         timeout=45)
        return data.get('result', {})
    
    async def fetch_list(self, tab_id: int, options: dict = None) -> dict:
        """抓取列表类页面"""
        data = await self._send_and_wait("Hermes.fetchList", 
                                         {"tabId": tab_id, "options": options or {}})
        return data.get('result', {})
    
    async def fetch_article(self, tab_id: int) -> dict:
        """抓取文章内容"""
        data = await self._send_and_wait("Hermes.fetchArticle", {"tabId": tab_id})
        return data.get('result', {})


def start_server() -> subprocess.Popen:
    """启动 WebSocket 服务器"""
    # 先检查是否已运行
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:9234/health", timeout=2)
        print("✅ WebSocket 服务已运行")
        return None
    except:
        pass
    
    # 启动服务
    print("启动 WebSocket 服务...")
    process = subprocess.Popen(
        ["node", "server.js"],
        cwd=str(SERVER_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 等待启动
    for _ in range(10):
        try:
            urllib.request.urlopen("http://localhost:9234/health", timeout=1)
            print("✅ WebSocket 服务启动成功")
            return process
        except:
            asyncio.sleep(1)
    
    raise Exception("WebSocket 服务启动失败")


def stop_server(process: subprocess.Popen):
    """关闭 WebSocket 服务器"""
    if process:
        process.terminate()
        print("✅ WebSocket 服务已关闭")


async def fetch_zhihu_collection(collection_url: str):
    """抓取知乎收藏夹的完整示例"""
    
    # 1. 启动服务
    server_process = start_server()
    
    try:
        # 2. 提示用户
        print("\n" + "=" * 50)
        print("请在 Chrome 中打开目标页面:")
        print(f"  {collection_url}")
        print("")
        print("并确认 Hermes Web Fetcher 扩展已连接")
        print("（点击扩展图标，状态应显示「已连接」）")
        print("=" * 50 + "\n")
        
        await asyncio.sleep(2)  # 给用户时间准备
        
        # 3. 连接 WebSocket
        client = WebFetcher()
        await client.connect()
        
        # 4. 获取活动标签页
        tab = await client.get_active_tab()
        tab_id = tab.get('id')
        print(f"当前标签页: {tab.get('title', 'N/A')[:40]}")
        
        # 5. 导航到目标页面（如果需要）
        if 'zhihu.com/collection' not in tab.get('url', '').split('?')[0]:
            print(f"导航到收藏夹...")
            await client.navigate(tab_id, collection_url)
            await asyncio.sleep(3)  # 等待加载
        
        # 6. 抓取列表
        print("抓取收藏夹内容...")
        result = await client.fetch_list(tab_id)
        
        items = result.get('items', [])
        page_info = result.get('pageInfo', {})
        print(f"✅ 抓取成功: {len(items)} 项")
        print(f"   页码: {page_info.get('currentPage', 1)} / {page_info.get('totalPages', '?')}")
        
        # 7. 显示前几项
        for i, item in enumerate(items[:5]):
            print(f"   [{i+1}] {item.get('title', '无标题')[:45]}...")
        
        # 8. 断开连接
        await client.disconnect()
        
        return result
        
    finally:
        # 9. 关闭服务（如果是本会话启动的）
        stop_server(server_process)


# 使用示例
if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.zhihu.com/collection/797328373?page=1"
    asyncio.run(fetch_zhihu_collection(url))