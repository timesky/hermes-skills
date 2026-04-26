#!/usr/bin/env python3
"""抓取原文和竞品数据 - 供闭环分析使用"""

import json
import os
import yaml
import argparse
import requests
import re
from datetime import datetime
from pathlib import Path

KB_ROOT = config.get('paths', {}).get('kb_root', os.path.expanduser("~/Documents/My_Obsidian"))
MCN_ROOT = f"{KB_ROOT}/mcn"
MCN_CONFIG = os.path.expanduser("~/.hermes/mcn_config.yaml")
WEB_FETCHER_API = "http://localhost:9234"

# 从外部配置读取 KB_ROOT（可选）
if os.path.exists(MCN_CONFIG):
    try:
        with open(MCN_CONFIG) as f:
            config = yaml.safe_load(f)
        kb_root = config.get("paths", {}).get("kb_root", KB_ROOT)
        KB_ROOT = kb_root
        MCN_ROOT = f"{KB_ROOT}/mcn"
    except:
        pass


def slugify(text: str) -> str:
    """将文本转换为目录名安全的 slug"""
    s = re.sub(r'[<>:"/\\|?*！？；：，。（）「」『』【】\n\r\t]', '', text)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s[:50].strip('-')


def fetch_page_via_web_fetcher(url: str) -> dict:
    """通过 web-fetcher API 抓取页面"""
    try:
        response = requests.post(
            f"{WEB_FETCHER_API}/fetch",
            json={"url": url, "format": "markdown"},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


def parse_zhihu_metrics(html_content: str) -> dict:
    """解析知乎文章的互动数据"""
    metrics = {
        "read_count": None,
        "like_count": None,
        "comment_count": None,
        "favorite_count": None
    }
    
    # 知乎点赞数通常在 ContentItem-actions 中
    like_match = re.search(r'(\d+)\s*赞同', html_content)
    if like_match:
        metrics["like_count"] = int(like_match.group(1))
    
    comment_match = re.search(r'(\d+)\s*评论', html_content)
    if comment_match:
        metrics["comment_count"] = int(comment_match.group(1))
    
    return metrics


def parse_weibo_metrics(html_content: str) -> dict:
    """解析微博的互动数据"""
    metrics = {
        "read_count": None,
        "like_count": None,
        "comment_count": None,
        "share_count": None
    }
    
    # 微博点赞/转发/评论
    like_match = re.search(r'点赞[：:]\s*(\d+)', html_content)
    if like_match:
        metrics["like_count"] = int(like_match.group(1))
    
    return metrics


def detect_platform(url: str) -> str:
    """检测 URL 所属平台"""
    if "zhihu.com" in url:
        return "zhihu"
    elif "weibo.com" in url or "weibo.cn" in url:
        return "weibo"
    elif "mp.weixin.qq.com" in url:
        return "wechat"
    elif "36kr.com" in url:
        return "36kr"
    elif "douyin.com" in url:
        return "douyin"
    else:
        return "unknown"


def fetch_source_article(url: str, title: str) -> dict:
    """抓取原文完整数据"""
    platform = detect_platform(url)
    
    print(f"  抓取原文: {url} ({platform})")
    
    # 通过 web-fetcher 抓取
    result = fetch_page_via_web_fetcher(url)
    
    if "error" in result:
        return {
            "title": title,
            "url": url,
            "platform": platform,
            "error": result["error"],
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    content = result.get("content", "")
    
    # 解析互动数据
    metrics = {}
    if platform == "zhihu":
        metrics = parse_zhihu_metrics(content)
    elif platform == "weibo":
        metrics = parse_weibo_metrics(content)
    
    # 提取关键词
    keywords = extract_keywords(title, content)
    
    # 提取关键段落（前 500 字）
    snippets = []
    paragraphs = content.split("\n\n")
    for p in paragraphs[:3]:
        if len(p) > 50:
            snippets.append(p[:200])
    
    return {
        "title": title,
        "url": url,
        "platform": platform,
        "content": content[:10000],  # 截取前 10000 字
        "content_length": len(content),
        "metrics": metrics,
        "keywords": keywords,
        "snippets": snippets,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def extract_keywords(title: str, content: str) -> list:
    """提取关键词"""
    # 技术词库
    tech_words = [
        'AI', '机器人', '算力', '芯片', '模型', 'GPU', 'LLM', 'GPT',
        '英伟达', '苹果', '小米', '华为', 'OpenAI', 'Anthropic',
        '自动驾驶', '大模型', '深度学习', '具身智能', 'HBM'
    ]
    
    keywords = []
    text = title + " " + content[:1000]
    
    for word in tech_words:
        if word in text or word.lower() in text.lower():
            keywords.append(word)
    
    # 提取中文关键词（简单版：2-4字的词）
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
    for w in chinese_words:
        if w not in keywords and w not in ['时候', '大家', '问题', '方法', '因为']:
            keywords.append(w)
    
    return keywords[:10]


def fetch_competitors(topic_keywords: list, platform: str = "zhihu") -> dict:
    """搜索同话题竞品文章"""
    search_keyword = topic_keywords[0] if topic_keywords else ""
    
    print(f"  搜索竞品: {search_keyword}")
    
    competitors = {
        "topic": search_keyword,
        "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "articles": []
    }
    
    # 知乎搜索
    if platform in ["zhihu", "all"]:
        zhihu_search_url = f"https://www.zhihu.com/search?type=content&q={search_keyword}"
        result = fetch_page_via_web_fetcher(zhihu_search_url)
        
        if "content" in result:
            # 解析搜索结果（简化版：提取标题）
            titles = re.findall(r'###\s*(.+)', result["content"])
            for i, title in enumerate(titles[:5]):
                competitors["articles"].append({
                    "title": title.strip(),
                    "platform": "zhihu",
                    "metrics": {},
                    "style_tags": [],
                    "title_type": classify_title_type(title)
                })
    
    return competitors


def classify_title_type(title: str) -> str:
    """分类标题类型"""
    if re.search(r'\d+', title):
        return "数据钩子"
    elif "?" in title or "？" in title:
        return "疑问钩子"
    elif "为什么" in title or "原因" in title:
        return "解释钩子"
    elif "争议" in title or "反驳" in title:
        return "争议钩子"
    else:
        return "普通"


def save_source_data(topic_idx: int, date: str, source_data: dict, competitors_data: dict):
    """保存原文和竞品数据"""
    topic_dir = Path(MCN_ROOT) / "topic" / date / "sources" / f"topic-{topic_idx}"
    topic_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存原文数据
    source_file = topic_dir / "source.json"
    with open(source_file, "w", encoding="utf-8") as f:
        json.dump(source_data, f, indent=2, ensure_ascii=False)
    
    # 保存竞品数据
    competitors_file = topic_dir / "competitors.json"
    with open(competitors_file, "w", encoding="utf-8") as f:
        json.dump(competitors_data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ 已保存到: {topic_dir}")


def fetch_topic_sources(date: str, topic_idx: int = None):
    """抓取指定日期的选题原文数据"""
    
    # 读取选题推荐
    recommend_file = Path(MCN_ROOT) / "topic" / date / "analysis.json"
    if not recommend_file.exists():
        print(f"❌ 选题数据不存在: {recommend_file}")
        return
    
    with open(recommend_file, encoding="utf-8") as f:
        analysis_data = json.load(f)
    
    recommendations = analysis_data.get("recommendations", [])
    
    if topic_idx:
        # 只抓取指定选题
        topics = [recommendations[topic_idx - 1]] if topic_idx <= len(recommendations) else []
    else:
        # 抓取所有 Top 5
        topics = recommendations[:5]
    
    print(f"抓取 {len(topics)} 个选题的原文数据...")
    
    for i, topic in enumerate(topics, 1):
        idx = topic_idx if topic_idx else i
        print(f"\n[{idx}] {topic.get('title', '未知标题')}")
        
        url = topic.get("url", "")
        title = topic.get("title", "")
        
        if not url:
            print(f"  ⚠️ 无 URL，跳过")
            continue
        
        # 抓取原文
        source_data = fetch_source_article(url, title)
        
        # 抓取竞品
        keywords = source_data.get("keywords", [])
        competitors_data = fetch_competitors(keywords)
        
        # 保存
        save_source_data(idx, date, source_data, competitors_data)


def main():
    parser = argparse.ArgumentParser(description="抓取原文和竞品数据")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--topic", type=int, help="只抓取指定选题 (1-5)")
    
    args = parser.parse_args()
    
    fetch_topic_sources(args.date, args.topic)


if __name__ == "__main__":
    main()