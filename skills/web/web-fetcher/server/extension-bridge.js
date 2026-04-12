/**
 * Hermes Web Fetcher - Extension Side
 * Connects to local WebSocket server and forwards CDP commands
 */

const SERVER_URL = `ws://localhost:${9234}`;
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

function connectToServer() {
  console.log('[Hermes] Connecting to server:', SERVER_URL);
  
  ws = new WebSocket(SERVER_URL);
  
  ws.onopen = () => {
    console.log('[Hermes] ✅ Connected to server');
    reconnectAttempts = 0;
  };
  
  ws.onmessage = async (event) => {
    try {
      const msg = JSON.parse(event.data);
      
      if (msg.type === 'welcome') {
        console.log('[Hermes] Server welcome:', msg);
        return;
      }
      
      if (msg.method === 'forwardCDPCommand') {
        const { method, params } = msg.params;
        console.log(`[Hermes] ← Command: ${method}`);
        
        // Handle command
        let result;
        try {
          if (method === 'Hermes.fetchArticle') {
            result = await handleFetchArticle(params.tabId);
          } else if (method === 'Hermes.fetchList') {
            result = await handleFetchList(params.tabId, params.options);
          } else if (method === 'Hermes.getPageInfo') {
            result = await handleGetPageInfo(params.tabId);
          } else {
            result = { error: `Unknown method: ${method}` };
          }
        } catch (err) {
          result = { error: err.message };
        }
        
        // Send response
        ws.send(JSON.stringify({
          id: msg.id,
          result
        }));
      }
    } catch (err) {
      console.error('[Hermes] Message error:', err);
    }
  };
  
  ws.onclose = () => {
    console.log('[Hermes] ❌ Disconnected from server');
    scheduleReconnect();
  };
  
  ws.onerror = (err) => {
    console.error('[Hermes] WebSocket error:', err);
  };
}

function scheduleReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.log('[Hermes] Max reconnect attempts reached');
    return;
  }
  
  reconnectAttempts++;
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  console.log(`[Hermes] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
  
  setTimeout(connectToServer, delay);
}

// Command handlers
async function handleFetchArticle(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const title = document.querySelector('h1')?.textContent?.trim() || document.title.split('-')[0].trim() || '';
      const contentEl = document.querySelector('.Post-RichText, .RichText, article, .content') || document.body;
      const contentParts = [];
      
      const walk = (node) => {
        if (node.nodeType === 3) {
          const t = node.textContent.replace(/\s+/g, ' ').trim();
          if (t) contentParts.push(t);
          return;
        }
        if (node.nodeType !== 1) return;
        
        const tag = node.tagName;
        if (/^H[1-6]$/.test(tag)) {
          contentParts.push('\n' + '#'.repeat(+tag[1]) + ' ' + node.textContent.trim());
        } else if (tag === 'P') {
          contentParts.push('\n' + node.innerText.replace(/\s+/g, ' ').trim());
        } else if (tag === 'PRE' || tag === 'CODE') {
          contentParts.push('\n```\n' + node.textContent.trim() + '\n```');
        } else {
          for (const child of node.childNodes) walk(child);
        }
      };
      
      walk(contentEl);
      
      const author = document.querySelector('.UserLink-link, .AuthorInfo-name')?.textContent?.trim() || '';
      const dateEl = document.querySelector('time');
      const date = dateEl ? dateEl.getAttribute('datetime') || dateEl.textContent.trim() : '';
      
      return {
        title,
        content: contentParts.join('\n').replace(/\n{3,}/g, '\n\n').trim().slice(0, 50000),
        author,
        date,
        url: window.location.href
      };
    }
  });
  
  return results[0]?.result || { error: 'No result' };
}

async function handleFetchList(tabId, options = {}) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (selectors) => {
      const items = [];
      const elements = document.querySelectorAll(selectors.itemSelector || '[data-zop], article, .post');
      
      elements.forEach((item, index) => {
        const titleEl = item.querySelector(selectors.titleSelector || 'h2, .title');
        const linkEl = item.querySelector(selectors.linkSelector || 'a[href]');
        
        if (titleEl && linkEl) {
          items.push({
            index,
            title: titleEl.textContent.trim(),
            url: linkEl.href.split('?')[0]
          });
        }
      });
      
      return { items, totalItems: items.length };
    },
    args: [options]
  });
  
  return results[0]?.result || { error: 'No result' };
}

async function handleGetPageInfo(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => ({
      title: document.title,
      url: window.location.href,
      isReady: document.readyState === 'complete'
    })
  });
  
  return results[0]?.result || { error: 'No result' };
}

// Start connection
connectToServer();

// Keep service worker alive
chrome.alarms.create('hermesKeepAlive', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'hermesKeepAlive' && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
});
