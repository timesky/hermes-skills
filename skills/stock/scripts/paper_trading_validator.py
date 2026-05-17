#!/usr/bin/env python3
"""
实盘模拟验证脚本 - 验证昨日预测并分析偏差

核心流程：
1. 获取昨日预测记录（target_date = 昨天）
2. 获取昨日实际价格（从Baostock/缓存）
3. 计算偏差和成功率
4. 分析失败原因
5. 输出改进建议

用法：
    python3 paper_trading_validator.py                    # 验证昨天的预测
    python3 paper_trading_validator.py --date 2026-05-11  # 验证指定日期
    python3 paper_trading_validator.py --backfill         # 批量补填历史验证
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import baostock as bs
import pandas as pd

DB_PATH = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "paper_trading" / "paper_trading.db"
CACHE_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "cache"


def get_actual_price(symbol: str, date: str) -> dict:
    """从Baostock获取指定日期的实际价格"""
    # 转换代码格式 (600036 -> sh.600036)
    if symbol.startswith('6'):
        bs_code = f'sh.{symbol}'
    else:
        bs_code = f'sz.{symbol}'
    
    # 检查缓存
    cache_file = CACHE_DIR / bs_code.replace('.', '_') / f"{date}_{date}.csv"
    if cache_file.exists():
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if len(df) > 0:
            row = df.iloc[0]
            return {
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
            }
    
    # 从Baostock获取
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        bs_code,
        'date,open,high,low,close',
        start_date=date,
        end_date=date,
        frequency='d',
        adjustflag='1'  # 前复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    bs.logout()
    
    if len(data_list) == 0:
        return None
    
    row = data_list[0]
    return {
        'open': float(row[1]),
        'high': float(row[2]),
        'low': float(row[3]),
        'close': float(row[4]),
    }


def validate_prediction(prediction: dict, actual: dict) -> dict:
    """验证单个预测"""
    predict_low = prediction['predict_low']
    predict_high = prediction['predict_high']
    actual_low = actual['low']
    actual_high = actual['high']
    
    # 判断是否在预测范围内
    low_in_range = actual_low >= predict_low * 0.97  # 允许3%偏差
    high_in_range = actual_high <= predict_high * 1.03
    
    # 计算偏差百分比
    low_deviation = abs(actual_low - predict_low) / predict_low * 100
    high_deviation = abs(actual_high - predict_high) / predict_high * 100
    avg_deviation = (low_deviation + high_deviation) / 2
    
    # 判断成功
    is_success = low_in_range and high_in_range
    
    # 分析失败原因
    failure_reason = None
    if not is_success:
        if actual_low < predict_low:
            failure_reason = f"实际最低价({actual_low:.2f})低于预测({predict_low:.2f})，偏差{low_deviation:.1f}%"
        if actual_high > predict_high:
            failure_reason = f"实际最高价({actual_high:.2f})高于预测({predict_high:.2f})，偏差{high_deviation:.1f}%"
        if not low_in_range and not high_in_range:
            failure_reason = f"振幅超出预期：预测区间[{predict_low:.2f}, {predict_high:.2f}]，实际[{actual_low:.2f}, {actual_high:.2f}]"
    
    return {
        'actual_low': actual_low,
        'actual_high': actual_high,
        'actual_open': actual['open'],
        'actual_close': actual['close'],
        'is_success': 1 if is_success else 0,
        'deviation_pct': avg_deviation,
        'failure_reason': failure_reason,
    }


def analyze_patterns(results: list) -> dict:
    """分析整体验证模式"""
    if len(results) == 0:
        return {'success_rate': 0, 'avg_deviation': 0}
    
    successes = [r for r in results if r['is_success']]
    failures = [r for r in results if not r['is_success']]
    
    success_rate = len(successes) / len(results) * 100
    avg_deviation = sum(r['deviation_pct'] for r in results) / len(results)
    
    # 分析失败模式
    failure_patterns = []
    for f in failures:
        if f['failure_reason']:
            failure_patterns.append(f['failure_reason'])
    
    # 评分
    accuracy_score = max(0, 100 - avg_deviation * 10)
    
    return {
        'success_rate': success_rate,
        'avg_deviation': avg_deviation,
        'accuracy_score': accuracy_score,
        'failure_count': len(failures),
        'failure_patterns': failure_patterns[:3],  # 只取前3条
    }


def generate_improvement_suggestions(patterns: dict) -> list:
    """生成改进建议"""
    suggestions = []
    
    if patterns['avg_deviation'] > 5:
        suggestions.append("⚠️ 偏差较大，建议调整预测模型参数")
    
    if patterns['success_rate'] < 60:
        suggestions.append("⚠️ 成功率偏低，需重新校准策略")
    
    if patterns['accuracy_score'] < 80:
        suggestions.append("⚠️ 准确度低于80分，触发策略反思流程")
    
    if len(patterns['failure_patterns']) > 0:
        suggestions.append("常见失败模式:")
        for p in patterns['failure_patterns']:
            suggestions.append(f"  - {p}")
    
    if patterns['accuracy_score'] >= 80:
        suggestions.append("✅ 准确度达标，策略验证通过")
    
    return suggestions


def main():
    parser = argparse.ArgumentParser(description='实盘模拟验证脚本')
    parser.add_argument('--date', type=str, help='验证指定日期（格式：2026-05-11）')
    parser.add_argument('--backfill', action='store_true', help='批量补填历史验证')
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print("❌ 数据库不存在，请先运行 paper_trading_daily.py")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 确定验证日期
    if args.date:
        target_date = args.date
    else:
        # 验证昨天的预测
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print(f"📊 实盘模拟验证 - {target_date}")
    print(f"{'='*60}\n")
    
    # 获取待验证的预测
    cursor.execute("""
        SELECT id, predict_date, target_date, symbol, name, predict_type,
               predict_low, predict_high, current_price, action, action_price
        FROM predictions
        WHERE target_date = ? AND actual_low IS NULL
    """, (target_date,))
    
    predictions = cursor.fetchall()
    
    if len(predictions) == 0:
        print(f"⚠️ 无待验证预测（target_date={target_date}）")
        
        # 显示最近的预测状态
        cursor.execute("""
            SELECT predict_date, target_date, symbol, actual_low, actual_high
            FROM predictions
            ORDER BY predict_date DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()
        print("\n最近预测状态:")
        for r in recent:
            status = "✅已验证" if r[3] else "⏳待验证"
            print(f"  {r[0]} → {r[1]} | {r[2]} | {status}")
        
        conn.close()
        return
    
    print(f"待验证预测: {len(predictions)} 条\n")
    
    # 逐条验证
    results = []
    for pred in predictions:
        pred_id, pred_date, target_date, symbol, name, pred_type, pred_low, pred_high, current_price, action, action_price = pred
        
        print(f"验证 {symbol} {name}:")
        print(f"  预测区间: [{pred_low:.2f}, {pred_high:.2f}]")
        print(f"  预测操作: {action} @ {action_price:.2f}")
        
        # 获取实际价格
        actual = get_actual_price(symbol, target_date)
        
        if actual is None:
            print(f"  ⚠️ 无法获取实际价格（可能停牌或非交易日）")
            continue
        
        print(f"  实际区间: [{actual['low']:.2f}, {actual['high']:.2f}]")
        
        # 验证
        validation = validate_prediction({
            'predict_low': pred_low,
            'predict_high': pred_high,
        }, actual)
        
        # 更新数据库
        cursor.execute("""
            UPDATE predictions
            SET actual_low = ?, actual_high = ?, actual_open = ?, actual_close = ?,
                is_success = ?, deviation_pct = ?, verified_at = ?
            WHERE id = ?
        """, (
            validation['actual_low'],
            validation['actual_high'],
            validation['actual_open'],
            validation['actual_close'],
            validation['is_success'],
            validation['deviation_pct'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pred_id
        ))
        
        # 记录结果
        status = "✅" if validation['is_success'] else "❌"
        print(f"  验证结果: {status} 偏差 {validation['deviation_pct']:.1f}%")
        
        results.append({
            'symbol': symbol,
            'is_success': validation['is_success'],
            'deviation_pct': validation['deviation_pct'],
            'failure_reason': validation['failure_reason'],
        })
    
    conn.commit()
    
    # 分析整体模式
    patterns = analyze_patterns(results)
    
    print(f"\n{'='*60}")
    print("📊 验证统计")
    print(f"{'='*60}")
    print(f"验证数量: {len(results)} 条")
    print(f"成功数量: {len([r for r in results if r['is_success']])} 条")
    print(f"成功率: {patterns['success_rate']:.1f}%")
    print(f"平均偏差: {patterns['avg_deviation']:.1f}%")
    print(f"准确度评分: {patterns['accuracy_score']:.1f} 分")
    
    # 改进建议
    suggestions = generate_improvement_suggestions(patterns)
    print(f"\n{'='*60}")
    print("💡 改进建议")
    print(f"{'='*60}")
    for s in suggestions:
        print(s)
    
    # 触发策略反思
    if patterns['accuracy_score'] < 60:
        print(f"\n⚠️ 准确度低于60分，建议运行策略反思脚本")
        print("  命令: python3 strategy_reflector.py --analyze-failures")
    
    conn.close()
    print(f"\n{'='*60}")
    print("✅ 验证完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()