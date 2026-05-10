# Wiki Frontmatter 格式说明

## Sources 字段格式

Wiki 页面使用 YAML 列表格式存储来源：

```yaml
---
sources:
  - raw/sources/2026-04-24/article-xxx.md
  - raw/notes/开发工具/xxx.md
---
```

**注意**: 是 `sources:`（复数，列表），不是 `source:`（单数）。

## 提取 Source 路径的正则

```python
# 方法1: 匹配 YAML 列表格式
match = re.search(r'sources:\s*\n?\s*-\s*(.+?)(?:\n|$)', content)

# 方法2: 匹配 YAML 行内数组格式
match = re.search(r'sources:\s*\[(.+?)\]', content)
```

## 常见路径格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 相对路径 | `raw/sources/xxx.md` | 标准 |
| 带上级目录 | `../../raw/notes/xxx.md` | 可用但需标准化 |
| 相对路径列表 | `- raw/sources/zhihu/xxx.md` | 多来源页面 |

## 验证原始文件存在

```python
# 检查原始文件
raw_path = KB_ROOT / source
if not raw_path.exists():
    # 尝试移除前缀路径
    clean_source = source.replace('../../', '')
    raw_path = KB_ROOT / clean_source
```
