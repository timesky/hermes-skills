#!/usr/bin/env python3
"""
Hermes Web Fetcher - Python Client

Connects to local WebSocket server to communicate with Chrome extension
Similar to how Accio's Python code works with its extension
"""

import asyncio
import json
import websockets
from typing import Optional, Dict, Any
from datetime import datetime

SERVER_URL = "ws://localhost:9234"

class HermesWebFetcher:
    """Python client for Hermes Web Fetcher extension"""
    
    def __init__(self, server_url: str = SERVER_URL):
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_id_counter = 0
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"✅ Connected to Hermes server at {self.server_url}")
            
            # Start message listener
            asyncio.create_task(self._listen())
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"   Make sure the server is running: node server.js")
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            print("👋 Disconnected from server")
    
    async def _listen(self):
        """Listen for messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # Handle response
                if 'id' in data:
                    request_id = data['id']
                    if request_id in self.pending_requests:
                        future = self.pending_requests.pop(request_id)
                        if 'error' in data:
                            future.set_exception(Exception(data['error']))
                        else:
                            future.set_result(data.get('result'))
        except websockets.ConnectionClosed:
            print("⚠️  Connection closed")
        except Exception as e:
            print(f"❌ Listen error: {e}")
    
    async def _send_request(self, method: str, params: Dict[str, Any] = None, timeout: float = 30.0) -> Any:
        """Send request to extension via server"""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        request_id = f"{datetime.now().timestamp()}-{self.request_id_counter}"
        self.request_id_counter += 1
        
        message = {
            "id": request_id,
            "method": "forwardCDPCommand",
            "params": {
                "method": method,
                "params": params or {},
                "ts": int(datetime.now().timestamp() * 1000)
            }
        }
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future
        
        # Send message
        await self.websocket.send(json.dumps(message))
        print(f"→ Sent: {method} (id: {request_id})")
        
        # Wait for response with timeout
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request timeout: {method}")
    
    async def get_active_tab(self) -> Dict[str, Any]:
        """Get the currently active tab in Chrome"""
        return await self._send_request("Hermes.getActiveTab")
    
    async def navigate(self, tab_id: int, url: str) -> Dict[str, Any]:
        """Navigate a tab to a URL and wait for load"""
        return await self._send_request("Hermes.navigate", {"tabId": tab_id, "url": url})
    
    async def fetch_article(self, tab_id: int) -> Dict[str, Any]:
        """Fetch full article content from a tab"""
        return await self._send_request("Hermes.fetchArticle", {"tabId": tab_id})
    
    async def fetch_list(self, tab_id: int, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fetch list items from a tab"""
        return await self._send_request("Hermes.fetchList", {
            "tabId": tab_id,
            "options": options or {}
        })
    
    async def get_page_info(self, tab_id: int) -> Dict[str, Any]:
        """Get page info from a tab"""
        return await self._send_request("Hermes.getPageInfo", {"tabId": tab_id})


async def main():
    """Example usage"""
    print("=" * 60)
    print("Hermes Web Fetcher - Python Client Example")
    print("=" * 60)
    
    client = HermesWebFetcher()
    
    # Connect
    if not await client.connect():
        print("\n❌ Failed to connect. Make sure:")
        print("   1. Server is running: cd server && npm install && node server.js")
        print("   2. Extension is loaded in Chrome")
        return
    
    try:
        # Get active tab
        tab = await client.get_active_tab()
        print(f"\n📄 Active tab: {tab.get('title', 'N/A')}")
        
        if 'error' not in tab:
            tab_id = tab['id']
            
            # Navigate to URL
            # await client.navigate(tab_id, "https://example.com")
            # await asyncio.sleep(2)
            
            # Fetch list (for collection pages)
            # items = await client.fetch_list(tab_id)
            # print(f"Found {len(items.get('items', []))} items")
            
            # Fetch article content
            # article = await client.fetch_article(tab_id)
            # print(f"Title: {article.get('title')}")
            # print(f"Content length: {len(article.get('content', ''))}")
        
        print("\n✅ Client ready!")
        print("\nComplete workflow example:")
        print("""
from hermes_web_fetcher import HermesWebFetcher
import asyncio

async def fetch_collection():
    client = HermesWebFetcher()
    await client.connect()
    
    # Get active tab
    tab = await client.get_active_tab()
    tab_id = tab['id']
    
    # Navigate to collection page
    await client.navigate(tab_id, "https://zhihu.com/collection/123")
    await asyncio.sleep(3)
    
    # Fetch list items
    items = await client.fetch_list(tab_id)
    for item in items['items']:
        print(f"  {item['title']}")
    
    await client.disconnect()
        """)
        
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
