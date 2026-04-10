# OKX MACD Divergence Monitor (GUI 版) 🚀

这是一个基于 Python 开发的 OKX 交易所 MACD 背离实时监控工具。它具备图形化界面，支持自定义交易对、多周期同时监控，并通过钉钉机器人及本地语音实时预警。

## ✨ 功能特性
* **可视化操作**：无需修改代码，直接在界面配置交易对、周期、代理及通知信息。
* **多周期监控**：支持 15m, 1h, 4h, 1d 等多时间维度同步巡检。
* **背离算法**：内置经典底背离（多信号）与顶背离（空信号）检测逻辑。
* **三重预警**：
    * **本地日志**：实时显示巡检状态与发现的信号。
    * **语音播报**：发现信号时自动通过系统语音进行提醒。
    * **钉钉推送**：支持钉钉机器人加签安全推送，实现移动端预警。
* **异步高效**：基于 `asyncio` 与 `ccxt` 异步库，网络请求不阻塞界面。

## 🛠️ 环境要求
* Python 3.8+
* OKX 账户（仅需行情权限，无需 API Key 即可查看公共行情）

## 🚀 快速开始
1. **克隆项目**
   ```bash
   git clone [https://github.com/你的用户名/OKX-MACD-Monitor.git](https://github.com/你的用户名/OKX-MACD-Monitor.git)
   cd OKX-MACD-Monitor
注意：安装依赖

Bash
pip install -r requirements.txt
依赖包包括：ccxt, pandas, pandas_ta, pyttsx3, aiohttp，需要封装打包成exe文件；


使用说明
代理地址：如果你在某些墙国使用，请确保填写正确的本地代理端口（如 Clash 默认为 http://127.0.0.1:7897）。

钉钉配置：在钉钉群机器人设置中开启“加签”校验，并将 Webhook 和 Secret 粘贴至对应输入框。

交易对格式：使用大写，英文逗号分隔，例如 BTC/USDT,ETH/USDT。

⚖️ 免责声明
本工具仅供技术研究使用，不构成任何投资建议。市场有风险，量化需谨慎。
“如果您通过此监控信号抓到了暴涨单，欢迎请作者喝杯咖啡，支持我持续维护算法！”
Donate via Crypto:
USDT (ERC20): 0xB7c7FA777704F3c32DcE578634c4538867e7048A
