/**
 * Hermes Web Fetcher - Background Service Worker
 * 
 * Architecture inspired by Accio Browser Relay:
 * - 3-state model: DISABLED / DISCONNECTED / CONNECTED
 * - State persistence via chrome.storage.local
 * - Toggle control in popup
 */

// ========== Constants (State Model) ==========

const RelayState = {
  DISABLED: 'disabled',      // User toggled off - no connection
  DISCONNECTED: 'disconnected', // Enabled but not connected (connecting)
  CONNECTED: 'connected'     // WebSocket connected
};

const SERVER_URL = 'ws://localhost:9234';

// ========== State Variables ==========

let ws = null;
let relayEnabled = false;      // User preference (persisted)
let currentRelayState = RelayState.DISABLED;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

// ========== Initialization ==========

async function initFromStorage() {
  const result = await chrome.storage.local.get(['relayEnabled', '_relayState']);
  
  relayEnabled = result.relayEnabled ?? false;
  currentRelayState = relayEnabled ? RelayState.DISCONNECTED : RelayState.DISABLED;
  
  console.log('[Hermes] Init from storage:', { relayEnabled, currentRelayState });
  
  // Update internal state storage (for popup to read)
  await chrome.storage.local.set({ _relayState: currentRelayState });
  
  if (relayEnabled) {
    connectToServer();
  }
}

// ========== WebSocket Connection ==========

function connectToServer() {
  if (!relayEnabled) {
    console.log('[Hermes] Relay disabled, skip connection');
    return;
  }
  
  if (ws && ws.readyState !== WebSocket.CLOSED) {
    console.log('[Hermes] Already connected or connecting');
    return;
  }
  
  console.log('[Hermes] Connecting to server:', SERVER_URL);
  updateState(RelayState.DISCONNECTED);
  
  try {
    ws = new WebSocket(SERVER_URL);
  } catch (e) {
    console.error('[Hermes] WebSocket creation failed:', e);
    scheduleReconnect();
    return;
  }
  
  ws.onopen = () => {
    console.log('[Hermes] ✅ Connected to server');
    reconnectAttempts = 0;
    updateState(RelayState.CONNECTED);
  };
  
  ws.onmessage = handleServerMessage;
  
  ws.onclose = (e) => {
    console.log(`[Hermes] ❌ Disconnected: code=${e.code}, reason=${e.reason}`);
    ws = null;
    
    if (relayEnabled) {
      updateState(RelayState.DISCONNECTED);
      scheduleReconnect();
    }
  };
  
  ws.onerror = (err) => {
    console.error('[Hermes] WebSocket error:', err);
  };
}

function disconnectFromServer() {
  if (ws) {
    console.log('[Hermes] Disconnecting from server...');
    ws.close(1000, 'User disabled relay');
    ws = null;
  }
  updateState(RelayState.DISABLED);
}

function updateState(newState) {
  currentRelayState = newState;
  chrome.storage.local.set({ _relayState: newState });
}

function scheduleReconnect() {
  if (!relayEnabled) {
    console.log('[Hermes] Relay disabled, stop reconnecting');
    return;
  }
  
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.log('[Hermes] Max reconnect attempts, retry in 60s');
    setTimeout(() => {
      if (relayEnabled) {
        reconnectAttempts = 0;
        connectToServer();
      }
    }, 60000);
    return;
  }
  
  reconnectAttempts++;
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  console.log(`[Hermes] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
  
  setTimeout(() => {
    if (relayEnabled) {
      connectToServer();
    }
  }, delay);
}

// ========== Server Message Handling ==========

async function handleServerMessage(event) {
  try {
    // In Service Worker, WebSocket messages arrive as Blob objects
    // Convert Blob to text first before JSON parsing
    let textData;
    if (event.data instanceof Blob) {
      textData = await event.data.text();
    } else {
      textData = event.data;
    }
    
    const msg = JSON.parse(textData);
    
    if (msg.type === 'welcome') {
      console.log('[Hermes] Server welcome:', msg);
      return;
    }
    
    if (msg.type === 'ping') {
      ws.send(JSON.stringify({ type: 'pong' }));
      return;
    }
    
    if (msg.method === 'forwardCDPCommand') {
      const { method, params } = msg.params;
      console.log(`[Hermes] ← Command: ${method}`, params);
      
      let result;
      try {
        result = await handleCommand(method, params);
      } catch (err) {
        console.error(`[Hermes] Error executing ${method}:`, err);
        result = { error: err.message || String(err) };
      }
      
      const response = { id: msg.id, result };
      ws.send(JSON.stringify(response));
    }
  } catch (err) {
    console.error('[Hermes] Message error:', err);
  }
}

async function handleCommand(method, params) {
  switch (method) {
    case 'Hermes.fetchArticle':
      return handleFetchArticle(params.tabId);
    case 'Hermes.fetchList':
      return handleFetchList(params.tabId, params.options);
    case 'Hermes.getPageInfo':
      return handleGetPageInfo(params.tabId);
    case 'Hermes.getActiveTab':
      return handleGetActiveTab();
    case 'Hermes.navigate':
      return handleNavigate(params.tabId, params.url);
    default:
      return { error: `Unknown method: ${method}` };
  }
}

// ========== Command Handlers ==========

async function handleFetchArticle(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const title = document.querySelector('h1')?.textContent?.trim() || 
                   document.querySelector('meta[property="og:title"]')?.content ||
                   document.title.split('-')[0].trim() || '';
      
      function simpleExtract() {
        const main = document.querySelector('main, article, [role="main"], #content, .content, .Post-RichText, .RichText');
        const root = main || document.body;
        const lines = [];
        
        const walk = (node) => {
          if (node.nodeType === 3) {
            const t = node.textContent.replace(/\s+/g, ' ').trim();
            if (t) lines.push(t);
            return;
          }
          if (node.nodeType !== 1) return;
          
          const tag = node.tagName;
          try {
            const style = getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden') return;
          } catch { /* skip */ }
          
          if (/^H[1-6]$/.test(tag)) {
            lines.push('\n' + '#'.repeat(+tag[1]) + ' ' + node.textContent.trim());
          } else if (tag === 'P') {
            lines.push('\n' + node.innerText.replace(/\s+/g, ' ').trim());
          } else if (tag === 'LI') {
            lines.push('- ' + node.innerText.replace(/\s+/g, ' ').trim());
          } else if (tag === 'A' && node.href) {
            lines.push(`[${node.textContent.trim()}](${node.href})`);
          } else if (tag === 'IMG' && node.alt) {
            lines.push(`![${node.alt}](${node.src})`);
          } else if (tag === 'PRE' || tag === 'CODE') {
            lines.push('\n```\n' + node.textContent.trim() + '\n```');
          } else if (tag === 'BR') {
            lines.push('\n');
          } else if (tag === 'TABLE') {
            lines.push('\n' + node.innerText.replace(/\t/g, ' | ').trim());
          } else {
            for (const child of node.childNodes) walk(child);
          }
        };
        
        walk(root);
        return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
      }
      
      function scoringExtract() {
        const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'FOOTER', 'HEADER', 'ASIDE', 'FORM']);
        const candidates = [];
        
        function score(el) {
          if (SKIP.has(el.tagName)) return 0;
          const text = el.innerText || '';
          const textLen = text.length;
          if (textLen < 25) return 0;
          
          let s = 0;
          const paragraphs = el.querySelectorAll('p');
          s += paragraphs.length * 3;
          s += Math.min(textLen / 100, 30);
          
          const links = el.querySelectorAll('a');
          const linkText = [...links].reduce((sum, a) => sum + (a.textContent || '').length, 0);
          const linkDensity = textLen > 0 ? linkText / textLen : 1;
          if (linkDensity > 0.5) s *= 0.3;
          
          const commas = (text.match(/[,,.]/g) || []).length;
          s += commas;
          
          if (el.id?.match(/article|content|main|post|body/i)) s *= 1.5;
          if (el.className?.match(/article|content|main|post|body/i)) s *= 1.3;
          if (el.className?.match(/sidebar|comment|footer|nav|menu|ad|banner/i)) s *= 0.3;
          
          return s;
        }
        
        for (const el of document.querySelectorAll('div, section, article, main')) {
          const s = score(el);
          if (s > 0) candidates.push({ el, score: s });
        }
        
        candidates.sort((a, b) => b.score - a.score);
        const best = candidates[0];
        if (!best || best.score < 10) return '';
        
        const text = best.el.innerText || '';
        return text.replace(/\t/g, ' ').replace(/ {2,}/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
      }
      
      const simple = simpleExtract();
      const scored = scoringExtract();
      
      let content;
      if (simple.length >= scored.length || simple.length > 800) {
        content = simple;
      } else {
        content = scored;
      }
      
      if (content.length < 200) {
        const fallback = (document.body?.innerText || '')
          .replace(/\t/g, ' ').replace(/ {2,}/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
        if (fallback.length > content.length) content = fallback;
      }
      
      const author = document.querySelector('.UserLink-link, .AuthorInfo-name, .Post-Author, .author, .byline, meta[name="author"]')?.textContent?.trim() || 
                    document.querySelector('meta[property="article:author"]')?.content || '';
      
      const dateEl = document.querySelector('time, .date, .published, meta[property="article:published_time"]');
      const date = dateEl ? (dateEl.getAttribute('datetime') || dateEl.getAttribute('content') || dateEl.textContent.trim()) : '';
      
      return {
        title,
        content: content.slice(0, 50000),
        author: author.slice(0, 200),
        date: date.slice(0, 20),
        url: window.location.href,
        method: content === simple ? 'walker' : content.length < 200 ? 'body-fallback' : 'scoring'
      };
    }
  });
  
  return results[0]?.result || { error: 'No result' };
}

async function handleFetchList(tabId, options = {}) {
  const {
    itemSelector = '[data-zop-question], [data-zop], .CollectionItem, .ContentItem, article, .post',
    titleSelector = 'h2, h3, .ContentItem-title, a[data-zop-question], .title',
    linkSelector = 'a[href*="/question/"], a[href*="/p/"], a.article-link, a.post-link, a[href]',
    authorSelector = '.UserLink-link, .ContentItem-actions a[href*="/people/"], .author, .byline',
    dateSelector = 'time, .ContentItem-meta time, .date, .published',
    idPattern = '/p/(\\d+)|/question/(\\d+)|/article/(\\d+)',
    maxItems = 100
  } = options;
  
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (selectors, idPattern, maxItems) => {
      const items = [];
      const elements = document.querySelectorAll(selectors.itemSelector);
      
      elements.forEach((item, index) => {
        if (items.length >= maxItems) return;
        
        const titleEl = item.querySelector(selectors.titleSelector);
        const linkEl = item.querySelector(selectors.linkSelector);
        const authorEl = item.querySelector(selectors.authorSelector);
        const dateEl = item.querySelector(selectors.dateSelector);
        
        if (titleEl && linkEl) {
          const url = linkEl.href.split('?')[0];
          const idMatch = url.match(new RegExp(idPattern));
          const articleId = idMatch ? (idMatch[1] || idMatch[2] || idMatch[3]) : 'unknown';
          
          items.push({
            index: index,
            title: titleEl.textContent.trim(),
            url: url,
            id: articleId,
            author: authorEl ? authorEl.textContent.trim() : '',
            date: dateEl ? dateEl.getAttribute('datetime') || dateEl.textContent.trim() : ''
          });
        }
      });
      
      const pagination = document.querySelector('.Pagination, .pagination, .pager, [role="navigation"]');
      let pageInfo = { currentPage: 1, totalPages: 1 };
      
      if (pagination) {
        const pages = Array.from(pagination.querySelectorAll('button, a, span'))
          .map(el => el.textContent).filter(t => /^\d+$/.test(t.trim()));
        if (pages.length > 0) {
          pageInfo.totalPages = Math.max(...pages.map(Number));
        }
        
        const activePage = pagination.querySelector('.active, [aria-current="page"], button[disabled]');
        if (activePage && /^\d+$/.test(activePage.textContent.trim())) {
          pageInfo.currentPage = parseInt(activePage.textContent.trim());
        }
      }
      
      const urlParams = new URLSearchParams(window.location.search);
      const pageParam = urlParams.get('page');
      if (pageParam && /^\d+$/.test(pageParam)) {
        pageInfo.currentPage = parseInt(pageParam);
      }
      
      return {
        items,
        pageInfo,
        totalItems: items.length,
        url: window.location.href
      };
    },
    args: [{
      itemSelector,
      titleSelector,
      linkSelector,
      authorSelector,
      dateSelector
    }, idPattern, maxItems]
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

async function handleGetActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tabs.length === 0) {
    return { error: 'No active tab' };
  }
  const tab = tabs[0];
  return {
    id: tab.id,
    title: tab.title,
    url: tab.url
  };
}

async function handleNavigate(tabId, url) {
  await chrome.tabs.update(tabId, { url });
  
  return new Promise((resolve) => {
    const checkLoaded = () => {
      chrome.tabs.get(tabId, (tab) => {
        if (tab.status === 'complete') {
          setTimeout(() => resolve({ 
            success: true, 
            title: tab.title, 
            url: tab.url 
          }), 2000);
        } else {
          setTimeout(checkLoaded, 500);
        }
      });
    };
    checkLoaded();
  });
}

// ========== Popup Message Handlers ==========

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // Toggle relay on/off (from popup)
  if (msg.type === 'toggleRelay') {
    relayEnabled = !relayEnabled;
    chrome.storage.local.set({ relayEnabled });
    
    if (relayEnabled) {
      reconnectAttempts = 0;
      connectToServer();
    } else {
      disconnectFromServer();
    }
    
    sendResponse({ relayEnabled, relayState: currentRelayState });
    return true;
  }
  
  // Get relay status (from popup)
  if (msg.type === 'getRelayStatus') {
    sendResponse({
      relayEnabled,
      relayState: currentRelayState,
      connected: ws && ws.readyState === WebSocket.OPEN,
      reconnectAttempts
    });
    return true;
  }
  
  // Legacy actions (direct popup commands)
  if (msg.action === 'fetchList') {
    handleFetchList(msg.tabId, msg.options).then(result => {
      sendResponse({ success: true, data: result });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
  
  if (msg.action === 'fetchArticle') {
    handleFetchArticle(msg.tabId).then(result => {
      sendResponse({ success: true, data: result });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
  
  if (msg.action === 'navigate') {
    handleNavigate(msg.tabId, msg.url).then(result => {
      sendResponse({ success: true, data: result });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
  
  if (msg.action === 'getPageInfo') {
    handleGetPageInfo(msg.tabId).then(result => {
      sendResponse({ success: true, data: result });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
  
  if (msg.action === 'getActiveTab') {
    handleGetActiveTab().then(result => {
      sendResponse({ success: true, data: result });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
  
  if (msg.action === 'getStatus') {
    sendResponse({
      connected: ws && ws.readyState === WebSocket.OPEN,
      reconnectAttempts: reconnectAttempts,
      relayEnabled,
      relayState: currentRelayState
    });
    return true;
  }
});

// ========== Storage Change Listener ==========

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && 'relayEnabled' in changes) {
    relayEnabled = changes.relayEnabled.newValue;
    console.log('[Hermes] relayEnabled changed to:', relayEnabled);
    
    if (relayEnabled) {
      reconnectAttempts = 0;
      connectToServer();
    } else {
      disconnectFromServer();
    }
  }
});

// ========== Keep Alive (Service Worker) ==========

chrome.alarms.create('hermesKeepAlive', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'hermesKeepAlive') {
    if (relayEnabled) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      } else if (!ws || ws.readyState === WebSocket.CLOSED) {
        console.log('[Hermes] Keepalive: reconnecting...');
        connectToServer();
      }
    }
  }
});

// ========== Initialize on Install/Startup ==========

chrome.runtime.onInstalled.addListener(async () => {
  console.log('[Hermes] Extension installed');
  await initFromStorage();
});

chrome.runtime.onStartup.addListener(async () => {
  console.log('[Hermes] Browser startup');
  await initFromStorage();
});

// Also initialize immediately (for reload during development)
initFromStorage();