---
name: macos-fs-timeout-troubleshoot
description: macOS 文件系统访问超时诊断技能 - 当 ls/find 命令卡住时，排查网络挂载、损坏链接、Spotlight索引等问题
tags: [macos, filesystem, timeout, troubleshooting, network-mount]
version: 1.0
created: 2026-04-23
author: Luna
---

# macOS 文件系统访问超时诊断

当 `ls`、`find` 或 Python `os.listdir()` 在特定目录上卡住超时，按以下步骤排查。

---

## 常见原因

| 原因 | 症状 | 诊断命令 |
|------|------|----------|
| 网络挂载 (SMB/AFP) | 访问网络共享目录时卡住 | `mount | grep -E 'smb|afp'` |
| 损坏的符号链接 | 指向不存在的网络位置 | `find -L -type l` |
| Spotlight 索引 | 高 CPU 占用，文件访问慢 | `mdfind -onlyin /path name` |
| Time Machine 备份 | 备份进行时文件系统慢 | `tmutil status` |
| 外置驱动器休眠 | 需唤醒才能访问 | `diskutil list external` |

---

## 诊断流程

### Step 1: 确认系统状态

```bash
# 检查系统负载
uptime

# 检查磁盘空间
df -h /

# 检查是否有网络挂载
mount | grep -E 'smb|afp|nfs'
```

### Step 2: 测试不同层级

```bash
# 先测试父目录
ls ~/Downloads/  # 如果超时，问题在上层

# 测试同层其他目录
ls ~/Documents/ ~/Workspace/

# 测试目标目录是否存在
ls -ld ~/Downloads/software
```

### Step 3: 使用不同方法

```bash
# 方法1: stat 代替 ls（更快）
stat /path/to/directory

# 方法2: Python os.listdir（可能揭示不同错误）
python3 -c "import os; print(os.listdir('/path'))"

# 方法3: 只获取文件数量
find /path -maxdepth 0 -type f | wc -l
```

### Step 4: 检查 Spotlight

```bash
# 检查 Spotlight 是否正在索引
mdutil -s /path

# 如果卡住，可以临时禁用
sudo mdutil -d /path
```

### Step 5: 检查符号链接

```bash
# 查找损坏的符号链接
find ~/Downloads/software -xtype l 2>/dev/null
```

---

## 处理方案

### 网络挂载问题

```bash
# 卸载网络共享
umount /Volumes/sharename

# 或强制卸载
sudo umount -f /Volumes/sharename
```

### Spotlight 问题

```bash
# 重建索引
sudo mdutil -E /path

# 或临时禁用
sudo mdutil -d /path
```

### 损坏链接

```bash
# 删除损坏的符号链接
find /path -xtype l -delete
```

---

## 预防措施

1. **避免符号链接指向网络位置** - 网络断开时会导致超时
2. **定期检查网络挂载状态** - 用 `mount` 命令
3. **大目录可排除 Spotlight 索引** - 提高访问速度

---

## 相关技能

- `systematic-debugging` - 通用调试方法论
- `hermes-gateway-model-errors` - Gateway 错误排查