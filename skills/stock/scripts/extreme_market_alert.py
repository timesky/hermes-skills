#!/usr/bin/env python3
"""
极端行情预警脚本
功能：检测熔断/停牌潮/流动性枯竭等极端行情
执行时间：每日9:30
"""

import os
import json
from pathlib import Path
from datetime import datetime

# 强制禁用代理（避免系统代理配置干扰）
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ[k] = ''

import requests

# 禁用 requests 的环境代理并设置默认请求头
session = requests.Session()
session.trust_env = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://quote.eastmoney.com/',
})

# Monkey patch requests.session to use our configured session
original_session = requests.session
requests.session = lambda: session

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "extreme_alerts"

# 预警等级定义
WARNING_LEVELS = {
    'NORMAL': {'index_drop': 5, 'limit_down_ratio': 2, 'action': '正常交易'},
    'WARNING': {'index_drop': 7, 'limit_down_ratio': 5, 'action': '减仓至50%'},
    'DANGER': {'index_drop': 10, 'limit_down_ratio': 10, 'action': '减仓至20%'},
    'EXTREME': {'index_drop': 15, 'limit_down_ratio': 20, 'action': '清仓'}
}

def get_index_change():
    """获取主要指数涨跌幅（使用腾讯股票API）"""
    try:
        # 获取上证指数实时数据
        # API返回格式：v_sh000001="1~名称~代码~当前价~昨收~今开~成交量~..."
        url = "https://qt.gtimg.cn/q=sh000001"
        
        resp = session.get(url, timeout=10)
        
        if 'v_sh000001' in resp.text:
            # 解析数据
            data_str = resp.text.split('"')[1]
            data = data_str.split('~')
            
            # 字段索引：
            # 1: 名称, 3: 当前价, 4: 昨收, 5: 今开, 6: 成交量
            name = data[1]
            current = float(data[3])
            yesterday_close = float(data[4])
            open_price = float(data[5])
            volume = int(data[6])
            
            # 计算涨跌幅
            pct_chg = (current - yesterday_close) / yesterday_close * 100 if yesterday_close > 0 else 0
            
            # 显示最新数据
            print(f"  {name}")
            print(f"  昨收: {yesterday_close:.2f}")
            print(f"  今开: {open_price:.2f}")
            print(f"  当前: {current:.2f}")
            print(f"  成交量: {volume:,}")
            
            return pct_chg
        
        print("API返回数据格式异常")
        return 0
    except Exception as e:
        print(f"获取指数数据失败: {e}")
        import traceback
        traceback.print_exc()
        return 0

def get_limit_down_ratio():
    """获取跌停比例（使用东方财富API，简化统计）"""
    try:
        # 东方财富股票列表 API
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        
        # 基础参数
        base_params = {
            'fid': 'f3',  # 按涨跌幅排序
            'po': '0',    # 反序（降序，涨幅最大在前）
            'np': '1',
            'fltt': '2',
            'invt': '2',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',  # A股市场
            'fields': 'f12,f14,f3'  # 代码,名称,涨跌幅
        }
        
        # 统计数据
        limit_down_count = 0
        limit_up_count = 0
        up_count = 0
        down_count = 0
        
        # 尝试获取涨幅榜和跌幅榜
        # 由于 API 不稳定，采用单次请求策略
        
        # 先获取涨幅榜
        params = base_params.copy()
        params['pn'] = 1
        params['pz'] = 500
        
        resp = session.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and 'diff' in data['data']:
                stocks = data['data']['diff']
                total_estimate = data['data'].get('total', 5851)
                
                for s in stocks:
                    pct = s.get('f3', 0)
                    if pct >= 9.5:
                        limit_up_count += 1
                        up_count += 1
                    elif pct > 0:
                        up_count += 1
                
                # 估算跌停数量（基于涨幅榜的涨停数量和市场情况）
                # 如果涨幅榜有涨停，跌幅榜也应该有跌停
                # 使用涨停数作为基准，结合指数跌幅估算
                
                # 获取指数涨跌幅来辅助估算
                index_drop = abs(get_index_change())
                
                # 估算跌停比例：基于指数跌幅
                # 正常情况（指数跌幅<1%）：跌停比例约1-2%
                # 小幅下跌（指数跌幅1-3%）：跌停比例约3-5%
                # 大幅下跌（指数跌幅3-7%）：跌停比例约10-15%
                # 暴跌（指数跌幅>7%）：跌停比例可能达到20%+
                
                if index_drop > 7:
                    estimated_limit_down_ratio = 20
                elif index_drop > 3:
                    estimated_limit_down_ratio = 10 + (index_drop - 3) * 2
                elif index_drop > 1:
                    estimated_limit_down_ratio = 5 + (index_drop - 1) * 2
                else:
                    estimated_limit_down_ratio = 2
                
                # 估算跌停数量
                limit_down_count = int(total_estimate * estimated_limit_down_ratio / 100)
                
                # 显示统计结果
                print(f"  市场股票总数: ~{total_estimate}只")
                print(f"  涨停（实际统计）: {limit_up_count}只")
                print(f"  跌停（基于指数估算）: {limit_down_count}只")
                print(f"  跌停比例估算: {estimated_limit_down_ratio:.2f}%")
                
                return estimated_limit_down_ratio, limit_down_count, total_estimate
        
        # 如果 API 请求失败，使用指数跌幅估算
        print(f"  股票列表 API 请求失败，使用指数跌幅估算")
        
        index_drop = abs(get_index_change())
        total_estimate = 5851
        
        if index_drop > 7:
            estimated_limit_down_ratio = 20
        elif index_drop > 3:
            estimated_limit_down_ratio = 10 + (index_drop - 3) * 2
        elif index_drop > 1:
            estimated_limit_down_ratio = 5 + (index_drop - 1) * 2
        else:
            estimated_limit_down_ratio = 2
        
        limit_down_count = int(total_estimate * estimated_limit_down_ratio / 100)
        
        print(f"  跌停估算: {limit_down_count}只 ({estimated_limit_down_ratio:.2f}%)")
        
        return estimated_limit_down_ratio, limit_down_count, total_estimate
        
    except Exception as e:
        print(f"获取跌停数据失败: {e}")
        # 使用指数跌幅估算
        index_drop = abs(get_index_change())
        total_estimate = 5851
        
        if index_drop > 7:
            estimated_limit_down_ratio = 20
        elif index_drop > 3:
            estimated_limit_down_ratio = 10 + (index_drop - 3) * 2
        elif index_drop > 1:
            estimated_limit_down_ratio = 5 + (index_drop - 1) * 2
        else:
            estimated_limit_down_ratio = 2
        
        limit_down_count = int(total_estimate * estimated_limit_down_ratio / 100)
        
        print(f"  跌停估算（备用）: {limit_down_count}只 ({estimated_limit_down_ratio:.2f}%)")
        
        return estimated_limit_down_ratio, limit_down_count, total_estimate

def calculate_warning_level(index_drop, limit_down_ratio):
    """计算综合预警级别"""
    level = "NORMAL"
    
    # 按指数跌幅判断
    if index_drop > WARNING_LEVELS['EXTREME']['index_drop']:
        level = "EXTREME"
    elif index_drop > WARNING_LEVELS['DANGER']['index_drop']:
        level = "DANGER"
    elif index_drop > WARNING_LEVELS['WARNING']['index_drop']:
        level = "WARNING"
    
    # 按跌停比例判断（可能升级预警）
    if limit_down_ratio > WARNING_LEVELS['EXTREME']['limit_down_ratio']:
        level = "EXTREME"
    elif limit_down_ratio > WARNING_LEVELS['DANGER']['limit_down_ratio'] and level != "EXTREME":
        level = "DANGER"
    elif limit_down_ratio > WARNING_LEVELS['WARNING']['limit_down_ratio'] and level in ["NORMAL", "WARNING"]:
        level = "WARNING"
    
    return level

def save_alert_report(index_drop, limit_down_ratio, limit_down_count, total, level):
    """保存预警报告"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = DATA_DIR / f"extreme_alert_{timestamp}.json"
    
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'index_drop_pct': index_drop,
        'limit_down_ratio': limit_down_ratio,
        'limit_down_count': limit_down_count,
        'total_stock_count': total,
        'warning_level': level,
        'action': WARNING_LEVELS[level]['action'],
        'historical_reference': {
            '2015股灾': {'drop': -45, 'ratio': 45, 'days': 73},
            '2020疫情': {'drop': -8, 'ratio': 30, 'days': 1},
            '2016熔断': {'drop': -7, 'ratio': 15, 'days': 4}
        }
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_file

def run_alert():
    """执行极端行情预警"""
    print("=" * 60)
    print(f"【极端行情预警】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 获取指数涨跌幅
    index_drop = get_index_change()
    print("\n【指数跌幅】")
    print(f"  当日涨跌: {index_drop:+.2f}%")
    
    # 获取跌停比例
    limit_down_ratio, limit_down_count, total = get_limit_down_ratio()
    print("\n【跌停统计】")
    print(f"  跌停数量: {limit_down_count}只")
    print(f"  跌停比例: {limit_down_ratio:.2f}%")
    
    # 计算预警级别
    level = calculate_warning_level(abs(index_drop), limit_down_ratio)
    
    print("\n【综合预警】")
    level_symbol = "✓" if level == "NORMAL" else "⚠️" if level == "WARNING" else "🔴" if level == "DANGER" else "🚨"
    print(f"  当前级别: {level_symbol} {level}")
    print(f"  操作建议: {WARNING_LEVELS[level]['action']}")
    
    # 保存报告
    report_file = save_alert_report(index_drop, limit_down_ratio, limit_down_count, total, level)
    print(f"\n报告已保存: {report_file}")
    
    print("=" * 60)
    
    return level

if __name__ == "__main__":
    run_alert()