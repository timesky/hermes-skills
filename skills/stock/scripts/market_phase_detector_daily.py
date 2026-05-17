#!/usr/bin/env python3
"""
市场阶段判定脚本
功能：量化判断市场阶段（牛市/熊市/震荡/反转）
执行时间：每日9:15
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
import numpy as np

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "market_phase"

def get_index_data(symbol="sh000001", days=120):
    """获取指数历史数据"""
    try:
        df = ak.stock_zh_index_daily_em(symbol=symbol)
        if df is not None and len(df) > 0:
            # 取最近N天
            df = df.tail(days)
            return df
        return None
    except Exception as e:
        print(f"获取指数数据失败: {e}")
        return None

def calculate_ma_system(df):
    """计算均线系统"""
    if df is None or len(df) < 60:
        return None
    
    # 根据列名确定收盘价列
    close_col = '收盘价' if '收盘价' in df.columns else 'close'
    
    # 计算均线
    df['MA5'] = df[close_col].rolling(5).mean()
    df['MA20'] = df[close_col].rolling(20).mean()
    df['MA60'] = df[close_col].rolling(60).mean()
    
    return df

def calculate_macd(df):
    """计算MACD"""
    close_col = '收盘价' if '收盘价' in df.columns else 'close'
    
    ema12 = df[close_col].ewm(span=12, adjust=False).mean()
    ema26 = df[close_col].ewm(span=26, adjust=False).mean()
    
    df['MACD'] = ema12 - ema26
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']
    
    return df

def calculate_atr(df, period=14):
    """计算ATR波动率"""
    high_col = '最高价' if '最高价' in df.columns else 'high'
    low_col = '最低价' if '最低价' in df.columns else 'low'
    close_col = '收盘价' if '收盘价' in df.columns else 'close'
    
    high = df[high_col]
    low = df[low_col]
    close = df[close_col].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    return atr.iloc[-1] if len(atr) > 0 else 0

def determine_market_phase(df):
    """判定市场阶段"""
    if df is None or len(df) < 60:
        return "UNKNOWN", 0, {}
    
    latest = df.iloc[-1]
    close_col = '收盘价' if '收盘价' in df.columns else 'close'
    
    # 均线排列判断
    ma5_above_ma20 = latest['MA5'] > latest['MA20']
    ma20_above_ma60 = latest['MA20'] > latest['MA60']
    price_above_ma60 = latest[close_col] > latest['MA60']
    
    # MACD判断
    macd_positive = latest['MACD'] > 0
    macd_hist_positive = latest['MACD_HIST'] > 0
    
    # ATR波动率
    atr = calculate_atr(df)
    atr_ratio = atr / latest[close_col] * 100
    
    # 60日涨跌幅
    price_60d_ago = df.iloc[-60][close_col]
    pct_60d = (latest[close_col] - price_60d_ago) / price_60d_ago * 100
    
    # 综合判断
    phase = "RANGE"  # 默认震荡
    confidence = 50
    
    # 牛市信号
    bull_signals = 0
    if ma5_above_ma20 and ma20_above_ma60:
        bull_signals += 1
    if price_above_ma60:
        bull_signals += 1
    if macd_positive and macd_hist_positive:
        bull_signals += 1
    if pct_60d > 8:
        bull_signals += 1
    
    # 熊市信号
    bear_signals = 0
    if not ma5_above_ma20 and not ma20_above_ma60:
        bear_signals += 1
    if not price_above_ma60:
        bear_signals += 1
    if not macd_positive:
        bear_signals += 1
    if pct_60d < -8:
        bear_signals += 1
    
    # 阈值判断
    if bull_signals >= 3:
        phase = "BULL"
        confidence = 60 + bull_signals * 10
    elif bear_signals >= 3:
        phase = "BEAR"
        confidence = 60 + bear_signals * 10
    elif bull_signals == 2 and bear_signals == 0:
        phase = "BULL_EARLY"  # 牛市初期
        confidence = 55
    elif bear_signals == 2 and bull_signals == 0:
        phase = "BEAR_EARLY"  # 熊市初期
        confidence = 55
    
    indicators = {
        'ma5_above_ma20': ma5_above_ma20,
        'ma20_above_ma60': ma20_above_ma60,
        'price_above_ma60': price_above_ma60,
        'macd_positive': macd_positive,
        'macd_hist_positive': macd_hist_positive,
        'atr_ratio': atr_ratio,
        'pct_60d': pct_60d,
        'bull_signals': bull_signals,
        'bear_signals': bear_signals
    }
    
    return phase, confidence, indicators

def save_phase_report(phase, confidence, indicators):
    """保存阶段判定报告"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = DATA_DIR / f"market_phase_{timestamp}.json"
    
    phase_names = {
        'BULL': '牛市',
        'BULL_EARLY': '牛市初期',
        'BEAR': '熊市',
        'BEAR_EARLY': '熊市初期',
        'RANGE': '震荡市',
        'UNKNOWN': '未知'
    }
    
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'phase': phase,
        'phase_name': phase_names.get(phase, phase),
        'confidence': confidence,
        'indicators': indicators,
        'strategy_suggestion': {
            'BULL': '持有指数/满仓',
            'BULL_EARLY': '逐步建仓',
            'BEAR': '低波动防御+快进快出',
            'BEAR_EARLY': '空仓观望',
            'RANGE': 'MA交叉+成交量确认'
        }
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_file

def run_detector():
    """执行市场阶段判定"""
    print("=" * 60)
    print(f"【市场阶段判定】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 获取指数数据
    df = get_index_data()
    if df is None:
        print("无法获取指数数据")
        return "UNKNOWN"
    
    # 计算指标
    df = calculate_ma_system(df)
    df = calculate_macd(df)
    
    # 判定阶段
    phase, confidence, indicators = determine_market_phase(df)
    
    # 输出结果
    print("\n【技术指标】")
    print(f"  MA5 > MA20: {indicators['ma5_above_ma20']}")
    print(f"  MA20 > MA60: {indicators['ma20_above_ma60']}")
    print(f"  价格 > MA60: {indicators['price_above_ma60']}")
    print(f"  MACD > 0: {indicators['macd_positive']}")
    print(f"  MACD柱 > 0: {indicators['macd_hist_positive']}")
    print(f"  ATR波动率: {indicators['atr_ratio']:.2f}%")
    print(f"  60日涨跌: {indicators['pct_60d']:+.2f}%")
    
    print("\n【信号统计】")
    print(f"  牛市信号: {indicators['bull_signals']}")
    print(f"  熊市信号: {indicators['bear_signals']}")
    
    print("\n【市场阶段】")
    phase_names = {
        'BULL': '牛市 📈',
        'BULL_EARLY': '牛市初期 📈',
        'BEAR': '熊市 📉',
        'BEAR_EARLY': '熊市初期 📉',
        'RANGE': '震荡市 ↔️',
        'UNKNOWN': '未知 ❓'
    }
    print(f"  当前阶段: {phase_names.get(phase, phase)}")
    print(f"  置信度: {confidence}%")
    
    # 保存报告
    report_file = save_phase_report(phase, confidence, indicators)
    print(f"\n报告已保存: {report_file}")
    
    print("=" * 60)
    
    return phase

if __name__ == "__main__":
    run_detector()