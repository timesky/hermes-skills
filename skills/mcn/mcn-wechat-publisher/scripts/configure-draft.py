# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
公众号草稿配置脚本 - 通过浏览器自动化配置赞赏、留言、合集

用法:
    python configure-draft.py --media_id xxx --enable-comment --enable-reward --collection "AI技术"

前置条件:
    - 已登录公众号后台（浏览器 cookie 有效）
    - 使用 Hermes browser 工具执行

功能:
    1. 打开草稿箱页面
    2. 找到指定 media_id 的草稿
    3. 配置留言（开启/仅粉丝可评论）
    4. 配置赞赏（开启）
    5. 添加到合集
"""

import argparse
import json
import os
import yaml

# Profile隔离：HERMES_HOME在子profile指向子目录，需推导主目录找技能
_hermes_home = os.environ.get('HERMES_HOME', '/Users/hy_timesky/.hermes')
if '/profiles/' in _hermes_home:
    HERMES_MAIN_HOME = _hermes_home.split('/profiles/')[0]
else:
    HERMES_MAIN_HOME = _hermes_home
HERMES_HOME = _hermes_home
SKILLS_DIR = os.path.join(HERMES_MAIN_HOME, 'skills')

# 配置文件（profile隔离）
config_path = os.path.join(HERMES_HOME, 'mcn_config.yaml')
if not os.path.exists(config_path):
    config_path = os.path.join(HERMES_MAIN_HOME, 'mcn_config.yaml')
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = {}

KB_ROOT = config.get('paths', {}).get('kb_root', os.path.expanduser("~/Documents/My_Obsidian"))

# 公众号后台 URL
DRAFT_LIST_URL = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=list&lang=zh_CN"


def generate_browser_instructions(media_id: str, enable_comment: bool = True, 
                                   enable_reward: bool = True, 
                                   collection: str = None):
    """生成浏览器操作指令（供 Hermes 执行）"""
    
    instructions = {
        "steps": [
            {
                "step": 1,
                "action": "navigate",
                "url": DRAFT_LIST_URL,
                "description": "打开草稿箱页面"
            },
            {
                "step": 2,
                "action": "wait",
                "selector": ".appmsg_list",
                "timeout": 5,
                "description": "等待草稿列表加载"
            },
            {
                "step": 3,
                "action": "find_and_click",
                "target": f"包含 media_id={media_id} 的草稿",
                "selector": f"[data-id='{media_id}']",
                "fallback": "遍历草稿列表，找到标题匹配的文章",
                "description": "找到目标草稿并点击编辑"
            },
            {
                "step": 4,
                "action": "wait",
                "selector": ".editor_toolbar",
                "timeout": 5,
                "description": "等待编辑器加载"
            }
        ]
    }
    
    # 配置留言
    if enable_comment:
        instructions["steps"].append({
            "step": 5,
            "action": "click",
            "selector": "[data-key='comment']",
            "description": "点击留言设置"
        })
        instructions["steps"].append({
            "step": 6,
            "action": "select",
            "selector": "input[name='need_open_comment'][value='1']",
            "description": "开启留言"
        })
    
    # 配置赞赏
    if enable_reward:
        instructions["steps"].append({
            "step": 7,
            "action": "click",
            "selector": "[data-key='reward']",
            "description": "点击赞赏设置"
        })
        instructions["steps"].append({
            "step": 8,
            "action": "select",
            "selector": "input[name='is_reward'][value='1']",
            "description": "开启赞赏"
        })
    
    # 添加到合集
    if collection:
        instructions["steps"].append({
            "step": 9,
            "action": "click",
            "selector": "[data-key='collection']",
            "description": "点击合集设置"
        })
        instructions["steps"].append({
            "step": 10,
            "action": "click",
            "selector": f".collection-item:contains('{collection}')",
            "description": f"选择合集: {collection}"
        })
    
    # 保存
    instructions["steps"].append({
        "step": 11,
        "action": "click",
        "selector": ".save_btn",
        "description": "保存草稿"
    })
    
    return instructions


def main():
    parser = argparse.ArgumentParser(description='公众号草稿配置')
    parser.add_argument('--media_id', type=str, help='草稿 media_id')
    parser.add_argument('--title', type=str, help='文章标题（用于查找）')
    parser.add_argument('--enable-comment', action='store_true', default=True, help='开启留言')
    parser.add_argument('--fans-only-comment', action='store_true', help='仅粉丝可评论')
    parser.add_argument('--enable-reward', action='store_true', default=True, help='开启赞赏')
    parser.add_argument('--collection', type=str, help='添加到合集（合集名称）')
    parser.add_argument('--output', type=str, default='json', choices=['json', 'markdown'], help='输出格式')
    
    args = parser.parse_args()
    
    if not args.media_id and not args.title:
        print("❌ 必须指定 --media_id 或 --title")
        return
    
    # 生成操作指令
    instructions = generate_browser_instructions(
        media_id=args.media_id or "",
        enable_comment=args.enable_comment,
        enable_reward=args.enable_reward,
        collection=args.collection
    )
    
    if args.output == 'json':
        print(json.dumps(instructions, indent=2, ensure_ascii=False))
    else:
        print("# 公众号草稿配置步骤\n")
        for step in instructions["steps"]:
            print(f"## 步骤 {step['step']}: {step['description']}")
            print(f"- 动作: {step['action']}")
            if 'url' in step:
                print(f"- URL: {step['url']}")
            if 'selector' in step:
                print(f"- 选择器: {step['selector']}")
            print()


if __name__ == '__main__':
    main()
