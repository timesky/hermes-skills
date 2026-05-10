#!/usr/bin/env python3
"""
实盘模拟简报 - 用于cronjob推送
从SQLite数据库读取，不进行网络请求，快速生成报告（<1秒运行）

使用场景：
- Cronjob定时任务（避免超时）
- 快速查看实盘模拟状态

用法：
    python3 paper_trading_summary.py

输出格式：
    一、昨日预测验证（成功率、准确度）
    二、账户概况（总成本、总盈亏、仓位比例）
    三、持股监控（代码、名称、数量、盈亏%、操作建议）
    四、次日买入候选（选股池前5名）
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "paper_trading" / "paper_trading.db"


def get_db_data():
    """从数据库读取最新数据"""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 读取账户概况
    cursor.execute("""
        SELECT date, total_cost, total_pnl, stock_value, available_cash, total_value, position_ratio
        FROM account_summary
        ORDER BY date DESC LIMIT 1
    """)
    account = cursor.fetchone()
    
    # 读取持股（去重 - 每个symbol只保留一条）
    cursor.execute("""
        SELECT symbol, name, shares, cost_price, current_price, pnl_pct, stop_loss_price, take_profit_price
        FROM positions
        WHERE date = (SELECT MAX(date) FROM positions)
        GROUP BY symbol
        ORDER BY symbol
    """)
    positions = cursor.fetchall()
    
    # 读取次日预测（去重 - 每个symbol只保留一条）
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT symbol, name, predict_type, predict_low, predict_high, action, action_shares, action_price
        FROM predictions
        WHERE target_date = ? AND predict_date = (SELECT MAX(predict_date) FROM predictions)
        GROUP BY symbol
        ORDER BY predict_type DESC, symbol
    """, (tomorrow,))
    predictions = cursor.fetchall()
    
    # 读取验证准确度（从predictions表计算）
    cursor.execute("""
        SELECT AVG(deviation_pct) FROM predictions
        WHERE actual_low IS NOT NULL AND deviation_pct IS NOT NULL
        AND predict_date = (SELECT MAX(predict_date) FROM predictions WHERE actual_low IS NOT NULL)
    """)
    avg_deviation = cursor.fetchone()[0] or 0
    
    # 计算成功率
    cursor.execute("""
        SELECT COUNT(*) as total, SUM(CASE WHEN is_success = 1 THEN 1 ELSE 0 END) as success
        FROM predictions
        WHERE actual_low IS NOT NULL
        AND predict_date = (SELECT MAX(predict_date) FROM predictions WHERE actual_low IS NOT NULL)
    """)
    total, success = cursor.fetchone()
    
    conn.close()
    
    # 计算准确度分数（偏差越小分数越高）
    avg_accuracy = max(0, 100 - avg_deviation * 10) if avg_deviation else 0
    success_rate = success / total if total > 0 else 0
    
    return {
        'account': account,
        'positions': positions,
        'predictions': predictions,
        'avg_accuracy': avg_accuracy,
        'success_rate': success_rate,
        'total': total,
        'success': success
    }


def format_report(data):
    """格式化报告"""
    if not data:
        return "⚠️ 数据库无数据，请先运行 paper_trading_daily.py"
    
    account = data['account']
    positions = data['positions']
    predictions = data['predictions']
    avg_accuracy = data['avg_accuracy']
    
    lines = []
    lines.append("=" * 60)
    lines.append("📊 实盘模拟每日报告（{}）".format(datetime.now().strftime('%Y-%m-%d')))
    lines.append("=" * 60)
    
    # 一、昨日预测验证
    lines.append("\n【一、昨日预测验证】")
    if data['total'] > 0:
        lines.append("验证次数: {}/{}".format(data['success'], data['total']))
        lines.append("成功率: {:.1f}%".format(data['success_rate'] * 100))
        lines.append("平均准确度: {:.1f}分 {}".format(data['avg_accuracy'], "🎯" if data['avg_accuracy'] >= 80 else "⚠️"))
    else:
        lines.append("无验证数据")
    
    # 二、账户概况
    lines.append("\n【二、账户概况】")
    if account:
        total_value = account[5]
        position_ratio = account[6]
        lines.append("总成本: {:.0f}元".format(account[1]))
        lines.append("总盈亏: {:.0f}元 ({:+.2f}%)".format(account[2], account[2] / account[1] * 100 if account[1] > 0 else 0))
        lines.append("股票价值: {:.0f}元".format(account[3]))
        lines.append("可用资金: {:.0f}元".format(account[4]))
        lines.append("总资产: {:.0f}元".format(total_value))
        lines.append("仓位比例: {:.1f}%".format(position_ratio if position_ratio else 0))
    
    # 三、持股监控
    lines.append("\n【三、持股监控】（{}只）".format(len(positions)))
    if positions:
        lines.append("{:<8} {:<8} {:>6} {:>8} {:>8} {:>8} {:>8}".format(
            "代码", "名称", "数量", "成本", "现价", "盈亏%", "操作"
        ))
        lines.append("-" * 60)
        
        for pos in positions:
            symbol, name, shares, cost, current, return_pct, stop_loss, take_profit = pos
            return_str = "{:+.1f}%".format(return_pct)
            action = "持有 ✅" if return_pct >= -10 else "止损 ⚠️"
            lines.append("{:<8} {:<8} {:>6} {:>8.2f} {:>8.2f} {:>8} {:>8}".format(
                symbol, name, shares, cost, current, return_str, action
            ))
    else:
        lines.append("空仓")
    
    # 四、次日买入候选（选股池）
    lines.append("\n【四、次日买入候选】")
    buy_predictions = [p for p in predictions if p[5] == '买入']
    if buy_predictions:
        lines.append("{:<8} {:<8} {:>8} {:>8} {:>6} {:>8}".format(
            "代码", "名称", "预测高点", "预测低点", "数量", "买入价"
        ))
        lines.append("-" * 60)
        
        for pred in buy_predictions[:5]:  # 只显示前5名
            symbol, name, pred_type, pred_low, pred_high, action, shares, price = pred
            lines.append("{:<8} {:<8} {:>8.2f} {:>8.2f} {:>6} {:>8.2f}".format(
                symbol, name, pred_high, pred_low, shares or 0, price or 0
            ))
    else:
        lines.append("无买入候选")
    
    lines.append("\n" + "=" * 60)
    lines.append("✅ 报告完成")
    lines.append("📁 详细数据: ~/.hermes/profiles/stock/data/paper_trading/")
    lines.append("=" * 60)
    
    return "\n".join(lines)


if __name__ == "__main__":
    data = get_db_data()
    report = format_report(data)
    print(report)