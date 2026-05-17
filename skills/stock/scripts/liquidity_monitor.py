#!/usr/bin/env python3
"""
流动性监控脚本
功能：实时监控全市场流动性，预警流动性危机
执行时间：每日9:15
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
import akshare as ak
import pandas as pd

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "liquidity_monitor"

def get_limit_up_down_stats():
    """获取涨跌停统计"""
    try:
        # 获取涨跌停数据
        limit_up_df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
        limit_down_df = ak.stock_zt_pool_dtgc_em(date=datetime.now().strftime('%Y%m%d'))
        
        limit_up_count = len(limit_up_df) if limit_up_df is not None else 0
        limit_down_count = len(limit_down_df) if limit_down_df is not None else 0
        
        return {
            'limit_up': limit_up_count,
            'limit_down': limit_down_count,
            'strict_limit_down': limit_down_count  # 简化处理
        }
    except Exception as e:
        print(f"获取涨跌停数据失败: {e}")
        return {'limit_up': 0, 'limit_down': 0, 'strict_limit_down': 0}

def get_volume_stats():
    """获取成交量统计"""
    try:
        # 获取市场成交数据
        sh_volume = ak.stock_zh_a_spot_em()
        total_amount = sh_volume['成交额'].sum() if '成交额' in sh_volume.columns else 0
        zero_trade = len(sh_volume[sh_volume['成交量'] == 0]) if '成交量' in sh_volume.columns else 0
        
        return {
            'total_amount': total_amount / 1e8,  # 亿元
            'zero_trade_count': zero_trade
        }
    except Exception as e:
        print(f"获取成交量数据失败: {e}")
        return {'total_amount': 0, 'zero_trade_count': 0}

def get_stock_count():
    """获取全市场股票数量"""
    try:
        stock_list = ak.stock_zh_a_spot_em()
        return len(stock_list)
    except:
        return 5000  # 默认A股约5000只

def calculate_warning_level(stats, stock_count):
    """计算预警级别"""
    level = "NORMAL"
    warnings = []
    
    # 跌停数量预警
    limit_down_ratio = stats['strict_limit_down'] / stock_count * 100
    if stats['strict_limit_down'] >= 200:
        level = "WARNING"
        warnings.append(f"跌停数量≥200只 ({stats['strict_limit_down']}只)")
    if limit_down_ratio >= 5:
        level = "DANGER"
        warnings.append(f"跌停比例≥5% ({limit_down_ratio:.2f}%)")
    
    # 成交量预警
    if stats['total_amount'] < 2000:  # 成交额低于2000亿
        warnings.append(f"成交额较低 ({stats['total_amount']:.0f}亿元)")
    
    # 零成交预警
    if stats['zero_trade_count'] >= 50:
        if level == "NORMAL":
            level = "WARNING"
        warnings.append(f"零成交股票≥50只 ({stats['zero_trade_count']}只)")
    
    return level, warnings

def save_report(stats, level, warnings):
    """保存监控报告"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = DATA_DIR / f"liquidity_{timestamp}.json"
    
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stats': stats,
        'warning_level': level,
        'warnings': warnings
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_file

def run_monitor():
    """执行流动性监控"""
    print("=" * 60)
    print(f"【流动性监控】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 获取统计数据
    stock_count = get_stock_count()
    limit_stats = get_limit_up_down_stats()
    volume_stats = get_volume_stats()
    
    stats = {
        **limit_stats,
        **volume_stats,
        'stock_count': stock_count
    }
    
    # 打印统计
    print("\n【涨跌停统计】")
    print(f"  涨停股票: {stats['limit_up']}只")
    print(f"  跌停股票: {stats['limit_down']}只")
    print(f"  严格跌停: {stats['strict_limit_down']}只")
    
    print("\n【成交量统计】")
    print(f"  总成交额: {stats['total_amount']:.0f}亿元")
    print(f"  零成交股票: {stats['zero_trade_count']}只")
    
    # 计算预警级别
    level, warnings = calculate_warning_level(stats, stock_count)
    
    print("\n【预警级别】")
    level_symbol = "✓" if level == "NORMAL" else "⚠️" if level == "WARNING" else "🔴"
    print(f"  当前级别: {level_symbol} {level}")
    
    if warnings:
        for w in warnings:
            print(f"  - {w}")
    
    # 保存报告
    report_file = save_report(stats, level, warnings)
    print(f"\n报告已保存: {report_file}")
    
    print("=" * 60)
    
    # 返回预警级别（供Cronjob使用）
    return level

if __name__ == "__main__":
    run_monitor()