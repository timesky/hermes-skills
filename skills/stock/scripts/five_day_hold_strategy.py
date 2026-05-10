#!/usr/bin/env python3
"""
五日不破策略 - Backtrader回测实现
策略核心: 收盘不破5日均线持仓, 有效跌破(2日确认)清仓

用法:
    python3 five_day_hold_strategy.py --code sh.600036 --start 2023-01-01 --end 2025-04-25
    
回测结论 (2024-2025 A股):
- 招商银行: +17.32%, 夏普0.053, 胜率60.9%
- 平安银行: -1.88%, 震荡市频繁止损
- 比亚迪: -47.81%, 不适合该策略

适用场景:
- 趋势明显的蓝筹股
- 中长线持有心态
- 能承受小亏损

不适用:
- 震荡剧烈股票
- 妖股/小盘股(<30亿)
"""

import argparse
import backtrader as bt
import baostock as bs
import pandas as pd
from datetime import datetime


class FiveDayHoldStrategy(bt.Strategy):
    """五日不破策略"""
    
    params = (
        ('stop_loss', 0.10),      # 止损比例 10%
        ('initial_position', 0.3), # 初始仓位 30%
        ('add_position', 0.3),     # 加仓比例 30%
    )
    
    def __init__(self):
        self.ma5 = bt.indicators.SMA(self.data.close, period=5)
        self.ma60 = bt.indicators.SMA(self.data.close, period=60)
        self.close = self.data.close
        
        # 状态追踪
        self.order = None
        self.buy_price = None
        self.position_size = 0
        self.days_below_ma5 = 0
        self.days_above_ma5 = 0
        self.buy_comm = None
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                print(f'买入执行: 价格{order.executed.price:.2f}, '
                      f'成本{order.executed.comm:.2f}, '
                      f'持仓{self.position.size}')
            else:
                print(f'卖出执行: 价格{order.executed.price:.2f}, '
                      f'成本{order.executed.comm:.2f}')
                self.buy_price = None
                self.position_size = 0
                self.days_above_ma5 = 0
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('订单取消/保证金不足/拒绝')
            
        self.order = None
        
    def next(self):
        # 如果有未完成订单，等待
        if self.order:
            return
            
        current_close = self.close[0]
        ma5 = self.ma5[0]
        ma60 = self.ma60[0]
        
        # 无持仓情况
        if not self.position:
            # 条件: 站稳60日线 + 收盘站稳5日线
            if current_close > ma60 and current_close > ma5:
                self.days_above_ma5 += 1
                # 连续2日站稳5日线，买入
                if self.days_above_ma5 >= 2:
                    size = int((self.broker.getcash() * self.params.initial_position) / current_close)
                    if size > 0:
                        self.order = self.buy(size=size)
                        self.position_size = 0.3
            else:
                self.days_above_ma5 = 0
                
        # 有持仓情况
        else:
            # 策略止损: 收盘价 < MA5 * 0.98 (MA5下方2%)
            if current_close < ma5 * 0.98:
                self.order = self.sell(size=self.position.size)
                print(f'触发MA5止损: 当前价{current_close:.2f}, MA5{ma5:.2f} (下方{(1-current_close/ma5)*100:.1f}%)')
                return
                
            # 硬止损: -10%
            if self.buy_price and current_close < self.buy_price * (1 - self.params.stop_loss):
                self.order = self.sell(size=self.position.size)
                print(f'触发硬止损: 买入价{self.buy_price:.2f}, 当前价{current_close:.2f}')
                return
                
            # 加仓逻辑: 连续2日站稳5日线
            if current_close > ma5:
                self.days_above_ma5 += 1
                self.days_below_ma5 = 0
                
                if self.days_above_ma5 >= 2 and self.position_size < 0.6:
                    size = int((self.broker.getcash() * self.params.add_position) / current_close)
                    if size > 0:
                        self.order = self.buy(size=size)
                        self.position_size += 0.3
            else:
                # 收盘跌破5日线
                self.days_below_ma5 += 1
                self.days_above_ma5 = 0
                
                # 有效跌破: 连续2日收盘跌破5日线
                if self.days_below_ma5 >= 2:
                    self.order = self.sell(size=self.position.size)
                    print(f'有效跌破5日线，清仓: 当前价{current_close:.2f}, MA5{ma5:.2f}')
                    
    def stop(self):
        """策略结束时输出"""
        pnl = self.broker.getvalue() - 100000  # 初始资金10万
        print(f'策略结束，总盈亏: {pnl:.2f}')


def fetch_data(code, start_date, end_date):
    """从Baostock获取数据"""
    lg = bs.login()
    print(f'登录Baostock: {lg.error_msg}')
    
    rs = bs.query_history_k_data_plus(
        code,
        'date,open,high,low,close,volume',
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        adjustflag='2'  # 不复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.dropna(inplace=True)
    
    return bt.feeds.PandasData(dataname=df)


def main():
    parser = argparse.ArgumentParser(description='五日不破策略回测')
    parser.add_argument('--code', type=str, required=True, help='股票代码，如 sh.600036')
    parser.add_argument('--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2025-04-25', help='结束日期')
    parser.add_argument('--cash', type=float, default=100000, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.001, help='手续费率')
    
    args = parser.parse_args()
    
    # 创建回测引擎
    cerebro = bt.Cerebro()
    cerebro.addstrategy(FiveDayHoldStrategy)
    
    # 获取数据
    print(f'获取 {args.code} 数据...')
    data = fetch_data(args.code, args.start, args.end)
    cerebro.adddata(data)
    
    # 设置资金和手续费
    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(commission=args.commission)
    
    # 添加分析指标
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # 运行回测
    print(f'\n===== 五日不破策略回测: {args.code} =====')
    print(f'回测区间: {args.start} ~ {args.end}')
    print(f'初始资金: {args.cash:,.0f}')
    print('-' * 40)
    
    results = cerebro.run()
    strat = results[0]
    
    # 输出结果
    final_value = cerebro.broker.getvalue()
    pnl = final_value - args.cash
    pnl_pct = (pnl / args.cash) * 100
    
    print('-' * 40)
    print(f'最终资金: {final_value:,.2f}')
    print(f'总收益: {pnl:,.2f} ({pnl_pct:+.2f}%)')
    
    # 夏普比率
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', 0)
    if sharpe_ratio:
        print(f'夏普比率: {sharpe_ratio:.3f}')
    
    # 最大回撤
    dd = strat.analyzers.drawdown.get_analysis()
    print(f'最大回撤: {dd.get("max", {}).get("drawdown", 0):.2f}%')
    
    # 交易分析
    trades = strat.analyzers.trades.get_analysis()
    total = trades.get('total', {})
    won = trades.get('won', {})
    lost = trades.get('lost', {})
    
    total_trades = total.get('total', 0)
    won_trades = won.get('total', 0)
    lost_trades = lost.get('total', 0)
    
    if total_trades > 0:
        win_rate = (won_trades / total_trades) * 100
        print(f'交易次数: {total_trades}')
        print(f'胜率: {win_rate:.1f}% ({won_trades}胜/{lost_trades}负)')
        
        # 盈亏比
        avg_won = won.get('pnl', {}).get('average', 0)
        avg_lost = abs(lost.get('pnl', {}).get('average', 0))
        if avg_lost > 0:
            profit_loss_ratio = avg_won / avg_lost
            print(f'平均盈利: {avg_won:.2f}, 平均亏损: {avg_lost:.2f}')
            print(f'盈亏比: {profit_loss_ratio:.2f}')


if __name__ == '__main__':
    main()