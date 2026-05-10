#!/usr/bin/env python3
"""
自定义均线策略完整明细报告
输出：交易流水、月度收益、回撤记录、所有指标原始值

策略说明:
- 来源: 知乎文章《亏了3年才懂：默认均线就是主力陷阱》
- 均线: MA7/MA22/MA53/MA87 组合
- 买入条件: 回调到MA22附近止跌 + 7日金叉22日 + 股价站稳87日线 + 温和放量
- 止损: 跌破MA22

用法:
    python3 custom_ma_detailed_report.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
"""

import argparse
from datetime import datetime
from pathlib import Path

import backtrader as bt
import baostock as bs
import pandas as pd
import numpy as np


CACHE_DIR = Path.home() / ".hermes/profiles/stock/data/cache"


def linear_regression_slope(values, period):
    """线性回归斜率"""
    if len(values) < period:
        return 0
    x = np.arange(period)
    y = np.array(values[-period:])
    slope, intercept = np.polyfit(x, y, 1)
    slope_pct = (slope / y[0]) * 100 if y[0] != 0 else 0
    return slope_pct


class TradeRecorder(bt.Analyzer):
    """交易记录分析器"""
    
    def __init__(self):
        self.trades = []
        self.open_positions = []
        self.trade_id = 0
        self.monthly_values = {}
        self.last_month = None
        
    def notify_order(self, order):
        if order.status in [order.Completed]:
            current_date = self.strategy.data.datetime.date(0)
            
            if order.isbuy():
                self.open_positions.append({
                    'open_date': current_date,
                    'open_price': order.executed.price,
                    'size': order.executed.size,
                    'commission': order.executed.comm,
                })
            else:
                if self.open_positions:
                    self.trade_id += 1
                    total_size = sum(p['size'] for p in self.open_positions)
                    total_cost = sum(p['open_price'] * p['size'] for p in self.open_positions)
                    avg_open_price = total_cost / total_size if total_size > 0 else 0
                    first_open_date = min(p['open_date'] for p in self.open_positions)
                    total_commission = sum(p['commission'] for p in self.open_positions) + order.executed.comm
                    
                    sell_value = order.executed.price * total_size
                    pnl = sell_value - total_cost - total_commission
                    pnl_pct = pnl / total_cost * 100 if total_cost > 0 else 0
                    
                    self.trades.append({
                        'trade_id': self.trade_id,
                        'open_date': first_open_date,
                        'open_price': avg_open_price,
                        'close_date': current_date,
                        'close_price': order.executed.price,
                        'size': total_size,
                        'holding_days': (current_date - first_open_date).days,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'commission': total_commission,
                    })
                    self.open_positions = []
    
    def next(self):
        current_date = self.strategy.data.datetime.date(0)
        month_key = current_date.strftime('%Y-%m')
        value = self.strategy.broker.getvalue()
        
        if self.last_month != month_key:
            self.monthly_values[month_key] = value
            self.last_month = month_key
        else:
            self.monthly_values[month_key] = value
        
    def get_analysis(self):
        return {
            'trades': self.trades,
            'monthly_values': self.monthly_values,
        }


class DrawDownRecorder(bt.Analyzer):
    """回撤记录分析器"""
    
    def __init__(self):
        self.peak = 0
        self.drawdown_events = []
        
    def next(self):
        value = self.strategy.broker.getvalue()
        if value > self.peak:
            self.peak = value
        else:
            dd = (self.peak - value) / self.peak * 100 if self.peak > 0 else 0
            if dd > 3:
                current_date = self.strategy.data.datetime.date(0)
                self.drawdown_events.append({
                    'date': current_date,
                    'peak': self.peak,
                    'current': value,
                    'drawdown': dd,
                })
    
    def get_analysis(self):
        return self.drawdown_events


class CustomMAStrategy(bt.Strategy):
    """自定义均线策略 (MA7/MA22/MA53/MA87)"""
    
    params = (
        ('ma7', 7),
        ('ma22', 22),
        ('ma53', 53),
        ('ma87', 87),
        ('position_pct', 0.5),
        ('slope_period', 22),
        ('slope_threshold', 0.5),
        ('pullback_min', 0.05),
        ('pullback_max', 0.15),
        ('near_ma_threshold', 0.05),
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

    def check_pullback_and_stop_falling(self):
        """检查回调止跌条件"""
        ma22_values = []
        for i in range(self.params.slope_period - 1, -1, -1):
            ma22_values.append(self.ma22[-i])
        
        slope_pct = linear_regression_slope(ma22_values, self.params.slope_period)
        ma22_trending_up = slope_pct > self.params.slope_threshold
        
        high_values = [self.data.high[-i] for i in range(1, 21)]
        recent_high = max(high_values) if high_values else self.data.high[0]
        
        current_close = self.data.close[0]
        current_low = self.data.low[0]
        ma22_val = self.ma22[0]
        
        drawdown_pct = (recent_high - current_close) / recent_high * 100
        distance_to_ma = abs(current_close - ma22_val) / ma22_val
        
        pullback_range_ok = (self.params.pullback_min * 100 <= drawdown_pct <= self.params.pullback_max * 100)
        near_ma22 = distance_to_ma <= self.params.near_ma_threshold
        stopped_falling = current_low >= self.data.low[-1]
        
        is_pullback = ma22_trending_up and pullback_range_ok and near_ma22 and stopped_falling
        
        return is_pullback, slope_pct, drawdown_pct

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
            pullback_ok, slope_pct, drawdown_pct = self.check_pullback_and_stop_falling()
            
            trend_ok = current_close > ma87 and ma87_slope_val > 0
            cross_ok = self.golden_cross[0] > 0
            volume_ok = 1.2 <= volume_ratio <= 3.0
            
            if pullback_ok and trend_ok and cross_ok and volume_ok:
                size = int((self.broker.getcash() * self.params.position_pct) / current_close)
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            if current_close < ma22:
                self.order = self.sell(size=self.position.size)
                return
                
            if current_close < ma87 and ma87_slope_val < 0:
                self.order = self.sell(size=self.position.size)
                return


def fetch_data_with_cache(code, start_date, end_date):
    """带缓存的数据获取"""
    symbol = code.replace('.', '_')
    cache_file = CACHE_DIR / symbol / f"{start_date}_{end_date}.csv"

    if cache_file.exists():
        print(f'读取缓存: {cache_file}')
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    else:
        print(f'下载中: {code} ({start_date} ~ {end_date})')
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

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file)
        print(f'已缓存: {cache_file}')

    return bt.feeds.PandasData(dataname=df), df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', type=str, required=True)
    parser.add_argument('--start', type=str, default='2024-01-01')
    parser.add_argument('--end', type=str, default='2026-04-30')
    parser.add_argument('--cash', type=float, default=100000)
    parser.add_argument('--commission', type=float, default=0.001)

    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(CustomMAStrategy)

    data, df_prices = fetch_data_with_cache(args.code, args.start, args.end)
    cerebro.adddata(data)

    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(commission=args.commission)

    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(TradeRecorder, _name='trade_recorder')
    cerebro.addanalyzer(DrawDownRecorder, _name='dd_recorder')

    results = cerebro.run()
    strat = results[0]
    final_value = cerebro.broker.getvalue()

    # ==================== 输出完整报告 ====================
    
    print("\n" + "=" * 80)
    print(f"自定义均线策略完整明细报告 (MA7/MA22/MA53/MA87)")
    print(f"股票: {args.code}")
    print(f"回测区间: {args.start} ~ {args.end}")
    print("=" * 80)

    # 一、交易流水明细
    print("\n【一、交易流水明细】")
    print("-" * 100)
    
    trade_recorder = strat.analyzers.trade_recorder.get_analysis()
    trades = trade_recorder.get('trades', [])
    
    if trades:
        print(f"{'序号':<4} {'开仓日期':<12} {'开仓价':<10} {'平仓日期':<12} {'平仓价':<10} {'数量':<8} {'持仓天数':<8} {'盈亏额':<12} {'盈亏%':<10} {'手续费':<10}")
        print("-" * 100)
        
        for t in trades:
            print(f"{t['trade_id']:<4} {str(t['open_date']):<12} {t['open_price']:<10.2f} {str(t['close_date']):<12} "
                  f"{t['close_price']:<10.2f} {t['size']:<8.0f} {t['holding_days']:<8} "
                  f"{t['pnl']:<+12.2f} {t['pnl_pct']:<+10.2f}% {t['commission']:<10.2f}")
        
        total_pnl = sum(t['pnl'] for t in trades)
        total_commission = sum(t['commission'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        print("-" * 100)
        print(f"交易汇总: 共{len(trades)}笔 | 盈利{len(wins)}笔 | 亏损{len(losses)}笔 | 总盈亏: {total_pnl:+.2f} | 总手续费: {total_commission:.2f}")
    else:
        print("无交易记录")

    # 二、月度净值与收益
    print("\n\n【二、月度净值与收益】")
    print("-" * 80)
    
    monthly_values = trade_recorder.get('monthly_values', {})
    if monthly_values:
        sorted_months = sorted(monthly_values.keys())
        
        print(f"{'月份':<10} {'期末净值':<15} {'月度收益':<12} {'收益额':<12}")
        print("-" * 80)
        
        prev_value = args.cash
        for month in sorted_months:
            value = monthly_values[month]
            monthly_return = (value - prev_value) / prev_value * 100
            monthly_pnl = value - prev_value
            
            print(f"{month:<10} {value:<15.2f} {monthly_return:<+12.2f}% {monthly_pnl:<+12.2f}")
            prev_value = value

    # 三、回撤记录
    print("\n\n【三、回撤事件记录（>3%）】")
    print("-" * 80)
    
    dd_events = strat.analyzers.dd_recorder.get_analysis()
    if dd_events:
        print(f"{'日期':<12} {'峰值':<15} {'当前值':<15} {'回撤':<10}")
        print("-" * 80)
        
        for event in sorted(dd_events, key=lambda x: x['drawdown'], reverse=True)[:10]:
            print(f"{str(event['date']):<12} {event['peak']:<15.2f} {event['current']:<15.2f} {event['drawdown']:<10.2f}%")
    else:
        print("无显著回撤事件")

    # 四、所有指标原始值
    print("\n\n【四、所有指标原始值】")
    print("-" * 80)
    
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - args.cash) / args.cash
    
    start_dt = pd.to_datetime(args.start)
    end_dt = pd.to_datetime(args.end)
    days = (end_dt - start_dt).days
    trading_days = len(df_prices)
    years = days / 365
    
    annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
    
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', 0) or 0
    
    dd = strat.analyzers.drawdown.get_analysis()
    max_dd = dd.get('max', {}).get('drawdown', 0) or 0
    
    trades_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trades_analysis.get('total', {}).get('total', 0)
    won_trades = trades_analysis.get('won', {}).get('total', 0)
    lost_trades = trades_analysis.get('lost', {}).get('total', 0)
    
    avg_won = trades_analysis.get('won', {}).get('pnl', {}).get('average', 0) or 0
    avg_lost = abs(trades_analysis.get('lost', {}).get('pnl', {}).get('average', 0) or 0)
    
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    profit_loss_ratio = avg_won / avg_lost if avg_lost > 0 else 0
    
    df_prices['daily_return'] = df_prices['close'].pct_change()
    daily_vol = df_prices['daily_return'].std()
    annual_vol = daily_vol * np.sqrt(252)
    
    negative_returns = df_prices['daily_return'][df_prices['daily_return'] < 0]
    downside_risk = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
    
    rf = 0.03
    sortino_ratio = (annual_return - rf) / downside_risk if downside_risk > 0 else 0
    calmar_ratio = annual_return / (max_dd / 100) if max_dd > 0 else 0
    
    returns_clean = df_prices['daily_return'].dropna()
    skewness = returns_clean.skew()
    kurtosis = returns_clean.kurtosis()

    print("\n【收益类指标】")
    print(f"  初始资金: {args.cash:,.0f} 元")
    print(f"  最终资金: {final_value:,.2f} 元")
    print(f"  总收益率: {total_return*100:+.4f}%")
    print(f"  年化收益率: {annual_return*100:+.4f}%")
    
    print("\n【风险类指标】")
    print(f"  最大回撤: {max_dd:.4f}%")
    print(f"  年化波动率: {annual_vol*100:.4f}%")
    print(f"  下行风险: {downside_risk*100:.4f}%")
    
    print("\n【风险调整收益指标】")
    print(f"  夏普比率: {sharpe_ratio:.6f}")
    print(f"  索提诺比率: {sortino_ratio:.6f}")
    print(f"  卡玛比率: {calmar_ratio:.6f}")
    
    print("\n【交易类指标】")
    print(f"  交易次数: {total_trades}")
    print(f"  盈利次数: {won_trades}")
    print(f"  亏损次数: {lost_trades}")
    print(f"  胜率: {win_rate:.4f}%")
    print(f"  平均盈利: {avg_won:.4f} 元")
    print(f"  平均亏损: {avg_lost:.4f} 元")
    print(f"  盈亏比: {profit_loss_ratio:.4f}")
    
    print("\n【稳定性指标】")
    print(f"  收益偏度: {skewness:.6f}")
    print(f"  收益峰度: {kurtosis:.6f}")
    
    print("\n【时间信息】")
    print(f"  回测天数: {days}")
    print(f"  交易日数: {trading_days}")
    print(f"  时间跨度: {years:.4f} 年")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()