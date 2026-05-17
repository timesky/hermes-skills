#!/usr/bin/env python3
"""
财务数据增量更新脚本
功能：每季度增量更新A股财务数据
数据源：AkShare（东方财富）
执行时间：每季度1日 2:00
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import time
import akshare as ak
import pandas as pd

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "financial_cache"
METADATA_FILE = DATA_DIR / "metadata.json"
STOCK_LIST_FILE = DATA_DIR / "stock_list.json"

# 财务报表类型
REPORT_TYPES = ['balance', 'profit', 'cashflow', 'indicator']

def get_stock_list():
    """获取股票列表（过滤指数）"""
    if STOCK_LIST_FILE.exists():
        with open(STOCK_LIST_FILE, 'r') as f:
            return json.load(f)
    
    # 从AkShare获取
    try:
        stock_list = ak.stock_zh_a_spot_em()
        # 过滤指数代码(399xxx)
        stocks = []
        for row in stock_list.itertuples():
            code = row.代码
            if not code.startswith('399'):
                stocks.append({
                    'code': code,
                    'name': row.名称
                })
        
        # 保存
        with open(STOCK_LIST_FILE, 'w') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        
        return stocks
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def download_financial_data(code, report_type):
    """下载单只股票财务数据"""
    try:
        if report_type == 'balance':
            df = ak.stock_balance_sheet_by_report_em(symbol=code)
        elif report_type == 'profit':
            df = ak.stock_profit_sheet_by_report_em(symbol=code)
        elif report_type == 'cashflow':
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=code)
        elif report_type == 'indicator':
            df = ak.stock_financial_analysis_indicator_em(symbol=code)
        else:
            return None
        
        return df
    except Exception as e:
        print(f"  {code} {report_type} 失败: {e}")
        return None

def incremental_update():
    """增量更新财务数据"""
    print("=" * 60)
    print(f"【财务数据增量更新】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 确保目录存在
    for report_type in REPORT_TYPES:
        (DATA_DIR / report_type).mkdir(parents=True, exist_ok=True)
    
    # 获取股票列表
    stocks = get_stock_list()
    print(f"股票数量: {len(stocks)}")
    
    # 统计
    stats = {rt: {'success': 0, 'fail': 0} for rt in REPORT_TYPES}
    
    # 更新每只股票
    for i, stock in enumerate(stocks):
        code = stock['code']
        
        for report_type in REPORT_TYPES:
            try:
                df = download_financial_data(code, report_type)
                
                if df is not None and len(df) > 0:
                    # 保存
                    file_path = DATA_DIR / report_type / f"{code}.csv"
                    df.to_csv(file_path, index=False)
                    stats[report_type]['success'] += 1
                else:
                    stats[report_type]['fail'] += 1
                    
            except Exception as e:
                stats[report_type]['fail'] += 1
        
        # 进度
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{len(stocks)}")
        
        # 防止请求过快
        time.sleep(0.1)
    
    # 输出统计
    print("\n【更新统计】")
    for rt in REPORT_TYPES:
        print(f"  {rt}: 成功{stats[rt]['success']} 失败{stats[rt]['fail']}")
    
    # 保存元数据
    metadata = {
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stock_count': len(stocks),
        'stats': stats
    }
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)

def check_status():
    """检查财务数据状态"""
    print("=" * 60)
    print("【财务数据缓存状态】")
    print("=" * 60)
    
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
        print(f"最后更新: {metadata.get('last_update', 'N/A')}")
        print(f"股票数量: {metadata.get('stock_count', 'N/A')}")
    
    # 计算数据量
    total_size = 0
    for rt in REPORT_TYPES:
        rt_dir = DATA_DIR / rt
        if rt_dir.exists():
            for f in rt_dir.glob("*.csv"):
                total_size += f.stat().st_size
    
    print(f"数据总量: {total_size / 1024 / 1024:.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    # 确保主目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 解析参数
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "incremental":
            incremental_update()
        elif cmd == "status":
            check_status()
        else:
            print("用法: python financial_cache.py [incremental|status]")
    else:
        incremental_update()