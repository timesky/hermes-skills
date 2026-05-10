# KB_ROOT Path Detection

脚本默认路径可能不匹配实际知识库位置。以下是可靠的检测模式：

## 常见知识库路径

| 用户 | KB_ROOT |
|------|---------|
| hy_timesky | `/Users/hy_timesky/Documents/My_Obsidian` |
| timesky (backup) | `/Users/timesky/backup/知识库-Obsidian` |

## 检测策略

```python
def get_kb_root():
    """自动检测 KB_ROOT"""
    import os
    from pathlib import Path
    
    # 1. 环境变量优先
    kb_root = os.environ.get('KB_ROOT')
    if kb_root:
        return Path(kb_root)
    
    # 2. 尝试常见路径
    candidates = [
        Path.home() / "Documents" / "My_Obsidian",
        Path.home() / "backup" / "知识库-Obsidian",
    ]
    for c in candidates:
        if c.exists():
            return c
    
    # 3. 报错
    raise ValueError("无法检测 KB_ROOT，请设置环境变量: export KB_ROOT=/path/to/kb")
```

## 脚本修复

现有 `batch_ingest.py` 默认路径：
```python
KB_ROOT = Path(os.environ.get('KB_ROOT', "/Users/timesky/backup/知识库-Obsidian"))
```

建议修改为动态检测版本（见上方 `get_kb_root()`）。

## 使用方式

```bash
# 方法1: 设置环境变量
export KB_ROOT=/Users/hy_timesky/Documents/My_Obsidian

# 方法2: 脚本中传入
python3 scripts/batch_ingest.py --kb-root /Users/hy_timesky/Documents/My_Obsidian
```