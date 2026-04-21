/**
 * Hermes Web Fetcher - Background Service Worker
 * 
 * Architecture inspired by Accio Browser Relay:
 * - 3-state model: DISABLED / DISCONNECTED / CONNECTED
 * - State persistence via chrome.storage.local
 * - Toggle control in popup
 * 
 * v2.1: Added Agent Tab Group (separate from user tabs)
 */

// ========== Constants (State Model) ==========

const RelayState = {
  DISABLED: 'disabled',      // User toggled off - no connection
  DISCONNECTED: 'disconnected', // Enabled but not connected (connecting)
  CONNECTED: 'connected'     // WebSocket connected
};

const SERVER_URL = 'ws://localhost:9234';

// ========== Agent Tab Group Manager ==========

const TAB_GROUP_TITLE = 'Hermes Agent';
const TAB_GROUP_COLOR = 'purple';

let agentGroupId = null;
let agentTabs = new Set();  // Tab IDs created by Hermes
let groupQueue = Promise.resolve();  // Serialization queue

async function getOrCreateGroup() {
  // Try to find existing group
  if (agentGroupId !== null) {
    try {
      await chrome.tabGroups.get(agentGroupId);
      return agentGroupId;
    } catch {
      agentGroupId = null;
    }
  }
  
  // Try to recover existing group by title
  try {
    const groups = await chrome.tabGroups.query({ title: TAB_GROUP_TITLE });
    if (groups.length > 0) {
      agentGroupId = groups[0].id;
      console.log('[Hermes] Recovered existing group:', agentGroupId);
      return agentGroupId;
    }
  } catch {}
  
  // Create new group (will be created when first tab is added)
  return null;
}

async function addToAgentGroup(tabId) {
  // Direct execution (no queue - simpler for Service Worker)
  return await _doAddToGroup(tabId);
}

async function _doAddToGroup(tabId) {
  try {
    agentTabs.add(tabId);
    
    // Get or create group
    let gid = await getOrCreateGroup();
    
    // Add tab to group
    const newGroupId = await chrome.tabs.group({
      tabIds: [tabId],
      ...(gid !== null ? { groupId: gid } : {})
    });
    
    if (gid === null || newGroupId !== gid) {
      agentGroupId = newGroupId;
      await chrome.tabGroups.update(newGroupId, {
        title: TAB_GROUP_TITLE,
        color: TAB_GROUP_COLOR,
        collapsed: false
      });
      console.log('[Hermes] Created/updated agent group:', agentGroupId);
    }
    
    return { groupId: agentGroupId, tabId };
  } catch (err) {
    console.warn('[Hermes] addToAgentGroup failed:', err);
    return null;
  }
}

async function createAgentTab(url) {
  try {
    // Create new tab
    const tab = await chrome.tabs.create({ url, active: false });
    console.log('[Hermes] Created agent tab:', tab.id, url);
    
    // Add to agent group
    await addToAgentGroup(tab.id);
    
    // Wait for load (use Promise-based API)
    const waitForLoad = () => {
      return new Promise((resolve) => {
        const check = async () => {
          try {
            const t = await chrome.tabs.get(tab.id);
            if (t.status === 'complete') {
              resolve(t);
            } else {
              setTimeout(check, 500);
            }
          } catch (err) {
            console.warn('[Hermes] Tab check error:', err);
            resolve({ error: err.message });
          }
        };
        setTimeout(check, 500);  // Start checking after 500ms
      });
    };
    
    const loadedTab = await waitForLoad();
    if (loadedTab.error) {
      return { error: loadedTab.error };
    }
    
    // Wait 1 more second for JS to execute
    await new Promise(r => setTimeout(r, 1000));
    
    const finalTab = await chrome.tabs.get(tab.id);
    return { id: finalTab.id, title: finalTab.title, url: finalTab.url };
  } catch (err) {
    console.error('[Hermes] createAgentTab failed:', err);
    return { error: err.message };
  }
}

async function closeAgentTab(tabId) {
  try {
    agentTabs.delete(tabId);
    await chrome.tabs.remove(tabId);
    console.log('[Hermes] Closed agent tab:', tabId);
    return { success: true };
  } catch (err) {
    console.warn('[Hermes] closeAgentTab failed:', err);
    return { error: err.message };
  }
}

async function dissolveAgentGroup() {
  let gid = agentGroupId;
  agentGroupId = null;
  
  if (gid === null) {
    try {
      const groups = await chrome.tabGroups.query({ title: TAB_GROUP_TITLE });
      if (groups.length > 0) gid = groups[0].id;
    } catch {}
  }
  
  if (gid === null) {
    console.log('[Hermes] No agent group to dissolve');
    return { success: true, closed: 0 };
  }
  
  try {
    const tabs = await chrome.tabs.query({ groupId: gid });
    const tabIds = tabs.map(t => t.id).filter(id => id != null);
    
    // Close agent-created tabs
    const toClose = tabIds.filter(id => agentTabs.has(id));
    if (toClose.length > 0) {
      await chrome.tabs.remove(toClose);
      console.log('[Hermes] Closed', toClose.length, 'agent tabs');
    }
    
    // Ungroup user tabs (if any were added)
    const toUngroup = tabIds.filter(id => !agentTabs.has(id));
    if (toUngroup.length > 0) {
      await chrome.tabs.ungroup(toUngroup);
      console.log('[Hermes] Ungrouped', toUngroup.length, 'user tabs');
    }
    
    agentTabs.clear();
    return { success: true, closed: toClose.length, ungrouped: toUngroup.length };
  } catch (err) {
    console.warn('[Hermes] dissolveAgentGroup failed:', err);
    return { error: err.message };
  }
}

async function listAgentTabs() {
  return {
    groupId: agentGroupId,
    tabs: [...agentTabs],
    count: agentTabs.size
  };
}

// ========== State Variables ==========

let ws = null;
let relayEnabled = false;      // User preference (persisted)
let autoConnectEnabled = false; // Auto reconnect every 10s (persisted)
let currentRelayState = RelayState.DISABLED;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

// ========== Initialization ==========

async function initFromStorage() {
  const result = await chrome.storage.local.get(['relayEnabled', 'autoConnectEnabled', '_relayState']);
  
  relayEnabled = result.relayEnabled ?? false;
  autoConnectEnabled = result.autoConnectEnabled ?? false;
  currentRelayState = relayEnabled ? RelayState.DISCONNECTED : RelayState.DISABLED;
  
  console.log('[Hermes] Init from storage:', { relayEnabled, autoConnectEnabled, currentRelayState });
  
  // Update internal state storage (for popup to read)
  await chrome.storage.local.set({ _relayState: currentRelayState });
  
  // Create autoConnect alarm if enabled
  if (autoConnectEnabled) {
    chrome.alarms.create('hermesAutoConnect', { periodInMinutes: 1/6 }); // Every 10 seconds
  }
  
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
    // ========== Control Commands (v2.0) ==========
    case 'Hermes.fillInput':
      return handleFillInput(params.tabId, params.selector, params.value, params.options);
    case 'Hermes.clickElement':
      return handleClickElement(params.tabId, params.selector, params.options);
    case 'Hermes.sendKeys':
      return handleSendKeys(params.tabId, params.selector, params.text);
    case 'Hermes.waitFor':
      return handleWaitFor(params.tabId, params.selector, params.timeout);
    case 'Hermes.callApi':
      return handleCallApi(params.tabId, params.url, params.method, params.data);
    case 'Hermes.getElementInfo':
      return handleGetElementInfo(params.tabId, params.selector);
    case 'Hermes.blur':
      return handleBlur(params.tabId, params.selector);
    // ========== Agent Tab Group Commands (v2.1) ==========
    case 'Hermes.createAgentTab':
      return createAgentTab(params.url);
    case 'Hermes.addToAgentGroup':
      return addToAgentGroup(params.tabId);
    case 'Hermes.closeAgentTab':
      return closeAgentTab(params.tabId);
    case 'Hermes.dissolveAgentGroup':
      return dissolveAgentGroup();
    case 'Hermes.listAgentTabs':
      return listAgentTabs();
    // ========== Screenshot Command (v2.2) ==========
    case 'Hermes.screenshot':
      return handleScreenshot(params.tabId, params.options);
    default:
      return { error: `Unknown method: ${method}` };
  }
}

// ========== Screenshot Handler (v2.2) ==========

async function handleScreenshot(tabId, options = {}) {
  const { format = 'png', quality = 90, savePath = null } = options;
  
  try {
    // 使用 chrome.tabs.captureVisibleTab 截取可见区域
    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
      format: format === 'jpeg' ? 'jpeg' : 'png',
      quality: quality
    });
    
    console.log('[Hermes] Screenshot captured, size:', dataUrl.length);
    
    return {
      success: true,
      dataUrl: dataUrl,
      format: format,
      message: 'Screenshot captured successfully'
    };
  } catch (err) {
    console.error('[Hermes] Screenshot failed:', err);
    return {
      error: err.message || 'Screenshot failed',
      success: false
    };
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
      reconnectAttempts,
      autoConnectEnabled
    });
    return true;
  }
  
  // Toggle auto connect (from popup)
  if (msg.type === 'toggleAutoConnect') {
    autoConnectEnabled = msg.enabled;
    chrome.storage.local.set({ autoConnectEnabled });
    
    if (autoConnectEnabled) {
      // Create auto connect alarm (every 10 seconds)
      chrome.alarms.create('hermesAutoConnect', { periodInMinutes: 1/6 });
      console.log('[Hermes] Auto connect enabled, alarm created');
    } else {
      // Clear alarm
      chrome.alarms.clear('hermesAutoConnect');
      console.log('[Hermes] Auto connect disabled, alarm cleared');
    }
    
    sendResponse({ autoConnectEnabled });
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
  if (area === 'local') {
    if ('relayEnabled' in changes) {
      relayEnabled = changes.relayEnabled.newValue;
      console.log('[Hermes] relayEnabled changed to:', relayEnabled);
      
      if (relayEnabled) {
        reconnectAttempts = 0;
        connectToServer();
      } else {
        disconnectFromServer();
      }
    }
    
    if ('autoConnectEnabled' in changes) {
      autoConnectEnabled = changes.autoConnectEnabled.newValue;
      console.log('[Hermes] autoConnectEnabled changed to:', autoConnectEnabled);
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
  
  // Auto connect alarm (every 10 seconds)
  if (alarm.name === 'hermesAutoConnect') {
    if (!relayEnabled) {
      // relay 未启用 → 自动启用并连接
      console.log('[Hermes] AutoConnect: enabling relay...');
      relayEnabled = true;
      chrome.storage.local.set({ relayEnabled });
      reconnectAttempts = 0;
      connectToServer();
    } else if (!ws || ws.readyState !== WebSocket.OPEN) {
      // relay 已启用但连接断开 → 自动重连
      console.log('[Hermes] AutoConnect: attempting reconnect...');
      reconnectAttempts = 0; // Reset attempts for auto connect
      connectToServer();
    } else {
      // relay 已启用且已连接 → 本次跳过
      console.log('[Hermes] AutoConnect: already connected, skip');
    }
  }
});

// ========== Control Command Handlers (v2.0) ==========
// Inspired by Playwright's fill/click implementation for React/Draft.js editors

/**
 * Fill input/textarea/contenteditable (supports Draft.js, React, vanilla)
 * Key: Simulate Playwright's fill() - focus, select all, input events
 */
async function handleFillInput(tabId, selector, value, options = {}) {
  const { clearFirst = true, triggerReact = false } = options;
  
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (sel, val, opts) => {
      const el = document.querySelector(sel);
      if (!el) return { error: 'element not found', selector: sel };
      
      // Focus first
      el.focus();
      el.dispatchEvent(new FocusEvent('focus', { bubbles: true }));
      
      // Check if Draft.js or contenteditable
      const isContentEditable = el.getAttribute('contenteditable') === 'true';
      const isDraftEditor = el.closest('.DraftEditor-root, .public-DraftEditor-content');
      
      if (isContentEditable || isDraftEditor || opts.triggerReact) {
        // Draft.js / React contenteditable handling
        // 1. Select all existing content
        const selection = window.getSelection();
        const range = document.createRange();
        
        if (opts.clearFirst && el.textContent) {
          range.selectNodeContents(el);
          selection.removeAllRanges();
          selection.addRange(range);
          
          // Trigger delete event
          el.dispatchEvent(new InputEvent('beforeinput', {
            bubbles: true, cancelable: true, inputType: 'deleteContent'
          }));
        }
        
        // 2. Insert new text
        el.dispatchEvent(new InputEvent('beforeinput', {
          bubbles: true, cancelable: true, inputType: 'insertText', data: val
        }));
        
        // 3. Set content (different approaches for different frameworks)
        if (isDraftEditor) {
          // Draft.js: need to set on the inner node
          const innerEl = el.querySelector('[data-contents="true"]') || el;
          innerEl.textContent = val;
        } else {
          el.textContent = val;
        }
        
        // 4. Trigger input event (critical for React state)
        el.dispatchEvent(new InputEvent('input', {
          bubbles: true, inputType: 'insertText', data: val
        }));
        
        // 5. Move cursor to end
        range.selectNodeContents(el);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
        
        // 6. Trigger change
        el.dispatchEvent(new Event('change', { bubbles: true }));
        
      } else {
        // Regular input/textarea
        if (opts.clearFirst) {
          el.value = '';
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        // Use native value setter (React workaround)
        const nativeSetter = Object.getOwnPropertyDescriptor(
          el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
          'value'
        )?.set;
        
        if (nativeSetter) {
          nativeSetter.call(el, val);
        } else {
          el.value = val;
        }
        
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }
      
      // Return result
      const content = isContentEditable ? el.textContent : el.value;
      return {
        success: true,
        selector: sel,
        filledLength: val.length,
        currentContent: content.slice(0, 50)
      };
    },
    args: [selector, value, { clearFirst, triggerReact }]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Click element with proper event propagation
 */
async function handleClickElement(tabId, selector, options = {}) {
  const { delay = 100, doubleClick = false } = options;
  
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (sel, opts) => {
      const el = document.querySelector(sel);
      if (!el) return { error: 'element not found', selector: sel };
      
      // Scroll into view
      el.scrollIntoView({ behavior: 'instant', block: 'center' });
      
      // Click
      el.click();
      el.dispatchEvent(new MouseEvent('click', {
        bubbles: true, cancelable: true, view: window
      }));
      
      if (opts.doubleClick) {
        el.dispatchEvent(new MouseEvent('dblclick', {
          bubbles: true, cancelable: true, view: window
        }));
      }
      
      return { success: true, selector: sel };
    },
    args: [selector, { delay, doubleClick }]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Send keys to element (simulate typing)
 */
async function handleSendKeys(tabId, selector, text) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (sel, txt) => {
      const el = document.querySelector(sel);
      if (!el) return { error: 'element not found', selector: sel };
      
      el.focus();
      
      // Simulate each character
      for (const char of txt) {
        el.dispatchEvent(new KeyboardEvent('keydown', {
          key: char, bubbles: true
        }));
        el.dispatchEvent(new KeyboardEvent('keypress', {
          key: char, bubbles: true
        }));
        el.dispatchEvent(new KeyboardEvent('keyup', {
          key: char, bubbles: true
        }));
        
        // Also trigger input event for each char
        if (el.getAttribute('contenteditable') === 'true') {
          el.dispatchEvent(new InputEvent('input', {
            bubbles: true, inputType: 'insertText', data: char
          }));
        } else {
          el.value += char;
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
      
      el.dispatchEvent(new Event('change', { bubbles: true }));
      
      return { success: true, selector: sel, typed: txt.length };
    },
    args: [selector, text]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Wait for element to appear
 */
async function handleWaitFor(tabId, selector, timeout = 5000) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: async (sel, timeoutMs) => {
      const startTime = Date.now();
      
      while (Date.now() - startTime < timeoutMs) {
        const el = document.querySelector(sel);
        if (el) {
          // Wait for visible
          const style = getComputedStyle(el);
          if (style.display !== 'none' && style.visibility !== 'hidden') {
            return { success: true, selector: sel, found: true };
          }
        }
        await new Promise(r => setTimeout(r, 100));
      }
      
      return { error: 'timeout', selector: sel, timeout: timeoutMs };
    },
    args: [selector, timeout]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Call API from within the page (using page's cookies)
 */
async function handleCallApi(tabId, url, method = 'GET', data = null) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: async (apiUrl, apiMethod, apiData) => {
      // Get xsrf_token from cookie (for Zhihu and similar sites)
      const getXsrf = () => {
        const cookies = document.cookie.split(';');
        for (const c of cookies) {
          const trimmed = c.trim();
          if (trimmed.startsWith('xsrf_token=')) return trimmed.substring(11);
          if (trimmed.startsWith('_xsrf=')) return trimmed.substring(6);
          if (trimmed.startsWith('XSRF-TOKEN=')) return trimmed.substring(11);
        }
        return '';
      };
      
      const xsrf = getXsrf();
      
      const options = {
        method: apiMethod,
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      };
      
      // Add xsrf header for POST/PUT
      if (xsrf && ['POST', 'PUT', 'PATCH'].includes(apiMethod)) {
        options.headers['x-xsrftoken'] = xsrf;
        options.headers['x-zse-83'] = '3_2.0';
      }
      
      if (apiData && ['POST', 'PUT', 'PATCH'].includes(apiMethod)) {
        options.body = JSON.stringify(apiData);
      }
      
      try {
        const response = await fetch(apiUrl, options);
        const result = await response.json();
        return {
          success: response.ok,
          status: response.status,
          data: result
        };
      } catch (err) {
        return { error: err.message };
      }
    },
    args: [url, method, data]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Get element info (text, attributes, state)
 */
async function handleGetElementInfo(tabId, selector) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (sel) => {
      const el = document.querySelector(sel);
      if (!el) return { error: 'element not found', selector: sel };
      
      const isEditable = el.getAttribute('contenteditable') === 'true';
      const content = isEditable ? el.textContent : el.value || '';
      
      return {
        success: true,
        selector: sel,
        tagName: el.tagName,
        type: el.type || null,
        contentEditable: isEditable,
        value: content.slice(0, 200),
        valueLength: content.length,
        placeholder: el.placeholder || null,
        disabled: el.disabled,
        visible: getComputedStyle(el).display !== 'none'
      };
    },
    args: [selector]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Blur element (trigger save in auto-save editors)
 */
async function handleBlur(tabId, selector) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (sel) => {
      const el = document.querySelector(sel);
      if (!el) return { error: 'element not found', selector: sel };
      
      el.blur();
      el.dispatchEvent(new FocusEvent('blur', { bubbles: true }));
      
      return { success: true, selector: sel };
    },
    args: [selector]
  });
  
  return results[0]?.result || { error: 'No result' };
}

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