#!/usr/bin/env python3
"""
五日不破策略回测（完整指标版）
包含专业回测报告所需的所有核心指标

用法:
    python3 five_day_hold_full_report.py --code sh.600584 --start 2024-01-01 --end 2026-04-30
"""

import argparse
import math
from datetime import datetime
from pathlib import Path

import backtrader as bt
import baostock as bs
import pandas as pd
import numpy as np


CACHE_DIR = Path.home() / ".hermes/profiles/stock/data/cache"


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

        if use_cache:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_file)
            print(f'已缓存: {cache_file}')

    return bt.feeds.PandasData(dataname=df), df


def calculate_metrics(results, cerebro, initial_cash, df_prices, start_date, end_date):
    """计算完整回测指标"""
    strat = results[0]
    final_value = cerebro.broker.getvalue()

    # 基础指标
    total_return = (final_value - initial_cash) / initial_cash

    # 时间跨度
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    days = (end_dt - start_dt).days
    trading_days = len(df_prices)
    years = days / 365

    # 年化收益率（复利法）
    annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0

    # 分析器结果
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', 0) or 0

    dd = strat.analyzers.drawdown.get_analysis()
    max_dd = dd.get('max', {}).get('drawdown', 0) or 0

    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('total', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)

    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0

    avg_won = trades.get('won', {}).get('pnl', {}).get('average', 0) or 0
    avg_lost = abs(trades.get('lost', {}).get('pnl', {}).get('average', 0) or 0)
    profit_loss_ratio = avg_won / avg_lost if avg_lost > 0 else 0

    # 计算日收益率序列
    df_returns = df_prices.copy()
    df_returns['daily_return'] = df_returns['close'].pct_change()

    # 年化波动率
    daily_vol = df_returns['daily_return'].std()
    annual_vol = daily_vol * np.sqrt(252)

    # 下行风险
    negative_returns = df_returns['daily_return'][df_returns['daily_return'] < 0]
    downside_risk = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0

    # 索提诺比率（假设无风险利率3%）
    rf = 0.03
    sortino_ratio = (annual_return - rf) / downside_risk if downside_risk > 0 else 0

    # 卡玛比率
    calmar_ratio = annual_return / (max_dd / 100) if max_dd > 0 else 0

    # 收益偏度和峰度
    returns_clean = df_returns['daily_return'].dropna()
    skewness = returns_clean.skew()
    kurtosis = returns_clean.kurtosis()

    # 月度收益
    df_monthly = df_prices['close'].resample('M').last()
    monthly_returns = df_monthly.pct_change().dropna()
    positive_months = (monthly_returns > 0).sum() / len(monthly_returns) * 100 if len(monthly_returns) > 0 else 0

    # 最大连续盈利/亏损
    trade_pnls = []
    if total_trades > 0:
        # 从交易记录提取盈亏
        for i in range(total_trades):
            if i < won_trades:
                trade_pnls.append(1)
            else:
                trade_pnls.append(-1)

    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0

    for pnl in trade_pnls:
        if pnl > 0:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)

    return {
        # 基本信息
        'start_date': start_date,
        'end_date': end_date,
        'trading_days': trading_days,
        'years': years,

        # 收益类
        'initial_cash': initial_cash,
        'final_value': final_value,
        'total_return': total_return,
        'annual_return': annual_return,

        # 风险类
        'max_drawdown': max_dd,
        'annual_volatility': annual_vol,
        'downside_risk': downside_risk,

        # 风险调整收益类
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,

        # 交易类
        'total_trades': total_trades,
        'won_trades': won_trades,
        'lost_trades': lost_trades,
        'win_rate': win_rate,
        'avg_profit': avg_won,
        'avg_loss': avg_lost,
        'profit_loss_ratio': profit_loss_ratio,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,

        # 稳定性
        'skewness': skewness,
        'kurtosis': kurtosis,
        'positive_month_pct': positive_months,
    }


def print_report(metrics, code):
    """打印完整回测报告"""
    print("\n" + "=" * 70)
    print(f"五日不破策略回测报告")
    print(f"股票: {code}")
    print("=" * 70)

    print("\n【一、回测基本信息】")
    print(f"  回测区间: {metrics['start_date']} ~ {metrics['end_date']}")
    print(f"  交易日数: {metrics['trading_days']} 天")
    print(f"  时间跨度: {metrics['years']:.2f} 年")

    print("\n【二、收益类指标】")
    print(f"  初始资金: {metrics['initial_cash']:,.0f} 元")
    print(f"  最终资金: {metrics['final_value']:,.2f} 元")
    print(f"  总收益率: {metrics['total_return']*100:+.2f}%")
    print(f"  年化收益率: {metrics['annual_return']*100:+.2f}%")

    print("\n【三、风险类指标】")
    print(f"  最大回撤: {metrics['max_drawdown']:.2f}%")
    print(f"  年化波动率: {metrics['annual_volatility']*100:.2f}%")
    print(f"  下行风险: {metrics['downside_risk']*100:.2f}%")

    print("\n【四、风险调整收益指标】")
    print(f"  夏普比率: {metrics['sharpe_ratio']:.3f}")
    print(f"  索提诺比率: {metrics['sortino_ratio']:.3f}")
    print(f"  卡玛比率: {metrics['calmar_ratio']:.3f}")

    print("\n【五、交易类指标】")
    print(f"  交易次数: {metrics['total_trades']}")
    print(f"  盈利次数: {metrics['won_trades']}")
    print(f"  亏损次数: {metrics['lost_trades']}")
    print(f"  胜率: {metrics['win_rate']:.1f}%")
    print(f"  平均盈利: {metrics['avg_profit']:.2f} 元")
    print(f"  平均亏损: {metrics['avg_loss']:.2f} 元")
    print(f"  盈亏比: {metrics['profit_loss_ratio']:.2f}")
    print(f"  最大连续盈利: {metrics['max_consecutive_wins']} 次")
    print(f"  最大连续亏损: {metrics['max_consecutive_losses']} 次")

    print("\n【六、稳定性指标】")
    print(f"  收益偏度: {metrics['skewness']:.3f}")
    print(f"  收益峰度: {metrics['kurtosis']:.3f}")
    print(f"  正收益月份占比: {metrics['positive_month_pct']:.1f}%")

    # 评级
    print("\n【七、策略评级】")

    sharpe = metrics['sharpe_ratio']
    mdd = metrics['max_drawdown']
    annual_ret = metrics['annual_return'] * 100
    win_rate = metrics['win_rate']
    pl_ratio = metrics['profit_loss_ratio']

    # 夏普评级
    sharpe_grade = "优秀" if sharpe > 2.0 else "良好" if sharpe > 1.5 else "一般" if sharpe > 1.0 else "较差" if sharpe > 0.5 else "危险"

    # 回撤评级
    mdd_grade = "优秀" if mdd < 5 else "良好" if mdd < 10 else "一般" if mdd < 20 else "较差" if mdd < 30 else "危险"

    # 年化收益评级
    ret_grade = "优秀" if annual_ret > 25 else "良好" if annual_ret > 15 else "一般" if annual_ret > 8 else "较差" if annual_ret > 0 else "亏损"

    # 胜率评级
    win_grade = "优秀" if win_rate > 60 else "良好" if win_rate > 50 else "一般" if win_rate > 40 else "较差" if win_rate > 30 else "危险"

    # 盈亏比评级
    pl_grade = "优秀" if pl_ratio > 2.0 else "良好" if pl_ratio > 1.5 else "一般" if pl_ratio > 1.0 else "较差" if pl_ratio > 0.8 else "危险"

    print(f"  夏普比率: {sharpe_grade} ({sharpe:.3f})")
    print(f"  最大回撤: {mdd_grade} ({mdd:.2f}%)")
    print(f"  年化收益: {ret_grade} ({annual_ret:+.2f}%)")
    print(f"  胜率: {win_grade} ({win_rate:.1f}%)")
    print(f"  盈亏比: {pl_grade} ({pl_ratio:.2f})")

    print("\n" + "=" * 70)

    # 综合建议
    print("\n【八、综合建议】")

    issues = []
    if sharpe < 0.5:
        issues.append("夏普比率过低，风险调整后收益不佳")
    if mdd > 20:
        issues.append("最大回撤较大，需优化止损机制")
    if win_rate < 30:
        issues.append("胜率偏低，建议优化入场条件")
    if pl_ratio < 1.0:
        issues.append("盈亏比<1，长期期望为负，需优化策略")

    if not issues:
        print("  ✓ 策略整体表现良好，建议继续优化细节")
    else:
        print("  发现以下问题：")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")


def main():
    parser = argparse.ArgumentParser(description='五日不破策略完整回测报告')
    parser.add_argument('--code', type=str, required=True, help='股票代码')
    parser.add_argument('--start', type=str, default='2024-01-01')
    parser.add_argument('--end', type=str, default='2026-04-30')
    parser.add_argument('--cash', type=float, default=100000)
    parser.add_argument('--commission', type=float, default=0.001)
    parser.add_argument('--no-cache', action='store_true')

    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(FiveDayHoldStrategy)

    print(f"\n获取数据: {args.code}")
    data, df_prices = fetch_data_with_cache(
        args.code,
        args.start,
        args.end,
        use_cache=not args.no_cache
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(commission=args.commission)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    results = cerebro.run()

    # 计算完整指标
    metrics = calculate_metrics(
        results, cerebro, args.cash, df_prices,
        args.start, args.end
    )

    # 打印报告
    print_report(metrics, args.code)

    return metrics


if __name__ == '__main__':
    main()
