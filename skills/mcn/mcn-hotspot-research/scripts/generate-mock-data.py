#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点调研模拟数据生成器 - 当 OpenCLI 和 Playwright 都不可用时使用

适用场景：
- 流程演示/测试
- 网络问题导致抓取失败
- 环境未配置完成时的临时方案
- macOS 系统框架缺失导致浏览器无法启动

注意：模拟数据仅用于流程验证，正式生产环境应使用真实抓取数据。
"""

import json
import os
from datetime import datetime

def generate_mock_hotspot(date=None):
    """生成模拟热点数据"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # 从配置读取目录
    kb_root = "/Users/timesky/backup/知识库-Obsidian"
    config_path = os.path.expanduser("~/.hermes/mcn_config.yaml")
    if os.path.exists(config_path):
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        kb_root = config.get("paths", {}).get("kb_root", kb_root)
    
    mcn_root = kb_root + "/mcn"
    output_dir = mcn_root + "/hotspot/" + date
    os.makedirs(output_dir, exist_ok=True)
    
    # 模拟热点数据（科技、编程、机器人领域）
    articles = [
        # 微博热搜（带热度值）
        {"title": "华为发布新一代 AI 芯片昇腾 910C", "platform": "微博", "source": "weibo", "url": "https://s.weibo.com/weibo?q=华为昇腾 910C", "category": "科技", "hot_value": 5800000},
        {"title": "特斯拉 Optimus 机器人最新进展曝光", "platform": "微博", "source": "weibo", "url": "https://s.weibo.com/weibo?q=特斯拉 Optimus", "category": "机器人", "hot_value": 4200000},
        {"title": "Python 3.13 正式发布：性能提升 30%", "platform": "微博", "source": "weibo", "url": "https://s.weibo.com/weibo?q=Python3.13", "category": "编程", "hot_value": 3100000},
        {"title": "小米汽车 SU7 Ultra 赛道版亮相", "platform": "微博", "source": "weibo", "url": "https://s.weibo.com/weibo?q=小米 SU7 Ultra", "category": "科技", "hot_value": 2800000},
        {"title": "阿里通义千问开源 Qwen3 模型", "platform": "微博", "source": "weibo", "url": "https://s.weibo.com/weibo?q=通义千问 Qwen3", "category": "AI 应用", "hot_value": 2500000},
        
        # 知乎热榜（带摘要）
        {"title": "如何评价苹果 WWDC 2026 发布会？", "platform": "知乎", "source": "zhihu", "url": "https://www.zhihu.com/question/123456", "category": "科技", "excerpt": "苹果发布了 iOS 21、macOS 16 等新系统..."},
        {"title": "国内大模型哪家强？2026 年最新评测", "platform": "知乎", "source": "zhihu", "url": "https://www.zhihu.com/question/123457", "category": "AI 应用", "excerpt": "从能力、价格、生态三个维度对比..."},
        {"title": "35 岁程序员转行做什么比较好？", "platform": "知乎", "source": "zhihu", "url": "https://www.zhihu.com/question/123458", "category": "编程", "excerpt": "在互联网行业干了 10 年，现在感到迷茫..."},
        {"title": "人形机器人距离普及还有多远？", "platform": "知乎", "source": "zhihu", "url": "https://www.zhihu.com/question/123459", "category": "机器人", "excerpt": "从技术、成本、应用场景三个角度分析..."},
        {"title": "Rust 语言是否值得学习？", "platform": "知乎", "source": "zhihu", "url": "https://www.zhihu.com/question/123460", "category": "编程", "excerpt": "看到很多大厂都在用 Rust，想了解一下..."},
        
        # 36kr
        {"title": "宇树科技完成 D 轮融资，估值突破 100 亿", "platform": "36 氪", "source": "36kr", "url": "https://36kr.com/p/123456", "category": "机器人"},
        {"title": "月之暗面发布 K2 模型，上下文窗口达 1000K", "platform": "36 氪", "source": "36kr", "url": "https://36kr.com/p/123457", "category": "AI 应用"},
        {"title": "字节跳动开源新编程助手 CodeMind", "platform": "36 氪", "source": "36kr", "url": "https://36kr.com/p/123458", "category": "编程"},
        {"title": "英伟达 B200 芯片产能不足，订单排到 2027 年", "platform": "36 氪", "source": "36kr", "url": "https://36kr.com/p/123459", "category": "科技"},
        {"title": "大疆发布新一代农业无人机 T100", "platform": "36 氪", "source": "36kr", "url": "https://36kr.com/p/123460", "category": "机器人"},
        
        # 虎嗅
        {"title": "OpenAI 内部战略文档泄露：GPT-5 训练进度曝光", "platform": "虎嗅", "source": "huxiu", "url": "https://www.huxiu.com/article/123456.html", "category": "AI 应用"},
        {"title": "中国芯片自给率突破 30%：国产替代加速", "platform": "虎嗅", "source": "huxiu", "url": "https://www.huxiu.com/article/123457.html", "category": "科技"},
        {"title": "AI 编程助手正在重塑软件开发行业", "platform": "虎嗅", "source": "huxiu", "url": "https://www.huxiu.com/article/123458.html", "category": "编程"},
        {"title": "波士顿动力被现代出售：人形机器人商业化困境", "platform": "虎嗅", "source": "huxiu", "url": "https://www.huxiu.com/article/123459.html", "category": "机器人"},
        {"title": "Sora 正式开放：视频生成进入新时代", "platform": "虎嗅", "source": "huxiu", "url": "https://www.huxiu.com/article/123460.html", "category": "AI 应用"},
    ]
    
    # 保存 JSON
    json_file = output_dir + "/hotspot.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    # 构建 MD 报告
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    md_lines = [
        "---",
        "created: " + time_str,
        "total: " + str(len(articles)),
        "---",
        "",
        "# " + date + " 热点聚合（模拟数据）",
        "",
        "> ⚠️ **注意**：本数据为模拟数据，用于流程演示/测试。正式生产环境应使用真实抓取数据。",
        "",
        "## 来源统计",
        "",
        "| 来源 | 数量 |",
        "|------|------|"
    ]
    
    sources = {}
    for a in articles:
        src = a.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        md_lines.append("| " + src + " | " + str(count) + " |")
    
    md_lines.extend(["", "---", "", "## 热点列表", ""])
    
    for source in ['weibo', 'zhihu', '36kr', 'huxiu']:
        source_articles = [a for a in articles if a.get('source') == source]
        if source_articles:
            platform = source_articles[0].get('platform', source)
            md_lines.extend(["### " + platform, ""])
            
            for i, a in enumerate(source_articles, 1):
                title = a.get('title', '')
                url = a.get('url', '')
                hot_value = a.get('hot_value', '')
                
                line = str(i) + ". [" + title + "](" + url + ")"
                if hot_value:
                    line += " (热度:" + str(hot_value) + ")"
                md_lines.append(line)
            
            md_lines.append("")
    
    md_file = output_dir + "/hotspot-aggregated.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    return {
        "status": "success",
        "json_file": json_file,
        "md_file": md_file,
        "total": len(articles),
        "sources": sources,
        "note": "模拟数据 - 仅用于流程演示/测试"
    }


if __name__ == '__main__':
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_mock_hotspot(date)
    print("✓ 热点数据已生成：" + result['json_file'])
    print("✓ 聚合报告已生成：" + result['md_file'])
    print("✓ 总计：" + str(result['total']) + " 条热点")
    print("✓ 来源分布：" + ", ".join(f"{k}{v}条" for k, v in result['sources'].items()))
    print("⚠️ 注意：" + result['note'])
