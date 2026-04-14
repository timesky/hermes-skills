#!/usr/bin/env python3
"""配置更新脚本"""
import yaml
import argparse

CONFIG_PATH = "/Users/timesky/.hermes/mcn_config.yaml"

def update_config(key_path: str, value):
    """更新配置"""
    config = yaml.safe_load(open(CONFIG_PATH))
    
    keys = key_path.split('.')
    current = config
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value
    
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✓ 配置已更新：{key_path} = {value}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--set', type=str, help='设置配置 (格式：key=value)')
    args = parser.parse_args()
    
    if args.set:
        key, value = args.set.split('=', 1)
        # 简单解析 value
        if value.startswith('['):
            import ast
            value = ast.literal_eval(value)
        update_config(key, value)
