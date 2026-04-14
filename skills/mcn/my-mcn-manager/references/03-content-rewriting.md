---
module: 03-content-rewriting
type: reference
source: mcn-content-rewriter (整合)
---

# 模块 3: 内容改写

根据选题生成公众号文章（1500-2000 字）。

---

## 文章要求

| 项目 | 要求 | 验证 |
|------|------|------|
| 字数 | 1500-2000 字 | 发布前必须验证 |
| 结构 | 5-8 段落 + 开头 + 总结 | 合理分段 |
| 标题 | 15-25 字 | 吸引力公式 |
| 摘要 | ≤120 字 | 用于公众号概述 |
| 配图 | 3-5 张专属 | 与主题强相关 |

---

## 执行流程

### 1. 标题生成（5 选 1）

```python
def generate_titles(topic: str) -> list:
    """生成 5 个候选标题"""
    
    formulas = [
        '数字 + 结果 + 方法',
        '人群 + 痛点 + 方案',
        '对比 + 反差 + 原因',
        '悬念 + 揭秘 + 价值',
        '热点 + 观点 + 引发思考'
    ]
    
    # 调用 LLM 生成
    prompt = f"""
根据话题生成 5 个公众号标题：
话题：{topic}

使用不同公式：
1. 数字 + 结果 + 方法（如：3 个方法让存款翻倍）
2. 人群 + 痛点 + 方案（如：30 岁没存款？这个计划适合你）
3. 对比 + 反差 + 原因
4. 悬念 + 揭秘 + 价值
5. 热点 + 观点 + 引发思考

输出 JSON 格式。
"""
    return llm_generate(prompt)
```

### 2. 标题评估

```python
def evaluate_title(title: str, topic: str) -> dict:
    """评估标题"""
    
    score = 0
    reasons = []
    
    # 长度检查（15-25 字）
    length = len(title)
    if 15 <= length <= 25:
        score += 20
        reasons.append(f"长度合适 ({length}字)")
    
    # 吸引力词
    attract_words = ['揭秘', '背后', '如何', '为什么', '方法']
    for word in attract_words:
        if word in title:
            score += 10
    
    # 数字元素
    if re.search(r'\d+', title):
        score += 15
    
    # 负面词扣分
    negative_words = ['失败', '惨', '悲剧']
    for word in negative_words:
        if word in title:
            score -= 20
    
    return {'title': title, 'score': score, 'reasons': reasons}
```

### 3. 正文撰写

```python
def write_article(topic: str, title: str, style: str = 'professional') -> str:
    """撰写文章"""
    
    prompt = f"""
请根据话题生成公众号文章：

话题：{topic}
标题：{title}
风格：{style}

要求：
1. 开头 300 字内抓住读者（场景引入式）
2. 正文 1500-2000 字，分 5-8 个要点
3. 结尾总结升华 + 互动引导
4. 避免敏感内容，保持客观中立
5. 去 AI 化：用口语化表达，添加个人观点

输出格式：
# {title}

[正文内容]
"""
    return llm_generate(prompt)
```

### 4. 字数验证与补充

```python
def verify_word_count(content: str) -> dict:
    """验证字数"""
    
    text_only = re.sub(r'[^\w]', '', content)
    word_count = len(text_only)
    
    if word_count < 1500:
        return {'status': 'insufficient', 'count': word_count, 'need': 1500 - word_count}
    elif word_count > 2000:
        return {'status': 'excessive', 'count': word_count, 'excess': word_count - 2000}
    else:
        return {'status': 'valid', 'count': word_count}

def supplement_article(content: str, need_words: int, topic: str) -> str:
    """补充文章内容"""
    
    prompt = f"""
当前文章字数不足，需要补充约{need_words}字。

主题：{topic}

请补充以下内容（选择适合的角度）：
1. 相关案例或数据
2. 行业背景分析
3. 技术细节说明
4. 实操建议

要求：与原文风格一致，内容有价值。
"""
    supplement = llm_generate(prompt)
    return content + "\n\n" + supplement
```

### 5. 品牌名称替换

```python
def replace_brand_names(content: str) -> str:
    """替换品牌名称"""
    
    replacements = {
        '豆包': '某 AI',
        '字节跳动': '平台',
        '莫氏鸡煲': '网红店',
        # 根据具体文章添加
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    return content
```

---

## 输出格式

```markdown
---
created: 2026-04-14 18:00
source_topic: 原话题
source_url: 原链接
platform: wechat-mp
status: draft
style: professional
word_count: 1856
---

# 文章标题

[正文内容 1500-2000 字]

## 标签建议
#AI #技术 #干货
```

---

## Pitfalls

1. **字数验证必须执行**：低于 1500 字禁止发布
2. **自动补充机制**：字数不够自动补充（最多 2 次）
3. **品牌名称替换**：避免品牌风险和地域侵权
4. **标题长度**：公众号标题建议 15-25 字
5. **特殊字符**：标题不能包含「」【】等符号

---

*整合自：mcn-content-rewriter*
