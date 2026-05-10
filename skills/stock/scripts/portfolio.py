#!/usr/bin/env python3
"""持仓管理系统

用法:
    # 查看持仓
    python3 portfolio.py list
    
    # 添加持仓
    python3 portfolio.py add 600584 --shares 200 --price 45.56 --strategy 5日线
    
    # 更新持仓（卖出/调整）
    python3 portfolio.py update 600584 --shares 100
    
    # 删除持仓
    python3 portfolio.py remove 600584
    
    # 持仓分析（结合实时数据）
    python3 portfolio.py analyze
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

PORTFOLIO_FILE = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "portfolio.json"

def load_portfolio():
    """加载持仓数据"""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"positions": [], "cash": 0, "account": "A股账户"}

def save_portfolio(data):
    """保存持仓数据"""
    data['last_update'] = datetime.now().isoformat()
    PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fmt_price(p):
    try:
        return f"{float(p):.2f}"
    except:
        return str(p)

def fmt_pct(p):
    try:
        return f"{float(p):+.2f}%"
    except:
        return str(p)

def cmd_list():
    """列出持仓"""
    pf = load_portfolio()
    
    print("\n" + "="*70)
    print(f"📊 {pf.get('account', 'A股账户')} - 持仓列表")
    print("="*70)
    print(f"更新时间: {pf.get('last_update', 'N/A')}\n")
    
    if not pf['positions']:
        print("暂无持仓")
        return
    
    total_cost = 0
    total_value = 0
    
    print(f"{'代码':<8} {'名称':<8} {'数量':>6} {'成本':>8} {'现价':>8} {'盈亏':>10} {'策略':<12}")
    print("-"*70)
    
    for pos in pf['positions']:
        symbol = pos['symbol']
        name = pos.get('name', 'N/A')
        shares = pos['shares']
        buy_price = pos.get('buy_price') or pos.get('avg_cost', 0)
        strategy = pos.get('strategy', '-')
        
        # 计算成本
        cost = shares * buy_price
        total_cost += cost
        
        # 尝试读取当前价格（从缓存）
        try:
            import pandas as pd
            cache_file = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "cache" / symbol / "daily_kline.csv"
            if cache_file.exists():
                df = pd.read_csv(cache_file)
                current_price = float(df.iloc[-1]['close'])
                value = shares * current_price
                total_value += value
                pnl = value - cost
                pnl_pct = (current_price - buy_price) / buy_price * 100
                
                pnl_str = f"{fmt_price(pnl)}元 ({fmt_pct(pnl_pct)})"
            else:
                current_price = buy_price
                pnl_str = "N/A"
        except:
            current_price = buy_price
            pnl_str = "N/A"
        
        print(f"{symbol:<8} {name:<8} {shares:>6} {fmt_price(buy_price):>8} {fmt_price(current_price):>8} {pnl_str:>10} {strategy:<12}")
    
    print("-"*70)
    
    if total_value > 0:
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_value - total_cost) / total_cost * 100
        print(f"\n总成本: {fmt_price(total_cost)}元")
        print(f"总市值: {fmt_price(total_value)}元")
        print(f"总盈亏: {fmt_price(total_pnl)}元 ({fmt_pct(total_pnl_pct)})")
    
    # 现金
    if pf.get('cash', 0) > 0:
        print(f"\n可用现金: {fmt_price(pf['cash'])}元")

def cmd_add(symbol, shares, price, strategy=None, notes=None):
    """添加持仓"""
    pf = load_portfolio()
    
    # 检查是否已存在
    for pos in pf['positions']:
        if pos['symbol'] == symbol:
            print(f"错误: {symbol} 已在持仓中，请使用 update 命令调整")
            return
    
    # 添加新持仓
    position = {
        'symbol': symbol,
        'name': get_stock_name(symbol),
        'shares': shares,
        'buy_price': price,
        'buy_date': datetime.now().strftime('%Y-%m-%d'),
        'strategy': strategy or '自定义',
    }
    
    if strategy == '5日线策略':
        position['stop_loss'] = price * 0.973  # MA5下方2%
        position['target_1'] = price * 1.034    # +3.4%
        position['target_2'] = price * 1.068   # +6.8%
        position['hard_stop'] = price * 0.90    # -10%
    
    if notes:
        position['notes'] = notes
    
    pf['positions'].append(position)
    save_portfolio(pf)
    
    print(f"✅ 已添加: {symbol} {shares}股 @ {price}元")

def cmd_update(symbol, shares=None, price=None):
    """更新持仓"""
    pf = load_portfolio()
    
    for pos in pf['positions']:
        if pos['symbol'] == symbol:
            if shares is not None:
                pos['shares'] = shares
            if price is not None:
                pos['buy_price'] = price
            save_portfolio(pf)
            print(f"✅ 已更新: {symbol}")
            return
    
    print(f"错误: 未找到 {symbol}")

def cmd_remove(symbol):
    """删除持仓"""
    pf = load_portfolio()
    
    original_len = len(pf['positions'])
    pf['positions'] = [p for p in pf['positions'] if p['symbol'] != symbol]
    
    if len(pf['positions']) < original_len:
        save_portfolio(pf)
        print(f"✅ 已删除: {symbol}")
    else:
        print(f"错误: 未找到 {symbol}")

def get_stock_name(symbol):
    """获取股票名称"""
    # 常用股票映射
    stock_names = {
        '600584': '长电科技',
        '000001': '平安银行',
        '600036': '招商银行',
        '000002': '万科A',
        '600519': '贵州茅台',
    }
    return stock_names.get(symbol, symbol)

def cmd_analyze():
    """持仓分析（结合5日线策略）"""
    pf = load_portfolio()
    
    if not pf['positions']:
        print("暂无持仓")
        return
    
    print("\n" + "="*70)
    print("📊 持仓策略分析")
    print("="*70)
    
    for pos in pf['positions']:
        symbol = pos['symbol']
        print(f"\n【{symbol} {pos.get('name', '')}】")
        print("-"*50)
        
        # 持仓信息
        shares = pos['shares']
        buy_price = pos.get('buy_price') or pos.get('avg_cost', 0)
        print(f"持仓: {shares}股 @ {buy_price:.2f}元")
        
        # 策略相关
        if pos.get('strategy') == '5日线策略':
            print(f"策略: 5日线策略")
            print(f"止损: {pos.get('stop_loss', 'N/A')}元 (MA5下方2%)")
            print(f"目标: {pos.get('target_1', 'N/A')}元 → {pos.get('target_2', 'N/A')}元")
            print(f"硬止损: {pos.get('hard_stop', 'N/A')}元 (-10%)")
        
        # 读取最新行情
        try:
            import pandas as pd
            cache_file = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "cache" / symbol / "daily_kline.csv"
            if cache_file.exists():
                df = pd.read_csv(cache_file, parse_dates=['date'])
                df['ma5'] = df['close'].rolling(5).mean()
                
                latest = df.iloc[-1]
                current = latest['close']
                ma5 = latest['ma5']
                
                print(f"\n当前价: {current:.2f}元")
                print(f"MA5: {ma5:.2f}元 ({'站上✓' if current > ma5 else '跌破✗'})")
                
                # 距离MA5
                distance = (current - ma5) / ma5 * 100
                print(f"距离MA5: {distance:+.2f}%")
                
                # 盈亏
                pnl_pct = (current - buy_price) / buy_price * 100
                pnl = (current - buy_price) * shares
                print(f"盈亏: {pnl:.2f}元 ({pnl_pct:+.2f}%)")
                
                # 操作建议
                print(f"\n操作建议:")
                if current > ma5:
                    if distance > 2:
                        print("  🟢 持仓安全，继续持有")
                    else:
                        print("  🟡 安全垫较薄，注意监控")
                else:
                    print("  🔴 跌破MA5，关注是否连续2日")
        except Exception as e:
            print(f"无法读取行情数据: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="持仓管理")
    subparsers = parser.add_subparsers(dest="command")
    
    # list
    p_list = subparsers.add_parser("list", help="查看持仓")
    
    # add
    p_add = subparsers.add_parser("add", help="添加持仓")
    p_add.add_argument("symbol", help="股票代码")
    p_add.add_argument("--shares", type=int, required=True, help="股数")
    p_add.add_argument("--price", type=float, required=True, help="买入价")
    p_add.add_argument("--strategy", help="策略名称")
    p_add.add_argument("--notes", help="备注")
    
    # update
    p_update = subparsers.add_parser("update", help="更新持仓")
    p_update.add_argument("symbol", help="股票代码")
    p_update.add_argument("--shares", type=int, help="新股数")
    p_update.add_argument("--price", type=float, help="新成本价")
    
    # remove
    p_remove = subparsers.add_parser("remove", help="删除持仓")
    p_remove.add_argument("symbol", help="股票代码")
    
    # analyze
    p_analyze = subparsers.add_parser("analyze", help="持仓分析")
    
    args = parser.parse_args()
    
    if args.command == "list":
        cmd_list()
    elif args.command == "add":
        cmd_add(args.symbol, args.shares, args.price, args.strategy, args.notes)
    elif args.command == "update":
        cmd_update(args.symbol, args.shares, args.price)
    elif args.command == "remove":
        cmd_remove(args.symbol)
    elif args.command == "analyze":
        cmd_analyze()
    else:
        parser.print_help()
