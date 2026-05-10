# AkShare 网络问题排查指南

> 问题日期：2026-05-07
> 核心发现：AkShare是MIT开源库，问题不在库本身，而是本地网络/代理配置

## 一、典型错误

```
ProxyError: Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))
HTTPSConnectionPool(host='17.push2.eastmoney.com', port=443): Max retries exceeded
```

## 二、排查步骤

### 步骤1：确认网络连通性

```bash
# DNS解析测试
nslookup 17.push2.eastmoney.com

# ping测试
ping -c 2 17.push2.eastmoney.com
```

如果ping成功但HTTP失败 → 问题在代理配置，不是网络断开

### 步骤2：检查代理环境变量

```bash
# shell环境变量
echo $http_proxy $HTTP_PROXY $https_proxy $HTTPS_PROXY

# Python检测的代理
python3 -c "import os; print(os.environ.get('http_proxy', '未设置'))"
```

**关键发现**：即使shell环境变量未设置，Python requests库可能仍检测到系统级代理配置

### 步骤3：禁用代理（核心解决方案）

```python
import requests
import os

# 方法1：环境变量禁用
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

# 方法2：session禁用代理检测（推荐）
session = requests.Session()
session.trust_env = False  # 关键！不使用环境变量中的代理

# 方法3：添加浏览器headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://quote.eastmoney.com/'
}
resp = session.get(url, headers=headers, timeout=20)
```

### 步骤4：验证API URL

东方财富板块数据API的正确URL：
```
https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2+f:!50&fields=f12,f14,f2,f3,f4
```

**常见错误**：
- URL拼写错误（如 `clist.get` 写成 `clist`）
- 参数缺失导致404

## 三、替代方案

### 方案1：使用pytdx（通达信实时行情）

```python
from pytdx.hq import TdxHq_API

api = TdxHq_API()
if api.connect('218.75.126.9', 7709):  # 已验证可用的服务器
    # 获取行情数据
    data = api.get_security_list(1, 0)  # 深市前100只
    api.disconnect()
```

**优点**：秒级延迟、免费无需token、不依赖HTTP代理

### 方案2：使用Baostock历史数据

```python
import baostock as bs

bs.login()  # 无需注册，自动匿名登录
rs = bs.query_history_k_data_plus("sh.600584", "date,code,open,high,low,close", "2024-01-01", "2026-04-30")
```

**优点**：稳定可靠、不依赖东方财富API

### 方案3：使用第三方平台（聚宽）

登录聚宽 → 行情中心 → 板块排行 → 完整涨跌数据

**优点**：不受本地网络限制（云端访问）

## 四、根本原因分析

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| AkShare报代理错误 | requests检测到系统代理配置 | `session.trust_env = False` |
| 东方财富API返回404 | URL拼写错误或参数缺失 | 验证完整URL |
| 连接被中断 | 公司防火墙/反爬机制 | 添加浏览器headers |
| SSL证书警告 | urllib3版本问题（警告不影响功能） | 忽略警告即可 |

## 五、预防措施

1. **封装请求函数**：所有AkShare调用前禁用代理
2. **备用数据源**：pytdx/Baostock作为备用
## 相关链接

- AkShare文档：https://akshare.readthedocs.io
- pytdx文档：https://github.com/rainx/pytdx
- Baostock文档：http://baostock.com