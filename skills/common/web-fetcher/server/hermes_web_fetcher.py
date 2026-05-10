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
    
    # ========== Control Methods (v2.0) ==========
    
    async def fill_input(self, tab_id: int, selector: str, value: str, 
                         clear_first: bool = True, trigger_react: bool = False) -> Dict[str, Any]:
        """
        Fill input/textarea/contenteditable element (supports Draft.js, React)
        
        Args:
            tab_id: Tab ID
            selector: CSS selector for the element
            value: Text to fill
            clear_first: Clear existing content first (default True)
            trigger_react: Force React/Draft.js handling (default False, auto-detected)
        
        Returns:
            Dict with success status and filled content info
        """
        return await self._send_request("Hermes.fillInput", {
            "tabId": tab_id,
            "selector": selector,
            "value": value,
            "options": {"clearFirst": clear_first, "triggerReact": trigger_react}
        })
    
    async def click_element(self, tab_id: int, selector: str,
                           double_click: bool = False) -> Dict[str, Any]:
        """
        Click an element
        
        Args:
            tab_id: Tab ID
            selector: CSS selector for the element
            double_click: Perform double click (default False)
        
        Returns:
            Dict with success status
        """
        return await self._send_request("Hermes.clickElement", {
            "tabId": tab_id,
            "selector": selector,
            "options": {"doubleClick": double_click}
        })
    
    async def send_keys(self, tab_id: int, selector: str, text: str) -> Dict[str, Any]:
        """
        Simulate typing text into element
        
        Args:
            tab_id: Tab ID
            selector: CSS selector for the element
            text: Text to type
        
        Returns:
            Dict with success status and typed character count
        """
        return await self._send_request("Hermes.sendKeys", {
            "tabId": tab_id,
            "selector": selector,
            "text": text
        })
    
    async def wait_for(self, tab_id: int, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """
        Wait for element to appear and be visible
        
        Args:
            tab_id: Tab ID
            selector: CSS selector for the element
            timeout: Timeout in milliseconds (default 5000)
        
        Returns:
            Dict with success status or timeout error
        """
        return await self._send_request("Hermes.waitFor", {
            "tabId": tab_id,
            "selector": selector,
            "timeout": timeout
        })
    
    async def call_api(self, tab_id: int, url: str, method: str = "GET",
                       data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call API from within the page (uses page's cookies/auth)
        
        Args:
            tab_id: Tab ID
            url: API URL
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request body data (for POST/PUT)
        
        Returns:
            Dict with API response
        """
        return await self._send_request("Hermes.callApi", {
            "tabId": tab_id,
            "url": url,
            "method": method,
            "data": data
        }, timeout=60.0)
    
    async def get_element_info(self, tab_id: int, selector: str) -> Dict[str, Any]:
        """
        Get element info (value, attributes, state)
        
        Args:
            tab_id: Tab ID
            selector: CSS selector for the element
        
        Returns:
            Dict with element info
        """
        return await self._send_request("Hermes.getElementInfo", {
            "tabId": tab_id,
            "selector": selector
        })
    
    async def blur(self, tab_id: int, selector: str) -> Dict[str, Any]:
        """
        Blur element (trigger save in auto-save editors)
        
        Args:
            tab_id: Tab ID
            selector: CSS selector for the element
        
        Returns:
            Dict with success status
        """
        return await self._send_request("Hermes.blur", {
            "tabId": tab_id,
            "selector": selector
        })
    
    # ========== Screenshot Methods (v2.2) ==========
    
    async def screenshot(self, tab_id: int = None, 
                         options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Capture screenshot of visible tab
        
        Args:
            tab_id: Tab ID (optional, captures active tab if not specified)
            options: Dict with format ('png' or 'jpeg'), quality (0-100)
        
        Returns:
            Dict with success, dataUrl (base64 image), format
        """
        opts = options or {}
        return await self._send_request("Hermes.screenshot", {
            "tabId": tab_id,
            "options": opts
        })
    
    async def screenshot_to_file(self, tab_id: int = None, 
                                  filepath: str = None,
                                  format: str = 'png') -> str:
        """
        Capture screenshot and save to file
        
        Args:
            tab_id: Tab ID (optional)
            filepath: Output file path (default: ~/.hermes/screenshot_{timestamp}.png)
            format: Image format ('png' or 'jpeg')
        
        Returns:
            File path where screenshot was saved
        """
        import base64
        import os
        from datetime import datetime
        
        result = await self.screenshot(tab_id, {"format": format})
        
        if 'error' in result or not result.get('success'):
            raise Exception(result.get('error', 'Screenshot failed'))
        
        # Generate default filepath
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.expanduser(f"~/.hermes/screenshot_{timestamp}.{format}")
        
        # Decode base64 and save
        data_url = result.get('dataUrl', '')
        if data_url.startswith('data:image'):
            # Remove data:image/png;base64, prefix
            base64_data = data_url.split(',', 1)[1]
            image_data = base64.b64decode(base64_data)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            return filepath
        
        raise Exception("Invalid screenshot data format")
    
    # ========== Agent Tab Group Methods (v2.1) ==========
    
    async def create_agent_tab(self, url: str) -> Dict[str, Any]:
        """
        Create new tab in Hermes Agent group (not user's active tab)
        
        Args:
            url: URL to navigate
        
        Returns:
            Dict with tab id, title, url
        """
        return await self._send_request("Hermes.createAgentTab", {"url": url})
    
    async def add_to_agent_group(self, tab_id: int) -> Dict[str, Any]:
        """
        Add existing tab to Hermes Agent group
        
        Args:
            tab_id: Tab ID to add
        
        Returns:
            Dict with groupId and tabId
        """
        return await self._send_request("Hermes.addToAgentGroup", {"tabId": tab_id})
    
    async def close_agent_tab(self, tab_id: int) -> Dict[str, Any]:
        """
        Close an agent tab
        
        Args:
            tab_id: Tab ID to close
        
        Returns:
            Dict with success status
        """
        return await self._send_request("Hermes.closeAgentTab", {"tabId": tab_id})
    
    async def dissolve_agent_group(self) -> Dict[str, Any]:
        """
        Dissolve Hermes Agent group - close all agent tabs
        
        Returns:
            Dict with closed count and ungrouped count
        """
        return await self._send_request("Hermes.dissolveAgentGroup")
    
    async def list_agent_tabs(self) -> Dict[str, Any]:
        """
        List all agent tabs
        
        Returns:
            Dict with groupId, tabs list, count
        """
        return await self._send_request("Hermes.listAgentTabs")


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
