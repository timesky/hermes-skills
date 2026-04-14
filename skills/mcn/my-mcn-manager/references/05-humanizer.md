---
module: 05-humanizer
type: reference
source: humanizer-zh (第三方技能引用)
---

# 模块 5: 去 AI 化处理

去除文章中的 AI 写作痕迹，提升阅读体验。

---

## 调用方式

```python
# 方法 1：直接调用 humanizer-zh 技能
from humanizer_zh import humanize

humanized_text = humanize(original_text)
score = evaluate_humanization(humanized_text)
```

```python
# 方法 2：通过脚本调用
import subprocess

result = subprocess.run(
    ["python", "scripts/humanize-article.py", "--input", "article.md"],
    capture_output=True, text=True
)
```

---

## 评分标准（满分 50）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| 删除模板词 | 10 分 | 去除"综上所述""值得注意的是" |
| 口语化表达 | 10 分 | 使用"其实""说白了" |
| 个人观点 | 10 分 | 添加"我觉得""在我看来" |
| 句子节奏 | 10 分 | 长短句交替 |
| 行业黑话 | 10 分 | 使用圈内术语/流行梗 |

**阈值**：≥ 45 分合格，低于则重新处理（最多 2 次）

---

## 去 AI 化检查清单

### 删除词汇

- ❌ "作为...的证明"
- ❌ "此外"
- ❌ "首先/其次/最后"（三段式）
- ❌ 过度使用破折号
- ❌ 模糊归因（"相关研究表明"）

### 添加元素

- ✅ 个人观点（"我个人认为"）
- ✅ 口语化（"说白了""你想想"）
- ✅ 反问句（"你说这事儿离谱不？"）
- ✅ 行业术语/黑话
- ✅ 具体细节（数据、案例）

---

## 执行流程

```python
def humanize_article(article_path: str, max_attempts: int = 2) -> tuple:
    """去 AI 化处理"""
    
    content = open(article_path, encoding='utf-8').read()
    
    for attempt in range(max_attempts):
        # 调用 humanizer-zh
        humanized = humanize(content)
        
        # 评分
        score = evaluate_score(humanized)
        
        if score >= 45:
            print(f"✓ 去 AI 化成功：{score}/50")
            return humanized, score
        else:
            print(f"⚠️ 评分不足：{score}/50，重试第{attempt+2}次")
            content = humanized
    
    print(f"⚠️ 最终评分：{score}/50，建议人工审核")
    return humanized, score
```

---

## Pitfalls

1. **评分阈值**：≥ 45 分才能发布
2. **重试次数**：最多 2 次
3. **保留原意**：去 AI 化不能改变文章核心观点
4. **适度口语**：不要过度口语化影响专业性

---

*引用：humanizer-zh (第三方技能)*
