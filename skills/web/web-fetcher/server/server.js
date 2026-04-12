/**
 * Hermes Web Fetcher - Local WebSocket Server
 * 
 * Bridges Hermes Agent (Python) ↔ Chrome Extension
 * Similar to Accio's relay server
 */

import { WebSocketServer, WebSocket } from 'ws';
import { createServer } from 'http';

const PORT = process.env.HERMES_RELAY_PORT || 9234;

// Server state
const clients = new Map();
const pendingRequests = new Map();

console.log(`🚀 Hermes Web Fetcher Server starting on port ${PORT}...`);

// Create HTTP server
const httpServer = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      clients: clients.size,
      pending: pendingRequests.size
    }));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

// Create WebSocket server
const wss = new WebSocketServer({ server: httpServer });

wss.on('connection', (ws, req) => {
  const clientId = req.socket.remoteAddress + ':' + req.socket.remotePort;
  console.log(`📌 Client connected: ${clientId}`);
  
  clients.set(clientId, ws);
  
  // Handle messages from extension
  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      console.log(`← Extension: ${msg.type || msg.method} (id: ${msg.id})`);
      
      // Forward to Python client
      for (const [id, client] of clients) {
        if (id !== clientId && client.readyState === WebSocket.OPEN) {
          client.send(data);
        }
      }
      
      // Handle response
      if (msg.id && pendingRequests.has(msg.id)) {
        const { resolve, reject, timeout } = pendingRequests.get(msg.id);
        clearTimeout(timeout);
        pendingRequests.delete(msg.id);
        
        if (msg.error) {
          reject(new Error(msg.error));
        } else {
          resolve(msg.result || msg.data);
        }
      }
    } catch (err) {
      console.error('❌ Message parse error:', err);
    }
  });
  
  ws.on('close', () => {
    console.log(`📌 Client disconnected: ${clientId}`);
    clients.delete(clientId);
  });
  
  ws.on('error', (err) => {
    console.error(`❌ Client error (${clientId}):`, err.message);
  });
  
  // Send welcome message
  ws.send(JSON.stringify({
    type: 'welcome',
    server: 'hermes-web-fetcher',
    version: '0.1.0'
  }));
});

// API for Python client
export async function sendToExtension(method, params = {}, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const requestId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    const timeoutTimer = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error(`Request timeout: ${method}`));
    }, timeout);
    
    pendingRequests.set(requestId, { resolve, reject, timeout: timeoutTimer });
    
    const message = {
      id: requestId,
      method: 'forwardCDPCommand',
      params: {
        method,
        params,
        ts: Date.now()
      }
    };
    
    console.log(`→ To Extension: ${method} (id: ${requestId})`);
    
    // Send to all connected extension clients
    let sent = false;
    for (const [id, client] of clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(message));
        sent = true;
      }
    }
    
    if (!sent) {
      clearTimeout(timeoutTimer);
      pendingRequests.delete(requestId);
      reject(new Error('No extension clients connected'));
    }
  });
}

// Start server
httpServer.listen(PORT, () => {
  console.log(`✅ Server running on ws://localhost:${PORT}`);
  console.log(`   Health check: http://localhost:${PORT}/health`);
  console.log(`   Waiting for extension connection...`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down...');
  wss.clients.forEach(client => {
    client.close(1000, 'Server shutting down');
  });
  httpServer.close(() => {
    console.log('✅ Server stopped');
    process.exit(0);
  });
});
