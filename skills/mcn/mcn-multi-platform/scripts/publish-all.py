#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多平台内容分发脚本
自动将公众号文章适配并发布到知乎、掘金、CSDN等平台
Created: 2026-05-07
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

# 平台配置
PLATFORM_CONFIG = {
    "zhihu": {
        "name": "知乎",
        "content_type": "问答型/深度分析",
        "delay_hours": 0,  # 即时发布
        "priority": 1,
        "title_rules": {
            "prefer_question": True,  # 疑问式标题效果更好
            "max_length": 50,
            "emoji_limit": 0
        },
        "content_rules": {
            "add_signature": True,
            "image_position": "文中分散",
            "need_citation": True,
            "footer_template": "\n\n---\n\n**相关话题**: #{tags}\n\n*关注我，看更多科技深度解读*"
        }
    },
    "juejin": {
        "name": "掘金",
        "content_type": "技术干货/教程",
        "delay_hours": 1,  # 1小时后发布
        "priority": 2,
        "title_rules": {
            "add_prefix": True,  # 加技术标签 [AI][前端]
            "max_length": 50,
            "emoji_limit": 1
        },
        "content_rules": {
            "add_signature": True,
            "image_position": "代码块后",
            "need_citation": False,
            "footer_template": "\n\n---\n\n> 如果觉得有帮助，欢迎点赞收藏关注 ❤️"
        }
    },
    "csdn": {
        "name": "CSDN",
        "content_type": "教程/工具推荐",
        "delay_hours": 2,  # 2小时后发布
        "priority": 3,
        "title_rules": {
            "seo_optimize": True,  # SEO优化，加关键词
            "max_length": 60,
            "emoji_limit": 0
        },
        "content_rules": {
            "add_signature": True,
            "image_position": "章节开头",
            "need_citation": False,
            "footer_template": "\n\n---\n\n**热门标签**: {tags}\n\n*欢迎在评论区交流讨论*"
        }
    },
    "toutiao": {
        "name": "头条号",
        "content_type": "大众科技/热点解读",
        "delay_hours": 0,  # 即时发布
        "priority": 2,
        "title_rules": {
            "can_exaggerate": True,  # 可适当夸张，增加情绪词
            "max_length": 30,
            "emoji_limit": 2
        },
        "content_rules": {
            "add_signature": False,
            "image_position": "封面+文中",
            "need_citation": False,
            "footer_template": "\n\n---\n\n*点击关注，不错过精彩内容*"
        }
    },
    "xiaohongshu": {
        "name": "小红书",
        "content_type": "科技种草/工具推荐",
        "delay_hours": 3,  # 3小时后发布（避开公众号高峰期）
        "priority": 2,
        "title_rules": {
            "emoji_required": True,  # 必须带emoji
            "max_length": 20,
            "emoji_limit": 3,
            "keywords": ["宝藏", "神器", "必备", "干货"]
        },
        "content_rules": {
            "add_signature": True,
            "image_position": "封面+步骤图",
            "need_citation": False,
            "footer_template": "\n\n---\n\n💬 评论区分享你的看法吧～\n\n#科技好物 #效率工具 #干货分享",
            "style_adjustments": [
                "段落开头加emoji",
                "重点内容加粗/高亮",
                "文末加话题标签（3-5个）",
                "字数控制在500-800字"
            ]
        }
    }
}


class MultiPlatformPublisher:
    """多平台内容发布器"""
    
    def __init__(self, article_path):
        self.article_path = Path(article_path)
        self.article_data = self._load_article()
        
    def _load_article(self):
        """加载文章内容"""
        with open(self.article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                import yaml
                metadata = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return {
                    'metadata': metadata,
                    'body': body
                }
        
        return {
            'metadata': {},
            'body': content
        }
    
    def _adapt_title(self, platform, original_title):
        """根据平台规则适配标题"""
        config = PLATFORM_CONFIG[platform]['title_rules']
        adapted_title = original_title
        
        # 知乎：疑问式标题
        if platform == 'zhihu' and config.get('prefer_question'):
            if not original_title.endswith('？') and not original_title.endswith('?'):
                # 转换为疑问句
                if '背后' in original_title:
                    adapted_title = original_title.replace('背后', '背后，发生了什么？')
                elif '曝光' in original_title or '爆出' in original_title:
                    adapted_title = f"{original_title}，真相是什么？"
                else:
                    adapted_title = f"{original_title}，你怎么看？"
        
        # 掘金：添加技术标签
        elif platform == 'juejin' and config.get('add_prefix'):
            # 根据内容判断标签
            tags = self._extract_tech_tags(self.article_data['body'])
            if tags:
                adapted_title = f"[{tags[0]}] {original_title}"
        
        # CSDN：SEO优化
        elif platform == 'csdn' and config.get('seo_optimize'):
            # 添加关键词
            keywords = self._extract_keywords(self.article_data['body'])
            if keywords and len(original_title) < config['max_length'] - 10:
                adapted_title = f"{original_title}_{keywords[0]}"
        
        # 头条：情绪词增强
        elif platform == 'toutiao' and config.get('can_exaggerate'):
            emotion_words = ['终于', '竟然', '偷偷', '突然', '刚刚']
            if not any(word in original_title for word in emotion_words):
                # 根据内容选择情绪词
                if '暴涨' in original_title or '大跌' in original_title:
                    adapted_title = f"刚刚，{original_title}"
        
        # 小红书：emoji+关键词
        elif platform == 'xiaohongshu':
            keywords = config.get('keywords', [])
            emojis = ['🔥', '💡', '✨', '🚀', '💎', '🎯', '⭐', '📌']
            import random
            
            # 添加emoji
            if config.get('emoji_required'):
                if not any(emoji in original_title for emoji in emojis):
                    adapted_title = f"{random.choice(emojis)}{original_title}"
            
            # 添加关键词
            if not any(kw in original_title for kw in keywords):
                # 选择合适的关键词
                if '推荐' in self.article_data['body'] or '工具' in self.article_data['body']:
                    adapted_title = f"{adapted_title}｜宝藏神器"
                elif '干货' in self.article_data['body']:
                    adapted_title = f"{adapted_title}｜干货满满"
        
        # 长度限制
        if len(adapted_title) > config['max_length']:
            adapted_title = adapted_title[:config['max_length']-3] + '...'
        
        return adapted_title
    
    def _adapt_content(self, platform, original_content):
        """根据平台规则适配内容"""
        config = PLATFORM_CONFIG[platform]['content_rules']
        adapted_content = original_content
        
        # 添加引言（知乎需要）
        if platform == 'zhihu':
            intro = self._generate_zhihu_intro(original_content)
            adapted_content = f"{intro}\n\n---\n\n{adapted_content}"
        
        # 小红书：格式化适配
        elif platform == 'xiaohongshu':
            adapted_content = self._adapt_for_xiaohongshu(original_content)
        
        # 添加签名和footer
        if config.get('add_signature'):
            footer = config.get('footer_template', '')
            tags = self._extract_keywords(original_content)[:3]
            footer = footer.format(tags=' '.join([f'#{t}' for t in tags]))
            adapted_content = f"{adapted_content}{footer}"
        
        return adapted_content
    
    def _adapt_for_xiaohongshu(self, content):
        """小红书内容适配：emoji + 短段落 + 话题标签"""
        import random
        emojis = ['💡', '✨', '🔥', '📌', '🎯', '⭐', '💪', '👍']
        
        # 分段处理
        paragraphs = content.split('\n\n')
        adapted_paragraphs = []
        
        for i, para in enumerate(paragraphs):
            # 每段开头加emoji
            if i < len(emojis):
                para = f"{emojis[i]} {para}"
            adapted_paragraphs.append(para)
        
        # 字数控制：截取前800字
        adapted_content = '\n\n'.join(adapted_paragraphs)
        if len(adapted_content) > 800:
            adapted_content = adapted_content[:800] + '...'
        
        return adapted_content
    
    def _extract_tech_tags(self, content):
        """提取技术标签"""
        tech_keywords = ['AI', '人工智能', '机器学习', '深度学习', '前端', '后端', 
                        '区块链', '云计算', '大数据', 'IoT', '芯片', '算法']
        found_tags = []
        for keyword in tech_keywords:
            if keyword in content:
                found_tags.append(keyword)
        return found_tags[:2] if found_tags else ['科技']
    
    def _extract_keywords(self, content):
        """提取关键词"""
        # 简单提取：出现频率高的词
        # 实际应用可使用TF-IDF或TextRank
        common_keywords = ['AI', '科技', '互联网', '芯片', '创新', '创业', '投资']
        found_keywords = []
        for keyword in common_keywords:
            if keyword in content:
                found_keywords.append(keyword)
        return found_keywords if found_keywords else ['科技', '创新']
    
    def _generate_zhihu_intro(self, content):
        """生成知乎风格引言"""
        # 提取文章核心观点
        first_paragraph = content.split('\n\n')[0]
        if len(first_paragraph) > 100:
            return f"**前言**：{first_paragraph[:100]}...\n\n这是近期科技圈的热门话题，让我来为你深度解读。"
        return "**前言**：这篇文章将为你深入分析近期的科技热点事件，带你了解背后的真相。\n\n"
    
    def publish_to_all(self, platforms=None):
        """发布到所有平台"""
        if platforms is None:
            platforms = list(PLATFORM_CONFIG.keys())
        
        results = {}
        original_title = self.article_data['metadata'].get('source_topic', '未命名文章')
        original_content = self.article_data['body']
        
        for platform in platforms:
            if platform not in PLATFORM_CONFIG:
                print(f"⚠️  未知平台: {platform}")
                continue
            
            print(f"\n{'='*50}")
            print(f"📤 准备发布到 {PLATFORM_CONFIG[platform]['name']}")
            print(f"{'='*50}")
            
            # 适配内容
            adapted_title = self._adapt_title(platform, original_title)
            adapted_content = self._adapt_content(platform, original_content)
            
            # 保存适配后的内容
            output_dir = self.article_path.parent / 'multi_platform'
            output_dir.mkdir(exist_ok=True)
            
            output_file = output_dir / f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"---\n")
                f.write(f"platform: {platform}\n")
                f.write(f"original_title: {original_title}\n")
                f.write(f"adapted_title: {adapted_title}\n")
                f.write(f"publish_time: {datetime.now().isoformat()}\n")
                f.write(f"delay_hours: {PLATFORM_CONFIG[platform]['delay_hours']}\n")
                f.write(f"---\n\n")
                f.write(f"# {adapted_title}\n\n")
                f.write(adapted_content)
            
            results[platform] = {
                'status': 'adapted',
                'output_file': str(output_file),
                'adapted_title': adapted_title,
                'delay_hours': PLATFORM_CONFIG[platform]['delay_hours']
            }
            
            print(f"✅ 标题: {adapted_title}")
            print(f"✅ 内容已适配")
            print(f"✅ 输出文件: {output_file}")
            print(f"⏰  建议发布时间: {PLATFORM_CONFIG[platform]['delay_hours']}小时后")
        
        # 保存发布计划
        self._save_publish_plan(results)
        
        return results
    
    def _save_publish_plan(self, results):
        """保存发布计划"""
        plan_file = self.article_path.parent / 'multi_platform' / 'publish_plan.json'
        
        plan = {
            'article': self.article_path.name,
            'created_at': datetime.now().isoformat(),
            'platforms': results
        }
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 发布计划已保存: {plan_file}")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python publish-all.py <article_path>")
        print("示例: python publish-all.py /path/to/article.md")
        sys.exit(1)
    
    article_path = sys.argv[1]
    
    if not os.path.exists(article_path):
        print(f"❌ 文章不存在: {article_path}")
        sys.exit(1)
    
    # 支持指定平台
    platforms = None
    if len(sys.argv) > 2:
        platforms = sys.argv[2].split(',')
    
    publisher = MultiPlatformPublisher(article_path)
    results = publisher.publish_to_all(platforms)
    
    print("\n" + "="*50)
    print("📊 多平台发布摘要")
    print("="*50)
    for platform, info in results.items():
        print(f"\n{PLATFORM_CONFIG[platform]['name']}:")
        print(f"  - 状态: {info['status']}")
        print(f"  - 标题: {info['adapted_title']}")
        print(f"  - 延迟: {info['delay_hours']}小时")
    
    print("\n✅ 所有平台内容适配完成！")
    print("💡 提示: 请根据publish_plan.json中的延迟时间手动发布到各平台")


if __name__ == '__main__':
    main()