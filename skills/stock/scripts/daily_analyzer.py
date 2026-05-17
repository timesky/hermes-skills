#!/usr/bin/env python3
"""每日股票分析器 - 支持数据缓存和增量更新

Usage:
    # 每日分析（自动判断全量/增量）
    python3 daily_analyzer.py analyze 600584
    
    # 强制全量更新
    python3 daily_analyzer.py analyze 600584 --full
    
    # 查看缓存状态
    python3 daily_analyzer.py status 600584
    
    # 清理缓存
    python3 daily_analyzer.py clean 600584

数据源:
    - 日线K线: Baostock
    - 财报数据: AkShare
    - 基本面: AkShare
    - 交易日历: AkShare
"""

import sys
import os
import json
import csv
import datetime
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

# 数据源
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
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# 缓存目录
CACHE_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "cache"
TRADE_CALENDAR_FILE = Path.home() / ".hermes" / "profiles" / "stock" / "data" / "trade_calendar.csv"

# ============== 格式化函数 ==============

def fmt_price(price) -> str:
    try:
        return f"{float(price):.2f}"
    except:
        return str(price)

def fmt_pct(pct) -> str:
    try:
        p = float(pct)
        return f"{'+' if p > 0 else ''}{p:.2f}%"
    except:
        return str(pct)

def fmt_volume(vol) -> str:
    try:
        v = float(vol)
        if v >= 1e8:
            return f"{v/1e8:.2f}亿"
        if v >= 1e4:
            return f"{v/1e4:.2f}万"
        return f"{v:.0f}"
    except:
        return str(vol)

def fmt_amount(val) -> str:
    """格式化金额（元->万元或亿元）"""
    try:
        v = float(val)
        if v >= 1e8:
            return f"{v/1e8:.2f}亿"
        if v >= 1e4:
            return f"{v/1e4:.2f}万"
        return f"{v:.0f}元"
    except:
        return str(val)

# ============== 交易日历 ==============

def get_trade_calendar(force_update: bool = False) -> List[str]:
    """获取交易日历（缓存到本地）"""
    
    # 检查缓存（保留30天）
    if TRADE_CALENDAR_FILE.exists() and not force_update:
        cache_age = (datetime.date.today() - datetime.date.fromtimestamp(TRADE_CALENDAR_FILE.stat().st_mtime)).days
        if cache_age < 30:
            dates = []
            with open(TRADE_CALENDAR_FILE, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过表头
                for row in reader:
                    if row:
                        dates.append(row[0])
            return dates
    
    # 从AkShare获取
    if not AKSHARE_AVAILABLE:
        print("警告: AkShare未安装，无法获取交易日历")
        return []
    
    try:
        print("正在更新交易日历...")
        df = ak.tool_trade_date_hist_sina()
        dates = df['trade_date'].astype(str).tolist()
        
        # 保存到本地
        TRADE_CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRADE_CALENDAR_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['trade_date'])
            for d in dates:
                writer.writerow([d])
        
        print(f"交易日历已更新: {len(dates)}个交易日")
        return dates
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        return []

def is_trade_day(date: datetime.date, calendar: List[str] = None) -> bool:
    """判断是否为交易日"""
    if calendar is None:
        calendar = get_trade_calendar()
    return date.strftime("%Y-%m-%d") in calendar

def get_last_trade_day(calendar: List[str] = None) -> str:
    """获取最近一个交易日"""
    if calendar is None:
        calendar = get_trade_calendar()
    
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    # 如果今天在交易日历中且已收盘（假设在15:30后运行）
    if today_str in calendar:
        now = datetime.datetime.now()
        if now.hour >= 15 and now.minute >= 30:
            return today_str
    
    # 找最近的交易日
    for d in reversed(calendar):
        if d <= today_str:
            return d
    
    return calendar[-1] if calendar else today_str

# ============== 数据获取 ==============

def get_stock_list_date(symbol: str) -> str:
    """获取股票上市日期"""
    if not AKSHARE_AVAILABLE:
        return None
    
    try:
        # 使用东方财富股票信息接口
        df = ak.stock_individual_info_em(symbol=symbol)
        for _, row in df.iterrows():
            if '上市时间' in row['item'] or '上市日期' in row['item']:
                return row['value']
        return None
    except Exception as e:
        print(f"获取上市日期失败: {e}")
        return None

def fetch_daily_kline(symbol: str, start: str, end: str) -> pd.DataFrame:
    """获取日线K线数据（Baostock）"""
    if not BOSTOCK_AVAILABLE:
        raise RuntimeError("Baostock未安装")
    
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"Baostock登录失败: {lg.error_msg}")
    
    try:
        code = symbol.zfill(6)
        bs_code = f"sh.{code}" if code.startswith(('6', '5', '9')) else f"sz.{code}"
        
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,turn",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag='1'  # 前复权（统一设置）
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 类型转换
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    finally:
        bs.logout()

def fetch_financials(symbol: str) -> Dict[str, Any]:
    """获取财报数据（最近4个季度）"""
    if not AKSHARE_AVAILABLE:
        raise RuntimeError("AkShare未安装")
    
    try:
        # 尝试使用东方财富财务指标接口
        df_indicator = ak.stock_financial_analysis_indicator_em(symbol=symbol)
        
        # 取最近4个季度
        recent_4 = df_indicator.head(4).to_dict('records') if df_indicator is not None else []
        
        return {
            "indicators": recent_4,
            "update_time": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"获取财报数据失败: {e}，跳过财报数据")
        return {}

def fetch_fundamentals(symbol: str) -> Dict[str, Any]:
    """获取基本面数据（市盈率、市净率等）"""
    if not AKSHARE_AVAILABLE:
        raise RuntimeError("AkShare未安装")
    
    try:
        # 使用百度估值数据（更稳定）
        df_pe = ak.stock_zh_valuation_baidu(symbol=symbol, indicator='市盈率')
        df_pb = ak.stock_zh_valuation_baidu(symbol=symbol, indicator='市净率')
        df_mv = ak.stock_zh_valuation_baidu(symbol=symbol, indicator='总市值')
        
        latest = {}
        if df_pe is not None and len(df_pe) > 0:
            latest['pe'] = df_pe.iloc[-1]['value']
        if df_pb is not None and len(df_pb) > 0:
            latest['pb'] = df_pb.iloc[-1]['value']
        if df_mv is not None and len(df_mv) > 0:
            latest['total_mv'] = df_mv.iloc[-1]['value']
        
        return {
            "data": latest,
            "update_time": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"获取基本面数据失败: {e}，跳过基本面数据")
        return {}

# ============== 缓存管理 ==============

def get_cache_dir(symbol: str) -> Path:
    """获取缓存目录"""
    d = CACHE_DIR / symbol
    d.mkdir(parents=True, exist_ok=True)
    return d

def load_metadata(symbol: str) -> Dict[str, Any]:
    """加载元数据"""
    meta_file = get_cache_dir(symbol) / "metadata.json"
    if meta_file.exists():
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_metadata(symbol: str, meta: Dict[str, Any]):
    """保存元数据"""
    meta_file = get_cache_dir(symbol) / "metadata.json"
    meta['update_time'] = datetime.datetime.now().isoformat()
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def load_daily_kline(symbol: str) -> pd.DataFrame:
    """加载缓存的日线数据"""
    kline_file = get_cache_dir(symbol) / "daily_kline.csv"
    if kline_file.exists():
        return pd.read_csv(kline_file, parse_dates=['date'])
    return pd.DataFrame()

def save_daily_kline(symbol: str, df: pd.DataFrame):
    """保存日线数据"""
    kline_file = get_cache_dir(symbol) / "daily_kline.csv"
    df.to_csv(kline_file, index=False)

def load_financials(symbol: str) -> Dict[str, Any]:
    """加载财报缓存"""
    fin_file = get_cache_dir(symbol) / "financials.json"
    if fin_file.exists():
        with open(fin_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_financials(symbol: str, data: Dict[str, Any]):
    """保存财报数据"""
    fin_file = get_cache_dir(symbol) / "financials.json"
    with open(fin_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_fundamentals(symbol: str) -> Dict[str, Any]:
    """加载基本面缓存"""
    fund_file = get_cache_dir(symbol) / "fundamentals.json"
    if fund_file.exists():
        with open(fund_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_fundamentals(symbol: str, data: Dict[str, Any]):
    """保存基本面数据"""
    fund_file = get_cache_dir(symbol) / "fundamentals.json"
    with open(fund_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============== 数据更新逻辑 ==============

def update_daily_kline(symbol: str, force_full: bool = False) -> pd.DataFrame:
    """更新日线数据（全量或增量）"""
    
    meta = load_metadata(symbol)
    today = datetime.date.today()
    
    # 判断是否需要全量更新
    need_full = force_full or 'list_date' not in meta
    
    if need_full:
        # 全量更新：获取上市日期或5年数据
        print(f"[{symbol}] 执行全量更新...")
        
        # 获取上市日期
        list_date = get_stock_list_date(symbol)
        if list_date:
            try:
                start = datetime.datetime.strptime(list_date, "%Y-%m-%d").date()
                meta['list_date'] = list_date
            except:
                start = today - datetime.timedelta(days=365*5)
        else:
            start = today - datetime.timedelta(days=365*5)
        
        start_str = start.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        
        print(f"  数据范围: {start_str} ~ {end_str}")
        
        df = fetch_daily_kline(symbol, start_str, end_str)
        
        if not df.empty:
            save_daily_kline(symbol, df)
            meta['last_trade_date'] = df.iloc[-1]['date']
            save_metadata(symbol, meta)
            print(f"  已缓存 {len(df)} 条日线数据")
        
        return df
    else:
        # 增量更新
        cached_df = load_daily_kline(symbol)
        
        if cached_df.empty:
            return update_daily_kline(symbol, force_full=True)
        
        # 获取最后缓存的日期
        last_date = pd.to_datetime(cached_df.iloc[-1]['date'])
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        
        # 如果最后日期已经是昨天或今天，检查是否需要更新
        if last_date.date() >= yesterday:
            print(f"[{symbol}] 日线数据已是最新")
            return cached_df
        
        # 增量获取
        start_str = (last_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        
        print(f"[{symbol}] 执行增量更新: {start_str} ~ {end_str}")
        
        new_df = fetch_daily_kline(symbol, start_str, end_str)
        
        if not new_df.empty:
            # 合并数据
            combined = pd.concat([cached_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['date'], keep='last')
            combined = combined.sort_values('date')
            
            save_daily_kline(symbol, combined)
            meta['last_trade_date'] = combined.iloc[-1]['date']
            save_metadata(symbol, meta)
            print(f"  新增 {len(new_df)} 条，总计 {len(combined)} 条")
            
            return combined
        
        return cached_df

def update_financials(symbol: str, force: bool = False) -> Dict[str, Any]:
    """更新财报数据（每日检查，有新报告才更新）"""
    
    meta = load_metadata(symbol)
    today = datetime.date.today()
    
    # 财报发布周期较长，每天检查即可
    cached = load_financials(symbol)
    
    # 如果有缓存且不是强制更新，检查缓存时间
    if cached and not force:
        update_time = datetime.datetime.fromisoformat(cached.get('update_time', '2000-01-01'))
        # 同一交易日不重复更新
        if update_time.date() == today:
            print(f"[{symbol}] 财报数据已是今日最新")
            return cached
    
    print(f"[{symbol}] 更新财报数据...")
    data = fetch_financials(symbol)
    
    if data:
        save_financials(symbol, data)
        print(f"  已缓存最新财报")
    
    return data

def update_fundamentals(symbol: str, force: bool = False) -> Dict[str, Any]:
    """更新基本面数据"""
    
    meta = load_metadata(symbol)
    today = datetime.date.today()
    
    cached = load_fundamentals(symbol)
    
    if cached and not force:
        update_time = datetime.datetime.fromisoformat(cached.get('update_time', '2000-01-01'))
        if update_time.date() == today:
            print(f"[{symbol}] 基本面数据已是今日最新")
            return cached
    
    print(f"[{symbol}] 更新基本面数据...")
    data = fetch_fundamentals(symbol)
    
    if data:
        save_fundamentals(symbol, data)
        print(f"  已缓存基本面数据")
    
    return data

# ============== 分析报告生成 ==============

def generate_report(symbol: str, df_kline: pd.DataFrame, financials: Dict, fundamentals: Dict) -> str:
    """生成每日分析报告"""
    
    lines = []
    lines.append(f"## 📊 {symbol} 每日分析报告")
    lines.append(f"📅 {datetime.date.today().strftime('%Y-%m-%d')}\n")
    
    # ===== 行情概览 =====
    if not df_kline.empty:
        latest = df_kline.iloc[-1]
        prev = df_kline.iloc[-2] if len(df_kline) > 1 else latest
        
        lines.append("### 📈 行情概览")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 收盘价 | {fmt_price(latest['close'])}元 |")
        
        if prev['close'] > 0:
            pct = (latest['close'] - prev['close']) / prev['close'] * 100
            lines.append(f"| 日涨跌 | {fmt_pct(pct)} |")
        
        lines.append(f"| 最高 | {fmt_price(latest['high'])}元 |")
        lines.append(f"| 最低 | {fmt_price(latest['low'])}元 |")
        lines.append(f"| 成交量 | {fmt_volume(latest['volume'])}股 |")
        lines.append(f"| 成交额 | {fmt_volume(latest['amount'])}元 |")
        lines.append(f"| 换手率 | {fmt_pct(latest.get('turn', 0))} |\n")
        
        # 近期走势
        if len(df_kline) >= 20:
            days_5 = df_kline.tail(5)
            days_10 = df_kline.tail(10)
            days_20 = df_kline.tail(20)
            
            chg_5d = (latest['close'] - days_5.iloc[0]['close']) / days_5.iloc[0]['close'] * 100
            chg_10d = (latest['close'] - days_10.iloc[0]['close']) / days_10.iloc[0]['close'] * 100
            chg_20d = (latest['close'] - days_20.iloc[0]['close']) / days_20.iloc[0]['close'] * 100
            
            lines.append("### 📉 近期走势")
            lines.append(f"| 周期 | 涨跌幅 |")
            lines.append(f"|------|--------|")
            lines.append(f"| 5日 | {fmt_pct(chg_5d)} |")
            lines.append(f"| 10日 | {fmt_pct(chg_10d)} |")
            lines.append(f"| 20日 | {fmt_pct(chg_20d)} |")
            lines.append(f"| 数据范围 | {len(df_kline)}个交易日 |\n")
    
    # ===== 技术指标 =====
    if len(df_kline) >= 20:
        lines.append("### 🔧 技术指标")
        
        close_prices = df_kline['close']
        
        # MA均线
        ma5 = close_prices.rolling(5).mean().iloc[-1]
        ma10 = close_prices.rolling(10).mean().iloc[-1]
        ma20 = close_prices.rolling(20).mean().iloc[-1]
        
        latest_close = float(latest['close'])
        
        lines.append(f"| 指标 | 数值 | 状态 |")
        lines.append(f"|------|------|------|")
        lines.append(f"| MA5 | {fmt_price(ma5)} | {'站上' if latest_close > ma5 else '跌破'} |")
        lines.append(f"| MA10 | {fmt_price(ma10)} | {'站上' if latest_close > ma10 else '跌破'} |")
        lines.append(f"| MA20 | {fmt_price(ma20)} | {'站上' if latest_close > ma20 else '跌破'} |")
        
        # RSI (14日)
        if len(df_kline) >= 14:
            delta = close_prices.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            rsi_status = "超买⚠️" if rsi > 70 else ("超卖💡" if rsi < 30 else "正常")
            lines.append(f"| RSI(14) | {rsi:.1f} | {rsi_status} |")
        
        lines.append("")
    
    # ===== 基本面 =====
    if fundamentals and 'data' in fundamentals:
        lines.append("### 💰 基本面指标")
        fd = fundamentals['data']
        
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        
        # 市盈率
        if 'pe' in fd:
            lines.append(f"| 市盈率(PE) | {fd['pe']} |")
        if 'pe_ttm' in fd:
            lines.append(f"| 市盈率TTM | {fd['pe_ttm']} |")
        
        # 市净率
        if 'pb' in fd:
            lines.append(f"| 市净率(PB) | {fd['pb']} |")
        
        # 市值
        if 'total_mv' in fd:
            mv = float(fd['total_mv'])
            lines.append(f"| 总市值 | {fmt_amount(mv * 1e4)} |")  # 万元转元
        
        if 'circ_mv' in fd:
            cv = float(fd['circ_mv'])
            lines.append(f"| 流通市值 | {fmt_amount(cv * 1e4)} |")
        
        lines.append("")
    
    # ===== 财报摘要 =====
    if financials and 'indicators' in financials and financials['indicators']:
        lines.append("### 📋 财报摘要（最近季度）")
        
        indicators = financials['indicators']
        if indicators:
            latest_report = indicators[0]
            
            lines.append(f"| 项目 | 数值 |")
            lines.append(f"|------|------|")
            
            # 从财报数据中提取关键指标
            for key in ['日期', '报告日期', '净利润', '营业收入', '净资产收益率', '毛利率']:
                if key in latest_report:
                    val = latest_report[key]
                    if isinstance(val, (int, float)):
                        if '利润' in key or '收入' in key or '资产' in key:
                            lines.append(f"| {key} | {fmt_amount(val)} |")
                        elif '率' in key:
                            lines.append(f"| {key} | {fmt_pct(val)} |")
                        else:
                            lines.append(f"| {key} | {val} |")
                    else:
                        lines.append(f"| {key} | {val} |")
            
            lines.append("")
    
    # ===== 缓存状态 =====
    meta = load_metadata(symbol)
    lines.append("### 💾 数据状态")
    lines.append(f"- 日线数据: {len(df_kline)} 条")
    lines.append(f"- 最后更新: {meta.get('last_trade_date', 'N/A')}")
    lines.append(f"- 上市日期: {meta.get('list_date', 'N/A')}")
    
    return "\n".join(lines)

# ============== 主命令 ==============

def cmd_analyze(symbol: str, force_full: bool = False):
    """执行每日分析"""
    
    print(f"\n{'='*50}")
    print(f"每日分析: {symbol}")
    print(f"{'='*50}\n")
    
    # 更新交易日用历
    calendar = get_trade_calendar()
    
    # 检查是否交易日
    last_trade_day = get_last_trade_day(calendar)
    print(f"最近交易日: {last_trade_day}\n")
    
    # 更新数据
    df_kline = update_daily_kline(symbol, force_full)
    financials = update_financials(symbol)
    fundamentals = update_fundamentals(symbol)
    
    # 生成报告
    if not df_kline.empty:
        report = generate_report(symbol, df_kline, financials, fundamentals)
        print("\n" + "="*50)
        print(report)
        print("="*50)
        return report
    else:
        print(f"错误: 无法获取 {symbol} 的数据")
        return None

def cmd_status(symbol: str):
    """查看缓存状态"""
    
    cache_dir = get_cache_dir(symbol)
    meta = load_metadata(symbol)
    
    print(f"\n{'='*50}")
    print(f"缓存状态: {symbol}")
    print(f"{'='*50}\n")
    
    print(f"缓存目录: {cache_dir}")
    print(f"目录存在: {cache_dir.exists()}\n")
    
    if meta:
        print("元数据:")
        for k, v in meta.items():
            print(f"  {k}: {v}")
    else:
        print("元数据: 无")
    
    # 日线数据
    df = load_daily_kline(symbol)
    print(f"\n日线数据: {len(df)} 条")
    if not df.empty:
        print(f"  日期范围: {df.iloc[0]['date']} ~ {df.iloc[-1]['date']}")
    
    # 财报数据
    fin = load_financials(symbol)
    print(f"\n财报数据: {'已缓存' if fin else '无'}")
    
    # 基本面
    fund = load_fundamentals(symbol)
    print(f"\n基本面数据: {'已缓存' if fund else '无'}")

def cmd_clean(symbol: str):
    """清理缓存"""
    import shutil
    
    cache_dir = get_cache_dir(symbol)
    
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"已清理: {cache_dir}")
    else:
        print(f"目录不存在: {cache_dir}")

# ============== 入口 ==============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="每日股票分析器")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # analyze 命令
    p_analyze = subparsers.add_parser("analyze", help="执行每日分析")
    p_analyze.add_argument("symbol", help="股票代码")
    p_analyze.add_argument("--full", action="store_true", help="强制全量更新")
    
    # status 命令
    p_status = subparsers.add_parser("status", help="查看缓存状态")
    p_status.add_argument("symbol", help="股票代码")
    
    # clean 命令
    p_clean = subparsers.add_parser("clean", help="清理缓存")
    p_clean.add_argument("symbol", help="股票代码")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        cmd_analyze(args.symbol, args.full)
    elif args.command == "status":
        cmd_status(args.symbol)
    elif args.command == "clean":
        cmd_clean(args.symbol)
    else:
        parser.print_help()
