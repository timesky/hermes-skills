#!/usr/bin/env python3
"""
策略对比回测 - 五日不破策略 vs 自定义均线策略
同时运行两个策略，对比回测效果

用法:
    python3 strategy_comparison.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
    python3 strategy_comparison.py --code sh.600036 --start 2023-01-01 --end 2026-04-30
"""

import argparse
import backtrader as bt
import baostock as bs
import pandas as pd
from datetime import datetime
from tabulate import tabulate


# ============ 策略1: 五日不破策略 ============
class FiveDayHoldStrategy(bt.Strategy):
    """五日不破策略"""
    
    params = (
        ('stop_loss', 0.10),
        ('initial_position', 0.3),
        ('add_position', 0.3),
    )
    
    def __init__(self):
        self.ma5 = bt.indicators.SMA(self.data.close, period=5)
        self.ma60 = bt.indicators.SMA(self.data.close, period=60)
        self.close = self.data.close
        
        self.order = None
        self.buy_price = None
        self.position_size = 0
        self.days_below_ma5 = 0
        self.days_above_ma5 = 0
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
            else:
                self.buy_price = None
                self.position_size = 0
                self.days_above_ma5 = 0
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        current_close = self.close[0]
        ma5 = self.ma5[0]
        ma60 = self.ma60[0]
        
        if not self.position:
            if current_close > ma60 and current_close > ma5:
                self.days_above_ma5 += 1
                if self.days_above_ma5 >= 2:
                    size = int((self.broker.getcash() * self.params.initial_position) / current_close)
                    if size > 0:
                        self.order = self.buy(size=size)
                        self.position_size = 0.3
            else:
                self.days_above_ma5 = 0
        else:
            if self.buy_price and current_close < self.buy_price * (1 - self.params.stop_loss):
                self.order = self.sell(size=self.position.size)
                return
                
            if current_close > ma5:
                self.days_above_ma5 += 1
                self.days_below_ma5 = 0
                if self.days_above_ma5 >= 2 and self.position_size < 0.6:
                    size = int((self.broker.getcash() * self.params.add_position) / current_close)
                    if size > 0:
                        self.order = self.buy(size=size)
                        self.position_size += 0.3
            else:
                self.days_below_ma5 += 1
                self.days_above_ma5 = 0
                if self.days_below_ma5 >= 2:
                    self.order = self.sell(size=self.position.size)


# ============ 策略2: 自定义均线策略 ============
class CustomMAStrategy(bt.Strategy):
    """自定义均线策略 (MA7/MA22/MA53/MA87)"""
    
    params = (
        ('ma7', 7),
        ('ma22', 22),
        ('ma53', 53),
        ('ma87', 87),
        ('position_pct', 0.5),
    )
    
    def __init__(self):
        self.ma7 = bt.indicators.SMA(self.data.close, period=self.params.ma7)
        self.ma22 = bt.indicators.SMA(self.data.close, period=self.params.ma22)
        self.ma53 = bt.indicators.SMA(self.data.close, period=self.params.ma53)
        self.ma87 = bt.indicators.SMA(self.data.close, period=self.params.ma87)
        self.ma87_slope = bt.indicators.RateOfChange(self.ma87, period=3)
        self.golden_cross = bt.indicators.CrossOver(self.ma7, self.ma22)
        self.volume_ma5 = bt.indicators.SMA(self.data.volume, period=5)
        
        self.order = None
        self.buy_price = None
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
            else:
                self.buy_price = None
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        current_close = self.data.close[0]
        current_volume = self.data.volume[0]
        volume_ratio = current_volume / self.volume_ma5[0] if self.volume_ma5[0] > 0 else 1
        
        ma7 = self.ma7[0]
        ma22 = self.ma22[0]
        ma87 = self.ma87[0]
        ma87_slope_val = self.ma87_slope[0]
        
        if not self.position:
            trend_ok = current_close > ma87 and ma87_slope_val > 0
            cross_ok = self.golden_cross[0] > 0
            volume_ok = 1.2 <= volume_ratio <= 3.0
            
            if trend_ok and cross_ok and volume_ok:
                size = int((self.broker.getcash() * self.params.position_pct) / current_close)
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            if current_close < ma22:
                self.order = self.sell(size=self.position.size)
                return
                
            if self.golden_cross[0] < 0 and current_close < ma22:
                self.order = self.sell(size=self.position.size)
                return
                
            if current_close < ma87 and ma87_slope_val < 0:
                self.order = self.sell(size=self.position.size)
                return


def fetch_data(code, start_date, end_date):
    """从Baostock获取数据"""
    lg = bs.login()
    
    rs = bs.query_history_k_data_plus(
        code,
        'date,open,high,low,close,volume',
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        adjustflag='2'
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
    
    return df


def run_backtest(data_df, strategy_class, strategy_name, cash=100000, commission=0.001):
    """运行单个策略回测"""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)
    
    data = bt.feeds.PandasData(dataname=data_df.copy())
    cerebro.adddata(data)
    
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    results = cerebro.run()
    strat = results[0]
    
    # 提取结果
    final_value = cerebro.broker.getvalue()
    pnl = final_value - cash
    pnl_pct = (pnl / cash) * 100
    
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio') or 0
    
    dd = strat.analyzers.drawdown.get_analysis()
    max_dd = dd.get('max', {}).get('drawdown', 0)
    
    trades = strat.analyzers.trades.get_analysis()
    total = trades.get('total', {})
    won = trades.get('won', {})
    lost = trades.get('lost', {})
    
    total_trades = total.get('total', 0)
    won_trades = won.get('total', 0)
    lost_trades = lost.get('total', 0)
    
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    avg_won = won.get('pnl', {}).get('average', 0) or 0
    avg_lost = abs(lost.get('pnl', {}).get('average', 0) or 0)
    profit_loss_ratio = (avg_won / avg_lost) if avg_lost > 0 else 0
    
    return {
        '策略': strategy_name,
        '总收益': f'{pnl:,.2f}',
        '收益率': f'{pnl_pct:+.2f}%',
        '夏普比率': f'{sharpe_ratio:.3f}',
        '最大回撤': f'{max_dd:.2f}%',
        '交易次数': total_trades,
        '胜率': f'{win_rate:.1f}%',
        '盈亏比': f'{profit_loss_ratio:.2f}',
    }


def main():
    parser = argparse.ArgumentParser(description='策略对比回测')
    parser.add_argument('--code', type=str, required=True, help='股票代码，如 sh.600584')
    parser.add_argument('--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2026-04-30', help='结束日期')
    parser.add_argument('--cash', type=float, default=100000, help='初始资金')
    
    args = parser.parse_args()
    
    print(f'\n{"="*60}')
    print(f'策略对比回测: {args.code}')
    print(f'回测区间: {args.start} ~ {args.end}')
    print(f'初始资金: {args.cash:,.0f}')
    print(f'{"="*60}\n')
    
    # 获取数据
    print('获取数据中...')
    data_df = fetch_data(args.code, args.start, args.end)
    print(f'数据条数: {len(data_df)}')
    print(f'数据范围: {data_df.index[0].date()} ~ {data_df.index[-1].date()}\n')
    
    # 运行两个策略
    print('运行五日不破策略...')
    result1 = run_backtest(data_df, FiveDayHoldStrategy, '五日不破策略', args.cash)
    
    print('运行自定义均线策略...')
    result2 = run_backtest(data_df, CustomMAStrategy, '自定义均线策略', args.cash)
    
    # 输出对比结果
    print(f'\n{"="*60}')
    print('回测结果对比')
    print(f'{"="*60}\n')
    
    results_table = [
        ['指标', '五日不破策略', '自定义均线策略'],
        ['总收益', result1['总收益'], result2['总收益']],
        ['收益率', result1['收益率'], result2['收益率']],
        ['夏普比率', result1['夏普比率'], result2['夏普比率']],
        ['最大回撤', result1['最大回撤'], result2['最大回撤']],
        ['交易次数', result1['交易次数'], result2['交易次数']],
        ['胜率', result1['胜率'], result2['胜率']],
        ['盈亏比', result1['盈亏比'], result2['盈亏比']],
    ]
    
    print(tabulate(results_table, headers='firstrow', tablefmt='grid'))
    
    # 判断哪个策略更好
    r1 = float(result1['收益率'].replace('%', '').replace('+', ''))
    r2 = float(result2['收益率'].replace('%', '').replace('+', ''))
    
    print(f'\n结论: ', end='')
    if r1 > r2:
        print(f'五日不破策略表现更好 ({result1["收益率"]} vs {result2["收益率"]})')
    elif r2 > r1:
        print(f'自定义均线策略表现更好 ({result2["收益率"]} vs {result1["收益率"]})')
    else:
        print('两个策略收益相当')
    
    # 风险提示
    dd1 = float(result1['最大回撤'].replace('%', ''))
    dd2 = float(result2['最大回撤'].replace('%', ''))
    
    if dd1 < dd2:
        print(f'风险: 五日不破策略回撤更小 ({result1["最大回撤"]} vs {result2["最大回撤"]})')
    elif dd2 < dd1:
        print(f'风险: 自定义均线策略回撤更小 ({result2["最大回撤"]} vs {result1["最大回撤"]})')


if __name__ == '__main__':
    main()