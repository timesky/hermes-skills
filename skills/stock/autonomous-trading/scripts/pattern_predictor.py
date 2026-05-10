#!/usr/bin/env python3
"""
走势模式预测模块
基于技术指标判断次日走势模式

模式类型：
- 'low_open_high_close': 低开高走
- 'high_open_low_close': 高开低走
- 'oscillation_up': 震荡上行
- 'oscillation_down': 震荡下行
- 'strong_up': 强势上涨
- 'weak_down': 弱势下跌
- 'narrow_oscillation': 窄幅震荡
"""

import pandas as pd
import numpy as np

def predict_price_pattern(df: pd.DataFrame) -> dict:
    """判断次日走势模式"""
    
    if len(df) < 20:
        return {'pattern': '数据不足', 'pattern_code': 'unknown', 'confidence': 0}
    
    last_close = df['close'].iloc[-1]
    
    # RSI (14日)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss if loss.iloc[-1] > 0 else 100
    rsi = 100 - (100 / (1 + rs.iloc[-1]))
    
    # 趋势方向 (MA5 vs MA20)
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    ma20 = df['close'].rolling(20).mean().iloc[-1]
    trend = 'up' if ma5 > ma20 else 'down' if ma5 < ma20 else 'flat'
    
    # 波动率 (ATR)
    high_20 = df['high'].iloc[-20:].max()
    low_20 = df['low'].iloc[-20:].min()
    atr = (high_20 - low_20) / 20
    
    # 成交量变化
    vol_avg = df['volume'].rolling(10).mean().iloc[-1]
    vol_last = df['volume'].iloc[-1]
    vol_change = vol_last / vol_avg if vol_avg > 0 else 1
    
    # 连续涨跌天数
    recent_changes = df['close'].iloc[-5:].pct_change()
    up_days = (recent_changes > 0).sum()
    down_days = (recent_changes < 0).sum()
    
    # 判断逻辑
    if rsi > 70:
        if trend == 'up':
            return {'pattern': '震荡下行', 'confidence': 0.6, 'reason': f'RSI={rsi:.1f}超买'}
        return {'pattern': '弱势下跌', 'confidence': 0.7, 'reason': f'RSI={rsi:.1f}超买+趋势弱'}
    elif rsi < 30:
        if trend == 'down':
            return {'pattern': '震荡上行', 'confidence': 0.6, 'reason': f'RSI={rsi:.1f}超卖'}
        return {'pattern': '强势上涨', 'confidence': 0.7, 'reason': f'RSI={rsi:.1f}超卖+趋势强'}
    elif vol_change > 1.5:
        if trend == 'up':
            return {'pattern': '强势上涨', 'confidence': 0.65, 'reason': '放量+向上趋势'}
        return {'pattern': '弱势下跌', 'confidence': 0.65, 'reason': '放量+向下趋势'}
    elif up_days >= 3:
        return {'pattern': '高开低走', 'confidence': 0.55, 'reason': f'连续{up_days}日上涨'}
    elif down_days >= 3:
        return {'pattern': '低开高走', 'confidence': 0.55, 'reason': f'连续{down_days}日下跌'}
    
    return {'pattern': '窄幅震荡', 'confidence': 0.5, 'reason': '无明确信号'}


def predict_next_day_range(df: pd.DataFrame, pattern_result: dict) -> dict:
    """基于走势模式预测次日高低点范围"""
    
    last_close = df['close'].iloc[-1]
    pattern_code = pattern_result['pattern']
    
    # 基础振幅
    recent_amp = df['close'].iloc[-10:].pct_change().abs().mean() * 100
    atr_amp = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / 20 / last_close * 100
    base_amp = max(recent_amp, atr_amp, 2.0)
    
    # 振幅因子
    amp_factors = {
        '强势上涨': 1.5, '弱势下跌': 1.5,
        '低开高走': 1.2, '高开低走': 1.2,
        '震荡上行': 1.3, '震荡下行': 1.3,
        '窄幅震荡': 0.8
    }
    amp_factor = amp_factors.get(pattern_code, 1.0)
    
    predict_amp = base_amp * amp_factor
    half_amp = predict_amp / 2
    
    predict_high = round(last_close * (1 + half_amp / 100), 2)
    predict_low = round(last_close * (1 - half_amp / 100), 2)
    
    return {
        'predict_high': predict_high,
        'predict_low': predict_low,
        'predict_amplitude': round(predict_amp, 2)
    }


def full_prediction(df: pd.DataFrame) -> dict:
    """完整的次日预测"""
    pattern_result = predict_price_pattern(df)
    range_result = predict_next_day_range(df, pattern_result)
    
    return {
        'pattern': pattern_result['pattern'],
        'predict_high': range_result['predict_high'],
        'predict_low': range_result['predict_low'],
        'predict_amplitude': range_result['predict_amplitude'],
        'confidence': pattern_result['confidence'],
        'reason': pattern_result['reason']
    }