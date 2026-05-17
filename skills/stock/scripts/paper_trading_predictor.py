#!/usr/bin/env python3
"""
实盘模拟每日预测脚本 - 预测次日走势并集成主力信号

核心流程：
1. 获取当前持仓和候选股票池
2. 技术分析预测（MA5/MA60支撑阻力）
3. 主力信号得分计算（两融+大单）
4. 信号结合生成最终预测
5. 写入predictions表

用法：
    python3 paper_trading_predictor.py                    # 默认预测
    python3 paper_trading_predictor.py --stocks 600036,600584  # 指定股票
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import json

import akshare as ak
import baostock as bs

DB_PATH = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "paper_trading" / "paper_trading.db"
CACHE_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "cache"


def get_stock_pool():
    """获取预测股票池（持仓+候选）"""
    # 默认股票池（可从配置读取）
    default_pool = [
        {'code': '600036', 'name': '招商银行'},
        {'code': '600584', 'name': '长电科技'},
        {'code': '601012', 'name': '隆基绿能'},
        {'code': '601698', 'name': '中国卫通'},
        {'code': '000506', 'name': '招金黄金'},
    ]
    
    # 从数据库读取持仓
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, name FROM positions
            WHERE date = (SELECT MAX(date) FROM positions)
            GROUP BY symbol
        """)
        positions = cursor.fetchall()
        
        # 合并持仓和默认池
        for pos in positions:
            code, name = pos
            if not any(s['code'] == code for s in default_pool):
                default_pool.append({'code': code, 'name': name})
        
        conn.close()
    
    return default_pool


def get_kline_data(code: str, days: int = 60) -> dict:
    """获取K线数据（前复权）"""
    # 转换代码格式
    if code.startswith('6'):
        bs_code = f'sh.{code}'
    else:
        bs_code = f'sz.{code}'
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        bs_code,
        'date,open,high,low,close,volume',
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        adjustflag='1'  # 前复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    bs.logout()
    
    if len(data_list) < 20:
        return None
    
    # 转换为DataFrame
    import pandas as pd
    df = pd.DataFrame(data_list, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    
    return {
        'latest_close': df['close'].iloc[-1],
        'latest_high': df['high'].iloc[-1],
        'latest_low': df['low'].iloc[-1],
        'ma5': df['close'].tail(5).mean(),
        'ma10': df['close'].tail(10).mean(),
        'ma20': df['close'].tail(20).mean(),
        'ma60': df['close'].tail(60).mean() if len(df) >= 60 else df['close'].mean(),
        'data': df,
    }


def calculate_main_force_score() -> dict:
    """
    计算市场主力信号得分（全局）
    
    返回:
        - margin_score: 两融得分（40分）
        - margin_change_5d: 5日融资余额变化（亿）
        - margin_level: 当前融资余额水平
        - sentiment: 市场情绪判断
    """
    result = {
        'margin_score': 0,
        'margin_change_5d': 0,
        'margin_level': 0,
        'sentiment': '中性',
    }
    
    try:
        # 获取两融数据
        df_margin = ak.stock_margin_account_info()
        
        if len(df_margin) < 6:
            return result
        
        latest = df_margin.iloc[-1]
        prev_5d = df_margin.iloc[-6]
        
        # 融资余额（单位已经是亿元）
        current_margin = float(latest['融资余额'])
        prev_margin = float(prev_5d['融资余额'])
        
        result['margin_level'] = current_margin
        result['margin_change_5d'] = current_margin - prev_margin
        
        # 计算得分
        change_rate = result['margin_change_5d']
        
        if change_rate > 500:
            result['margin_score'] = 40
            result['sentiment'] = '强势看多'
        elif change_rate > 100:
            result['margin_score'] = 30
            result['sentiment'] = '温和看多'
        elif change_rate > 0:
            result['margin_score'] = 20
            result['sentiment'] = '微弱看多'
        elif change_rate < -300:
            result['margin_score'] = 0
            result['sentiment'] = '强势看空'
        else:
            result['margin_score'] = 10
            result['sentiment'] = '中性'
        
    except Exception as e:
        print(f"两融数据获取失败: {e}")
    
    return result


def get_big_deal_signal(code: str) -> dict:
    """获取个股大单交易信号"""
    result = {
        'big_deal_score': 10,  # 默认中性
        'buy_ratio': 50,
        'has_big_deal': False,
    }
    
    try:
        df_big = ak.stock_fund_flow_big_deal()
        # 字段名是 '股票代码'，不是 '代码'
        stock_big = df_big[df_big['股票代码'] == code]
        
        if len(stock_big) > 0:
            result['has_big_deal'] = True
            
            # 从 '大单性质' 计算买入占比（买盘 vs 卖盘）
            buy_count = len(stock_big[stock_big['大单性质'] == '买盘'])
            sell_count = len(stock_big[stock_big['大单性质'] == '卖盘'])
            total = buy_count + sell_count
            
            if total > 0:
                buy_ratio = buy_count / total * 100
                result['buy_ratio'] = buy_ratio
                
                if buy_ratio > 70:
                    result['big_deal_score'] = 40
                elif buy_ratio > 55:
                    result['big_deal_score'] = 30
                elif buy_ratio > 50:
                    result['big_deal_score'] = 20
                elif buy_ratio < 30:
                    result['big_deal_score'] = 0
                else:
                    result['big_deal_score'] = 10
        
    except Exception as e:
        print(f"大单数据获取失败: {e}")
    
    return result


def predict_technical(kline: dict) -> dict:
    """
    技术分析预测
    
    基于:
    - MA5/MA10/MA20支撑阻力
    - 价格位置判断
    - 波动率估算
    """
    latest_close = kline['latest_close']
    latest_high = kline['latest_high']
    latest_low = kline['latest_low']
    ma5 = kline['ma5']
    ma10 = kline['ma10']
    ma20 = kline['ma20']
    
    # 预测区间（基于近期波动）
    recent_range = latest_high - latest_low
    predict_low = latest_close - recent_range * 0.3
    predict_high = latest_close + recent_range * 0.3
    
    # 技术信号判断
    signal = 'hold'
    confidence = 'medium'
    
    if latest_close > ma5 and latest_close > ma10:
        # 站稳均线 → 看多
        signal = 'buy'
        confidence = 'high'
        predict_low = max(predict_low, ma5 * 0.98)  # MA5支撑
        predict_high = latest_close + recent_range * 0.5
    
    elif latest_close < ma5 and latest_close < ma10:
        # 跌破均线 → 看空
        signal = 'sell'
        confidence = 'high'
        predict_high = min(predict_high, ma5 * 1.02)  # MA5阻力
        predict_low = latest_close - recent_range * 0.5
    
    else:
        # 震荡区间
        signal = 'hold'
        confidence = 'medium'
    
    return {
        'signal': signal,
        'confidence': confidence,
        'predict_low': predict_low,
        'predict_high': predict_high,
        'ma5': ma5,
        'ma10': ma10,
        'latest_close': latest_close,
    }


def combine_signals(technical: dict, main_force: dict, big_deal: dict) -> dict:
    """
    结合技术信号和主力信号
    """
    final_action = technical['signal']
    final_confidence = technical['confidence']
    note = []
    
    # 主力得分（满分80）
    total_main_score = main_force['margin_score'] + big_deal['big_deal_score']
    
    if technical['signal'] == 'buy':
        if total_main_score >= 60:
            final_confidence = 'high'
            note.append(f"主力强看多（得分{total_main_score}），与技术共振")
        elif total_main_score < 30:
            final_action = 'hold'
            final_confidence = 'low'
            note.append(f"主力看空（得分{total_main_score}），技术买入暂缓")
        else:
            note.append(f"主力中性（得分{total_main_score}），跟随技术信号")
    
    elif technical['signal'] == 'sell':
        if total_main_score < 30:
            final_confidence = 'high'
            note.append(f"主力看空（得分{total_main_score}），与技术共振卖出")
        else:
            note.append(f"主力中性偏多（得分{total_main_score}），但技术信号卖出")
    
    else:  # hold
        if total_main_score >= 50:
            note.append(f"主力偏多（得分{total_main_score}），可关注突破机会")
        elif total_main_score < 20:
            note.append(f"主力偏空（得分{total_main_score}），建议观望")
        else:
            note.append(f"主力中性（得分{total_main_score}），震荡整理")
    
    return {
        'action': final_action,
        'confidence': final_confidence,
        'main_force_score': total_main_score,
        'note': ' | '.join(note) if note else '中性',
    }


def save_prediction(prediction: dict):
    """保存预测到数据库"""
    if not DB_PATH.exists():
        # 创建数据库
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                predict_date TEXT NOT NULL,
                target_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                predict_type TEXT NOT NULL,
                
                predict_low REAL NOT NULL,
                predict_high REAL NOT NULL,
                current_price REAL NOT NULL,
                
                action TEXT NOT NULL,
                action_shares INTEGER NOT NULL,
                action_price REAL NOT NULL,
                action_amount REAL NOT NULL,
                
                actual_low REAL,
                actual_high REAL,
                is_success INTEGER,
                deviation_pct REAL,
                analysis TEXT,
                verified_at TEXT,
                
                main_force_score INTEGER,
                confidence TEXT,
                note TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO predictions (
            predict_date, target_date, symbol, name, predict_type,
            predict_low, predict_high, current_price,
            action, action_shares, action_price, action_amount,
            main_force_score, confidence, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prediction['predict_date'],
        prediction['target_date'],
        prediction['symbol'],
        prediction['name'],
        prediction['predict_type'],
        prediction['predict_low'],
        prediction['predict_high'],
        prediction['current_price'],
        prediction['action'],
        prediction['action_shares'],
        prediction['action_price'],
        prediction['action_amount'],
        prediction['main_force_score'],
        prediction['confidence'],
        prediction['note'],
    ))
    
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='实盘模拟每日预测')
    parser.add_argument('--stocks', type=str, help='指定股票代码（逗号分隔）')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📊 实盘模拟每日预测 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    
    # 获取股票池
    if args.stocks:
        stock_pool = [{'code': c, 'name': ''} for c in args.stocks.split(',')]
    else:
        stock_pool = get_stock_pool()
    
    print(f"预测股票池: {len(stock_pool)} 只")
    for s in stock_pool:
        print(f"  - {s['code']} {s['name']}")
    
    # 获取市场主力信号（全局）
    print(f"\n{'='*60}")
    print("📈 主力信号分析（市场整体）")
    print(f"{'='*60}")
    
    main_force = calculate_main_force_score()
    print(f"融资余额: {main_force['margin_level']:.0f} 亿元")
    print(f"5日变化: {main_force['margin_change_5d']:+.0f} 亿元")
    print(f"两融得分: {main_force['margin_score']} 分")
    print(f"市场情绪: {main_force['sentiment']}")
    
    # 预测每只股票
    print(f"\n{'='*60}")
    print("🎯 个股预测")
    print(f"{'='*60}\n")
    
    predictions = []
    
    for stock in stock_pool:
        code = stock['code']
        name = stock['name']
        
        print(f"分析 {code} {name}:")
        
        # 获取K线数据
        kline = get_kline_data(code)
        
        if kline is None:
            print(f"  ⚠️ K线数据不足，跳过")
            continue
        
        # 技术分析
        technical = predict_technical(kline)
        
        # 大单信号（个股）
        big_deal = get_big_deal_signal(code)
        
        if args.verbose:
            print(f"  最新收盘: {kline['latest_close']:.2f}")
            print(f"  MA5: {technical['ma5']:.2f}, MA10: {technical['ma10']:.2f}")
            print(f"  技术信号: {technical['signal']} ({technical['confidence']})")
            print(f"  大单信号: {big_deal['big_deal_score']} 分")
        
        # 结合信号
        combined = combine_signals(technical, main_force, big_deal)
        
        # 计算操作建议
        if combined['action'] == 'buy':
            action_shares = 100  # 默认100股
            action_price = technical['predict_low'] * 1.01  # 略高于预测低点
            action_amount = action_shares * action_price
        elif combined['action'] == 'sell':
            action_shares = 100
            action_price = technical['predict_high'] * 0.99
            action_amount = action_shares * action_price
        else:
            action_shares = 0
            action_price = 0
            action_amount = 0
        
        prediction = {
            'predict_date': datetime.now().strftime('%Y-%m-%d'),
            'target_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'symbol': code,
            'name': name,
            'predict_type': '技术+主力',
            'predict_low': technical['predict_low'],
            'predict_high': technical['predict_high'],
            'current_price': kline['latest_close'],
            'action': combined['action'],
            'action_shares': action_shares,
            'action_price': action_price,
            'action_amount': action_amount,
            'main_force_score': combined['main_force_score'],
            'confidence': combined['confidence'],
            'note': combined['note'],
        }
        
        predictions.append(prediction)
        
        # 输出预测
        print(f"  预测区间: [{prediction['predict_low']:.2f}, {prediction['predict_high']:.2f}]")
        print(f"  操作建议: {prediction['action']} ({prediction['confidence']})")
        print(f"  主力得分: {prediction['main_force_score']} 分")
        print(f"  {prediction['note']}")
        print()
        
        # 保存到数据库
        save_prediction(prediction)
    
    # 输出汇总
    print(f"\n{'='*60}")
    print("📊 预测汇总")
    print(f"{'='*60}")
    
    buy_count = len([p for p in predictions if p['action'] == 'buy'])
    sell_count = len([p for p in predictions if p['action'] == 'sell'])
    hold_count = len([p for p in predictions if p['action'] == 'hold'])
    
    print(f"预测数量: {len(predictions)} 只")
    print(f"买入建议: {buy_count} 只")
    print(f"卖出建议: {sell_count} 只")
    print(f"持有建议: {hold_count} 只")
    
    # 明日关注
    if buy_count > 0:
        print(f"\n【明日买入关注】")
        for p in predictions:
            if p['action'] == 'buy':
                print(f"  {p['symbol']} {p['name']}: 建议价 {p['action_price']:.2f}")
    
    if sell_count > 0:
        print(f"\n【明日卖出提醒】")
        for p in predictions:
            if p['action'] == 'sell':
                print(f"  {p['symbol']} {p['name']}: 建议价 {p['action_price']:.2f}")
    
    print(f"\n{'='*60}")
    print("✅ 预测完成")
    print(f"{'='*60}")
    print(f"📁 数据已保存至: {DB_PATH}")
    print(f"💡 明日运行: python3 paper_trading_validator.py")


if __name__ == "__main__":
    main()