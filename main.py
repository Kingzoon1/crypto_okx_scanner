import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import pyttsx3
import time
import hmac
import hashlib
import base64
import urllib.parse
import aiohttp
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import threading
from datetime import datetime, timedelta

# ================= 核心监控引擎 =================
class OKXMonitorEngine:
    def __init__(self, ui_callback):
        self.ui_callback = ui_callback
        self.running = False
        self.exchange = None
        
        try:
            self.speech_engine = pyttsx3.init()
            self.speech_engine.setProperty('rate', 150)
        except:
            self.speech_engine = None

    def log(self, message):
        self.ui_callback(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

    async def send_dingding(self, content, config):
        if not config['webhook'] or "access_token" not in config['webhook']:
            return
            
        timestamp = str(round(time.time() * 1000))
        secret_enc = config['secret'].encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, config['secret'])
        hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{config['webhook']}&timestamp={timestamp}&sign={sign}"
        
        data = {"msgtype": "text", "text": {"content": f"【MACD背离预警】\n{content}"}}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data, proxy=config['proxy']) as resp:
                    return await resp.json()
            except Exception as e:
                self.log(f"钉钉发送失败: {e}")

    def check_div(self, df):
        results = []
        def get_segments(is_pos):
            segs, curr = [], []
            for i in range(len(df)-1, 0, -1):
                val = df['hist'].iloc[i]
                if (val > 0 if is_pos else val < 0): curr.append(i)
                else:
                    if len(curr) >= 2: segs.append(curr); curr = []
                if len(segs) >= 2: break
            return segs

        # 经典背离逻辑
        bull = get_segments(False)
        if len(bull) >= 2:
            p_near, m_near = df['low'].iloc[bull[0]].min(), df['hist'].iloc[bull[0]].min()
            p_far, m_far = df['low'].iloc[bull[1]].min(), df['hist'].iloc[bull[1]].min()
            if p_near < p_far and m_near > m_far: results.append("底背离(多)")
        
        bear = get_segments(True)
        if len(bear) >= 2:
            p_near, m_near = df['high'].iloc[bear[0]].max(), df['hist'].iloc[bear[0]].max()
            p_far, m_far = df['high'].iloc[bear[1]].max(), df['hist'].iloc[bear[1]].max()
            if p_near > p_far and m_near < m_far: results.append("顶背离(空)")
        return results

    async def fetch_and_analyze(self, symbol, tf, config):
        try:
            bars = await self.exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
            macd = df.ta.macd()
            # 兼容不同版本的 pandas_ta 列名
            hist_col = [c for c in macd.columns if 'MACDh' in c][0]
            df['hist'] = macd[hist_col]
            
            divs = self.check_div(df)
            if divs:
                for d in divs:
                    msg = f"{symbol} | {tf} | {d}"
                    self.log(f"🔥 发现信号: {msg}")
                    await self.send_dingding(msg, config)
                    if self.speech_engine:
                        threading.Thread(target=lambda: (self.speech_engine.say(msg), self.speech_engine.runAndWait()), daemon=True).start()
            else:
                self.log(f"巡检完毕: {symbol}({tf}) 无信号")
        except Exception as e:
            self.log(f"行情获取失败({symbol}): 网络请求超时")

    async def worker(self, tf_str, mins, config):
        while self.running:
            now = datetime.now()
            # 逻辑：在每个周期的开始+2秒执行
            remaining = (mins * 60) - ((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() % (mins * 60))
            await asyncio.sleep(remaining + 2)
            
            if not self.running: break
            tasks = [self.fetch_and_analyze(s, tf_str, config) for s in config['symbols']]
            await asyncio.gather(*tasks)

    async def run_main(self, config):
        self.running = True
        self.exchange = ccxt.okx({'aiohttp_proxy': config['proxy'], 'enableRateLimit': True})
        self.log(">>> 系统开始运行...")
        
        tasks = []
        for tf, mins in config['tfs_map'].items():
            tasks.append(self.worker(tf, mins, config))
        
        await asyncio.gather(*tasks)

# ================= UI 界面类 =================
class MonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OKX 策略监控系统 Pro")
        self.geometry("800x700")
        self.engine = None
        self.loop = None
        self.setup_ui()

    def setup_ui(self):
        # 样式配置
        style = ttk.Style()
        style.configure("TButton", padding=5)
        
        # 1. 交易所配置
        frame_base = ttk.LabelFrame(self, text=" 基础配置 ", padding=10)
        frame_base.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_base, text="交易对:").grid(row=0, column=0, sticky="w")
        self.ent_symbols = ttk.Entry(frame_base, width=60)
        self.ent_symbols.insert(0, "BTC/USDT,ETH/USDT,XAUT/USDT")
        self.ent_symbols.grid(row=0, column=1, columnspan=3, pady=5, padx=5)
        ttk.Label(frame_base, text="(英文逗号隔开)").grid(row=0, column=4, sticky="w")

        ttk.Label(frame_base, text="监控周期:").grid(row=1, column=0, sticky="w")
        self.ent_tfs = ttk.Entry(frame_base, width=60)
        self.ent_tfs.insert(0, "15m 1h 4h")
        self.ent_tfs.grid(row=1, column=1, columnspan=3, pady=5, padx=5)
        ttk.Label(frame_base, text="(空格隔开: 15m 1h 4h 1d)").grid(row=1, column=4, sticky="w")

        ttk.Label(frame_base, text="代理地址:").grid(row=2, column=0, sticky="w")
        self.ent_proxy = ttk.Entry(frame_base, width=60)
        self.ent_proxy.insert(0, "http://127.0.0.1:7897")
        self.ent_proxy.grid(row=2, column=1, columnspan=3, pady=5, padx=5)

        # 2. 通知配置
        frame_notify = ttk.LabelFrame(self, text=" 钉钉推送配置 ", padding=10)
        frame_notify.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_notify, text="Webhook:").grid(row=0, column=0, sticky="w")
        self.ent_webhook = ttk.Entry(frame_notify, width=70)
        self.ent_webhook.insert(0, "在此处粘贴完整的钉钉Webhook链接")
        self.ent_webhook.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(frame_notify, text="Secret:").grid(row=1, column=0, sticky="w")
        self.ent_secret = ttk.Entry(frame_notify, width=70, show="*")
        self.ent_secret.insert(0, "在此处粘贴加签密钥")
        self.ent_secret.grid(row=1, column=1, pady=5, padx=5)

        # 3. 控制按钮
        frame_ctrl = tk.Frame(self)
        frame_ctrl.pack(pady=10)

        self.btn_start = tk.Button(frame_ctrl, text="▶ 启动系统", bg="#2ecc71", fg="white", 
                                  font=("Microsoft YaHei", 10, "bold"), width=20, command=self.on_start)
        self.btn_start.pack(side="left", padx=20)

        self.btn_stop = tk.Button(frame_ctrl, text="■ 停止运行", bg="#e74c3c", fg="white", 
                                 font=("Microsoft YaHei", 10, "bold"), width=20, state="disabled", command=self.on_stop)
        self.btn_stop.pack(side="left", padx=20)

        # 4. 日志显示
        self.log_area = scrolledtext.ScrolledText(self, bg="#2c3e50", fg="#ecf0f1", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, padx=15, pady=10)

    def write_log(self, msg):
        self.log_area.insert(tk.END, msg)
        self.log_area.see(tk.END)

    def on_start(self):
        # 解析周期映射
        raw_tfs = self.ent_tfs.get().split()
        full_map = {
            '15m': 15, '30m': 30, '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720, '1d': 1440
        }
        active_tfs = {tf: full_map[tf] for tf in raw_tfs if tf in full_map}
        
        if not active_tfs:
            messagebox.showerror("错误", "请输入有效的周期 (例如: 15m 1h)")
            return

        config = {
            'symbols': [s.strip().upper() for s in self.ent_symbols.get().split(",") if s.strip()],
            'tfs_map': active_tfs,
            'proxy': self.ent_proxy.get(),
            'webhook': self.ent_webhook.get(),
            'secret': self.ent_secret.get()
        }

        self.engine = OKXMonitorEngine(self.write_log)
        
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.engine.run_main(config))
            except Exception as e:
                self.write_log(f"停止运行: {e}\n")

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

    def on_stop(self):
        if self.engine:
            self.engine.running = False
            self.write_log("!!! 收到停止指令，等待当前轮次结束...\n")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

if __name__ == "__main__":
    app = MonitorApp()
    app.mainloop()
