# Wiki Ingest Optimization Changelog

## 优化任务

- **Skill**: wiki-ingest (从 wiki-auto-save 分离)
- **类型**: 工作流优化
- **起始分数**: 60%（内容验证缺失）
- **最终分数**: 95%（添加完整验证）
- **总轮数**: 2
- **问题发现**: 2026-04-12 raw 文件被写入缓存消息

---

## [Round 1] 添加内容验证函数

**改动内容**:
在 `scripts/wiki-curator.py` 中添加 `validate_file_content()` 函数：

```python
def validate_file_content(filepath: Path) -> tuple:
    """验证文件内容是否有效"""
    # 检查文件大小
    if filepath.stat().st_size < 100:
        return False, "文件过小，可能是 placeholder"
    
    # 检查是否是缓存消息
    cache_messages = ["File unchanged since last read", ...]
    if any(msg in content for msg in cache_messages):
        return False, "文件内容是缓存消息"
    
    return True, "验证通过"
```

**测试分数**: 60% → 85%
**效果**: ✅ 保留

---

## [Round 2] 添加移动验证流程

**改动内容**:
添加 `move_to_raw_with_validation()` 函数，移动前后都验证内容。

**测试分数**: 85% → 95%
**效果**: ✅ 保留

---

## 总结

**有效改动**: 
- 添加文件大小检查（<100 bytes 拒绝）
- 添加缓存消息检测
- 移动前后双重验证

**经验教训**:
1. 永远不要信任工具返回的缓存消息
2. 关键操作前后都要验证
3. 文件大小是快速检测指标

---

*Created: 2026-04-12*

---

## [Round 4] 实战优化（2026-04-12）

**改动内容**:
1. 添加实战经验章节，记录批量 ingest 的完整流程
2. 添加文件验证规则（过滤 placeholder、缓存消息）
3. 添加 index.md 更新实现（regex 替换 Statistics）
4. 添加 Pitfall：不要创建重复技能

**测试结果**:
- 处理文件：127 个
- 有效文件：109 个（85.8%）
- 无效文件：18 个（14.2%，被正确过滤）
- 生成页面：36 个 wiki 页面
- index.md：已更新 Statistics（5→14）

**效果**: ✅ 保留
**原因**: 实战验证的有效经验，避免未来重复踩坑

---

*Updated: 2026-04-12*
