#!/usr/bin/env python3
"""
策略调研脚本
功能：搜索知乎等平台获取新策略思路，注册到策略库
执行时间：每周日9:00
"""

import os
import json
from pathlib import Path
from datetime import datetime
import akshare as ak
import pandas as pd

# 数据路径配置
DATA_DIR = Path.home() / ".hermes" / "profiles" / "stock" / "data"
STRATEGY_REGISTRY = DATA_DIR / "strategy_registry.json"
STRATEGY_RESEARCH_DIR = DATA_DIR / "strategy_research"

# 策略家族定义
STRATEGY_FAMILY = [
    'RSI', 'MACD', 'MA_CROSS', 'BOLL', 'KDJ', 
    'MOMENTUM', 'MEAN_REVERSION', 'FACTOR',
    'DYNAMIC_STOP', 'VOLATILITY_ADAPT'
]

def load_strategy_registry():
    """加载策略注册表"""
    if STRATEGY_REGISTRY.exists():
        with open(STRATEGY_REGISTRY, 'r') as f:
            return json.load(f)
    return {'strategies': [], 'last_update': None}

def save_strategy_registry(registry):
    """保存策略注册表"""
    registry['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(STRATEGY_REGISTRY, 'w') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

def generate_strategy_fingerprint(strategy):
    """生成策略指纹（用于去重）"""
    key_params = ['family', 'buy_signal', 'sell_signal', 'stop_loss', 'take_profit', 'position_rule']
    fingerprint_parts = []
    for param in key_params:
        if param in strategy:
            fingerprint_parts.append(str(strategy[param]))
    return hash('|'.join(fingerprint_parts))

def register_strategy(strategy):
    """注册新策略"""
    registry = load_strategy_registry()
    
    # 生成指纹
    fingerprint = generate_strategy_fingerprint(strategy)
    strategy['fingerprint'] = fingerprint
    strategy['register_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 检查重复
    existing = [s for s in registry['strategies'] if s.get('fingerprint') == fingerprint]
    if existing:
        print(f"策略已存在: {strategy.get('name', 'Unknown')}")
        return False
    
    # 添加策略
    registry['strategies'].append(strategy)
    save_strategy_registry(registry)
    
    print(f"✅ 策略已注册: {strategy.get('name', 'Unknown')}")
    return True

def search_zhihu_strategies():
    """搜索知乎策略（模拟输出）"""
    # 实际搜索需要通过OpenCLI browser
    # 这里输出提示信息
    print("=" * 60)
    print(f"【策略调研】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    print("\n【调研任务】")
    print("  1. 使用OpenCLI browser访问知乎")
    print("  2. 搜索关键词：量化策略、A股策略、因子策略")
    print("  3. 提取有效策略思路")
    print("  4. 注册到策略库")
    
    # 加载现有策略
    registry = load_strategy_registry()
    print(f"\n【当前策略库】")
    print(f"  已注册策略: {len(registry['strategies'])}个")
    print(f"  最后更新: {registry.get('last_update', 'N/A')}")
    
    # 列出策略家族统计
    family_count = {}
    strategies = registry.get('strategies', {})
    # 支持字典和数组两种格式
    if isinstance(strategies, dict):
        strategy_list = strategies.values()
    else:
        strategy_list = strategies
    for s in strategy_list:
        if isinstance(s, dict):
            family = s.get('category', s.get('family', 'OTHER'))
            family_count[family] = family_count.get(family, 0) + 1
    
    print("\n【策略分布】")
    for family, count in sorted(family_count.items(), key=lambda x: -x[1]):
        print(f"  {family}: {count}个")
    
    print("\n" + "=" * 60)
    print("提示: 完整调研需要配合OpenCLI browser执行")
    print("=" * 60)

def list_top_strategies(n=5):
    """列出表现最优策略"""
    registry = load_strategy_registry()
    
    # 按回测表现排序
    strategies_data = registry.get('strategies', {})
    # 支持字典和数组两种格式
    if isinstance(strategies_data, dict):
        strategies = list(strategies_data.values())
    else:
        strategies = strategies_data
    
    # 过滤出字典类型的策略
    valid_strategies = [s for s in strategies if isinstance(s, dict)]
    
    # 提取回测收益率（支持多种字段名）
    def get_return(s):
        if 'backtest_return' in s:
            return s.get('backtest_return', 0)
        elif 'test_result' in s and isinstance(s.get('test_result'), dict):
            return s.get('test_result', {}).get('profit_pct', 0)
        elif 'backtest_result' in s and isinstance(s.get('backtest_result'), dict):
            return s.get('backtest_result', {}).get('annual_return', 0)
        return 0
    
    # 简单排序（按回测收益率）
    sorted_strategies = sorted(
        valid_strategies, 
        key=get_return,
        reverse=True
    )
    
    print("\n【Top策略】")
    for i, s in enumerate(sorted_strategies[:n]):
        name = s.get('name', 'Unknown')
        return_val = s.get('backtest_return', 'N/A')
        print(f"  {i+1}. {name} - 收益率: {return_val}")

def run_strategy_research():
    """执行策略调研"""
    search_zhihu_strategies()
    list_top_strategies(5)

if __name__ == "__main__":
    run_strategy_research()