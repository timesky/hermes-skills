#!/usr/bin/env python3
"""
五日不破策略完整明细报告
输出：交易流水、月度收益、回撤记录、所有指标原始值

用法:
    python3 five_day_hold_detailed_report.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
"""

import argparse
from datetime import datetime
from pathlib import Path

import backtrader as bt
import baostock as bs
import pandas as pd
import numpy as np


CACHE_DIR = Path.home() / ".hermes/profiles/stock/data/cache"


class TradeRecorder(bt.Analyzer):
    """交易记录分析器 - 记录完整的交易周期"""
    
    def __init__(self):
        self.trades = []
        self.open_positions = []  # 当前持仓列表（可能多次加仓）
        self.trade_id = 0
        self.monthly_values = {}
        self.last_month = None
        
    def notify_order(self, order):
        if order.status in [order.Completed]:
            current_date = self.strategy.data.datetime.date(0)
            
            if order.isbuy():
                # 买入加仓
                self.open_positions.append({
                    'open_date': current_date,
                    'open_price': order.executed.price,
                    'size': order.executed.size,
                    'commission': order.executed.comm,
                })
            else:
                # 卖出平仓 - 合算整个持仓周期
                if self.open_positions:
                    self.trade_id += 1
                    
                    # 计算总持仓成本和数量
                    total_size = sum(p['size'] for p in self.open_positions)
                    total_cost = sum(p['open_price'] * p['size'] for p in self.open_positions)
                    avg_open_price = total_cost / total_size if total_size > 0 else 0
                    first_open_date = min(p['open_date'] for p in self.open_positions)
                    total_commission = sum(p['commission'] for p in self.open_positions) + order.executed.comm
                    
                    # 计算盈亏
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
                    
                    # 清空持仓
                    self.open_positions = []
    
    def next(self):
        # 记录每月末净值
        current_date = self.strategy.data.datetime.date(0)
        month_key = current_date.strftime('%Y-%m')
        value = self.strategy.broker.getvalue()
        
        # 每个月只记录一次（月末）
        if self.last_month != month_key:
            self.monthly_values[month_key] = value
            self.last_month = month_key
        else:
            # 更新为该月最后一天的值
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
            if dd > 3:  # 只记录大于3%的回撤
                current_date = self.strategy.data.datetime.date(0)
                self.drawdown_events.append({
                    'date': current_date,
                    'peak': self.peak,
                    'current': value,
                    'drawdown': dd,
                })
    
    def get_analysis(self):
        return self.drawdown_events


class FiveDayHoldStrategy(bt.Strategy):
    """五日不破策略"""
    
    params = (
        ('stop_loss', 0.10),
        ('ma_stop_pct', 0.02),
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
            if current_close < ma5 * (1 - self.params.ma_stop_pct):
                self.order = self.sell(size=self.position.size)
                return

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


def fetch_data_with_cache(code, start_date, end_date, use_cache=True):
    """带缓存的数据获取"""
    symbol = code.replace('.', '_')
    cache_file = CACHE_DIR / symbol / f"{start_date}_{end_date}.csv"

    if use_cache and cache_file.exists():
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
    parser.add_argument('--no-cache', action='store_true')

    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(FiveDayHoldStrategy)

    data, df_prices = fetch_data_with_cache(
        args.code, args.start, args.end,
        use_cache=not args.no_cache
    )
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
    print(f"五日不破策略完整明细报告")
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
        
        # 交易汇总
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
        # 按月份排序
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
    
    # 波动率
    df_prices['daily_return'] = df_prices['close'].pct_change()
    daily_vol = df_prices['daily_return'].std()
    annual_vol = daily_vol * np.sqrt(252)
    
    # 下行风险
    negative_returns = df_prices['daily_return'][df_prices['daily_return'] < 0]
    downside_risk = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
    
    rf = 0.03
    sortino_ratio = (annual_return - rf) / downside_risk if downside_risk > 0 else 0
    calmar_ratio = annual_return / (max_dd / 100) if max_dd > 0 else 0
    
    # 偏度峰度
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
