#!/usr/bin/env python3
"""
MCN 飞书推送脚本
用法: python push_to_feishu.py
"""

import os
import json
import requests
from datetime import datetime


def send_to_feishu(topics: list, webhook_url: str = None) -> bool:
    """发送选题报告到飞书
    
    Args:
        topics: 选题列表，每个元素包含:
            - title: 标题
            - domain: 领域
            - heat: 热度值
            - score: 评分 (1-10)
            - reason: 推荐理由
        webhook_url: 飞书 Webhook URL（可选，默认从环境变量获取）
    
    Returns:
        bool: 发送是否成功
    """
    if not webhook_url:
        webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ 错误: 未找到 FEISHU_WEBHOOK_URL 环境变量")
        print("请设置: export FEISHU_WEBHOOK_URL='https://open.feishu.cn/...'")
        return False
    
    # 构建消息卡片内容
    content_lines = []
    for i, topic in enumerate(topics, 1):
        content_lines.append(f"**{i}. {topic['title']}**")
        content_lines.append(f"   领域：{topic['domain']} | 热度：{topic['heat']} | 评分：{topic['score']}/10")
        content_lines.append(f"   {topic['reason']}")
        content_lines.append("")
    
    content_text = "\n".join(content_lines)
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔥 MCN 选题推荐 - {datetime.now().strftime('%Y-%m-%d')}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content_text
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"生成时间：{datetime.now().strftime('%H:%M')}"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                print(f"✅ 成功发送 {len(topics)} 个选题到飞书")
                return True
            else:
                print(f"❌ 飞书 API 返回错误: {result}")
                return False
        else:
            print(f"❌ HTTP 错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False


# 示例用法
if __name__ == "__main__":
    # 示例数据
    topics = [
        {
            "title": "AI 编程工具对比",
            "domain": "编程",
            "heat": "500万",
            "score": 9,
            "reason": "热点高，与目标用户强相关"
        },
        {
            "title": "GPT-5 发布预测",
            "domain": "科技",
            "heat": "800万",
            "score": 10,
            "reason": "顶级热点，具备时效性"
        }
    ]
    
    send_to_feishu(topics)
