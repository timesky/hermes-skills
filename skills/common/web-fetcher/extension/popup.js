/**
 * Hermes Web Fetcher - Popup UI Logic
 * 
 * Relay Control (inspired by Accio):
 * - Toggle to enable/disable WebSocket connection
 * - Real-time status display
 */

const statusEl = document.getElementById('status');
const pageInfoEl = document.getElementById('pageInfo');
const relayToggle = document.getElementById('relayToggle');
const relayStatusBadge = document.getElementById('relayStatusBadge');
const relayToggleText = document.getElementById('relayToggleText');
const serverInfoEl = document.getElementById('serverInfo');
const autoConnectToggle = document.getElementById('autoConnectToggle');
const autoConnectText = document.getElementById('autoConnectText');

// ========== Relay Control ==========

async function initRelayControl() {
  const status = await getRelayStatus();
  updateRelayUI(status);
  if (autoConnectToggle) {
    updateAutoConnectUI(status.autoConnectEnabled);
  }
}

function updateRelayUI(status) {
  relayToggle.checked = status.relayEnabled;
  
  // Update badge
  relayStatusBadge.className = 'relay-status ' + status.relayState;
  relayStatusBadge.textContent = getStatusLabel(status.relayState);
  
  // Update toggle text
  relayToggleText.textContent = status.relayEnabled 
    ? '已启用 - 连接到服务器' 
    : '点击启用连接';
  
  // Update server info with connection details
  if (status.relayEnabled) {
    serverInfoEl.textContent = status.connected 
      ? `ws://localhost:9234 ✅ 已连接` 
      : `ws://localhost:9234 ⏳ ${status.reconnectAttempts > 0 ? `重试 #${status.reconnectAttempts}` : '连接中...'}`;
  } else {
    serverInfoEl.textContent = 'ws://localhost:9234 (未启用)';
  }
}

function updateAutoConnectUI(enabled) {
  if (!autoConnectToggle) return;
  autoConnectToggle.checked = enabled;
  if (autoConnectText) {
    autoConnectText.textContent = enabled 
      ? '自动连接 ✅ (每10秒)' 
      : '自动连接 (每10秒)';
  }
}

function getStatusLabel(state) {
  switch (state) {
    case 'connected': return '已连接';
    case 'disconnected': return '断开';
    case 'disabled': return '禁用';
    default: return '未知';
  }
}

async function getRelayStatus() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'getRelayStatus' }, (response) => {
      resolve(response || { relayEnabled: false, relayState: 'disabled', connected: false, autoConnectEnabled: false });
    });
  });
}

// Toggle handler
relayToggle.addEventListener('change', async () => {
  const response = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'toggleRelay' }, resolve);
  });
  
  updateRelayUI(response);
  
  // Show status message
  if (response.relayEnabled) {
    setStatus('状态：已启用 WebSocket 连接');
  } else {
    setStatus('状态：已禁用 WebSocket 连接');
  }
});

// Auto Connect Toggle handler
if (autoConnectToggle) {
  autoConnectToggle.addEventListener('change', async () => {
    const enabled = autoConnectToggle.checked;
    
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'toggleAutoConnect', enabled }, resolve);
    });
    
    updateAutoConnectUI(response.autoConnectEnabled);
    
    // Show status message
    if (response.autoConnectEnabled) {
      setStatus('状态：已启用自动连接 (每10秒尝试)');
    } else {
      setStatus('状态：已禁用自动连接');
    }
  });
}

// Periodically update relay status (every 2 seconds)
setInterval(async () => {
  const status = await getRelayStatus();
  updateRelayUI(status);
}, 2000);

// ========== Utility Functions ==========

function setStatus(text, type = 'info') {
  statusEl.textContent = text;
  statusEl.style.color = type === 'error' ? '#dc3545' : '#666';
}

async function getActiveTab() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'getActiveTab' }, (response) => {
      resolve(response?.data);
    });
  });
}

// ========== Button Handlers ==========

// Page Info button
document.getElementById('pageInfoBtn').addEventListener('click', async () => {
  setStatus('状态：获取页面信息...');
  
  try {
    const tab = await getActiveTab();
    if (!tab) {
      setStatus('状态：未找到活动标签页', 'error');
      return;
    }
    
    const result = await chrome.runtime.sendMessage({
      action: 'getPageInfo',
      tabId: tab.id
    });
    
    if (result.success) {
      const data = result.data;
      setStatus('状态：获取成功');
      pageInfoEl.innerHTML = `
        <strong>标题:</strong> ${data.title?.substring(0, 50)}...<br>
        <strong>URL:</strong> ${data.url?.substring(0, 60)}...<br>
        <strong>状态:</strong> ${data.isReady ? '已加载' : '加载中'}
      `;
      console.log('Page info:', data);
    } else {
      setStatus(`状态：错误 - ${result.error}`, 'error');
    }
  } catch (error) {
    setStatus(`状态：错误 - ${error.message}`, 'error');
  }
});

// List fetch button
document.getElementById('listBtn').addEventListener('click', async () => {
  setStatus('状态：抓取列表...');
  
  try {
    const tab = await getActiveTab();
    if (!tab) {
      setStatus('状态：未找到活动标签页', 'error');
      return;
    }
    
    const result = await chrome.runtime.sendMessage({
      action: 'fetchList',
      tabId: tab.id,
      options: {}
    });
    
    if (result.success) {
      const data = result.data;
      setStatus(`状态：获取到 ${data.totalItems || 0} 项`);
      pageInfoEl.innerHTML = `
        <strong>总数:</strong> ${data.totalItems || 0}<br>
        <strong>页码:</strong> ${data.pageInfo?.currentPage || 1} / ${data.pageInfo?.totalPages || 1}<br>
        <strong>URL:</strong> ${data.url?.substring(0, 50)}...
      `;
      console.log('List data:', data);
    } else {
      setStatus(`状态：错误 - ${result.error}`, 'error');
    }
  } catch (error) {
    setStatus(`状态：错误 - ${error.message}`, 'error');
  }
});

// Article fetch button
document.getElementById('articleBtn').addEventListener('click', async () => {
  setStatus('状态：抓取文章...');
  
  try {
    const tab = await getActiveTab();
    if (!tab) {
      setStatus('状态：未找到活动标签页', 'error');
      return;
    }
    
    const result = await chrome.runtime.sendMessage({
      action: 'fetchArticle',
      tabId: tab.id
    });
    
    if (result.success) {
      const data = result.data;
      setStatus(`状态：获取到 "${data.title?.substring(0, 20)}..."`);
      pageInfoEl.innerHTML = `
        <strong>标题:</strong> ${data.title?.substring(0, 50)}...<br>
        <strong>作者:</strong> ${data.author || '未知'}<br>
        <strong>日期:</strong> ${data.date || '未知'}<br>
        <strong>长度:</strong> ${data.content?.length || 0} 字符<br>
        <strong>方法:</strong> ${data.method || 'unknown'}
      `;
      console.log('Article data:', data);
    } else {
      setStatus(`状态：错误 - ${result.error}`, 'error');
    }
  } catch (error) {
    setStatus(`状态：错误 - ${error.message}`, 'error');
  }
});

// Quick access: Zhihu
document.getElementById('zhihuBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://www.zhihu.com/collection/797328373?page=1' });
  window.close();
});

// Quick access: GitHub Trending
document.getElementById('githubBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://github.com/trending' });
  window.close();
});

// ========== Initialize ==========

initRelayControl();