# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
公众号草稿赞赏配置 - 通过 Hermes browser 自动化

赞赏功能无法通过 API 配置，必须通过公众号后台网页操作。

用法（Hermes 执行步骤）:
    1. browser_navigate 到草稿列表
    2. browser_snapshot 找到目标草稿
    3. browser_click 进入编辑
    4. browser_click 赞赏开关
    5. browser_click 保存
"""

DRAFT_LIST_URL = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=list&lang=zh_CN"

# 赞赏配置步骤（供 Hermes agent 参考）
REWARD_CONFIG_STEPS = """
## 赞赏配置步骤（Browser 自动化）

### 前置条件
- 公众号后台已登录（Cookie 有效）
- Hermes browser 工具可用

### 操作流程

**Step 1: 打开草稿列表**
```
browser_navigate(url="https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=list&lang=zh_CN")
```

**Step 2: 获取草稿列表**
```
browser_snapshot(full=True)
```
找到目标文章的编辑按钮（通常在标题右侧）

**Step 3: 点击编辑**
```
browser_click(ref="@eXX")  # 编辑按钮的 ref ID
```

**Step 4: 等待编辑器加载**
```
browser_snapshot()
```

**Step 5: 找赞赏设置**
赞赏开关通常在编辑器右侧的"更多设置"面板
- 点击"赞赏"或"开启赞赏"
- 选择赞赏金额（默认选项即可）

**Step 6: 保存**
```
browser_click(ref="@eXX")  # 保存按钮
```

### 注意事项
- 赞赏功能需要公众号开通赞赏权限（原创功能）
- 草稿配置赞赏后，发布时会自动生效
"""

COLLECTION_CONFIG_STEPS = """
## 合集配置步骤

合集功能同样无法通过 API 配置。

### 操作流程

**Step 1-4: 同赞赏配置流程**

**Step 5: 找合集设置**
- 点击"合集"或"添加到合集"
- 从下拉列表选择合适的合集（如"AI技术"、"行业观察"）

**Step 6: 保存**
"""

def get_reward_instructions():
    """返回赞赏配置步骤"""
    return REWARD_CONFIG_STEPS

def get_collection_instructions():
    """返回合集配置步骤"""
    return COLLECTION_CONFIG_STEPS


if __name__ == '__main__':
    print(REWARD_CONFIG_STEPS)
    print("\n---\n")
    print(COLLECTION_CONFIG_STEPS)