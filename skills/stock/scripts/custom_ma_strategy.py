#!/usr/bin/env python3
"""
自定义均线策略 - Backtrader回测实现
来源: 知乎文章《亏了3年才懂：默认均线就是主力陷阱》
策略核心: MA7/MA22/MA53/MA87 组合，避开主力操控

均线参数:
- 7日均线: 短期资金动向线
- 22日均线: 主力洗盘临界线（核心）
- 53日均线: 中期成本均线
- 87日均线: 大趋势判断线

交易规则:
- 买入: 股价站稳87日线上方 + 7日金叉22日 + 温和放量
- 持有: 不破22日线 + 87日线保持向上
- 卖出: 跌破22日线+7日死叉22日 OR 跌破87日线+87日向下拐头
- 止损: 跌破22日均线且当天无法收回

用法:
    python3 custom_ma_strategy.py --code sh.600584 --start 2023-01-01 --end 2026-04-30
"""

import argparse
import backtrader as bt
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime


def linear_regression_slope(values, period):
    """
    对过去period天的值做线性回归，返回百分比斜率
    
    参数:
        values: 数组或列表，最新值在末尾
        period: 回归周期
    
    返回:
        slope_pct: 百分比斜率（相对于起点）
    """
    if len(values) < period:
        return 0
    
    x = np.arange(period)
    y = np.array(values[-period:])
    
    # 线性回归拟合: y = slope * x + intercept
    slope, intercept = np.polyfit(x, y, 1)
    
    # 转换为百分比斜率（相对于起点）
    slope_pct = (slope / y[0]) * 100 if y[0] != 0 else 0
    
    return slope_pct


class CustomMAStrategy(bt.Strategy):
    """自定义均线策略 (MA7/MA22/MA53/MA87)
    
    原文规则（序列条件）：
    1. 先发生回调：股价从高位回落到MA22附近（5%-15%回撤）
    2. 在MA22附近止跌：最低价不再创新低
    3. 随后金叉确认：MA7上穿MA22形成金叉
    """
    
    params = (
        ('ma7', 7),      # 短期资金动向线
        ('ma22', 22),    # 主力洗盘临界线（核心）
        ('ma53', 53),    # 中期成本均线
        ('ma87', 87),    # 大趋势判断线
        ('position_pct', 0.5),  # 每次买入仓位比例
        ('slope_period', 22),   # 斜率计算周期
        ('slope_threshold', 0.5),  # MA22斜率阈值（%）
        ('pullback_min', 0.05),  # 最小回撤幅度
        ('pullback_max', 0.15),  # 最大回撤幅度
        ('near_ma_threshold', 0.05),  # 距离MA22"附近"阈值
    )
    
    def __init__(self):
        # 均线指标
        self.ma7 = bt.indicators.SMA(self.data.close, period=self.params.ma7)
        self.ma22 = bt.indicators.SMA(self.data.close, period=self.params.ma22)
        self.ma53 = bt.indicators.SMA(self.data.close, period=self.params.ma53)
        self.ma87 = bt.indicators.SMA(self.data.close, period=self.params.ma87)
        
        # MA87斜率（判断大趋势）
        self.ma87_slope = bt.indicators.RateOfChange(self.ma87, period=3)
        
        # 金叉/死叉信号
        self.golden_cross = bt.indicators.CrossOver(self.ma7, self.ma22)
        
        # 成交量均线（判断温和放量）
        self.volume_ma5 = bt.indicators.SMA(self.data.volume, period=5)
        
        # 状态追踪
        self.order = None
        self.buy_price = None
        self.entry_date = None
        self.recent_high = None  # 近期最高点
        self.trades_log = []
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.entry_date = self.data.datetime.date(0)
                print(f'买入执行: 价格{order.executed.price:.2f}, '
                      f'成交量比{self.data.volume[0]/self.volume_ma5[0]:.2f}')
            else:
                pnl = order.executed.price - self.buy_price if self.buy_price else 0
                print(f'卖出执行: 价格{order.executed.price:.2f}, 盈亏{pnl:+.2f}')
                self.buy_price = None
                self.entry_date = None
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('订单取消/保证金不足/拒绝')
            
        self.order = None
        
    def check_pullback_and_stop_falling(self):
        """
        检查是否满足"回调到MA22附近止跌"条件
        
        条件序列：
        1. MA22斜率向上（上升趋势未破坏）
        2. 股价从高点回撤到MA22附近（5%-15%回撤）
        3. 止跌信号（最低价不再创新低）
        
        返回:
            tuple: (is_pullback, slope_pct, drawdown_pct)
        """
        # 1. 计算MA22线性回归斜率（22天）
        # 收集过去22天的MA22值
        ma22_values = []
        for i in range(self.params.slope_period - 1, -1, -1):
            ma22_values.append(self.ma22[-i])
        
        slope_pct = linear_regression_slope(ma22_values, self.params.slope_period)
        ma22_trending_up = slope_pct > self.params.slope_threshold
        
        # 2. 从高点回撤判断
        # 找过去20天的最高价
        high_values = [self.data.high[-i] for i in range(1, 21)]
        recent_high = max(high_values) if high_values else self.data.high[0]
        
        current_close = self.data.close[0]
        current_low = self.data.low[0]
        ma22_val = self.ma22[0]
        
        # 回撤幅度
        drawdown_pct = (recent_high - current_close) / recent_high * 100
        
        # 距离MA22的幅度
        distance_to_ma = abs(current_close - ma22_val) / ma22_val
        
        # 判断回撤幅度是否在合理区间（5%-15%）
        pullback_range_ok = (self.params.pullback_min * 100 <= drawdown_pct <= self.params.pullback_max * 100)
        
        # 判断是否在MA22附近
        near_ma22 = distance_to_ma <= self.params.near_ma_threshold
        
        # 3. 止跌信号：今天最低价 >= 昨天最低价
        stopped_falling = current_low >= self.data.low[-1]
        
        # 综合判断
        is_pullback = (
            ma22_trending_up and      # MA22向上
            pullback_range_ok and     # 回撤幅度合理
            near_ma22 and              # 在MA22附近
            stopped_falling           # 止跌
        )
        
        return is_pullback, slope_pct, drawdown_pct
        
    def next(self):
        # 如果有未完成订单，等待
        if self.order:
            return
            
        current_close = self.data.close[0]
        current_volume = self.data.volume[0]
        volume_ratio = current_volume / self.volume_ma5[0] if self.volume_ma5[0] > 0 else 1
        
        ma7 = self.ma7[0]
        ma22 = self.ma22[0]
        ma87 = self.ma87[0]
        ma87_slope_val = self.ma87_slope[0]
        
        # 无持仓情况 - 寻找买入机会
        if not self.position:
            # 前置条件：回调到MA22附近止跌
            pullback_ok, slope_pct, drawdown_pct = self.check_pullback_and_stop_falling()
            
            # 买入条件（序列）:
            # 前置: 回调到MA22附近止跌
            # 1. 大趋势向好: 股价站稳87日均线上方 + 87日线向上（斜率>0）
            # 2. 短期启动确认: 7日金叉22日
            # 3. 温和放量: 成交量比在1.2-3之间
            
            trend_ok = current_close > ma87 and ma87_slope_val > 0
            cross_ok = self.golden_cross[0] > 0  # 7日上穿22日
            volume_ok = 1.2 <= volume_ratio <= 3.0  # 温和放量
            
            # 完整买入条件：前置 + 三项同时满足
            if pullback_ok and trend_ok and cross_ok and volume_ok:
                size = int((self.broker.getcash() * self.params.position_pct) / current_close)
                if size > 0:
                    self.order = self.buy(size=size)
                    print(f'买入信号触发: MA7={ma7:.2f}, MA22={ma22:.2f}, MA87={ma87:.2f}')
                    print(f'  - MA22斜率={slope_pct:.2f}%, 回撤={drawdown_pct:.1f}%')
                    
        # 有持仓情况 - 持有/卖出判断
        else:
            # 止损检查: 收盘价 < MA22（跌破且无法收回）
            if current_close < ma22:
                self.order = self.sell(size=self.position.size)
                print(f'止损触发: 跌破MA22({ma22:.2f}), 当前价{current_close:.2f}')
                return
                
            # 趋势反转: 跌破87日线 + 87日线向下拐头
            if current_close < ma87 and ma87_slope_val < 0:
                self.order = self.sell(size=self.position.size)
                print(f'趋势反转: 跌破MA87({ma87:.2f}) + 斜率向下, 清仓')
                return
                
    def stop(self):
        """策略结束时输出"""
        pnl = self.broker.getvalue() - 100000
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
        adjustflag='1'  # 前复权（统一设置）
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
    parser = argparse.ArgumentParser(description='自定义均线策略回测 (MA7/MA22/MA53/MA87)')
    parser.add_argument('--code', type=str, required=True, help='股票代码，如 sh.600584')
    parser.add_argument('--start', type=str, default='2024-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2026-04-30', help='结束日期')
    parser.add_argument('--cash', type=float, default=100000, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.001, help='手续费率')
    
    args = parser.parse_args()
    
    # 创建回测引擎
    cerebro = bt.Cerebro()
    cerebro.addstrategy(CustomMAStrategy)
    
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
    print(f'\n===== 自定义均线策略回测: {args.code} =====')
    print(f'均线参数: MA7/MA22/MA53/MA87')
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
    else:
        print('无交易记录')


if __name__ == '__main__':
    main()