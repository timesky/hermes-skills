#!/usr/bin/env python3
"""
开盘前操作建议生成器

用法:
    python3 morning_advisor.py --real      # 读取用户实际持股
    python3 morning_advisor.py --paper     # 读取模拟盘持股
    python3 morning_advisor.py --all       # 同时显示两者

功能:
    - 读取持股文件
    - 获取最新价格和技术指标
    - 结合策略给出买入/卖出/持有建议
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3

# 路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
CACHE_DIR = DATA_DIR / "cache"
PAPER_TRADING_DIR = DATA_DIR / "paper_trading"
PAPER_TRADING_DB = PAPER_TRADING_DIR / "paper_trading.db"

# 技术指标阈值
MA_SHORT = 5
MA_MID = 10
MA_LONG = 20
RSI_PERIOD = 14

def load_real_portfolio():
    """加载用户实际持股"""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_paper_positions():
    """加载模拟盘持股"""
    if not PAPER_TRADING_DB.exists():
        return None
    
    conn = sqlite3.connect(str(PAPER_TRADING_DB))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, name, shares, cost_price, current_price, pnl_pct, 
               stop_loss_price, take_profit_price
        FROM positions
        WHERE date = (SELECT MAX(date) FROM positions)
        GROUP BY symbol
    """)
    positions = cursor.fetchall()
    conn.close()
    
    if not positions:
        return None
    
    return {
        "positions": [
            {
                "symbol": row[0],
                "name": row[1] or row[0],
                "quantity": row[2],
                "cost": row[3],
                "current_price": row[4],
                "pnl_pct": row[5],
                "stop_loss": row[6],
                "take_profit": row[7]
            }
            for row in positions
        ],
        "source": "paper_trading"
    }

def get_latest_price_from_cache(symbol):
    """从缓存获取最新价格和技术指标"""
    # 尝试多种缓存文件名格式
    cache_patterns = [
        CACHE_DIR / f"{symbol}_*.csv",
        CACHE_DIR / symbol / "daily_kline.csv",
        CACHE_DIR / f"sh_{symbol}" / "daily_kline.csv",
        CACHE_DIR / f"sz_{symbol}" / "daily_kline.csv",
    ]
    
    import glob
    for pattern in cache_patterns[:1]:  # 只用glob模式
        files = sorted(glob.glob(str(pattern)), reverse=True)
        if files:
            try:
                import pandas as pd
                df = pd.read_csv(files[0])
                if len(df) > 0:
                    last = df.iloc[-1]
                    return {
                        "close": float(last['close']),
                        "high": float(last['high']),
                        "low": float(last['low']),
                        "volume": float(last.get('volume', 0)),
                        "date": last.get('date', ''),
                        "ma5": float(last.get('ma5', 0)) if 'ma5' in df.columns else calc_ma(df, 5),
                        "ma10": float(last.get('ma10', 0)) if 'ma10' in df.columns else calc_ma(df, 10),
                        "ma20": float(last.get('ma20', 0)) if 'ma20' in df.columns else calc_ma(df, 20),
                        "rsi": calc_rsi(df) if len(df) > RSI_PERIOD else 50,
                    }
            except Exception as e:
                pass
    
    # 尝试子目录格式
    for subdir in [CACHE_DIR / symbol, CACHE_DIR / f"sh_{symbol}", CACHE_DIR / f"sz_{symbol}"]:
        kline_file = subdir / "daily_kline.csv"
        if kline_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(kline_file)
                if len(df) > 0:
                    last = df.iloc[-1]
                    return {
                        "close": float(last['close']),
                        "high": float(last['high']),
                        "low": float(last['low']),
                        "volume": float(last.get('volume', 0)),
                        "date": last.get('date', ''),
                        "ma5": calc_ma(df, 5),
                        "ma10": calc_ma(df, 10),
                        "ma20": calc_ma(df, 20),
                        "rsi": calc_rsi(df) if len(df) > RSI_PERIOD else 50,
                    }
            except:
                pass
    
    return None

def calc_ma(df, period):
    """计算均线"""
    try:
        import pandas as pd
        if len(df) >= period:
            return float(df['close'].tail(period).mean())
    except:
        pass
    return 0

def calc_rsi(df, period=14):
    """计算RSI"""
    try:
        import pandas as pd
        import numpy as np
        if len(df) < period + 1:
            return 50
        
        closes = df['close'].values
        deltas = np.diff(closes[-(period+20):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))
    except:
        return 50

def analyze_position(pos, price_data=None):
    """分析单个持仓并给出建议"""
    symbol = pos.get('symbol', '')
    name = pos.get('name', symbol)
    quantity = pos.get('quantity', pos.get('shares', 0))
    cost = pos.get('cost', pos.get('cost_price', pos.get('avg_cost', 0)))
    current_price = pos.get('current_price', cost)
    
    # 获取技术数据
    if price_data is None:
        price_data = get_latest_price_from_cache(symbol)
    
    result = {
        "symbol": symbol,
        "name": name,
        "quantity": quantity,
        "cost": cost,
        "current_price": current_price,
        "pnl_pct": (current_price - cost) / cost * 100 if cost > 0 else 0,
        "market_value": quantity * current_price,
        "cost_value": quantity * cost,
        "pnl": quantity * (current_price - cost),
        "action": "持有",
        "action_reason": "",
        "action_strength": "中性",
        "risk_level": "中",
        "tech_data": price_data
    }
    
    if price_data is None:
        result["action_reason"] = "无法获取技术数据，建议观望"
        result["risk_level"] = "未知"
        return result
    
    # 更新当前价格
    result["current_price"] = price_data["close"]
    result["pnl_pct"] = (price_data["close"] - cost) / cost * 100 if cost > 0 else 0
    result["market_value"] = quantity * price_data["close"]
    result["pnl"] = quantity * (price_data["close"] - cost)
    
    close = price_data["close"]
    ma5 = price_data["ma5"]
    ma10 = price_data["ma10"]
    ma20 = price_data["ma20"]
    rsi = price_data["rsi"]
    
    # 技术分析
    ma_signal = ""
    rsi_signal = ""
    
    # 均线分析
    if ma5 > 0 and ma10 > 0 and ma20 > 0:
        if close > ma5 > ma10 > ma20:
            ma_signal = "多头排列"
        elif close < ma5 < ma10 < ma20:
            ma_signal = "空头排列"
        elif close > ma5 and ma5 > ma10:
            ma_signal = "短期走强"
        elif close < ma5 and ma5 < ma10:
            ma_signal = "短期走弱"
        else:
            ma_signal = "均线纠缠"
    else:
        ma_signal = "数据不足"
    
    # RSI分析
    if rsi > 80:
        rsi_signal = "超买"
    elif rsi > 70:
        rsi_signal = "偏强"
    elif rsi < 20:
        rsi_signal = "超卖"
    elif rsi < 30:
        rsi_signal = "偏弱"
    else:
        rsi_signal = "中性"
    
    # 综合建议
    action = "持有"
    reason = []
    strength = "中性"
    risk = "中"
    
    # 盈亏分析
    pnl_pct = result["pnl_pct"]
    
    if pnl_pct > 20:
        reason.append(f"盈利{pnl_pct:.1f}%，考虑止盈")
        action = "减仓"
        strength = "较强"
    elif pnl_pct > 10:
        reason.append(f"盈利{pnl_pct:.1f}%，可继续持有")
        action = "持有"
    elif pnl_pct < -15:
        reason.append(f"亏损{pnl_pct:.1f}%，考虑止损")
        action = "止损"
        strength = "强"
        risk = "高"
    elif pnl_pct < -8:
        reason.append(f"亏损{pnl_pct:.1f}%，关注支撑")
        risk = "较高"
    
    # 技术信号
    if ma_signal == "多头排列" and rsi_signal in ["中性", "偏强"]:
        if action != "减仓":
            action = "持有"
        reason.append(f"技术面: {ma_signal}, RSI {rsi_signal}")
    elif ma_signal == "空头排列" and rsi_signal in ["偏弱", "超卖"]:
        if action != "止损":
            action = "观望"
        reason.append(f"技术面: {ma_signal}, RSI {rsi_signal}")
        risk = "较高"
    elif rsi_signal == "超买":
        reason.append(f"RSI超买({rsi:.0f})，注意回调风险")
        risk = "较高"
    elif rsi_signal == "超卖":
        reason.append(f"RSI超卖({rsi:.0f})，可能存在反弹机会")
    else:
        reason.append(f"技术面: {ma_signal}, RSI {rsi_signal}")
    
    result["action"] = action
    result["action_reason"] = "; ".join(reason)
    result["action_strength"] = strength
    result["risk_level"] = risk
    result["ma_signal"] = ma_signal
    result["rsi_signal"] = rsi_signal
    
    return result

def generate_report(portfolio_data, title=""):
    """生成报告"""
    if not portfolio_data:
        return f"\n{title}: 无数据\n"
    
    positions = portfolio_data.get('positions', [])
    if not positions:
        return f"\n{title}: 暂无持仓\n"
    
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append(f"📊 {title}")
    lines.append("=" * 70)
    
    # 更新时间
    update_time = portfolio_data.get('updated_at', portfolio_data.get('last_update', 'N/A'))
    lines.append(f"📅 数据更新: {update_time}")
    lines.append(f"🕐 报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 汇总
    total_cost = 0
    total_value = 0
    total_pnl = 0
    results = []
    
    for pos in positions:
        result = analyze_position(pos)
        results.append(result)
        total_cost += result["cost_value"]
        total_value += result["market_value"]
        total_pnl += result["pnl"]
    
    # 账户概览
    lines.append("【账户概览】")
    lines.append(f"  总成本: {total_cost:,.0f}元")
    lines.append(f"  总市值: {total_value:,.0f}元")
    total_pnl_pct = (total_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
    pnl_emoji = "📈" if total_pnl >= 0 else "📉"
    lines.append(f"  总盈亏: {pnl_emoji} {total_pnl:+,.0f}元 ({total_pnl_pct:+.2f}%)")
    lines.append("")
    
    # 持仓详情
    lines.append("【持仓详情】")
    lines.append(f"{'代码':<8} {'名称':<8} {'数量':>6} {'成本':>8} {'现价':>8} {'盈亏%':>8} {'建议':<6} {'风险':<4}")
    lines.append("-" * 70)
    
    for r in results:
        pnl_str = f"{r['pnl_pct']:+.2f}%"
        action_str = r["action"]
        risk_str = r["risk_level"]
        lines.append(f"{r['symbol']:<8} {r['name']:<8} {r['quantity']:>6} {r['cost']:>8.2f} {r['current_price']:>8.2f} {pnl_str:>8} {action_str:<6} {risk_str:<4}")
    
    # 操作建议
    lines.append("")
    lines.append("【操作建议】")
    
    for r in results:
        action_emoji = {
            "持有": "🟡",
            "加仓": "🟢",
            "减仓": "🟠",
            "止损": "🔴",
            "观望": "⚪",
            "买入": "🟢"
        }.get(r["action"], "⚪")
        
        lines.append(f"\n{action_emoji} {r['symbol']} {r['name']}")
        lines.append(f"   操作: {r['action']} ({r['action_strength']})")
        lines.append(f"   理由: {r['action_reason']}")
        
        if r.get("tech_data"):
            tech = r["tech_data"]
            lines.append(f"   技术指标: MA5={tech['ma5']:.2f} MA10={tech['ma10']:.2f} MA20={tech['ma20']:.2f} RSI={tech['rsi']:.0f}")
            lines.append(f"   均线形态: {r.get('ma_signal', '-')} | RSI状态: {r.get('rsi_signal', '-')}")
    
    # 风险提示
    lines.append("")
    lines.append("【风险提示】")
    high_risk = [r for r in results if r["risk_level"] in ["高", "较高"]]
    if high_risk:
        high_risk_str = ', '.join([f"{r['symbol']}({r['pnl_pct']:+.1f}%)" for r in high_risk])
        lines.append(f"  ⚠️ 高风险持仓: {high_risk_str}")
    
    stop_loss = [r for r in results if r["action"] == "止损"]
    if stop_loss:
        lines.append(f"  🛑 建议止损: {', '.join([r['symbol'] for r in stop_loss])}")
    
    reduce_pos = [r for r in results if r["action"] == "减仓"]
    if reduce_pos:
        reduce_str = ', '.join([f"{r['symbol']}(盈利{r['pnl_pct']:.0f}%)" for r in reduce_pos])
        lines.append(f"  📉 建议减仓: {reduce_str}")
    
    lines.append("")
    lines.append("=" * 70)
    lines.append("💡 本建议仅供参考，投资决策请自行判断")
    lines.append("=" * 70)
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='开盘前操作建议生成器')
    parser.add_argument('--real', action='store_true', help='读取用户实际持股')
    parser.add_argument('--paper', action='store_true', help='读取模拟盘持股')
    parser.add_argument('--all', action='store_true', help='同时显示两者')
    args = parser.parse_args()
    
    if not (args.real or args.paper or args.all):
        args.all = True  # 默认显示全部
    
    output = []
    output.append("\n" + "=" * 70)
    output.append("📅 开盘前操作建议")
    output.append(f"   生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("=" * 70)
    
    if args.real or args.all:
        real_portfolio = load_real_portfolio()
        output.append(generate_report(real_portfolio, "实际持股"))
    
    if args.paper or args.all:
        paper_portfolio = load_paper_positions()
        output.append(generate_report(paper_portfolio, "模拟盘持股"))
    
    print("\n".join(output))

if __name__ == "__main__":
    main()