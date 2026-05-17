#!/usr/bin/env python3
"""
持仓监控脚本
功能：检查用户持仓股票状态，给出操作建议
执行时间：每日15:30
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data"

# 用户持仓配置（从记忆中获取）
USER_HOLDINGS = [
    {'code': '600584', 'name': '长电科技', 'shares': 200, 'cost': 48.19},
    {'code': '601012', 'name': '隆基绿能', 'shares': 100, 'cost': 18.38},
    {'code': '601698', 'name': '中国卫通', 'shares': 100, 'cost': 33.50},
    {'code': '000506', 'name': '招金黄金', 'shares': 100, 'cost': 20.04}
]

def get_current_price(code):
    """获取当前价格"""
    try:
        # 格式化代码
        if code.startswith('6'):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"
        
        df = ak.stock_zh_a_spot_em()
        stock = df[df['代码'] == code]
        
        if len(stock) > 0:
            price = float(stock.iloc[0]['最新价'])
            pct_chg = float(stock.iloc[0]['涨跌幅'])
            return price, pct_chg
        return None, None
    except Exception as e:
        print(f"获取 {code} 价格失败: {e}")
        return None, None

def calculate_position_status(holding):
    """计算持仓状态"""
    code = holding['code']
    price, pct_chg = get_current_price(code)
    
    if price is None:
        return None
    
    cost = holding['cost']
    shares = holding['shares']
    
    # 计算盈亏
    profit_pct = (price - cost) / cost * 100
    profit_amount = (price - cost) * shares
    current_value = price * shares
    
    return {
        'code': code,
        'name': holding['name'],
        'shares': shares,
        'cost': cost,
        'current_price': price,
        'pct_chg_today': pct_chg,
        'profit_pct': profit_pct,
        'profit_amount': profit_amount,
        'current_value': current_value
    }

def generate_operation_suggestion(status):
    """生成操作建议"""
    suggestions = []
    
    profit_pct = status['profit_pct']
    pct_chg_today = status['pct_chg_today']
    
    # 止损建议
    if profit_pct < -10:
        suggestions.append(f"⚠️ 止损建议: 已亏损{profit_pct:.2f}%，考虑止损")
    elif profit_pct < -5:
        suggestions.append(f"⚠️ 警告: 亏损{profit_pct:.2f}%，接近止损线")
    
    # 止盈建议
    if profit_pct > 20:
        suggestions.append(f"✅ 止盈建议: 已盈利{profit_pct:.2f}%，考虑止盈")
    elif profit_pct > 10:
        suggestions.append(f"✅ 盈利{profit_pct:.2f}%，可考虑分批止盈")
    
    # 当日异动
    if pct_chg_today and abs(pct_chg_today) > 5:
        if pct_chg_today > 0:
            suggestions.append(f"📈 今日大涨{pct_chg_today:.2f}%，注意追高风险")
        else:
            suggestions.append(f"📉 今日大跌{pct_chg_today:.2f}%，注意止损")
    
    if not suggestions:
        suggestions.append("持有观望，正常交易")
    
    return suggestions

def run_position_monitor():
    """执行持仓监控"""
    print("=" * 60)
    print(f"【持仓监控】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    total_profit = 0
    total_value = 0
    
    print("\n【持仓详情】\n")
    print(f"{'股票':<8} {'持仓':<6} {'成本':<8} {'现价':<8} {'盈亏%':<8} {'盈亏额':<10}")
    print("-" * 60)
    
    for holding in USER_HOLDINGS:
        status = calculate_position_status(holding)
        
        if status:
            total_profit += status['profit_amount']
            total_value += status['current_value']
            
            profit_symbol = "✅" if status['profit_pct'] > 0 else "⚠️" if status['profit_pct'] < 0 else "-"
            print(f"{status['name']:<8} {status['shares']:<6} {status['cost']:<8.2f} {status['current_price']:<8.2f} {profit_symbol}{status['profit_pct']:<7.2f}% {status['profit_amount']:<10.2f}")
            
            # 操作建议
            suggestions = generate_operation_suggestion(status)
            for s in suggestions:
                print(f"  → {s}")
    
    print("-" * 60)
    print(f"\n【账户汇总】")
    print(f"  总市值: {total_value:.2f}元")
    print(f"  总盈亏: {total_profit:+.2f}元")
    
    # 保存报告
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'holdings': [calculate_position_status(h) for h in USER_HOLDINGS],
        'total_value': total_value,
        'total_profit': total_profit
    }
    
    report_file = DATA_DIR / "reports" / f"position_monitor_{datetime.now().strftime('%Y%m%d')}.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存: {report_file}")
    print("=" * 60)

if __name__ == "__main__":
    run_position_monitor()