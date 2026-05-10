#!/bin/bash
# Hermes Web Fetcher - WebSocket Server 启动脚本
# 用法: ./start_server.sh [start|stop|status]

SERVER_DIR="$HOME/.hermes/skills/web/web-fetcher/server"
PORT=9234
PID_FILE="$SERVER_DIR/.server.pid"
LOG_FILE="$SERVER_DIR/.server.log"

start_server() {
    # 检查是否已运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "服务已在运行 (PID: $PID)"
            return 0
        fi
    fi
    
    # 检查端口
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "端口 $PORT 已被占用"
        return 1
    fi
    
    # 启动服务
    cd "$SERVER_DIR"
    nohup node server.js > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    # 等待启动
    sleep 2
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "服务启动成功 (PID: $PID)"
        echo "健康检查: $(curl -s http://localhost:$PORT/health)"
        return 0
    else
        echo "服务启动失败"
        return 1
    fi
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            rm "$PID_FILE"
            echo "服务已停止 (PID: $PID)"
        else
            echo "服务未运行"
            rm "$PID_FILE"
        fi
    else
        # 尝试通过端口查找
        PID=$(lsof -ti:$PORT)
        if [ -n "$PID" ]; then
            kill $PID
            echo "服务已停止 (PID: $PID)"
        else
            echo "服务未运行"
        fi
    fi
}

status_server() {
    echo "=== Hermes Web Fetcher 服务状态 ==="
    
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:$PORT/health)
        echo "服务运行中: $HEALTH"
        
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            echo "PID: $PID"
        fi
        
        # 检查扩展连接
        CLIENTS=$(echo $HEALTH | grep -o '"clients":[0-9]*' | grep -o '[0-9]*')
        if [ "$CLIENTS" = "0" ]; then
            echo "⚠️  扩展未连接 - 请在 Chrome 中启用 Hermes Web Fetcher 扩展"
        else
            echo "✅ 扩展已连接 ($CLIENTS 个客户端)"
        fi
    else
        echo "服务未运行"
    fi
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        status_server
        ;;
    *)
        echo "用法: $0 {start|stop|status}"
        exit 1
        ;;
esac