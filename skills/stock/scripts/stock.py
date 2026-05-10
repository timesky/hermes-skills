#!/usr/bin/env python3
"""Stock CLI helper — A股量化分析工具

Usage:
    # 实时行情 (pytdx秒级数据)
    python3 stock.py quote 000001
    python3 stock.py quote 600000
    
    # 历史K线 (Baostock)
    python3 stock.py history 000001 --start 20240101 --end 20241231
    
    # 指数查询
    python3 stock.py index sh000001
    
    # 涨幅榜
    python3 stock.py trending --limit 20
    
    # 搜索股票
    python3 stock.py search 平安
    
    # 策略回测 (Backtrader)
    python3 stock.py backtest 000001 --fast 5 --slow 20
    
    # 技术指标
    python3 stock.py indicator 000001 --ma 5,10,20 --rsi 14

数据源: pytdx(实时) + Baostock(历史) + AkShare(补充)
"""

import sys
import datetime
import argparse

# 数据源导入
try:
    from pytdx.hq import TdxHq_API
    PYTDX_AVAILABLE = True
except ImportError:
    PYTDX_AVAILABLE = False

try:
    import baostock as bs
    BOSTOCK_AVAILABLE = True
except ImportError:
    BOSTOCK_AVAILABLE = False

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

try:
    import backtrader as bt
    import pandas as pd
    BACKTRADER_AVAILABLE = True
except ImportError:
    BACKTRADER_AVAILABLE = False

# 通达信服务器列表
TDX_SERVERS = [
    ('119.147.212.81', 7709),
    ('218.75.126.9', 7709),
    ('115.238.56.198', 7709),
    ('106.14.95.149', 7709),
    ('180.153.39.51', 7709),
]

# 市场代码映射
MARKET_SH = 1  # 上海
MARKET_SZ = 0  # 深圳


def _fmt_price(price) -> str:
    """格式化价格"""
    try:
        return f"{float(price):.2f}"
    except (ValueError, TypeError):
        return str(price)


def _fmt_pct(pct) -> str:
    """格式化百分比"""
    try:
        p = float(pct)
        return f"{'+' if p > 0 else ''}{p:.2f}%"
    except (ValueError, TypeError):
        return str(pct)


def _fmt_volume(vol) -> str:
    """格式化成交量"""
    try:
        v = float(vol)
        if v >= 100_000_000:
            return f"{v / 100_000_000:.2f}亿"
        if v >= 10_000_000:
            return f"{v / 10_000_000:.1f}千万"
        if v >= 10_000:
            return f"{v / 10_000:.1f}万"
        return f"{v:.0f}"
    except (ValueError, TypeError):
        return str(vol)


def _get_market(code: str) -> int:
    """根据股票代码判断市场"""
    code = code.zfill(6)
    if code.startswith(('6', '5', '9')):
        return MARKET_SH
    return MARKET_SZ


def _connect_tdx():
    """连接通达信服务器"""
    if not PYTDX_AVAILABLE:
        return None, "pytdx未安装"
    
    api = TdxHq_API()
    for host, port in TDX_SERVERS:
        try:
            if api.connect(host, port, time_out=5):
                return api, f"{host}:{port}"
        except Exception:
            continue
    return None, "无法连接任何服务器"


def cmd_quote(symbol: str):
    """查询实时行情 (pytdx)"""
    print(f"\n=== {symbol} 实时行情 (pytdx) ===\n")
    
    if not PYTDX_AVAILABLE:
        print("错误: pytdx未安装。运行: pip3 install pytdx")
        return
    
    api, server = _connect_tdx()
    if api is None:
        print(f"连接失败: {server}")
        return
    
    try:
        market = _get_market(symbol)
        code = symbol.zfill(6)
        
        # 获取实时行情
        quotes = api.get_security_quotes([(market, code)])
        if not quotes:
            print(f"未找到股票: {symbol}")
            return
        
        q = quotes[0]
        print(f"代码: {q['code']}")
        print(f"当前价: {_fmt_price(q['price'])}")
        
        # 计算涨跌幅
        if q['last_close'] and q['last_close'] > 0:
            pct = (q['price'] - q['last_close']) / q['last_close'] * 100
            print(f"涨跌幅: {_fmt_pct(pct)}")
            print(f"涨跌额: {_fmt_price(q['price'] - q['last_close'])}")
        
        print(f"今开: {_fmt_price(q['open'])}")
        print(f"最高: {_fmt_price(q['high'])}")
        print(f"最低: {_fmt_price(q['low'])}")
        print(f"昨收: {_fmt_price(q['last_close'])}")
        print(f"成交量: {_fmt_volume(q['vol'] * 100)}")  # pytdx单位是手
        print(f"成交额: {_fmt_volume(q['amount'])}")
        print(f"\n[服务器: {server}]")
        
    finally:
        api.disconnect()


def cmd_history(symbol: str, start: str = None, end: str = None):
    """查询历史K线 (Baostock)"""
    if start is None:
        start = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    if end is None:
        end = datetime.date.today().strftime("%Y-%m-%d")
    
    print(f"\n=== {symbol} 历史K线 (Baostock) ===")
    print(f"周期: {start} ~ {end}\n")
    
    if not BOSTOCK_AVAILABLE:
        print("错误: baostock未安装。运行: pip3 install baostock")
        return
    
    # 登录Baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return
    
    try:
        # 确定市场代码
        code = symbol.zfill(6)
        bs_code = f"sh.{code}" if code.startswith(('6', '5', '9')) else f"sz.{code}"
        
        # 获取数据
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="3"  # 不复权
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            print(f"未找到数据: {symbol}")
            return
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 显示最近20条
        print("日期       | 开盘    | 最高    | 最低    | 收盘    | 成交量")
        print("-" * 60)
        
        for _, row in df.tail(20).iterrows():
            print(f"{row['date']} | {_fmt_price(row['open']):>7} | {_fmt_price(row['high']):>7} | {_fmt_price(row['low']):>7} | {_fmt_price(row['close']):>7} | {_fmt_volume(row['volume'])}")
        
        print(f"\n共 {len(df)} 条记录")
        
    finally:
        bs.logout()


def cmd_index(code: str):
    """查询指数行情"""
    print(f"\n=== {code} 指数行情 ===\n")
    
    # 使用AkShare获取指数数据
    if AKSHARE_AVAILABLE:
        try:
            index_map = {
                "sh000001": ("000001", "上证指数"),
                "sz399001": ("399001", "深证成指"),
                "sh000300": ("000300", "沪深300"),
                "sz399006": ("399006", "创业板指"),
                "sh000016": ("000016", "上证50"),
                "sh000905": ("000905", "中证500"),
            }
            
            if code.lower() in index_map:
                symbol, name = index_map[code.lower()]
                df = ak.stock_zh_index_daily(symbol=f"sh{symbol}" if symbol.startswith('0') else f"sz{symbol}")
                recent = df.tail(1).iloc[0]
                
                print(f"指数: {name}")
                print(f"代码: {code}")
                print(f"收盘: {_fmt_price(recent['close'])}")
                print(f"最高: {_fmt_price(recent['high'])}")
                print(f"最低: {_fmt_price(recent['low'])}")
                print(f"成交量: {_fmt_volume(recent['volume'])}")
                return
        except Exception as e:
            print(f"AkShare查询失败: {e}")
    
    # 回退到Baostock
    if BOSTOCK_AVAILABLE:
        lg = bs.login()
        try:
            rs = bs.query_history_k_data_plus(
                code.lower(),
                "date,code,open,high,low,close,volume",
                start_date=(datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
                end_date=datetime.date.today().strftime("%Y-%m-%d"),
                frequency="d"
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                recent = df.tail(1).iloc[0]
                print(f"指数: {code}")
                print(f"收盘: {_fmt_price(recent['close'])}")
                print(f"最高: {_fmt_price(recent['high'])}")
                print(f"最低: {_fmt_price(recent['low'])}")
                return
        finally:
            bs.logout()
    
    print(f"查询指数失败")


def cmd_trending(limit: int = 20):
    """A股涨幅榜"""
    print(f"\n=== A股涨幅榜 Top {limit} ===\n")
    
    if not PYTDX_AVAILABLE:
        print("错误: pytdx未安装")
        return
    
    api, server = _connect_tdx()
    if api is None:
        print(f"连接失败: {server}")
        return
    
    try:
        # 获取涨幅榜 (深圳+上海)
        all_stocks = []
        
        # 深圳市场
        sz_count = api.get_security_count(MARKET_SZ)
        if sz_count > 0:
            sz_stocks = api.get_security_list(MARKET_SZ, 0, min(2000, sz_count))
            all_stocks.extend(sz_stocks)
        
        # 上海市场
        sh_count = api.get_security_count(MARKET_SH)
        if sh_count > 0:
            sh_stocks = api.get_security_list(MARKET_SH, 0, min(2000, sh_count))
            all_stocks.extend(sh_stocks)
        
        # 获取实时行情并排序
        if all_stocks:
            # 取前200只获取实时行情
            codes = [(s['market'], s['code']) for s in all_stocks[:200]]
            quotes = api.get_security_quotes(codes)
            
            if quotes:
                # 按涨跌幅排序
                sorted_quotes = sorted(quotes, key=lambda x: x['price'] - x['last_close'] if x['last_close'] > 0 else 0, reverse=True)
                
                print("代码     | 名称           | 当前价  | 涨跌幅")
                print("-" * 55)
                
                for q in sorted_quotes[:limit]:
                    if q['last_close'] and q['last_close'] > 0:
                        pct = (q['price'] - q['last_close']) / q['last_close'] * 100
                        print(f"{q['code']} | {q.get('name', 'N/A')[:8]:<8} | {_fmt_price(q['price']):>7} | {_fmt_pct(pct):>7}")
        
        print(f"\n[服务器: {server}]")
        
    finally:
        api.disconnect()


def cmd_search(keyword: str):
    """搜索股票"""
    print(f"\n=== 搜索: {keyword} ===\n")
    
    if not PYTDX_AVAILABLE:
        print("错误: pytdx未安装")
        return
    
    api, server = _connect_tdx()
    if api is None:
        print(f"连接失败: {server}")
        return
    
    try:
        all_stocks = []
        
        # 获取股票列表
        for market in [MARKET_SZ, MARKET_SH]:
            count = api.get_security_count(market)
            if count > 0:
                stocks = api.get_security_list(market, 0, min(2000, count))
                all_stocks.extend(stocks)
        
        # 搜索
        keyword_upper = keyword.upper()
        matches = [s for s in all_stocks if keyword_upper in s['code'] or keyword in s.get('name', '')]
        
        if not matches:
            print(f"未找到匹配 '{keyword}' 的股票")
            return
        
        print(f"找到 {len(matches)} 个结果:\n")
        print("代码     | 名称")
        print("-" * 30)
        
        for s in matches[:20]:
            print(f"{s['code']} | {s.get('name', 'N/A')}")
        
        if len(matches) > 20:
            print(f"\n... 还有 {len(matches) - 20} 个结果")
        
    finally:
        api.disconnect()


def cmd_backtest(symbol: str, fast: int = 5, slow: int = 20, start: str = None, end: str = None):
    """双均线策略回测"""
    print(f"\n=== 双均线策略回测 ===")
    print(f"标的: {symbol}")
    print(f"快线: {fast}日  慢线: {slow}日\n")
    
    if not BACKTRADER_AVAILABLE:
        print("错误: backtrader未安装。运行: pip3 install backtrader")
        return
    
    if not BOSTOCK_AVAILABLE:
        print("错误: baostock未安装。运行: pip3 install baostock")
        return
    
    if start is None:
        start = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    if end is None:
        end = datetime.date.today().strftime("%Y-%m-%d")
    
    # 定义策略
    class MaCrossStrategy(bt.Strategy):
        params = (('fast', fast), ('slow', slow))
        
        def __init__(self):
            self.ma_fast = bt.indicators.SMA(self.data.close, period=self.p.fast)
            self.ma_slow = bt.indicators.SMA(self.data.close, period=self.p.slow)
            self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)
            self.order = None
            self.buy_price = None
            self.buy_comm = None
            self.trades = []
        
        def next(self):
            if self.order:
                return
            
            if self.crossover > 0:  # 金叉
                if not self.position:
                    self.order = self.buy()
            
            elif self.crossover < 0:  # 死叉
                if self.position:
                    self.order = self.sell()
        
        def notify_order(self, order):
            if order.status in [order.Completed]:
                if order.isbuy():
                    self.buy_price = order.executed.price
                    self.buy_comm = order.executed.comm
                self.order = None
        
        def notify_trade(self, trade):
            if trade.isclosed:
                self.trades.append(trade)
    
    # 获取数据
    lg = bs.login()
    try:
        code = symbol.zfill(6)
        bs_code = f"sh.{code}" if code.startswith(('6', '5', '9')) else f"sz.{code}"
        
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="2"  # 前复权
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            print(f"未找到数据: {symbol}")
            return
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 数据类型转换
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 创建Backtrader数据源
        data = bt.feeds.PandasData(dataname=df)
        
        # 创建回测引擎
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(MaCrossStrategy)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0003)  # 万三佣金
        
        # 运行回测
        initial_value = cerebro.broker.getvalue()
        cerebro.run()
        final_value = cerebro.broker.getvalue()
        
        # 计算结果
        pnl = final_value - initial_value
        pnl_pct = pnl / initial_value * 100
        
        print("回测结果:")
        print(f"  初始资金: {initial_value:,.2f}")
        print(f"  最终资金: {final_value:,.2f}")
        print(f"  收益: {pnl:,.2f} ({_fmt_pct(pnl_pct)})")
        print(f"  数据周期: {start} ~ {end}")
        print(f"  交易日数: {len(df)}")
        
    finally:
        bs.logout()


def cmd_indicator(symbol: str, ma: str = "5,10,20", rsi_period: int = 14):
    """计算技术指标"""
    print(f"\n=== {symbol} 技术指标 ===\n")
    
    if not BOSTOCK_AVAILABLE:
        print("错误: baostock未安装")
        return
    
    # 获取历史数据
    lg = bs.login()
    try:
        code = symbol.zfill(6)
        bs_code = f"sh.{code}" if code.startswith(('6', '5', '9')) else f"sz.{code}"
        
        end = datetime.date.today().strftime("%Y-%m-%d")
        start = (datetime.date.today() - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
        
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="2"
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            print(f"未找到数据: {symbol}")
            return
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算MA
        ma_periods = [int(x) for x in ma.split(',')]
        for period in ma_periods:
            df[f'MA{period}'] = df['close'].rolling(window=period).mean()
        
        # 计算RSI
        def calc_rsi(series, period):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        df['RSI'] = calc_rsi(df['close'], rsi_period)
        
        # 显示最近10天的数据
        recent = df.tail(10)
        
        print(f"日期       | 收盘   |", end="")
        for p in ma_periods:
            print(f" MA{p}  |", end="")
        print(f" RSI{rsi_period}")
        print("-" * 70)
        
        for _, row in recent.iterrows():
            print(f"{row['date']} | {_fmt_price(row['close']):>6} |", end="")
            for p in ma_periods:
                val = row.get(f'MA{p}')
                print(f" {_fmt_price(val) if pd.notna(val) else 'N/A':>6} |", end="")
            rsi_val = row.get('RSI')
            print(f" {_fmt_price(rsi_val) if pd.notna(rsi_val) else 'N/A':>6}")
        
        # 当前指标状态
        latest = df.iloc[-1]
        print(f"\n当前状态:")
        print(f"  收盘价: {_fmt_price(latest['close'])}")
        for p in ma_periods:
            val = latest.get(f'MA{p}')
            if pd.notna(val):
                trend = "上涨" if latest['close'] > val else "下跌"
                print(f"  MA{p}: {_fmt_price(val)} (价格在均线上方={latest['close'] > val})")
        
        rsi_val = latest.get('RSI')
        if pd.notna(rsi_val):
            if rsi_val > 70:
                rsi_status = "超买"
            elif rsi_val < 30:
                rsi_status = "超卖"
            else:
                rsi_status = "中性"
            print(f"  RSI{rsi_period}: {_fmt_price(rsi_val)} ({rsi_status})")
        
    finally:
        bs.logout()


def main():
    parser = argparse.ArgumentParser(description="A股量化分析工具", formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # quote命令
    subparsers.add_parser("quote", help="查询实时行情").add_argument("symbol", help="股票代码")
    
    # history命令
    hist_parser = subparsers.add_parser("history", help="查询历史K线")
    hist_parser.add_argument("symbol", help="股票代码")
    hist_parser.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    hist_parser.add_argument("--end", help="结束日期 (YYYY-MM-DD)")
    
    # index命令
    subparsers.add_parser("index", help="查询指数").add_argument("code", help="指数代码")
    
    # trending命令
    trend_parser = subparsers.add_parser("trending", help="A股涨幅榜")
    trend_parser.add_argument("--limit", type=int, default=20, help="显示数量")
    
    # search命令
    subparsers.add_parser("search", help="搜索股票").add_argument("keyword", help="关键词")
    
    # backtest命令
    bt_parser = subparsers.add_parser("backtest", help="策略回测")
    bt_parser.add_argument("symbol", help="股票代码")
    bt_parser.add_argument("--fast", type=int, default=5, help="快均线周期")
    bt_parser.add_argument("--slow", type=int, default=20, help="慢均线周期")
    bt_parser.add_argument("--start", help="开始日期")
    bt_parser.add_argument("--end", help="结束日期")
    
    # indicator命令
    ind_parser = subparsers.add_parser("indicator", help="技术指标")
    ind_parser.add_argument("symbol", help="股票代码")
    ind_parser.add_argument("--ma", default="5,10,20", help="MA周期 (逗号分隔)")
    ind_parser.add_argument("--rsi", type=int, default=14, help="RSI周期")
    
    args = parser.parse_args()
    
    if args.command == "quote":
        cmd_quote(args.symbol)
    elif args.command == "history":
        cmd_history(args.symbol, args.start, args.end)
    elif args.command == "index":
        cmd_index(args.code)
    elif args.command == "trending":
        cmd_trending(args.limit)
    elif args.command == "search":
        cmd_search(args.keyword)
    elif args.command == "backtest":
        cmd_backtest(args.symbol, args.fast, args.slow, args.start, args.end)
    elif args.command == "indicator":
        cmd_indicator(args.symbol, args.ma, args.rsi)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()