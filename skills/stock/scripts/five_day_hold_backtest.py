#!/usr/bin/env python3
"""
五日不破策略回测（带缓存）
- 数据本地缓存，避免重复下载
- 详细交易日志，便于验证未来函数

用法:
    python3 five_day_hold_backtest.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import backtrader as bt
import baostock as bs
import pandas as pd


CACHE_DIR = Path.home() / ".hermes/profiles/stock/data/cache"


class FiveDayHoldStrategy(bt.Strategy):
    """五日不破策略"""

    params = (
        ('stop_loss', 0.10),       # 止损比例 10%
        ('ma_stop_pct', 0.02),     # MA5下方2%止损
        ('initial_position', 0.3),  # 初始仓位 30%
        ('add_position', 0.3),     # 加仓比例 30%
        ('trade_log', None),       # 交易日志回调
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

    def log(self, msg, dt=None):
        """记录交易日志"""
        dt = dt or self.data.datetime.date(0)
        if self.params.trade_log:
            self.params.trade_log(f'[{dt}] {msg}')
        print(f'[{dt}] {msg}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                size = self.position.size
                cost = order.executed.comm
                self.log(f'买入执行: 价格{order.executed.price:.2f}, '
                         f'成本{cost:.2f}, 持仓{size}')
            else:
                pnl = 0
                if self.buy_price:
                    pnl = (order.executed.price - self.buy_price) * order.executed.size
                self.log(f'卖出执行: 价格{order.executed.price:.2f}, '
                         f'盈亏{pnl:.2f}')
                self.buy_price = None
                self.position_size = 0
                self.days_above_ma5 = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def next(self):
        # 如果有未完成订单，等待
        if self.order:
            return

        current_date = self.data.datetime.date(0)
        current_close = self.close[0]
        ma5 = self.ma5[0]
        ma60 = self.ma60[0]

        # 关键：打印当天信号判断数据，便于验证未来函数
        # 验证点: ma5包含当天收盘价, 判断是否收盘站稳

        # 无持仓情况
        if not self.position:
            # 条件: 站稳60日线 + 收盘站稳5日线
            if current_close > ma60 and current_close > ma5:
                self.days_above_ma5 += 1
                # 连续2日站稳5日线，买入
                if self.days_above_ma5 >= 2:
                    size = int((self.broker.getcash() * self.params.initial_position) / current_close)
                    if size > 0:
                        self.log(f'买入信号: 收盘{current_close:.2f} > MA5({ma5:.2f}) > MA60({ma60:.2f}), '
                                 f'连续{self.days_above_ma5}日站稳')
                        self.order = self.buy(size=size)
                        self.position_size = 0.3
            else:
                self.days_above_ma5 = 0

        # 有持仓情况
        else:
            # 策略止损: 收盘价 < MA5 * 0.98 (MA5下方2%)
            if current_close < ma5 * (1 - self.params.ma_stop_pct):
                stop_pct = (1 - current_close / ma5) * 100
                self.log(f'触发MA5止损: 收盘{current_close:.2f} < MA5({ma5:.2f})×0.98, '
                         f'下方{stop_pct:.1f}%')
                self.order = self.sell(size=self.position.size)
                return

            # 硬止损: -10%
            if self.buy_price and current_close < self.buy_price * (1 - self.params.stop_loss):
                loss_pct = (1 - current_close / self.buy_price) * 100
                self.log(f'触发硬止损: 买入价{self.buy_price:.2f}, 当前{current_close:.2f}, '
                         f'亏损{loss_pct:.1f}%')
                self.order = self.sell(size=self.position.size)
                return

            # 加仓逻辑: 连续2日站稳5日线
            if current_close > ma5:
                self.days_above_ma5 += 1
                self.days_below_ma5 = 0

                if self.days_above_ma5 >= 2 and self.position_size < 0.6:
                    size = int((self.broker.getcash() * self.params.add_position) / current_close)
                    if size > 0:
                        self.log(f'加仓信号: 连续{self.days_above_ma5}日站稳MA5({ma5:.2f})')
                        self.order = self.buy(size=size)
                        self.position_size += 0.3
            else:
                # 收盘跌破5日线
                self.days_below_ma5 += 1
                self.days_above_ma5 = 0

                # 有效跌破: 连续2日收盘跌破5日线
                if self.days_below_ma5 >= 2:
                    self.log(f'有效跌破5日线: 收盘{current_close:.2f} < MA5({ma5:.2f}), '
                             f'连续{self.days_below_ma5}日')
                    self.order = self.sell(size=self.position.size)

    def stop(self):
        """策略结束时输出"""
        pnl = self.broker.getvalue() - 100000  # 初始资金10万
        self.log(f'======== 策略结束 ========')
        self.log(f'总盈亏: {pnl:.2f} ({pnl/100000*100:+.2f}%)')


def fetch_data_with_cache(code, start_date, end_date, use_cache=True):
    """带缓存的数据获取"""
    # 缓存文件路径
    symbol = code.replace('.', '_')
    cache_file = CACHE_DIR / symbol / f"{start_date}_{end_date}.csv"

    if use_cache and cache_file.exists():
        print(f'读取缓存数据: {cache_file}')
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    else:
        print(f'从Baostock获取数据: {code} ({start_date} ~ {end_date})')
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

        # 保存缓存
        if use_cache:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_file)
            print(f'数据已缓存: {cache_file}')

    return bt.feeds.PandasData(dataname=df)


def main():
    parser = argparse.ArgumentParser(description='五日不破策略回测（带缓存）')
    parser.add_argument('--code', type=str, required=True, help='股票代码，如 sh.600036')
    parser.add_argument('--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2026-04-30', help='结束日期')
    parser.add_argument('--cash', type=float, default=100000, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.001, help='手续费率')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')

    args = parser.parse_args()

    # 确保缓存目录存在
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 创建回测引擎
    cerebro = bt.Cerebro()
    cerebro.addstrategy(FiveDayHoldStrategy)

    # 获取数据（带缓存）
    print(f'\n===== 五日不破策略回测: {args.code} =====')
    data = fetch_data_with_cache(
        args.code,
        args.start,
        args.end,
        use_cache=not args.no_cache
    )
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
    print(f'回测区间: {args.start} ~ {args.end}')
    print(f'初始资金: {args.cash:,.0f}')
    print('-' * 60)

    results = cerebro.run()
    strat = results[0]

    # 输出结果
    final_value = cerebro.broker.getvalue()
    pnl = final_value - args.cash
    pnl_pct = (pnl / args.cash) * 100

    print('-' * 60)
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
