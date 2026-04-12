#!/usr/bin/env python3
"""
Hermes Agent 完整备份脚本

备份内容：
1. 配置文件：config.yaml, .env, SOUL.md, auth.json
2. 自研技能：识别并备份用户开发的技能
3. 记忆：MEMORY.md, USER.md
4. 自定义脚本：scripts/ 目录
5. Cron 任务：cron/ 目录

自研技能识别规则：
- 技能目录中有 extension/ 或 server/ 子目录（如 web-fetcher）
- 技能 SKILL.md 中 author 字段是用户名（非 builtin）
- 技能目录中有 scripts/ 子目录且有自定义 Python 脚本
- 技能在 predefined CUSTOM_SKILLS 列表中

备份目录：/Users/timesky/backup/hermes_agent_bak/YYYY-MM-DD/
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# 配置
HERMES_DIR = Path.home() / ".hermes"
BACKUP_ROOT = Path("/Users/timesky/backup/hermes_agent_bak")
LOG_FILE = HERMES_DIR / "logs" / "backup.log"

# 预定义的自研技能列表（可扩展）
CUSTOM_SKILLS = [
    "web/web-fetcher",
    "note-taking/wiki-auto-save",
    "devops/hermes-backup",
    # MCN 相关技能
    "mcn/mcn-workflow",
    "mcn/mcn-topic-selector",
    "mcn/mcn-hotspot-aggregator",
    "mcn/mcn-content-rewriter",
    "mcn/mcn-wechat-publisher",
]

# 官方技能特征（用于排除）
BUILTIN_MARKERS = [
    "builtin",
    "hermes-agent",
    "nousresearch",
]


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    
    print(log_entry)


def get_file_hash(filepath: Path) -> str:
    """计算文件 MD5 哈希"""
    if not filepath.exists():
        return ""
    return hashlib.md5(filepath.read_bytes()).hexdigest()


def is_custom_skill(skill_path: Path) -> bool:
    """
    判断是否是自研技能
    
    规则：
    1. 在预定义列表中
    2. 有 extension/ 或 server/ 目录（Chrome 扩展等）
    3. SKILL.md 中 author 是用户名（非 builtin）
    4. 有自定义 scripts 目录（不含官方模板）
    """
    skill_name = skill_path.relative_to(HERMES_DIR / "skills")
    
    # 规则1: 在预定义列表中
    if str(skill_name) in CUSTOM_SKILLS:
        return True
    
    # 规则2: 有 extension/ 或 server/ 目录
    if (skill_path / "extension").exists() or (skill_path / "server").exists():
        return True
    
    # 规则3: 检查 SKILL.md 中的 author
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        # 检查是否是官方技能
        if any(marker in content.lower() for marker in BUILTIN_MARKERS):
            return False
        # 检查 author 字段
        if "author:" in content:
            for line in content.split("\n"):
                if line.startswith("author:") or "author:" in line:
                    author = line.split("author:")[-1].strip().lower()
                    if author and author not in ["builtin", "nous", "hermes"]:
                        return True
    
    # 规则4: 有自定义 scripts 目录
    scripts_dir = skill_path / "scripts"
    if scripts_dir.exists():
        # 检查是否有自定义 Python 脚本
        for py_file in scripts_dir.glob("*.py"):
            # 排除官方模板脚本
            if py_file.name not in ["example.py", "template.py", "__init__.py"]:
                return True
    
    return False


def scan_custom_skills() -> list:
    """扫描所有自研技能"""
    skills_dir = HERMES_DIR / "skills"
    custom_skills = []
    
    if not skills_dir.exists():
        return custom_skills
    
    # 遍历所有分类目录
    for category_dir in skills_dir.iterdir():
        if not category_dir.is_dir():
            continue
        
        # 遍历分类下的技能
        for skill_dir in category_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            if is_custom_skill(skill_dir):
                skill_name = f"{category_dir.name}/{skill_dir.name}"
                custom_skills.append({
                    "name": skill_name,
                    "path": str(skill_dir),
                    "files": sum(1 for _ in skill_dir.rglob("*") if _.is_file())
                })
    
    return custom_skills


def backup_config(backup_dir: Path, manifest: dict) -> bool:
    """备份配置文件"""
    config_files = [
        ("config.yaml", HERMES_DIR / "config.yaml"),
        (".env", HERMES_DIR / ".env"),
        ("SOUL.md", HERMES_DIR / "SOUL.md"),
        ("auth.json", HERMES_DIR / "auth.json"),
    ]
    
    success = True
    manifest["config"] = {}
    
    for name, src in config_files:
        if src.exists():
            dst = backup_dir / name
            shutil.copy2(src, dst)
            manifest["config"][name] = {
                "hash": get_file_hash(dst),
                "size": dst.stat().st_size
            }
            log(f"✅ {name} → {dst.name} ({dst.stat().st_size} bytes)")
        else:
            log(f"⚠️ {name} 不存在，跳过", "WARN")
    
    return success


def backup_memories(backup_dir: Path, manifest: dict) -> bool:
    """备份记忆文件"""
    memories_dir = HERMES_DIR / "memories"
    dst_dir = backup_dir / "memories"
    
    if not memories_dir.exists():
        log("⚠️ memories 目录不存在", "WARN")
        return True
    
    shutil.copytree(memories_dir, dst_dir, dirs_exist_ok=True)
    
    manifest["memories"] = {}
    for md_file in dst_dir.glob("*.md"):
        manifest["memories"][md_file.name] = {
            "hash": get_file_hash(md_file),
            "size": md_file.stat().st_size
        }
    
    file_count = sum(1 for _ in dst_dir.rglob("*") if _.is_file())
    log(f"✅ memories → {file_count} 文件")
    
    return True


def backup_scripts(backup_dir: Path, manifest: dict) -> bool:
    """备份自定义脚本"""
    scripts_dir = HERMES_DIR / "scripts"
    dst_dir = backup_dir / "scripts"
    
    if not scripts_dir.exists():
        log("⚠️ scripts 目录不存在", "WARN")
        return True
    
    shutil.copytree(scripts_dir, dst_dir, dirs_exist_ok=True)
    
    manifest["scripts"] = {}
    for py_file in dst_dir.glob("*.py"):
        manifest["scripts"][py_file.name] = {
            "hash": get_file_hash(py_file),
            "size": py_file.stat().st_size
        }
    
    file_count = sum(1 for _ in dst_dir.rglob("*") if _.is_file())
    log(f"✅ scripts → {file_count} 文件")
    
    return True


def backup_cron(backup_dir: Path, manifest: dict) -> bool:
    """备份 Cron 任务配置"""
    cron_dir = HERMES_DIR / "cron"
    dst_dir = backup_dir / "cron"
    
    if not cron_dir.exists():
        log("⚠️ cron 目录不存在", "WARN")
        return True
    
    shutil.copytree(cron_dir, dst_dir, dirs_exist_ok=True)
    
    manifest["cron"] = {}
    for job_file in dst_dir.glob("*.json"):
        manifest["cron"][job_file.name] = {
            "hash": get_file_hash(job_file)
        }
    
    file_count = sum(1 for _ in dst_dir.rglob("*") if _.is_file())
    log(f"✅ cron → {file_count} 文件")
    
    return True


def backup_skills(backup_dir: Path, manifest: dict) -> bool:
    """备份自研技能"""
    custom_skills = scan_custom_skills()
    
    if not custom_skills:
        log("⚠️ 未发现自研技能", "WARN")
        manifest["skills"] = {"custom": [], "installed": []}
        return True
    
    dst_dir = backup_dir / "skills"
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    manifest["skills"] = {"custom": [], "installed": []}
    
    for skill in custom_skills:
        skill_path = Path(skill["path"])
        skill_dst = dst_dir / skill["name"]
        
        shutil.copytree(skill_path, skill_dst, dirs_exist_ok=True)
        
        manifest["skills"]["custom"].append({
            "name": skill["name"],
            "files": skill["files"],
            "hash": get_file_hash(skill_dst / "SKILL.md") if (skill_dst / "SKILL.md").exists() else ""
        })
        
        log(f"✅ 技能 {skill['name']} → {skill['files']} 文件")
    
    # 记录所有已安装技能列表（用于恢复时重装）
    installed_skills = []
    skills_dir = HERMES_DIR / "skills"
    if skills_dir.exists():
        for category_dir in skills_dir.iterdir():
            if category_dir.is_dir():
                for skill_dir in category_dir.iterdir():
                    if skill_dir.is_dir():
                        installed_skills.append(f"{category_dir.name}/{skill_dir.name}")
    
    manifest["skills"]["installed"] = installed_skills
    
    log(f"✅ 共备份 {len(custom_skills)} 个自研技能，记录 {len(installed_skills)} 个已安装技能")
    
    return True


def generate_restore_guide(backup_dir: Path, manifest: dict):
    """生成恢复指南"""
    guide = backup_dir / "restore_guide.md"
    
    content = f"""# Hermes Agent 恢复指南

备份时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}
备份版本: {manifest["version"]}

---

## 快速恢复（本机）

```bash
# 恢复配置文件
cp {backup_dir}/config.yaml ~/.hermes/
cp {backup_dir}/.env ~/.hermes/
cp {backup_dir}/SOUL.md ~/.hermes/
cp {backup_dir}/auth.json ~/.hermes/

# 恢复记忆
cp -r {backup_dir}/memories ~/.hermes/

# 恢复脚本
cp -r {backup_dir}/scripts ~/.hermes/

# 恢复 Cron 任务
cp -r {backup_dir}/cron ~/.hermes/

# 恢复自研技能
cp -r {backup_dir}/skills/* ~/.hermes/skills/

# 重启 Gateway
hermes gateway restart
```

---

## 新机器迁移

### 1. 安装 Hermes Agent

```bash
pip install hermes-agent
hermes setup
```

### 2. 复制备份文件

```bash
# 从备份位置复制
scp -r {backup_dir} ~/.hermes/
```

### 3. 恢复配置和记忆

```bash
cd ~/.hermes
cp {backup_dir.name}/config.yaml .
cp {backup_dir.name}/.env .
cp {backup_dir.name}/SOUL.md .
cp {backup_dir.name}/auth.json .
cp -r {backup_dir.name}/memories .
cp -r {backup_dir.name}/scripts .
cp -r {backup_dir.name}/cron .
```

### 4. 恢复自研技能

```bash
mkdir -p ~/.hermes/skills
cp -r {backup_dir.name}/skills/* ~/.hermes/skills/
```

### 5. 重装开源技能

以下技能需要重新安装：

```bash
# 查看原机器的技能列表
cat {backup_dir}/manifest.json | jq '.skills.installed'

# 安装需要的技能
hermes skills install <skill-name>
```

### 6. 环境检测

```bash
# 检查 Python 版本
python3 --version  # 需要 3.10+

# 检查 Hermes
hermes --version

# 检查常用工具
curl --version
jq --version
git --version
```

---

## 自研技能列表

本次备份的自研技能：

"""
    
    for skill in manifest["skills"]["custom"]:
        content += f"- `{skill['name']}` ({skill['files']} 文件)\n"
    
    content += f"""

---

## 已安装技能列表

恢复后需要重装的技能：

"""
    
    for skill in manifest["skills"]["installed"]:
        if skill not in [s["name"] for s in manifest["skills"]["custom"]]:
            content += f"- `{skill}`\n"
    
    content += """

---

## 环境依赖检测清单

| 依赖 | 命令 | 说明 |
|------|------|------|
| Python 3.10+ | `python3 --version` | Hermes 运行基础 |
| hermes CLI | `hermes --version` | 主程序 |
| curl | `curl --version` | 技能常用工具 |
| jq | `jq --version` | JSON 处理 |
| git | `git --version` | GitHub 技能 |
| ffmpeg | `ffmpeg -version` | 音视频技能（可选） |
| pandoc | `pandoc --version` | 文档转换（可选） |

---

*此指南由 backup_hermes.py 自动生成*
"""
    
    guide.write_text(content, encoding="utf-8")
    log(f"✅ restore_guide.md 已生成")


def cleanup_old_backups(keep_days: int = 7):
    """清理超过指定天数的备份"""
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    cleaned = 0
    for item in BACKUP_ROOT.iterdir():
        if item.is_dir() and item.name not in ["latest"]:
            try:
                date_str = item.name
                item_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if item_date < cutoff_date:
                    shutil.rmtree(item)
                    log(f"🗑️ 清理旧备份: {item.name}")
                    cleaned += 1
            except ValueError:
                # 不是日期格式的目录，跳过
                pass
    
    if cleaned:
        log(f"清理了 {cleaned} 个旧备份（保留 {keep_days} 天）")


def update_latest_link(backup_dir: Path):
    """更新 latest 软链接"""
    latest_link = BACKUP_ROOT / "latest"
    
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    
    # macOS 使用绝对路径创建软链接
    os.symlink(str(backup_dir.absolute()), str(latest_link.absolute()))
    log(f"✅ latest → {backup_dir.name}")


def main():
    """执行备份"""
    log("=== 开始 Hermes Agent 备份 ===")
    
    # 创建备份目录
    timestamp = datetime.now().strftime("%Y-%m-%d")
    backup_dir = BACKUP_ROOT / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    log(f"备份目录: {backup_dir}")
    
    # 初始化 manifest
    manifest = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "hermes_dir": str(HERMES_DIR),
        "backup_dir": str(backup_dir),
        "config": {},
        "memories": {},
        "scripts": {},
        "cron": {},
        "skills": {"custom": [], "installed": []}
    }
    
    # 执行备份
    backup_config(backup_dir, manifest)
    backup_memories(backup_dir, manifest)
    backup_scripts(backup_dir, manifest)
    backup_cron(backup_dir, manifest)
    backup_skills(backup_dir, manifest)
    
    # 生成 manifest.json
    manifest_file = backup_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"✅ manifest.json 已生成")
    
    # 生成恢复指南
    generate_restore_guide(backup_dir, manifest)
    
    # 更新 latest 软链接
    update_latest_link(backup_dir)
    
    # 清理旧备份
    cleanup_old_backups(keep_days=7)
    
    # 统计
    total_files = sum(1 for _ in backup_dir.rglob("*") if _.is_file())
    total_size = sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file())
    
    log(f"=== 备份完成 ===")
    log(f"总文件数: {total_files}")
    log(f"总大小: {total_size / 1024:.1f} KB")
    log(f"备份位置: {backup_dir}")
    
    return {
        "success": True,
        "backup_dir": str(backup_dir),
        "total_files": total_files,
        "total_size_kb": round(total_size / 1024, 1),
        "custom_skills": len(manifest["skills"]["custom"]),
        "installed_skills": len(manifest["skills"]["installed"])
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False))