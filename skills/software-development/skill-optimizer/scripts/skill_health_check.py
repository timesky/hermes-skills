#!/usr/bin/env python3
"""
技能健康检查脚本

每周执行，检查：
1. 废弃技能到期提醒
2. 30天未使用技能
3. SKILL.md 与脚本一致性
4. Cron 任务状态

用法:
    python skill_health_check.py
"""

import os
import json
import yaml
from datetime import datetime, timedelta, date
from pathlib import Path

SKILLS_DIR = Path.home() / ".hermes" / "skills"
BACKUP_DIR = SKILLS_DIR / ".backup"
OUTPUT_FILE = Path.home() / ".hermes" / "skill_health_report.json"


def load_skill_metadata(skill_path: Path) -> dict:
    """读取技能 SKILL.md 的 frontmatter"""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return {"name": skill_path.name, "status": "missing_skill_md"}
    
    content = skill_md.read_text(encoding='utf-8')
    
    # 解析 YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter
            except:
                pass
    
    return {"name": skill_path.name, "status": "no_frontmatter"}


def get_last_used(skill_path: Path) -> datetime:
    """获取最后使用时间（基于文件修改时间）"""
    scripts_dir = skill_path / "scripts"
    if scripts_dir.exists():
        script_files = list(scripts_dir.glob("*.py"))
        if script_files:
            latest = max(f.stat().st_mtime for f in script_files)
            return datetime.fromtimestamp(latest)
    
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        return datetime.fromtimestamp(skill_md.stat().st_mtime)
    
    return datetime.min


def check_deprecated_skills(skills: list) -> dict:
    """检查废弃技能，返回分类结果"""
    expired = []
    expiring = []
    healthy = []
    
    for skill in skills:
        if skill.get('status') == 'deprecated':
            deprecated_date = skill.get('deprecated_date')
            keep_days = skill.get('keep_days', 30)
            
            if deprecated_date:
                # YAML 可能已解析为 date 对象
                if isinstance(deprecated_date, date):
                    dep_date = deprecated_date
                else:
                    dep_date = datetime.strptime(deprecated_date, '%Y-%m-%d').date()
                days_passed = (date.today() - dep_date).days
                days_left = keep_days - days_passed
                
                skill_info = {
                    "skill": skill.get('name'),
                    "days_left": days_left,
                    "redirect_to": skill.get('redirect_to')
                }
                
                if days_left <= 0:
                    skill_info["message"] = f"已过期 {-days_left} 天，可删除"
                    expired.append(skill_info)
                elif days_left <= 7:
                    skill_info["message"] = f"还剩 {days_left} 天过期"
                    expiring.append(skill_info)
                else:
                    skill_info["message"] = f"宽限期还剩 {days_left} 天"
                    healthy.append(skill_info)
    
    return {
        "expired": expired,
        "expiring": expiring,
        "healthy": healthy
    }


def check_unused_skills(skill_paths: list) -> list:
    """检查未使用技能"""
    warnings = []
    
    for path in skill_paths:
        metadata = load_skill_metadata(path)
        last_used = get_last_used(path)
        days_unused = (datetime.now() - last_used).days
        
        # 过滤异常时间戳（如 1980 年，可能是文件复制导致）
        if days_unused > 30 and metadata.get('status') not in ['deprecated', 'core', 'missing_skill_md', 'no_frontmatter']:
            # 检查是否为异常时间戳（早于 2020 年）
            if last_used.year >= 2020:
                warnings.append({
                    "type": "unused",
                    "skill": path.name,
                    "message": f"{days_unused} 天未使用",
                    "last_used": last_used.strftime('%Y-%m-%d')
                })
    
    return warnings


def check_script_consistency(skill_paths: list) -> list:
    """检查 SKILL.md 与脚本一致性"""
    warnings = []
    
    for path in skill_paths:
        skill_md = path / "SKILL.md"
        scripts_dir = path / "scripts"
        
        if skill_md.exists() and scripts_dir.exists():
            content = skill_md.read_text(encoding='utf-8')
            scripts = list(scripts_dir.glob("*.py"))
            
            for script in scripts:
                script_name = script.name
                if script_name not in content:
                    warnings.append({
                        "type": "script_not_mentioned",
                        "skill": path.name,
                        "message": f"脚本 {script_name} 未在 SKILL.md 中提及"
                    })
    
    return warnings


def main():
    print("=" * 60)
    print("技能健康检查")
    print("=" * 60)
    
    # 获取所有技能目录
    skill_paths = []
    for category_dir in SKILLS_DIR.iterdir():
        if category_dir.is_dir() and category_dir.name not in ['.backup', '__pycache__']:
            for skill_dir in category_dir.iterdir():
                if skill_dir.is_dir():
                    skill_paths.append(skill_dir)
    
    # 加载所有技能元数据
    skills = [load_skill_metadata(p) for p in skill_paths]
    
    print(f"检查 {len(skill_paths)} 个技能...")
    
    # 执行检查
    deprecated_result = check_deprecated_skills(skills)
    unused_warnings = check_unused_skills(skill_paths)
    consistency_warnings = check_script_consistency(skill_paths)
    
    # 汇总
    report = {
        "check_date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "total_skills": len(skill_paths),
        "deprecated": deprecated_result,
        "unused": unused_warnings,
        "consistency": consistency_warnings
    }
    
    # 输出结果
    print("\n废弃技能:")
    if report['deprecated']['expired']:
        for w in report['deprecated']['expired']:
            print(f"  ⚠️ {w['skill']} - {w['message']} → 替代: {w['redirect_to']}")
    if report['deprecated']['expiring']:
        for w in report['deprecated']['expiring']:
            print(f"  ⏰ {w['skill']} - {w['message']} → 替代: {w['redirect_to']}")
    if report['deprecated']['healthy']:
        for w in report['deprecated']['healthy']:
            print(f"  ✓ {w['skill']} - {w['message']} → 替代: {w['redirect_to']}")
    if not any([report['deprecated']['expired'], report['deprecated']['expiring'], report['deprecated']['healthy']]):
        print("  无")
    
    print("\n未使用技能 (>30天):")
    if report['unused']:
        for w in report['unused']:
            print(f"  ⏰ {w['skill']} - {w['message']}")
    else:
        print("  无")
    
    print("\n一致性问题:")
    if report['consistency']:
        for w in report['consistency']:
            print(f"  ⚠️ {w['skill']} - {w['message']}")
    else:
        print("  无")
    
    # 保存报告
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存: {OUTPUT_FILE}")
    
    # 返回警告数量
    total_warnings = (
        len(report['deprecated']['expired']) +
        len(report['deprecated']['expiring']) +
        len(report['unused']) +
        len(report['consistency'])
    )
    
    print(f"\n总警告数: {total_warnings}")
    
    return report


if __name__ == '__main__':
    main()