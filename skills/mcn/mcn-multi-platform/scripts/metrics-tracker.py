#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
效果追踪脚本
记录各平台阅读数据，生成周报分析
Created: 2026-05-07
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class MetricsTracker:
    """数据追踪器"""
    
    def __init__(self, data_dir="/Users/hy_timesky/Documents/My_Obsidian/mcn/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.data_dir / "metrics_tracking.json"
        
    def record_article_metrics(self, article_title, platform, metrics):
        """
        记录文章数据
        
        Args:
            article_title: 文章标题
            platform: 平台名称 (wechat/zhihu/juejin/csdn/toutiao)
            metrics: 数据字典 {
                'views': 阅读量,
                'opens': 打开数,
                'shares': 分享数,
                'likes': 点赞数,
                'comments': 评论数,
                'ctr': 打开率,
                'finish_rate': 完读率
            }
        """
        # 加载现有数据
        data = self._load_data()
        
        # 添加新记录
        record = {
            'article_title': article_title,
            'platform': platform,
            'metrics': metrics,
            'recorded_at': datetime.now().isoformat()
        }
        
        if 'records' not in data:
            data['records'] = []
        
        data['records'].append(record)
        
        # 保存
        self._save_data(data)
        
        print(f"✅ 已记录 {platform} 平台 '{article_title}' 的数据")
    
    def generate_weekly_report(self):
        """生成周报"""
        data = self._load_data()
        records = data.get('records', [])
        
        if not records:
            print("⚠️  没有数据可生成报告")
            return
        
        # 按平台分组统计
        platform_stats = {}
        for record in records:
            platform = record['platform']
            if platform not in platform_stats:
                platform_stats[platform] = {
                    'total_views': 0,
                    'total_opens': 0,
                    'total_shares': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'article_count': 0,
                    'articles': []
                }
            
            stats = platform_stats[platform]
            metrics = record['metrics']
            
            stats['total_views'] += metrics.get('views', 0)
            stats['total_opens'] += metrics.get('opens', 0)
            stats['total_shares'] += metrics.get('shares', 0)
            stats['total_likes'] += metrics.get('likes', 0)
            stats['total_comments'] += metrics.get('comments', 0)
            stats['article_count'] += 1
            stats['articles'].append(record['article_title'])
        
        # 计算平均CTR
        for platform, stats in platform_stats.items():
            if stats['total_views'] > 0:
                stats['avg_ctr'] = (stats['total_opens'] / stats['total_views']) * 100
            else:
                stats['avg_ctr'] = 0
        
        # 生成报告
        report = self._format_weekly_report(platform_stats)
        
        # 保存报告
        report_file = self.data_dir / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📊 周报已生成: {report_file}\n")
        print(report)
        
        return report
    
    def _format_weekly_report(self, platform_stats):
        """格式化周报"""
        report_lines = [
            "# MCN 内容周报",
            f"\n**报告周期**: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n---\n",
            "## 平台数据汇总\n"
        ]
        
        for platform, stats in platform_stats.items():
            platform_names = {
                'wechat': '微信公众号',
                'zhihu': '知乎',
                'juejin': '掘金',
                'csdn': 'CSDN',
                'toutiao': '头条号'
            }
            
            report_lines.append(f"### {platform_names.get(platform, platform)}\n")
            report_lines.append(f"- 文章数: {stats['article_count']}")
            report_lines.append(f"- 总阅读: {stats['total_views']:,}")
            report_lines.append(f"- 平均CTR: {stats['avg_ctr']:.2f}%")
            report_lines.append(f"- 总分享: {stats['total_shares']}")
            report_lines.append(f"- 总点赞: {stats['total_likes']}")
            report_lines.append(f"- 总评论: {stats['total_comments']}")
            report_lines.append(f"- 文章列表: {', '.join(stats['articles'][:3])}{'...' if len(stats['articles']) > 3 else ''}")
            report_lines.append("")
        
        # 添加验证对比
        report_lines.extend([
            "\n---\n",
            "## 验证指标对比\n",
            "| 指标 | 目标值 | 实际值 | 状态 |",
            "|------|--------|--------|------|"
        ])
        
        # 计算平均值
        avg_ctr = sum(s['avg_ctr'] for s in platform_stats.values()) / len(platform_stats) if platform_stats else 0
        
        metrics_to_check = [
            ("打开率", "5%", f"{avg_ctr:.1f}%", "✅" if avg_ctr >= 5 else "⚠️"),
            ("分享率", "2%", "待统计", "⏳"),
            ("完读率", "30%", "待统计", "⏳"),
            ("多平台增量", "20%", "待统计", "⏳")
        ]
        
        for metric, target, actual, status in metrics_to_check:
            report_lines.append(f"| {metric} | {target} | {actual} | {status} |")
        
        report_lines.extend([
            "\n---\n",
            "## 下周优化建议\n",
            "1. 根据CTR数据调整标题策略",
            "2. 优化低表现平台的发布时间",
            "3. 增加高CTR标题模式的使用频率",
            "4. 测试新的开场钩子\n",
            "---\n",
            "*自动生成 by MCN Metrics Tracker*"
        ])
        
        return '\n'.join(report_lines)
    
    def _load_data(self):
        """加载数据"""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'created': datetime.now().isoformat()}
    
    def _save_data(self, data):
        """保存数据"""
        data['last_updated'] = datetime.now().isoformat()
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    """主函数 - 演示用法"""
    tracker = MetricsTracker()
    
    # 演示：记录测试数据
    print("📊 MCN 数据追踪演示\n")
    print("="*50)
    
    # 记录示例数据（实际使用时从各平台API获取）
    test_data = [
        ("湖北惊现人造毒大米系AI生成", "wechat", {
            'views': 1250,
            'opens': 85,
            'shares': 32,
            'likes': 67,
            'comments': 23,
            'ctr': 6.8,
            'finish_rate': 35
        }),
        ("湖北惊现人造毒大米系AI生成", "zhihu", {
            'views': 890,
            'opens': 72,
            'shares': 18,
            'likes': 45,
            'comments': 34,
            'ctr': 8.1,
            'finish_rate': 42
        }),
        ("全球芯片巨头集体暴涨背后", "wechat", {
            'views': 2100,
            'opens': 168,
            'shares': 89,
            'likes': 134,
            'comments': 56,
            'ctr': 8.0,
            'finish_rate': 38
        })
    ]
    
    for title, platform, metrics in test_data:
        tracker.record_article_metrics(title, platform, metrics)
    
    print("\n" + "="*50)
    print("\n📈 生成周报...\n")
    tracker.generate_weekly_report()
    
    print("\n💡 提示:")
    print("- 实际使用时，请从各平台后台获取真实数据")
    print("- 建议每天记录一次数据")
    print("- 周报会自动对比目标值")


if __name__ == '__main__':
    main()