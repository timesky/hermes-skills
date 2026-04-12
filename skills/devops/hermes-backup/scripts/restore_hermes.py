#!/usr/bin/env python3
"""
Hermes Agent 恢复脚本

功能：
1. 本机恢复：从备份恢复配置、记忆、技能等
2. 新机器迁移：在全新环境恢复 Hermes
3. 环境检测：检查依赖项是否满足
4. 技能恢复：单独恢复自研技能

用法：
python3 restore_hermes.py --backup latest
python3 restore_hermes.py --backup YYYY-MM-DD --migrate
python3 restore_hermes.py --check-env
python3 restore_hermes.py --skills-only
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# 配置
HERMES_DIR = Path.home() / ".hermes"
BACKUP_ROOT = Path("/Users/timesky/backup/hermes_agent_bak")
LOG_FILE = HERMES_DIR / "logs" / "restore.log"

# 环境依赖检测清单
ENV_CHECKS = [
    {"name": "Python 3.10+", "cmd": "python3 --version", "required": True},
    {"name": "Hermes CLI", "cmd": "hermes --version", "required": True},
    {"name": "curl", "cmd": "curl --version", "required": True},
    {"name": "jq", "cmd": "jq --version", "required": False},
    {"name": "git", "cmd": "git --version", "required": False},
    {"name": "ffmpeg", "cmd": "ffmpeg -version", "required": False},
    {"name": "pandoc", "cmd": "pandoc --version", "required": False},
    {"name": "pyfiglet", "cmd": "pip show pyfiglet", "required": False},
    {"name": "faster-whisper", "cmd": "pip show faster-whisper", "required": False},
]


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    
    print(log_entry)


def get_backup_dir(backup_name: str) -> Path:
    """获取备份目录路径"""
    if backup_name == "latest":
        backup_link = BACKUP_ROOT / "latest"
        if backup_link.is_symlink():
            return Path(os.readlink(str(backup_link)))
        else:
            # 找最新的备份
            backups = sorted(BACKUP_ROOT.iterdir(), reverse=True)
            for b in backups:
                if b.is_dir() and b.name not in ["latest"]:
                    return b
            raise ValueError("未找到任何备份")
    else:
        backup_dir = BACKUP_ROOT / backup_name
        if not backup_dir.exists():
            raise ValueError(f"备份目录不存在: {backup_dir}")
        return backup_dir


def check_environment() -> dict:
    """检查环境依赖"""
    log("=== 环境检测 ===")
    
    results = []
    all_ok = True
    
    for check in ENV_CHECKS:
        try:
            result = subprocess.run(
                check["cmd"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            ok = result.returncode == 0
            version = result.stdout.strip().split("\n")[0] if ok else "未安装"
            
            if not ok and check["required"]:
                all_ok = False
                log(f"❌ {check['name']}: {version} (必需)", "ERROR")
            elif ok:
                log(f"✅ {check['name']}: {version}")
            else:
                log(f"⚠️ {check['name']}: {version} (可选)", "WARN")
            
            results.append({
                "name": check["name"],
                "ok": ok,
                "version": version,
                "required": check["required"]
            })
        except Exception as e:
            log(f"❌ {check['name']}: 检测失败 - {e}", "ERROR")
            results.append({
                "name": check["name"],
                "ok": False,
                "version": "检测失败",
                "required": check["required"]
            })
            if check["required"]:
                all_ok = False
    
    return {
        "all_ok": all_ok,
        "results": results
    }


def restore_config(backup_dir: Path, migrate: bool = False) -> bool:
    """恢复配置文件"""
    config_files = ["config.yaml", ".env", "SOUL.md", "auth.json"]
    
    success = True
    
    for name in config_files:
        src = backup_dir / name
        dst = HERMES_DIR / name
        
        if not src.exists():
            log(f"⚠️ {name} 不存在于备份中", "WARN")
            continue
        
        if migrate and dst.exists():
            log(f"⚠️ {name} 已存在，跳过（迁移模式）", "WARN")
            continue
        
        # 备份现有文件
        if dst.exists() and not migrate:
            backup_existing = dst.with_suffix(".bak")
            shutil.copy2(dst, backup_existing)
            log(f"📦 {name} 已备份到 {backup_existing.name}")
        
        shutil.copy2(src, dst)
        log(f"✅ {name} 已恢复")
    
    return success


def restore_memories(backup_dir: Path, migrate: bool = False) -> bool:
    """恢复记忆"""
    src_dir = backup_dir / "memories"
    dst_dir = HERMES_DIR / "memories"
    
    if not src_dir.exists():
        log("⚠️ memories 不存在于备份中", "WARN")
        return True
    
    # 迁移模式下，只复制不存在的文件
    if migrate:
        for md_file in src_dir.glob("*.md"):
            dst_file = dst_dir / md_file.name
            if not dst_file.exists():
                shutil.copy2(md_file, dst_file)
                log(f"✅ memories/{md_file.name} 已恢复")
    else:
        # 完全恢复
        if dst_dir.exists():
            # 备份现有记忆
            backup_existing = dst_dir.with_name("memories.bak")
            if backup_existing.exists():
                shutil.rmtree(backup_existing)
            shutil.copytree(dst_dir, backup_existing)
            log(f"📦 memories 已备份到 memories.bak")
        
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        file_count = sum(1 for _ in dst_dir.glob("*.md"))
        log(f"✅ memories 已恢复 ({file_count} 文件)")
    
    return True


def restore_scripts(backup_dir: Path, migrate: bool = False) -> bool:
    """恢复脚本"""
    src_dir = backup_dir / "scripts"
    dst_dir = HERMES_DIR / "scripts"
    
    if not src_dir.exists():
        log("⚠️ scripts 不存在于备份中", "WARN")
        return True
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制脚本
    for py_file in src_dir.glob("*.py"):
        dst_file = dst_dir / py_file.name
        if migrate and dst_file.exists():
            log(f"⚠️ scripts/{py_file.name} 已存在，跳过", "WARN")
            continue
        shutil.copy2(py_file, dst_file)
        log(f"✅ scripts/{py_file.name} 已恢复")
    
    return True


def restore_cron(backup_dir: Path, migrate: bool = False) -> bool:
    """恢复 Cron 任务"""
    src_dir = backup_dir / "cron"
    dst_dir = HERMES_DIR / "cron"
    
    if not src_dir.exists():
        log("⚠️ cron 不存在于备份中", "WARN")
        return True
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制任务配置
    for job_file in src_dir.glob("*.json"):
        dst_file = dst_dir / job_file.name
        if migrate and dst_file.exists():
            log(f"⚠️ cron/{job_file.name} 已存在，跳过", "WARN")
            continue
        shutil.copy2(job_file, dst_file)
        log(f"✅ cron/{job_file.name} 已恢复")
    
    log("💡 提示: 恢复后需要重启 Gateway: hermes gateway restart")
    
    return True


def restore_skills(backup_dir: Path, migrate: bool = False) -> bool:
    """恢复自研技能"""
    src_dir = backup_dir / "skills"
    dst_dir = HERMES_DIR / "skills"
    
    if not src_dir.exists():
        log("⚠️ skills 不存在于备份中", "WARN")
        return True
    
    # 读取 manifest
    manifest_file = backup_dir / "manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        custom_skills = manifest.get("skills", {}).get("custom", [])
        
        log(f"发现 {len(custom_skills)} 个自研技能待恢复")
    
    # 恢复自研技能
    for skill_dir in src_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        
        # 处理嵌套目录结构（如 web/web-fetcher）
        for category_dir in skill_dir.iterdir():
            if category_dir.is_dir():
                skill_name = f"{skill_dir.name}/{category_dir.name}"
                skill_dst = dst_dir / skill_dir.name / category_dir.name
                
                if migrate and skill_dst.exists():
                    log(f"⚠️ 技能 {skill_name} 已存在，跳过", "WARN")
                    continue
                
                skill_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(category_dir, skill_dst, dirs_exist_ok=True)
                file_count = sum(1 for _ in skill_dst.rglob("*") if _.is_file())
                log(f"✅ 技能 {skill_name} 已恢复 ({file_count} 文件)")
    
    return True


def restore_all(backup_dir: Path, migrate: bool = False) -> bool:
    """完整恢复"""
    log(f"=== 开始恢复 Hermes Agent ===")
    log(f"备份来源: {backup_dir}")
    log(f"恢复模式: {'迁移' if migrate else '本机恢复'}")
    
    # 检查 manifest
    manifest_file = backup_dir / "manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        log(f"备份时间: {manifest.get('timestamp', '未知')}")
    
    # 执行恢复
    restore_config(backup_dir, migrate)
    restore_memories(backup_dir, migrate)
    restore_scripts(backup_dir, migrate)
    restore_cron(backup_dir, migrate)
    restore_skills(backup_dir, migrate)
    
    log("=== 恢复完成 ===")
    log("💡 提示:")
    log("   1. 检查配置: hermes config show")
    log("   2. 重启 Gateway: hermes gateway restart")
    log("   3. 检查技能: hermes skills list")
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Hermes Agent 恢复脚本")
    parser.add_argument("--backup", default="latest", help="备份名称（latest 或 YYYY-MM-DD）")
    parser.add_argument("--migrate", action="store_true", help="新机器迁移模式")
    parser.add_argument("--check-env", action="store_true", help="只检查环境")
    parser.add_argument("--skills-only", action="store_true", help="只恢复技能")
    
    args = parser.parse_args()
    
    # 环境检测
    if args.check_env:
        result = check_environment()
        if result["all_ok"]:
            log("✅ 所有必需依赖已安装")
        else:
            log("❌ 部分必需依赖缺失，请先安装")
        return result
    
    # 获取备份目录
    try:
        backup_dir = get_backup_dir(args.backup)
    except ValueError as e:
        log(f"❌ {e}", "ERROR")
        return {"success": False, "error": str(e)}
    
    # 只恢复技能
    if args.skills_only:
        log("=== 只恢复技能 ===")
        restore_skills(backup_dir, args.migrate)
        return {"success": True}
    
    # 完整恢复
    restore_all(backup_dir, args.migrate)
    
    return {"success": True, "backup_dir": str(backup_dir)}


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else "")