#!/usr/bin/env python3
"""
Skill Optimizer - 使用 Autoresearch 方法优化 Hermes Skills

核心公式：Autoresearch = 改一小步 + 测试 + 保留/回退 × N 次

功能：
1. 读取目标 Skill 的 SKILL.md
2. 根据 Checklist 模板评估当前质量
3. 自动进行小改动
4. 测试改动效果
5. 保留有效改动，回退无效改动
6. 生成 Changelog

用法：
python3 skill_optimizer.py --skill wiki-auto-save --checklist content-generation
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path.home() / ".hermes" / "skills"
CHANGELOG_TEMPLATE = """
## [Round {round}] {title}

**改动内容**:
{change}

**测试分数**: {prev_score}% → {new_score}%
**效果**: {effect}
**原因**: {reason}

---
"""


def find_skill(skill_name: str) -> Path:
    """查找技能目录"""
    for category_dir in SKILLS_DIR.iterdir():
        if category_dir.is_dir():
            skill_dir = category_dir / skill_name
            if skill_dir.exists():
                return skill_dir
    raise ValueError(f"Skill '{skill_name}' not found")


def load_checklist(checklist_name: str) -> list:
    """加载 Checklist 模板"""
    checklists = {
        "content-generation": [
            {"id": "title_quality", "question": "标题是否包含具体数字或具体结果？"},
            {"id": "no_buzzword", "question": "是否避免了buzzword？"},
            {"id": "specific_cta", "question": "CTA是否使用了具体的动词短语？"},
            {"id": "pain_point_first", "question": "第一行是否指出了具体痛点？"},
            {"id": "length_control", "question": "总字数是否在指定范围内？"},
        ],
        "tool-calling": [
            {"id": "correct_tool", "question": "是否使用了正确的工具？"},
            {"id": "error_handling", "question": "是否有错误处理机制？"},
            {"id": "correct_output", "question": "输出格式是否正确？"},
            {"id": "pitfall_covered", "question": "是否处理了已知的Pitfall？"},
        ],
        "workflow": [
            {"id": "step_order", "question": "步骤顺序是否正确？"},
            {"id": "verification_step", "question": "关键步骤后是否有验证？"},
            {"id": "fallback_defined", "question": "是否有失败后的处理方案？"},
            {"id": "clear_output", "question": "最终输出是否清晰？"},
        ],
    }
    
    return checklists.get(checklist_name, checklists["content-generation"])


def evaluate_output(output: str, checklist: list) -> dict:
    """评估输出质量"""
    # 这里需要 LLM 来评估，返回模拟结果
    # 实际使用时需要调用 LLM API
    results = {
        "total": len(checklist),
        "passed": 0,
        "failed": [],
        "score": 0
    }
    
    # 模拟评估逻辑（实际需要 LLM）
    buzzwords = ["革命性", "颠覆性", "协同效应", "利用", "解锁"]
    for item in checklist:
        # 简单的关键词检测作为示例
        if item["id"] == "no_buzzword":
            if not any(b in output for b in buzzwords):
                results["passed"] += 1
            else:
                results["failed"].append(item)
        else:
            # 其他项需要 LLM 评估
            results["passed"] += 1  # 假设通过
    
    results["score"] = int(results["passed"] / results["total"] * 100)
    return results


def backup_skill(skill_dir: Path) -> Path:
    """备份原始 Skill"""
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_dir = skill_dir / "backup" / f"v{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        shutil.copy(skill_md, backup_dir / "SKILL.md")
    
    return backup_dir


def create_changelog(skill_dir: Path, optimization_log: list):
    """创建 Changelog"""
    changelog_path = skill_dir / "CHANGELOG.md"
    
    content = f"""# Skill Optimization Changelog

## 优化任务

- Skill: {skill_dir.name}
- 起始分数: {optimization_log[0]['prev_score'] if optimization_log else 'N/A'}%
- 最终分数: {optimization_log[-1]['new_score'] if optimization_log else 'N/A'}%
- 总轮数: {len(optimization_log)}

---

"""
    
    for entry in optimization_log:
        content += CHANGELOG_TEMPLATE.format(**entry)
    
    content += f"""
---

*此 Changelog 由 skill-optimizer 生成*
*Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    
    changelog_path.write_text(content, encoding="utf-8")
    return changelog_path


def main():
    parser = argparse.ArgumentParser(description="Skill Optimizer")
    parser.add_argument("--skill", required=True, help="目标技能名称")
    parser.add_argument("--checklist", default="content-generation", help="Checklist模板")
    parser.add_argument("--max-rounds", type=int, default=10, help="最大优化轮数")
    
    args = parser.parse_args()
    
    print(f"=== Skill Optimizer: {args.skill} ===\n")
    
    # Step 1: 查找 Skill
    try:
        skill_dir = find_skill(args.skill)
        print(f"✅ 找到 Skill: {skill_dir}")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # Step 2: 读取当前 SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print("❌ SKILL.md 不存在")
        return
    
    current_content = skill_md.read_text(encoding="utf-8")
    print(f"✅ 读取 SKILL.md ({len(current_content)} bytes)")
    
    # Step 3: 加载 Checklist
    checklist = load_checklist(args.checklist)
    print(f"✅ 加载 Checklist: {args.checklist} ({len(checklist)} 项)")
    
    # Step 4: 备份原始 Skill
    backup_dir = backup_skill(skill_dir)
    print(f"✅ 备份到: {backup_dir}")
    
    # Step 5: 获取基线分数（需要实际测试）
    print("\n⏳ 获取基线分数...")
    print("   提示: 需要执行实际测试来获取分数")
    print("   此脚本为框架，实际优化需要 LLM 参与")
    
    # 输出指导信息
    print("\n" + "="*50)
    print("优化指导")
    print("="*50)
    print("""
要实际执行优化，请：

1. 加载 skill-optimizer 技能
2. 执行 `run skill-optimizer on {skill_name}`
3. 提供测试输入
4. 等待 LLM 执行优化循环

优化流程：
- 分析当前 Skill 的 SKILL.md
- 运行测试获取基线分数
- 识别失败项，做小改动
- 重新测试，比较分数
- 保留有效改动，回退无效改动
- 生成 CHANGELOG.md

小改动策略：
- 增加规则（解决具体失败项）
- 添加 Pitfall（防止常见错误）
- 禁用模式（消除负面特征）
- 添加范例（让 Skill 看到什么是好）
""")
    
    return {
        "skill": args.skill,
        "skill_dir": str(skill_dir),
        "checklist": args.checklist,
        "backup_dir": str(backup_dir)
    }


if __name__ == "__main__":
    result = main()
    if result:
        print(json.dumps(result, ensure_ascii=False))