#!/usr/bin/env python3
"""
市场数据增量更新脚本
功能：每日收盘后增量更新全市场K线数据
数据源：Baostock
执行时间：每日16:00
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import baostock as bs

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "market_cache"
STOCKS_DIR = DATA_DIR / "stocks"
METADATA_FILE = DATA_DIR / "metadata.json"
STOCK_LIST_FILE = DATA_DIR / "stock_list.json"

def login_baostock():
    """登录Baostock"""
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return False
    return True

def logout_baostock():
    """登出Baostock"""
    bs.logout()

def get_trade_dates(start_date, end_date):
    """获取交易日列表"""
    rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
    trade_dates = []
    while (rs.error_code == '0') & rs.next():
        trade_dates.append(rs.get_row_data()[0])
    return trade_dates

def get_stock_list():
    """获取全市场股票列表"""
    if STOCK_LIST_FILE.exists():
        with open(STOCK_LIST_FILE, 'r') as f:
            return json.load(f)
    
    # 从Baostock获取
    rs = bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
    stock_list = []
    while (rs.error_code == '0') & rs.next():
        row = rs.get_row_data()
        code = row[0]
        # 排除指数代码(399xxx)和退市股
        if code.startswith('sh.') or code.startswith('sz.'):
            if not code.split('.')[1].startswith('399'):
                stock_list.append({
                    'code': code,
                    'name': row[1],
                    'status': row[2]
                })
    
    # 保存列表
    with open(STOCK_LIST_FILE, 'w') as f:
        json.dump(stock_list, f, ensure_ascii=False, indent=2)
    
    return stock_list

def get_last_update_date(code):
    """获取某只股票最后更新日期"""
    # 尝试两种文件名格式：sh_600000.csv 和 600000.csv
    code_num = code.split('.')[-1] if '.' in code else code
    
    possible_files = [
        STOCKS_DIR / f"{code.replace('.', '_')}.csv",  # sh_600000.csv
        STOCKS_DIR / f"{code_num}.csv"  # 600000.csv
    ]
    
    for stock_file in possible_files:
        if stock_file.exists():
            try:
                df = pd.read_csv(stock_file)
                if len(df) > 0 and 'date' in df.columns:
                    return df['date'].max()
            except:
                pass
    return None

def download_klines(code, start_date, end_date):
    """下载K线数据"""
    fields = "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
    
    rs = bs.query_history_k_data_plus(
        code=code,
        fields=fields,
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3"  # 不复权
    )
    
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    
    if len(data_list) == 0:
        return None
    
    # rs.fields 可能是字符串或列表，兼容处理
    columns = rs.fields if isinstance(rs.fields, list) else rs.fields.split(',')
    df = pd.DataFrame(data_list, columns=columns)
    return df

def incremental_update():
    """增量更新所有股票数据"""
    print("=" * 60)
    print(f"【市场数据增量更新】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 登录
    if not login_baostock():
        return
    
    # 获取股票列表
    stock_list = get_stock_list()
    print(f"股票数量: {len(stock_list)}")
    
    # 确定更新日期范围
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 获取交易日
    trade_dates = get_trade_dates(yesterday, today)
    if len(trade_dates) == 0:
        print("今日非交易日，无需更新")
        logout_baostock()
        return
    
    latest_trade_date = trade_dates[-1]
    print(f"最新交易日: {latest_trade_date}")
    
    # 统计
    success_count = 0
    fail_count = 0
    new_data_count = 0
    
    # 增量更新每只股票
    for i, stock in enumerate(stock_list):
        # 兼容 code 和 symbol 两种字段名
        code = stock.get('code') or stock.get('symbol')
        if not code:
            fail_count += 1
            continue
        
        # 如果是纯数字代码，添加市场前缀
        if '.' not in code:
            if code.startswith('6'):
                code = f'sh.{code}'
            elif code.startswith(('0', '3')):
                code = f'sz.{code}'
            elif code.startswith(('68',)):
                code = f'sh.{code}'
            else:
                fail_count += 1
                continue
        
        # 获取最后更新日期
        last_date = get_last_update_date(code)
        
        # 确定起始日期
        if last_date:
            start_date = (datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # 全量下载（从2010年开始）
            start_date = "2010-01-04"
        
        # 如果起始日期大于最新交易日，跳过
        if start_date > latest_trade_date:
            success_count += 1
            continue
        
        # 下载数据
        try:
            df = download_klines(code, start_date, latest_trade_date)
            
            if df is not None and len(df) > 0:
                # 使用纯数字文件名（与现有文件格式一致）
                symbol = code.split('.')[-1] if '.' in code else code
                stock_file = STOCKS_DIR / f"{symbol}.csv"
                
                if stock_file.exists():
                    # 追加模式
                    old_df = pd.read_csv(stock_file)
                    new_df = pd.concat([old_df, df], ignore_index=True)
                    new_df.to_csv(stock_file, index=False)
                    new_data_count += len(df)
                else:
                    # 新建文件
                    df.to_csv(stock_file, index=False)
                    new_data_count += len(df)
                
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            fail_count += 1
            print(f"  {code} 失败: {e}")
        
        # 进度显示
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{len(stock_list)} 成功:{success_count} 失败:{fail_count}")
    
    # 登出
    logout_baostock()
    
    # 更新元数据
    metadata = {
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'latest_trade_date': latest_trade_date,
        'stock_count': len(stock_list),
        'success_count': success_count,
        'fail_count': fail_count,
        'new_data_count': new_data_count
    }
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("【更新完成】")
    print(f"  股票总数: {len(stock_list)}")
    print(f"  成功更新: {success_count}")
    print(f"  失败数量: {fail_count}")
    print(f"  新增数据: {new_data_count} 条")
    print(f"  最新交易日: {latest_trade_date}")
    print("=" * 60)

def full_update():
    """全量更新（重新下载所有数据）"""
    print("执行全量更新...")
    # 清空现有数据
    import shutil
    if STOCKS_DIR.exists():
        shutil.rmtree(STOCKS_DIR)
    STOCKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 执行增量更新（从2010年开始）
    incremental_update()

def check_status():
    """检查数据状态"""
    print("=" * 60)
    print("【市场数据缓存状态】")
    print("=" * 60)
    
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
        print(f"  最后更新: {metadata.get('last_update', 'N/A')}")
        print(f"  最新交易日: {metadata.get('latest_trade_date', 'N/A')}")
        print(f"  股票数量: {metadata.get('stock_count', 'N/A')}")
    
    # 计算数据量
    if STOCKS_DIR.exists():
        total_size = 0
        file_count = 0
        for f in STOCKS_DIR.glob("*.csv"):
            total_size += f.stat().st_size
            file_count += 1
        
        print(f"  文件数量: {file_count}")
        print(f"  数据总量: {total_size / 1024 / 1024:.2f} MB")
    
    print("=" * 60)

if __name__ == "__main__":
    # 确保目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STOCKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 解析参数
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--incremental":
            incremental_update()
        elif cmd == "--full":
            full_update()
        elif cmd == "--status":
            check_status()
        else:
            print("用法: python market_cache.py [--incremental|--full|--status]")
    else:
        # 默认执行增量更新
        incremental_update()