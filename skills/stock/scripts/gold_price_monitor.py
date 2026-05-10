#!/usr/bin/env python3
"""
沪金期货价格监控脚本（智能版）
监控规则：
1. 非交易日：不监控
2. 交易时段（09:00-15:00）：每小时检查
3. 收盘后（15:30）：只检查一次收盘价
4. 夜盘（21:00-02:30）：可选监控（默认关闭）

止损条件：
- 沪金跌破1000元/克 → 止损预警
- 沪金反弹到1040元/克以上 → 减仓信号
"""

import sys
import json
from datetime import datetime, time
from pathlib import Path

# 添加路径
sys.path.insert(0, '/Users/hy_timesky/Library/Python/3.9/lib/python/site-packages')

try:
    import akshare as ak
except ImportError:
    print("ERROR: akshare not found")
    sys.exit(1)

# 阈值设置
STOP_LOSS_PRICE = 1000.0       # 止损预警线
REDUCE_POSITION_PRICE = 1040.0  # 减仓信号线
ENABLE_NIGHT_SESSION = False    # 是否监控夜盘（默认关闭）

# 缓存文件路径
CACHE_DIR = Path("/Users/hy_timesky/.hermes/profiles/stock/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TRADE_CALENDAR_CACHE = CACHE_DIR / "trade_calendar.json"
LAST_CHECK_FILE = CACHE_DIR / "gold_last_check.json"


def get_trade_calendar():
    """获取交易日历"""
    # 检查缓存（每年更新一次）
    if TRADE_CALENDAR_CACHE.exists():
        cache_data = json.loads(TRADE_CALENDAR_CACHE.read_text())
        cache_year = cache_data.get('year')
        current_year = datetime.now().year
        
        if cache_year == current_year:
            return set(cache_data.get('dates', []))
    
    # 从akshare获取交易日历
    try:
        df = ak.tool_trade_date_hist_sina()
        dates = df['trade_date'].astype(str).tolist()
        
        # 缓存
        cache_data = {
            'year': datetime.now().year,
            'dates': dates
        }
        TRADE_CALENDAR_CACHE.write_text(json.dumps(cache_data))
        
        return set(dates)
    except Exception as e:
        print(f"ERROR: 获取交易日历失败 - {e}")
        # 返回空集合，继续执行（不做交易日判断）
        return set()


def is_trading_day():
    """判断是否为交易日"""
    calendar = get_trade_calendar()
    today = datetime.now().strftime('%Y-%m-%d')
    return today in calendar


def get_trading_session():
    """
    获取当前交易时段
    返回：
    - 'day': 日盘交易时段（09:00-15:00）
    - 'after_close': 收盘后（15:00-21:00）
    - 'night': 夜盘交易时段（21:00-02:30）
    - 'closed': 非交易时段
    """
    now = datetime.now()
    current_time = now.time()
    
    # 日盘：09:00-15:00
    if time(9, 0) <= current_time <= time(15, 0):
        return 'day'
    
    # 收盘后：15:00-21:00（只检查一次）
    if time(15, 0) < current_time < time(21, 0):
        return 'after_close'
    
    # 夜盘：21:00-02:30（次日）
    if time(21, 0) <= current_time or current_time <= time(2, 30):
        return 'night'
    
    return 'closed'


def should_check_price():
    """
    判断是否应该检查价格
    
    规则：
    1. 非交易日 → False
    2. 交易时段 → True
    3. 收盘后 → 只检查一次（15:30-16:00之间）
    4. 夜盘 → 根据配置决定
    """
    # 非交易日不检查
    if not is_trading_day():
        return False, "非交易日"
    
    session = get_trading_session()
    now = datetime.now()
    
    # 日盘交易时段：每小时检查
    if session == 'day':
        return True, "日盘交易时段"
    
    # 收盘后：只检查一次
    if session == 'after_close':
        # 检查是否已在收盘后检查过
        if LAST_CHECK_FILE.exists():
            last_check = json.loads(LAST_CHECK_FILE.read_text())
            last_date = last_check.get('date')
            last_type = last_check.get('type')
            
            # 如果今天已经检查过收盘价
            if last_date == now.strftime('%Y-%m-%d') and last_type == 'after_close':
                return False, "今日收盘后已检查"
        
        # 15:30-16:00之间检查
        if time(15, 30) <= now.time() <= time(16, 0):
            # 记录已检查
            LAST_CHECK_FILE.write_text(json.dumps({
                'date': now.strftime('%Y-%m-%d'),
                'type': 'after_close',
                'time': now.strftime('%H:%M')
            }))
            return True, "收盘后检查"
        
        return False, "收盘后检查时段已过"
    
    # 夜盘：根据配置决定
    if session == 'night':
        if ENABLE_NIGHT_SESSION:
            return True, "夜盘交易时段"
        return False, "夜盘监控已关闭"
    
    return False, "非交易时段"


def get_gold_price():
    """获取沪金主力合约最新价格"""
    try:
        df = ak.futures_zh_daily_sina(symbol="AU0")
        if not df.empty:
            latest = df.iloc[-1]
            return {
                'date': latest['date'],
                'close': float(latest['close']),
                'high': float(latest['high']),
                'low': float(latest['low']),
                'volume': int(latest['volume'])
            }
    except Exception as e:
        print(f"ERROR: 获取金价失败 - {e}")
    return None


def check_alert(price_data):
    """检查是否触发警报"""
    if not price_data:
        return None
    
    close = price_data['close']
    alerts = []
    
    if close <= STOP_LOSS_PRICE:
        alerts.append({
            'type': 'STOP_LOSS',
            'level': '🔴 紧急',
            'message': f"沪金跌破止损线！当前 {close:.2f} 元/克 < {STOP_LOSS_PRICE} 元/克",
            'action': '建议：立即考虑止损离场或设置更紧止损'
        })
    elif close >= REDUCE_POSITION_PRICE:
        alerts.append({
            'type': 'REDUCE_POSITION',
            'level': '🟡 提示',
            'message': f"沪金反弹至减仓位！当前 {close:.2f} 元/克 ≥ {REDUCE_POSITION_PRICE} 元/克",
            'action': '建议：考虑减半仓锁定收益'
        })
    
    # 价格区间提示
    if STOP_LOSS_PRICE < close < REDUCE_POSITION_PRICE:
        alerts.append({
            'type': 'INFO',
            'level': '📊 观察',
            'message': f"沪金处于观察区间 {STOP_LOSS_PRICE}-{REDUCE_POSITION_PRICE} 元/克，当前 {close:.2f}",
            'action': '继续持有，等待方向明确'
        })
    
    return alerts


def format_alert_message(price_data, alerts, check_reason):
    """格式化警报消息"""
    if not alerts:
        return None
    
    now = datetime.now()
    lines = [
        "🪙 沪金期货价格提醒",
        "=" * 40,
        f"📅 时间: {now.strftime('%Y-%m-%d %H:%M')}",
        f"📊 触发原因: {check_reason}",
        f"📈 最新价: {price_data['close']:.2f} 元/克",
        f"📊 最高: {price_data['high']:.2f} | 最低: {price_data['low']:.2f}",
        "=" * 40,
        ""
    ]
    
    for alert in alerts:
        lines.append(f"{alert['level']}")
        lines.append(f"{alert['message']}")
        lines.append(f"💡 {alert['action']}")
        lines.append("")
    
    lines.extend([
        "=" * 40,
        "📌 你的持仓: 招金矿业 100股 @ 20.04元",
        f"📌 当前浮亏约 -20%",
        "📌 杠杆系数: 金价每跌1%，股票跌约2%"
    ])
    
    return "\n".join(lines)


def main():
    """主函数"""
    # 判断是否应该检查价格
    should_check, reason = should_check_price()
    
    if not should_check:
        print(f"跳过检查: {reason}")
        sys.exit(0)
    
    print(f"检查原因: {reason}")
    
    # 获取金价
    price_data = get_gold_price()
    
    if not price_data:
        print("无法获取金价数据")
        sys.exit(1)
    
    # 检查警报
    alerts = check_alert(price_data)
    
    if not alerts:
        # 无警报时输出简要状态
        print(f"沪金当前 {price_data['close']:.2f} 元/克，处于正常区间")
        sys.exit(0)
    
    # 输出警报消息
    message = format_alert_message(price_data, alerts, reason)
    print(message)
    
    # 如果触发重要警报，输出JSON供cron捕获
    critical_alerts = [a for a in alerts if a['type'] in ['STOP_LOSS', 'REDUCE_POSITION']]
    if critical_alerts:
        # 输出到stdout，Hermes会自动捕获并通知
        sys.exit(0)


if __name__ == "__main__":
    main()